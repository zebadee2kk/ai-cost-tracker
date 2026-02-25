"""
Alert generation logic.

Called after each usage sync to detect threshold breaches.
"""

from datetime import datetime, timezone
from decimal import Decimal

from app import db
from models.alert import Alert


def check_and_generate_alerts(account, monthly_cost: Decimal, monthly_limit: Decimal):
    """
    Evaluate account usage against its monthly limit and create Alert records.

    Only fires a new alert if one of the same type hasn't been acknowledged yet.
    """
    if not monthly_limit or monthly_limit <= 0:
        return

    usage_pct = (monthly_cost / monthly_limit * 100) if monthly_limit else Decimal("0")

    # Approaching limit (>= 80%)
    if usage_pct >= 80:
        _upsert_alert(
            account,
            alert_type="approaching_limit",
            threshold_percentage=80,
            message=(
                f"{account.account_name}: {float(usage_pct):.1f}% of monthly limit used "
                f"(${float(monthly_cost):.4f} / ${float(monthly_limit):.4f})."
            ),
        )

    # Limit exceeded (>= 100%)
    if usage_pct >= 100:
        _upsert_alert(
            account,
            alert_type="limit_exceeded",
            threshold_percentage=100,
            message=(
                f"{account.account_name}: Monthly limit exceeded! "
                f"${float(monthly_cost):.4f} spent vs ${float(monthly_limit):.4f} limit."
            ),
        )


def _upsert_alert(account, alert_type: str, threshold_percentage: int, message: str):
    """Create a new alert or update last_triggered on an existing unacknowledged one."""
    existing = (
        Alert.query.filter_by(
            account_id=account.id,
            alert_type=alert_type,
            is_acknowledged=False,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    if existing:
        existing.last_triggered = now
        existing.message = message
    else:
        alert = Alert(
            account_id=account.id,
            alert_type=alert_type,
            threshold_percentage=threshold_percentage,
            is_active=True,
            is_acknowledged=False,
            last_triggered=now,
            notification_method="dashboard",
            message=message,
        )
        db.session.add(alert)

    db.session.commit()
