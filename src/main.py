import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
# Import db instance from the central models init
from src.models import db 
# Import the new blueprints
from src.routes.admin import admin_bp
from src.routes.client import client_bp
# Import models to ensure tables are created
from src.models.service import Service
from src.models.appointment import Appointment

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'a_strong_secret_key_here' # Changed default key

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:{os.getenv('DB_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'mydb')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db with app
db.init_app(app)

# Register blueprints
app.register_blueprint(admin_bp, url_prefix='/admin/api') # Prefix for admin routes
app.register_blueprint(client_bp, url_prefix='/api')     # Prefix for client routes

# Create database tables within app context
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created (if they didn't exist).")

# Serve static files (like index.html, css, js) and handle client-side routing
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    # If path points to an existing file in static folder, serve it
    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        # Serve specific files like CSS, JS, images
        if os.path.isfile(os.path.join(static_folder_path, path)):
             return send_from_directory(static_folder_path, path)
        # If it's a directory, potentially serve index.html within it or deny
        # For simplicity, we'll fall back to the main index.html

    # Otherwise, serve the main index.html (for SPA routing)
    index_path = os.path.join(static_folder_path, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(static_folder_path, 'index.html')
    else:
        # If no index.html exists at all, return an error
        return "index.html not found in static folder", 404

if __name__ == '__main__':
    # Make sure to run with debug=False in production
    app.run(host='0.0.0.0', port=5000, debug=True) 

