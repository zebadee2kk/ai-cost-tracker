from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app import db
from models.service import Service

services_bp = Blueprint("services", __name__)


@services_bp.route("", methods=["GET"])
@jwt_required()
def list_services():
    services = Service.query.all()
    return jsonify({"services": [s.to_dict() for s in services]}), 200


@services_bp.route("/<int:service_id>", methods=["GET"])
@jwt_required()
def get_service(service_id):
    service = db.session.get(Service, service_id)
    if not service:
        return jsonify({"error": "Service not found."}), 404
    return jsonify({"service": service.to_dict()}), 200


@services_bp.route("/<int:service_id>/pricing", methods=["PUT"])
@jwt_required()
def update_pricing(service_id):
    service = db.session.get(Service, service_id)
    if not service:
        return jsonify({"error": "Service not found."}), 404

    data = request.get_json() or {}
    pricing = data.get("pricing_model")
    if not isinstance(pricing, dict):
        return jsonify({"error": "pricing_model must be a JSON object."}), 400

    service.pricing_model = pricing
    db.session.commit()
    return jsonify({"service": service.to_dict()}), 200
