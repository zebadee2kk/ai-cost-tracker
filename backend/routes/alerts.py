from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from models.account import Account
from models.alert import Alert, ALERT_TYPES, NOTIFICATION_METHODS
from utils.validators import require_fields

alerts_bp = Blueprint("alerts", __name__)


def _user_account_ids(user_id: int) -> list[int]:
    return [
        a.id for a in Account.query.filter_by(user_id=user_id).with_entities(Account.id)
    ]


@alerts_bp.route("", methods=["GET"])
@jwt_required()
def list_alerts():
    user_id = int(get_jwt_identity())
    account_ids = _user_account_ids(user_id)
    if not account_ids:
        return jsonify({"alerts": []}), 200

    alerts = (
        Alert.query.filter(
            Alert.account_id.in_(account_ids),
            Alert.is_active == True,
        )
        .order_by(Alert.last_triggered.desc())
        .all()
    )
    return jsonify({"alerts": [a.to_dict() for a in alerts]}), 200


@alerts_bp.route("", methods=["POST"])
@jwt_required()
def create_alert():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    missing = require_fields(data, ["account_id", "alert_type"])
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if data["alert_type"] not in ALERT_TYPES:
        return jsonify({"error": f"alert_type must be one of: {ALERT_TYPES}"}), 400

    account = db.session.get(Account, data["account_id"])
    if not account or account.user_id != user_id:
        return jsonify({"error": "Account not found."}), 404

    notification_method = data.get("notification_method", "dashboard")
    if notification_method not in NOTIFICATION_METHODS:
        return jsonify({"error": f"notification_method must be one of: {NOTIFICATION_METHODS}"}), 400

    alert = Alert(
        account_id=data["account_id"],
        alert_type=data["alert_type"],
        threshold_percentage=data.get("threshold_percentage", 80),
        notification_method=notification_method,
    )
    db.session.add(alert)
    db.session.commit()
    return jsonify({"alert": alert.to_dict()}), 201


@alerts_bp.route("/<int:alert_id>", methods=["PUT"])
@jwt_required()
def update_alert(alert_id):
    user_id = int(get_jwt_identity())
    account_ids = _user_account_ids(user_id)

    alert = db.session.get(Alert, alert_id)
    if not alert or alert.account_id not in account_ids:
        return jsonify({"error": "Alert not found."}), 404

    data = request.get_json() or {}
    if "threshold_percentage" in data:
        alert.threshold_percentage = int(data["threshold_percentage"])
    if "is_active" in data:
        alert.is_active = bool(data["is_active"])
    if "notification_method" in data:
        if data["notification_method"] not in NOTIFICATION_METHODS:
            return jsonify({"error": f"notification_method must be one of: {NOTIFICATION_METHODS}"}), 400
        alert.notification_method = data["notification_method"]

    db.session.commit()
    return jsonify({"alert": alert.to_dict()}), 200


@alerts_bp.route("/<int:alert_id>", methods=["DELETE"])
@jwt_required()
def delete_alert(alert_id):
    user_id = int(get_jwt_identity())
    account_ids = _user_account_ids(user_id)

    alert = db.session.get(Alert, alert_id)
    if not alert or alert.account_id not in account_ids:
        return jsonify({"error": "Alert not found."}), 404

    db.session.delete(alert)
    db.session.commit()
    return jsonify({"message": "Alert deleted."}), 200


@alerts_bp.route("/<int:alert_id>/acknowledge", methods=["POST"])
@jwt_required()
def acknowledge_alert(alert_id):
    user_id = int(get_jwt_identity())
    account_ids = _user_account_ids(user_id)

    alert = db.session.get(Alert, alert_id)
    if not alert or alert.account_id not in account_ids:
        return jsonify({"error": "Alert not found."}), 404

    alert.is_acknowledged = True
    db.session.commit()
    return jsonify({"alert": alert.to_dict()}), 200
