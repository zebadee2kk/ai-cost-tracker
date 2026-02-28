import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import get_config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config=None):
    app = Flask(__name__)

    # Load config
    app.config.from_object(config or get_config())

    # Ensure log directory exists
    os.makedirs("logs", exist_ok=True)

    # Logging
    logging.basicConfig(
        level=getattr(logging, app.config["LOG_LEVEL"], logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, origins=app.config["CORS_ORIGINS"])

    # Validate encryption key is set
    if not app.config.get("ENCRYPTION_KEY"):
        app.logger.warning(
            "ENCRYPTION_KEY is not set — API key encryption will fail at runtime. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    # Register blueprints
    from routes.auth import auth_bp
    from routes.accounts import accounts_bp
    from routes.services import services_bp
    from routes.usage import usage_bp
    from routes.alerts import alerts_bp
    from routes.notifications import notifications_bp
    from routes.analytics import analytics_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(accounts_bp, url_prefix="/api/accounts")
    app.register_blueprint(services_bp, url_prefix="/api/services")
    app.register_blueprint(usage_bp, url_prefix="/api/usage")
    app.register_blueprint(alerts_bp, url_prefix="/api/alerts")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    # Start notification dispatcher (every 5 min) – skipped during testing
    if not app.config.get("TESTING"):
        from jobs.notification_processor import start_notification_processor
        start_notification_processor(app)

    # Health check
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "env": app.config["FLASK_ENV"]})

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": "Invalid token", "reason": reason}), 401

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Authorization required", "reason": reason}), 401

    # Generic error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Internal server error")
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
