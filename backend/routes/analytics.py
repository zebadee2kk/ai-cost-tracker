"""
Analytics API routes.

GET /api/analytics/trends/<account_id>
    Query params: period (7d | 30d | 90d), metric (cost | tokens)
    Returns daily aggregates, moving averages, growth rate.

GET /api/analytics/forecast/<account_id>
    Query params: horizon (30 | 60 | 90 days)
    Returns linear regression forecast with confidence intervals.

GET /api/analytics/anomalies/<account_id>
    Query params: start_date, end_date, acknowledged (true|false)
    Returns previously detected anomalies.

POST /api/analytics/anomalies/<account_id>/detect
    Triggers anomaly detection for the account over a date range.

GET /api/analytics/anomalies/<anomaly_id>/acknowledge
    Mark an anomaly as acknowledged.
"""

import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from models.account import Account
from models.anomaly_detection import AnomalyDetectionConfig, DetectedAnomaly

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

VALID_PERIODS = {"7d": 7, "30d": 30, "90d": 90}
VALID_METRICS = {"cost", "tokens"}
VALID_HORIZONS = {30, 60, 90}


def _get_account_or_403(account_id: int, user_id: int):
    """Return the account if it belongs to the user, else None."""
    return Account.query.filter_by(id=account_id, user_id=user_id).first()


def _fetch_daily_aggregates(account_id: int, metric: str, start_date, end_date):
    """
    Return sorted list of daily {date, value} dicts for the given metric.
    """
    from models.usage_record import UsageRecord
    from sqlalchemy import func

    if metric == "tokens":
        agg_col = func.sum(UsageRecord.tokens_used)
    else:
        agg_col = func.sum(UsageRecord.cost)

    rows = (
        db.session.query(
            func.date(UsageRecord.timestamp).label("day"),
            agg_col.label("total"),
        )
        .filter(
            UsageRecord.account_id == account_id,
            func.date(UsageRecord.timestamp) >= start_date.isoformat(),
            func.date(UsageRecord.timestamp) <= end_date.isoformat(),
        )
        .group_by(func.date(UsageRecord.timestamp))
        .order_by(func.date(UsageRecord.timestamp))
        .all()
    )

    return [
        {
            "date": row.day if isinstance(row.day, str) else row.day.isoformat(),
            "value": float(row.total or 0),
        }
        for row in rows
    ]


# ------------------------------------------------------------------
# GET /api/analytics/trends/<account_id>
# ------------------------------------------------------------------

@analytics_bp.route("/trends/<int:account_id>", methods=["GET"])
@jwt_required()
def get_trends(account_id: int):
    """
    Return trend data for an account.

    Query params:
        period  – 7d | 30d | 90d  (default: 30d)
        metric  – cost | tokens   (default: cost)
    """
    user_id = int(get_jwt_identity())
    account = _get_account_or_403(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    period_str = request.args.get("period", "30d")
    if period_str not in VALID_PERIODS:
        return jsonify({"error": f"period must be one of {list(VALID_PERIODS.keys())}"}), 400

    metric = request.args.get("metric", "cost")
    if metric not in VALID_METRICS:
        return jsonify({"error": f"metric must be one of {list(VALID_METRICS)}"}), 400

    days = VALID_PERIODS[period_str]
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days - 1)

    daily = _fetch_daily_aggregates(account_id, metric, start_date, end_date)

    # Build dict for moving average utility
    from utils.forecasting import (
        calculate_growth_rate,
        calculate_moving_average,
    )

    data_dict = {row["date"]: row["value"] for row in daily}

    ma7 = calculate_moving_average(data_dict, window=7)
    ma30 = calculate_moving_average(data_dict, window=30) if days >= 30 else []
    growth_rate = calculate_growth_rate(data_dict)

    return jsonify(
        {
            "account_id": account_id,
            "account_name": account.account_name,
            "period": period_str,
            "metric": metric,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": daily,
            "moving_avg_7d": ma7,
            "moving_avg_30d": ma30,
            "growth_rate_pct": growth_rate,
            "total": round(sum(row["value"] for row in daily), 4),
        }
    )


# ------------------------------------------------------------------
# GET /api/analytics/forecast/<account_id>
# ------------------------------------------------------------------

@analytics_bp.route("/forecast/<int:account_id>", methods=["GET"])
@jwt_required()
def get_forecast(account_id: int):
    """
    Return a linear regression cost forecast.

    Query params:
        horizon – 30 | 60 | 90 (days; default: 30)
    """
    user_id = int(get_jwt_identity())
    account = _get_account_or_403(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    try:
        horizon = int(request.args.get("horizon", 30))
    except ValueError:
        return jsonify({"error": "horizon must be an integer"}), 400

    if horizon not in VALID_HORIZONS:
        return jsonify({"error": f"horizon must be one of {sorted(VALID_HORIZONS)}"}), 400

    # Use last 90 days of actuals for regression
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=89)

    daily = _fetch_daily_aggregates(account_id, "cost", start_date, end_date)
    data_dict = {row["date"]: row["value"] for row in daily}

    from utils.forecasting import linear_forecast

    result = linear_forecast(data_dict, horizon=horizon)

    return jsonify(
        {
            "account_id": account_id,
            "account_name": account.account_name,
            "horizon_days": horizon,
            "historical_start": start_date.isoformat(),
            "historical_end": end_date.isoformat(),
            **result,
        }
    )


# ------------------------------------------------------------------
# GET /api/analytics/anomalies/<account_id>
# ------------------------------------------------------------------

@analytics_bp.route("/anomalies/<int:account_id>", methods=["GET"])
@jwt_required()
def list_anomalies(account_id: int):
    """Return detected anomalies for an account."""
    user_id = int(get_jwt_identity())
    account = _get_account_or_403(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    ack_param = request.args.get("acknowledged")
    acknowledged = None
    if ack_param is not None:
        acknowledged = ack_param.lower() == "true"

    from services.anomaly_detector import AnomalyDetector

    detector = AnomalyDetector()
    anomalies = detector.get_anomalies(
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        acknowledged=acknowledged,
    )

    return jsonify(
        {
            "account_id": account_id,
            "account_name": account.account_name,
            "anomalies": [a.to_dict() for a in anomalies],
            "total": len(anomalies),
        }
    )


# ------------------------------------------------------------------
# POST /api/analytics/anomalies/<account_id>/detect
# ------------------------------------------------------------------

@analytics_bp.route("/anomalies/<int:account_id>/detect", methods=["POST"])
@jwt_required()
def trigger_detection(account_id: int):
    """
    Trigger anomaly detection for an account.

    Body (JSON, all optional):
        start_date  – ISO date string
        end_date    – ISO date string
    """
    user_id = int(get_jwt_identity())
    account = _get_account_or_403(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    body = request.get_json(silent=True) or {}
    start_date = body.get("start_date")
    end_date = body.get("end_date")

    date_range = None
    if start_date and end_date:
        date_range = (start_date, end_date)

    from services.anomaly_detector import AnomalyDetector

    detector = AnomalyDetector()
    try:
        new_anomalies = detector.detect_anomalies(
            account_id=account_id, date_range=date_range
        )
    except Exception as exc:
        logger.exception("Anomaly detection failed for account %d.", account_id)
        return jsonify({"error": "Detection failed", "detail": str(exc)}), 500

    return jsonify(
        {
            "account_id": account_id,
            "detected": len(new_anomalies),
            "anomalies": [a.to_dict() for a in new_anomalies],
        }
    ), 201


# ------------------------------------------------------------------
# POST /api/analytics/anomalies/<anomaly_id>/acknowledge
# ------------------------------------------------------------------

@analytics_bp.route("/anomalies/<int:anomaly_id>/acknowledge", methods=["POST"])
@jwt_required()
def acknowledge_anomaly(anomaly_id: int):
    """Mark an anomaly as acknowledged."""
    user_id = int(get_jwt_identity())

    anomaly = DetectedAnomaly.query.get(anomaly_id)
    if not anomaly:
        return jsonify({"error": "Anomaly not found"}), 404

    # Verify ownership via account
    account = _get_account_or_403(anomaly.account_id, user_id)
    if not account:
        return jsonify({"error": "Anomaly not found"}), 404

    anomaly.is_acknowledged = True
    db.session.commit()

    return jsonify({"message": "Anomaly acknowledged.", "anomaly": anomaly.to_dict()})


# ------------------------------------------------------------------
# GET/PUT /api/analytics/config/<account_id>
# ------------------------------------------------------------------

@analytics_bp.route("/config/<int:account_id>", methods=["GET"])
@jwt_required()
def get_config(account_id: int):
    """Return the anomaly detection config for an account."""
    user_id = int(get_jwt_identity())
    account = _get_account_or_403(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    config = AnomalyDetectionConfig.query.filter_by(account_id=account_id).first()
    if not config:
        # Return defaults
        return jsonify(
            {
                "account_id": account_id,
                "sensitivity": 2.0,
                "baseline_days": 30,
                "is_enabled": True,
            }
        )

    return jsonify(config.to_dict())


@analytics_bp.route("/config/<int:account_id>", methods=["PUT"])
@jwt_required()
def update_config(account_id: int):
    """Upsert anomaly detection config for an account."""
    user_id = int(get_jwt_identity())
    account = _get_account_or_403(account_id, user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    body = request.get_json(silent=True) or {}

    sensitivity = body.get("sensitivity", 2.0)
    if sensitivity not in [1.5, 2.0, 2.5]:
        return jsonify({"error": "sensitivity must be 1.5, 2.0, or 2.5"}), 400

    baseline_days = int(body.get("baseline_days", 30))
    if not (7 <= baseline_days <= 90):
        return jsonify({"error": "baseline_days must be between 7 and 90"}), 400

    is_enabled = body.get("is_enabled", True)

    config = AnomalyDetectionConfig.query.filter_by(account_id=account_id).first()
    now = datetime.now(timezone.utc)

    if config:
        config.sensitivity = sensitivity
        config.baseline_days = baseline_days
        config.is_enabled = bool(is_enabled)
        config.updated_at = now
    else:
        config = AnomalyDetectionConfig(
            account_id=account_id,
            sensitivity=sensitivity,
            baseline_days=baseline_days,
            is_enabled=bool(is_enabled),
        )
        db.session.add(config)

    db.session.commit()
    return jsonify(config.to_dict())
