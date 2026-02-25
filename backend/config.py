import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ai_tracker.db")
    # SQLAlchemy expects postgresql:// not postgres://
    SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    # Encryption key for API keys at rest (Fernet)
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    # Background job interval (minutes)
    SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))

    # SendGrid (email notifications)
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@ai-cost-tracker.com")
    SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "AI Cost Tracker")

    # Notification rate limits (max per channel per hour; defaults match spec)
    NOTIFICATION_MAX_PER_HOUR_EMAIL = int(os.getenv("NOTIFICATION_MAX_PER_HOUR_EMAIL", "10"))
    NOTIFICATION_MAX_PER_HOUR_SLACK = int(os.getenv("NOTIFICATION_MAX_PER_HOUR_SLACK", "20"))


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///ai_tracker.db"
    ).replace("postgres://", "postgresql://", 1)


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
