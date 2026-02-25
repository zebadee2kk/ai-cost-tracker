from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from models.account import Account
from models.service import Service
from utils.encryption import decrypt_api_key, encrypt_api_key
from utils.validators import require_fields, sanitize_string

accounts_bp = Blueprint("accounts", __name__)


def _get_current_user_id() -> int:
    return int(get_jwt_identity())


def _own_account_or_404(account_id: int, user_id: int) -> Account:
    account = db.session.get(Account, account_id)
    if not account or account.user_id != user_id:
        return None
    return account


@accounts_bp.route("", methods=["GET"])
@jwt_required()
def list_accounts():
    user_id = _get_current_user_id()
    accounts = Account.query.filter_by(user_id=user_id).all()
    return jsonify({"accounts": [a.to_dict() for a in accounts]}), 200


@accounts_bp.route("", methods=["POST"])
@jwt_required()
def create_account():
    user_id = _get_current_user_id()
    data = request.get_json() or {}

    missing = require_fields(data, ["service_id", "account_name"])
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    service = db.session.get(Service, data["service_id"])
    if not service:
        return jsonify({"error": "Service not found."}), 404

    # Encrypt the API key before storing
    encrypted_key = None
    if data.get("api_key"):
        encrypted_key = encrypt_api_key(data["api_key"])

    encrypted_token = None
    if data.get("auth_token"):
        encrypted_token = encrypt_api_key(data["auth_token"])

    account = Account(
        user_id=user_id,
        service_id=data["service_id"],
        account_name=sanitize_string(data["account_name"]),
        api_key=encrypted_key,
        auth_token=encrypted_token,
        monthly_limit=data.get("monthly_limit"),
        session_limit=data.get("session_limit"),
    )
    db.session.add(account)
    db.session.commit()
    return jsonify({"account": account.to_dict()}), 201


@accounts_bp.route("/<int:account_id>", methods=["GET"])
@jwt_required()
def get_account(account_id):
    user_id = _get_current_user_id()
    account = _own_account_or_404(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404
    return jsonify({"account": account.to_dict()}), 200


@accounts_bp.route("/<int:account_id>", methods=["PUT"])
@jwt_required()
def update_account(account_id):
    user_id = _get_current_user_id()
    account = _own_account_or_404(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    data = request.get_json() or {}
    if "account_name" in data:
        account.account_name = sanitize_string(data["account_name"])
    if "monthly_limit" in data:
        account.monthly_limit = data["monthly_limit"]
    if "session_limit" in data:
        account.session_limit = data["session_limit"]
    if "is_active" in data:
        account.is_active = bool(data["is_active"])
    if data.get("api_key"):
        account.api_key = encrypt_api_key(data["api_key"])
    if data.get("auth_token"):
        account.auth_token = encrypt_api_key(data["auth_token"])

    db.session.commit()
    return jsonify({"account": account.to_dict()}), 200


@accounts_bp.route("/<int:account_id>", methods=["DELETE"])
@jwt_required()
def delete_account(account_id):
    user_id = _get_current_user_id()
    account = _own_account_or_404(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    db.session.delete(account)
    db.session.commit()
    return jsonify({"message": "Account deleted."}), 200


@accounts_bp.route("/<int:account_id>/test", methods=["POST"])
@jwt_required()
def test_account(account_id):
    """Test API connection for the given account."""
    user_id = _get_current_user_id()
    account = _own_account_or_404(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    if not account.api_key:
        return jsonify({"error": "No API key configured for this account."}), 400

    try:
        plaintext_key = decrypt_api_key(account.api_key)
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

    # Delegate to the appropriate service client
    from services.openai_service import OpenAIService
    from services.base_service import ServiceError

    service_name = account.service.name if account.service else ""

    try:
        if service_name == "ChatGPT":
            client = OpenAIService(plaintext_key)
            valid = client.validate_credentials()
        else:
            return jsonify({"error": f"Connection test not yet implemented for {service_name}."}), 501

        if valid:
            return jsonify({"status": "ok", "message": "Connection successful."}), 200
        return jsonify({"status": "failed", "message": "Invalid credentials."}), 400

    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502
