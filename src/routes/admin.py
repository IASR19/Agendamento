from flask import Blueprint, request, jsonify
from src.models import db
from src.models.service import Service

admin_bp = Blueprint("admin", __name__)

# Rota para adicionar um novo serviço (POST)
# Rota para listar todos os serviços (GET)
@admin_bp.route("/services", methods=["POST", "GET"])
def handle_services():
    if request.method == "POST":
        data = request.get_json()
        if not data or not data.get("name") or not data.get("duration") or data.get("price") is None:
            return jsonify({"error": "Missing data for service"}), 400
        
        existing_service = Service.query.filter_by(name=data["name"]).first()
        if existing_service:
            return jsonify({"error": "Service name already exists"}), 409

        new_service = Service(
            name=data["name"],
            duration=data["duration"],
            price=data["price"]
        )
        db.session.add(new_service)
        db.session.commit()
        return jsonify({"message": "Service added successfully", "service_id": new_service.id}), 201

    elif request.method == "GET":
        services = Service.query.all()
        return jsonify([{
            "id": service.id,
            "name": service.name,
            "duration": service.duration,
            "price": service.price
        } for service in services])

# Rota para obter, atualizar ou deletar um serviço específico
@admin_bp.route("/services/<int:service_id>", methods=["GET", "PUT", "DELETE"])
def handle_service(service_id):
    service = Service.query.get_or_404(service_id)

    if request.method == "GET":
        return jsonify({
            "id": service.id,
            "name": service.name,
            "duration": service.duration,
            "price": service.price
        })

    elif request.method == "PUT":
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided for update"}), 400
        
        # Check for duplicate name if name is being updated
        if "name" in data and data["name"] != service.name:
             existing_service = Service.query.filter(Service.name == data["name"], Service.id != service_id).first()
             if existing_service:
                 return jsonify({"error": "Service name already exists"}), 409

        service.name = data.get("name", service.name)
        service.duration = data.get("duration", service.duration)
        service.price = data.get("price", service.price)
        db.session.commit()
        return jsonify({"message": "Service updated successfully"})

    elif request.method == "DELETE":
        # Add check here if appointments depend on this service before deleting
        db.session.delete(service)
        db.session.commit()
        return jsonify({"message": "Service deleted successfully"})

# Rota para listar agendamentos (pode ser expandida depois)
@admin_bp.route("/appointments", methods=["GET"])
def get_appointments():
    # Import Appointment model here to avoid circular dependency at top level if needed
    from src.models.appointment import Appointment 
    appointments = Appointment.query.order_by(Appointment.appointment_time.asc()).all()
    return jsonify([{
        "id": app.id,
        "client_name": app.client_name,
        "client_phone": app.client_phone,
        "service_id": app.service_id,
        "service_name": app.service.name, # Assumes relationship is set up correctly
        "appointment_time": app.appointment_time.isoformat(),
        "created_at": app.created_at.isoformat()
    } for app in appointments])

