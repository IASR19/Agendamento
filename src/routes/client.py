from flask import Blueprint, request, jsonify
from src.models import db
from src.models.service import Service
from src.models.appointment import Appointment
from datetime import datetime, timedelta, time
import pytz # For timezone handling

client_bp = Blueprint("client", __name__)

# Define working hours and lunch break (Brasilia Timezone)
brasilia_tz = pytz.timezone("America/Sao_Paulo")
WORK_START_TIME = time(8, 0, tzinfo=brasilia_tz)
WORK_END_TIME = time(17, 0, tzinfo=brasilia_tz)
LUNCH_START_TIME = time(11, 45, tzinfo=brasilia_tz)
LUNCH_END_TIME = time(12, 0, tzinfo=brasilia_tz)
WORKING_DAYS = [0, 1, 2, 3, 4, 5] # Monday to Saturday

# Rota para listar serviços disponíveis para clientes
@client_bp.route("/services", methods=["GET"])
def list_available_services():
    services = Service.query.all()
    return jsonify([{
        "id": service.id,
        "name": service.name,
        "duration": service.duration,
        "price": service.price
    } for service in services])

# Rota para obter horários disponíveis para um serviço em uma data específica
@client_bp.route("/available_slots", methods=["GET"])
def get_available_slots():
    service_id = request.args.get("service_id", type=int)
    date_str = request.args.get("date") # Expected format: YYYY-MM-DD

    if not service_id or not date_str:
        return jsonify({"error": "Missing service_id or date"}), 400

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    service = Service.query.get(service_id)
    if not service:
        return jsonify({"error": "Service not found"}), 404

    # Check if the selected date is a working day (Mon-Sat)
    if selected_date.weekday() not in WORKING_DAYS:
        return jsonify({"available_slots": []}) # Not a working day
        
    # Check if the selected date is in the past (using Brasilia time)
    now_brasilia = datetime.now(brasilia_tz).date()
    if selected_date < now_brasilia:
         return jsonify({"available_slots": []}) # Date is in the past

    service_duration = timedelta(minutes=service.duration)
    available_slots = []

    # Get existing appointments for the selected date
    start_of_day = brasilia_tz.localize(datetime.combine(selected_date, time(0, 0)))
    end_of_day = brasilia_tz.localize(datetime.combine(selected_date, time(23, 59, 59)))
    existing_appointments = Appointment.query.filter(
        Appointment.appointment_time >= start_of_day,
        Appointment.appointment_time <= end_of_day
    ).all()

    booked_slots = []
    for app in existing_appointments:
        app_service = Service.query.get(app.service_id)
        if app_service:
             app_duration = timedelta(minutes=app_service.duration)
             booked_slots.append((app.appointment_time, app.appointment_time + app_duration))

    # Iterate through possible time slots for the day
    current_time = brasilia_tz.localize(datetime.combine(selected_date, WORK_START_TIME.replace(tzinfo=None)))
    end_work_time = brasilia_tz.localize(datetime.combine(selected_date, WORK_END_TIME.replace(tzinfo=None)))
    lunch_start = brasilia_tz.localize(datetime.combine(selected_date, LUNCH_START_TIME.replace(tzinfo=None)))
    lunch_end = brasilia_tz.localize(datetime.combine(selected_date, LUNCH_END_TIME.replace(tzinfo=None)))

    while current_time + service_duration <= end_work_time:
        slot_start = current_time
        slot_end = current_time + service_duration
        
        # Check if slot is in the past (relative to current time in Brasilia)
        if selected_date == now_brasilia and slot_start < datetime.now(brasilia_tz):
            current_time += timedelta(minutes=15) # Check next 15-min interval
            continue

        # Check for overlap with lunch break
        is_during_lunch = not (slot_end <= lunch_start or slot_start >= lunch_end)
        if is_during_lunch:
            current_time = lunch_end # Skip to after lunch
            continue

        # Check for overlap with existing appointments
        is_booked = False
        for booked_start, booked_end in booked_slots:
            if not (slot_end <= booked_start or slot_start >= booked_end):
                is_booked = True
                # Move current_time to the end of the conflicting appointment to check next slot
                current_time = booked_end 
                break # Exit inner loop, check next potential start time
        
        if not is_booked:
            # Check again if the adjusted current_time is still within working hours
            if current_time + service_duration <= end_work_time:
                 # Check again for lunch overlap after potential adjustment from booking conflict
                 slot_start = current_time # Re-evaluate slot_start
                 slot_end = current_time + service_duration
                 is_during_lunch_after_adjust = not (slot_end <= lunch_start or slot_start >= lunch_end)
                 if not is_during_lunch_after_adjust:
                     available_slots.append(slot_start.isoformat())
                     current_time += timedelta(minutes=15) # Check next 15-min interval for start time
                 else:
                     current_time = lunch_end # Skip to after lunch if adjustment caused lunch conflict
            else:
                 break # No more possible slots within working hours
        # If it was booked, current_time was already advanced, so loop continues
        elif not is_booked: # This else corresponds to the original is_booked check
             # This case should not be reached if is_booked was true, but kept for clarity
             current_time += timedelta(minutes=15) # Check next 15-min interval

    return jsonify({"available_slots": available_slots})

# Rota para criar um novo agendamento
@client_bp.route("/appointments", methods=["POST"])
def create_appointment():
    data = request.get_json()
    if not data or not data.get("client_name") or not data.get("client_phone") or not data.get("service_id") or not data.get("appointment_time"):
        return jsonify({"error": "Missing required appointment data"}), 400

    service_id = data["service_id"]
    service = Service.query.get(service_id)
    if not service:
        return jsonify({"error": "Service not found"}), 404

    try:
        # Ensure the incoming time has timezone info or assume Brasilia
        appointment_dt = datetime.fromisoformat(data["appointment_time"])
        if appointment_dt.tzinfo is None:
             appointment_dt = brasilia_tz.localize(appointment_dt)
        else:
             appointment_dt = appointment_dt.astimezone(brasilia_tz)
             
    except ValueError:
        return jsonify({"error": "Invalid appointment_time format. Use ISO format (e.g., YYYY-MM-DDTHH:MM:SS+HH:MM)"}), 400

    # --- Re-validate Slot Availability --- 
    # (Crucial to prevent double booking if multiple requests come simultaneously)
    selected_date = appointment_dt.date()
    
    # Check working day & past date
    if selected_date.weekday() not in WORKING_DAYS:
        return jsonify({"error": "Selected date is not a working day"}), 400
    now_brasilia = datetime.now(brasilia_tz)
    if appointment_dt < now_brasilia:
         return jsonify({"error": "Selected time slot is in the past"}), 400

    service_duration = timedelta(minutes=service.duration)
    slot_start = appointment_dt
    slot_end = appointment_dt + service_duration

    # Check working hours
    if not (slot_start.time() >= WORK_START_TIME and slot_end.time() <= WORK_END_TIME):
         # Allow slot_end.time() to be exactly WORK_END_TIME
         if not (slot_start.time() >= WORK_START_TIME and slot_end.time() == WORK_END_TIME and slot_end.second == 0 and slot_end.microsecond == 0):
             return jsonify({"error": "Appointment time is outside working hours"}), 400

    # Check lunch break
    lunch_start_dt = brasilia_tz.localize(datetime.combine(selected_date, LUNCH_START_TIME.replace(tzinfo=None)))
    lunch_end_dt = brasilia_tz.localize(datetime.combine(selected_date, LUNCH_END_TIME.replace(tzinfo=None)))
    is_during_lunch = not (slot_end <= lunch_start_dt or slot_start >= lunch_end_dt)
    if is_during_lunch:
        return jsonify({"error": "Appointment time conflicts with lunch break"}), 400

    # Check existing appointments
    existing_appointments = Appointment.query.filter(
        Appointment.appointment_time >= slot_start - timedelta(minutes=service.duration -1), # Check potential overlaps
        Appointment.appointment_time < slot_end
    ).all()
    
    is_booked = False
    for app in existing_appointments:
        app_service = Service.query.get(app.service_id)
        if app_service:
            app_start = app.appointment_time
            app_end = app.appointment_time + timedelta(minutes=app_service.duration)
            # Check for overlap: (StartA < EndB) and (EndA > StartB)
            if slot_start < app_end and slot_end > app_start:
                is_booked = True
                break
                
    if is_booked:
        return jsonify({"error": "Selected time slot is no longer available"}), 409 # Conflict
    # --- End Re-validation ---

    new_appointment = Appointment(
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        service_id=service_id,
        appointment_time=appointment_dt
    )
    db.session.add(new_appointment)
    db.session.commit()

    return jsonify({
        "message": "Appointment created successfully",
        "appointment_id": new_appointment.id,
        "client_name": new_appointment.client_name,
        "service_name": service.name,
        "appointment_time": new_appointment.appointment_time.isoformat()
    }), 201

