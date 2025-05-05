# src/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

class Config:
    """Base configuration variables."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-generate-a-real-secret-key' # Generate one!
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Twilio Credentials (Load from environment)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url or 'sqlite:///dev.db' # Default to SQLite if URL not set

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:' # Use in-memory SQLite for tests

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Ensure DATABASE_URL is set in production environment
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Add any production specific initializations here (e.g., logging)


# Dictionary to access configs by name
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}