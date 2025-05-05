from . import db  # Import db from the models package's __init__.py
from datetime import datetime
from .service import Service # Import Service model for relationship

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(150), nullable=False)
    client_phone = db.Column(db.String(20), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=False)
    appointment_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship("Service", backref=db.backref("appointments", lazy=True))

    def __repr__(self):
        return f"<Appointment {self.client_name} at {self.appointment_time}>"
