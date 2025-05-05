# src/__init__.py
import os
from flask import Flask
from .models import db # Import db instance from models
from .config import config # Import config dictionary

def create_app(config_name=None):
    """Application Factory Function"""
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name]) # Load config from config.py
    config[config_name].init_app(app) # Perform any init specific to the config

    print(f"INFO: Initializing DB with URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    db.init_app(app) # Initialize SQLAlchemy with this app instance

    # --- Register Blueprints ---
    from .webhook import webhook_bp # Import blueprint
    app.register_blueprint(webhook_bp) # Register the webhook blueprint

    # You could register other blueprints here (e.g., for an admin interface)
    # from .admin import admin_bp
    # app.register_blueprint(admin_bp, url_prefix='/admin')

    # --- Add a simple root route ---
    @app.route('/')
    def home():
        try:
            # Simple DB check
            user_count = db.session.query(db.func.count(User.id)).scalar()
            return f"LightHouse Chatbot Flask server is running! Config: {config_name}. DB Connected. User count: {user_count}"
        except Exception as e:
            print(f"DB Connection check failed: {e}")
            return f"LightHouse Chatbot Flask server is running! Config: {config_name}. ERROR: Could not connect to DB."

    # --- Utility function to create tables (can be called via Flask shell) ---
    @app.cli.command('create-db')
    def create_db_command():
        """Creates the database tables."""
        print("Creating database tables...")
        db.create_all()
        print("Database tables created.")

    return app

# Import User model here AFTER db is defined, for convenience if needed elsewhere,
# but models are primarily used within command handlers/routes.
from .models import User