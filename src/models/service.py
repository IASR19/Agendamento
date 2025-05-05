from . import db  # Import db from the models package's __init__.py

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Service {self.name}>'
