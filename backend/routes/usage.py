from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app import db
from models.account import Account
from models.usage_record import UsageRecord
from utils.cost_calculator import project_monthly_cost
from decimal import Decimal
import calendar

usage_bp = Blueprint("usage", __name__)


def _user_account_ids(user_id: int) -> list[int]:
    return [
        a.id for a in Account.query.filter_by(user_id=user_id).with_entities(Account.id)
    ]


@usage_bp.route("", methods=["GET"])
@jwt_required()
def current_usage():
    """Current month usage summary across all accounts."""
    user_id = int(get_jwt_identity())
    account_ids = _user_account_ids(user_id)
    if not account_ids:
        return jsonify({"usage": []}), 200

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = (
        db.session.query(
            UsageRecord.account_id,
            func.sum(UsageRecord.tokens_used).label("total_tokens"),
            func.sum(UsageRecord.cost).label("total_cost"),
            func.count(UsageRecord.id).label("total_calls"),
        )
        .filter(
            UsageRecord.account_id.in_(account_ids),
            UsageRecord.timestamp >= month_start,
        )
        .group_by(UsageRecord.account_id)
        .all()
    )

    result = []
    for row in rows:
        account = db.session.get(Account, row.account_id)
        result.append(
            {
                "account_id": row.account_id,
                "account_name": account.account_name if account else None,
                "service_name": account.service.name if account and account.service else None,
                "total_tokens": row.total_tokens or 0,
                "total_cost": float(row.total_cost or 0),
                "total_calls": row.total_calls or 0,
                "monthly_limit": float(account.monthly_limit) if account and account.monthly_limit else None,
            }
        )
    return jsonify({"usage": result}), 200


@usage_bp.route("/history", methods=["GET"])
@jwt_required()
def usage_history():
    """Historical usage records with optional filters."""
    user_id = int(get_jwt_identity())
    account_ids = _user_account_ids(user_id)
    if not account_ids:
        return jsonify({"records": [], "total": 0}), 200

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    account_id = request.args.get("account_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = UsageRecord.query.filter(UsageRecord.account_id.in_(account_ids))

    if account_id and account_id in account_ids:
        query = query.filter(UsageRecord.account_id == account_id)
    if start_date:
        query = query.filter(UsageRecord.timestamp >= start_date)
    if end_date:
        query = query.filter(UsageRecord.timestamp <= end_date)

    paginated = query.order_by(UsageRecord.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify(
        {
            "records": [r.to_dict() for r in paginated.items],
            "total": paginated.total,
            "page": page,
            "pages": paginated.pages,
        }
    ), 200


@usage_bp.route("/by-service", methods=["GET"])
@jwt_required()
def usage_by_service():
    """Usage totals grouped by service for the current month."""
    user_id = int(get_jwt_identity())
    account_ids = _user_account_ids(user_id)
    if not account_ids:
        return jsonify({"by_service": []}), 200

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    rows = (
        db.session.query(
            UsageRecord.service_id,
            func.sum(UsageRecord.tokens_used).label("total_tokens"),
            func.sum(UsageRecord.cost).label("total_cost"),
            func.count(UsageRecord.id).label("total_calls"),
        )
        .filter(
            UsageRecord.account_id.in_(account_ids),
            UsageRecord.timestamp >= month_start,
        )
        .group_by(UsageRecord.service_id)
        .all()
    )

    from models.service import Service
    result = []
    for row in rows:
        svc = db.session.get(Service, row.service_id)
        result.append(
            {
                "service_id": row.service_id,
                "service_name": svc.name if svc else None,
                "total_tokens": row.total_tokens or 0,
                "total_cost": float(row.total_cost or 0),
                "total_calls": row.total_calls or 0,
            }
        )
    return jsonify({"by_service": result}), 200


@usage_bp.route("/forecast", methods=["GET"])
@jwt_required()
def usage_forecast():
    """Project cost to month-end for each account."""
    user_id = int(get_jwt_identity())
    accounts = Account.query.filter_by(user_id=user_id).all()
    if not accounts:
        return jsonify({"forecasts": []}), 200

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_elapsed = (now - month_start).days + 1
    total_days = calendar.monthrange(now.year, now.month)[1]

    forecasts = []
    for account in accounts:
        total_cost = (
            db.session.query(func.sum(UsageRecord.cost))
            .filter(
                UsageRecord.account_id == account.id,
                UsageRecord.timestamp >= month_start,
            )
            .scalar()
            or Decimal("0")
        )
        projected, confidence = project_monthly_cost(
            Decimal(str(total_cost)), days_elapsed, total_days
        )
        forecasts.append(
            {
                "account_id": account.id,
                "account_name": account.account_name,
                "cost_so_far": float(total_cost),
                "projected_total": float(projected),
                "confidence_score": float(confidence),
                "monthly_limit": float(account.monthly_limit) if account.monthly_limit else None,
            }
        )
    return jsonify({"forecasts": forecasts}), 200


@usage_bp.route("/manual", methods=["POST"])
@jwt_required()
def create_manual_entry():
    """Create a manual usage entry for services that lack an API (e.g. Groq, Perplexity).

    Request body:
        {
            "account_id": 1,
            "date": "2026-02-25",
            "tokens": 100000,
            "cost": "5.50",
            "notes": "From invoice #12345"  // optional
        }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields
    required = ("account_id", "date", "cost")
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    # Ensure the account belongs to the requesting user
    account = Account.query.filter_by(
        id=data["account_id"], user_id=user_id
    ).first()
    if not account:
        return jsonify({"error": "Account not found"}), 404

    # Parse and validate date
    try:
        entry_date = datetime.strptime(data["date"], "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return jsonify({"error": "Invalid date format; expected YYYY-MM-DD"}), 400

    # Parse and validate cost
    try:
        cost = Decimal(str(data["cost"]))
        if cost < 0:
            raise ValueError("cost must be non-negative")
    except (ValueError, Exception):
        return jsonify({"error": "Invalid cost value; must be a non-negative number"}), 400

    # Parse optional token count
    tokens = data.get("tokens", 0)
    try:
        tokens = int(tokens)
        if tokens < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid tokens value; must be a non-negative integer"}), 400

    notes = data.get("notes", "")

    entry = UsageRecord(
        account_id=account.id,
        service_id=account.service_id,
        timestamp=entry_date,
        tokens_used=tokens,
        cost=cost,
        cost_currency="USD",
        api_calls=1,
        request_type="manual",
        source="manual",
        extra_data={"notes": notes} if notes else {},
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify(entry.to_dict()), 201


@usage_bp.route("/manual/<int:entry_id>", methods=["PUT"])
@jwt_required()
def update_manual_entry(entry_id):
    """Update an existing manual usage entry.

    Only the owning user may update their entries.
    Only fields provided in the request body are updated.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Look up the record and verify ownership via the account
    entry = UsageRecord.query.get(entry_id)
    if not entry or entry.source != "manual":
        return jsonify({"error": "Manual entry not found"}), 404

    account = Account.query.filter_by(id=entry.account_id, user_id=user_id).first()
    if not account:
        return jsonify({"error": "Manual entry not found"}), 404

    if "date" in data:
        try:
            entry.timestamp = datetime.strptime(data["date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return jsonify({"error": "Invalid date format; expected YYYY-MM-DD"}), 400

    if "cost" in data:
        try:
            cost = Decimal(str(data["cost"]))
            if cost < 0:
                raise ValueError
            entry.cost = cost
        except (ValueError, Exception):
            return jsonify({"error": "Invalid cost value"}), 400

    if "tokens" in data:
        try:
            tokens = int(data["tokens"])
            if tokens < 0:
                raise ValueError
            entry.tokens_used = tokens
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid tokens value"}), 400

    if "notes" in data:
        entry.extra_data = {"notes": data["notes"]}

    entry.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(entry.to_dict()), 200


@usage_bp.route("/manual/<int:entry_id>", methods=["DELETE"])
@jwt_required()
def delete_manual_entry(entry_id):
    """Delete a manual usage entry."""
    user_id = int(get_jwt_identity())

    entry = UsageRecord.query.get(entry_id)
    if not entry or entry.source != "manual":
        return jsonify({"error": "Manual entry not found"}), 404

    account = Account.query.filter_by(id=entry.account_id, user_id=user_id).first()
    if not account:
        return jsonify({"error": "Manual entry not found"}), 404

    db.session.delete(entry)
    db.session.commit()

    return jsonify({"message": "Entry deleted"}), 200
