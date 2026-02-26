"""
Alert generation logic.

Called after each usage sync to detect threshold breaches.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app import db
from models.alert import Alert

logger = logging.getLogger(__name__)


def check_and_generate_alerts(account, monthly_cost: Decimal, monthly_limit: Decimal):
    """
    Evaluate account usage against its monthly limit and create Alert records.

    Threshold levels (per spec):
    - 70%  → approaching_limit (warning)
    - 90%  → high_cost (critical)
    - 100% → limit_exceeded (emergency)

    Only fires a new alert if one of the same type hasn't been acknowledged yet.
    """
    if not monthly_limit or monthly_limit <= 0:
        return

    usage_pct = (monthly_cost / monthly_limit * 100) if monthly_limit else Decimal("0")

    # Warning: >= 70% (approaching limit)
    if usage_pct >= 70:
        _upsert_alert(
            account,
            alert_type="approaching_limit",
            threshold_percentage=70,
            message=(
                f"{account.account_name}: {float(usage_pct):.1f}% of monthly limit used "
                f"(${float(monthly_cost):.4f} / ${float(monthly_limit):.4f})."
            ),
        )

    # Critical: >= 90%
    if usage_pct >= 90:
        _upsert_alert(
            account,
            alert_type="high_cost",
            threshold_percentage=90,
            message=(
                f"{account.account_name}: {float(usage_pct):.1f}% of monthly limit used – "
                f"critical threshold reached "
                f"(${float(monthly_cost):.4f} / ${float(monthly_limit):.4f})."
            ),
        )

    # Emergency: >= 100% (limit exceeded)
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
    """Create a new alert or update last_triggered on an existing unacknowledged one.

    When a *new* alert is created, notification queue entries are inserted for
    every enabled NotificationPreference that matches the alert category.
    """
    existing = (
        Alert.query.filter_by(
            account_id=account.id,
            alert_type=alert_type,
            is_acknowledged=False,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    is_new = existing is None

    if existing:
        existing.last_triggered = now
        existing.message = message
        db.session.commit()
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
        # flush so alert.id is available before we reference it in the queue
        db.session.flush()
        db.session.commit()
        _queue_notifications(account, alert, alert_type)


# ---------------------------------------------------------------------------
# Notification queuing
# ---------------------------------------------------------------------------

# Maps alert_type → (notification category for preference matching, priority)
_ALERT_META = {
    "approaching_limit": ("budget", 1),
    "high_cost":         ("budget", 2),
    "limit_exceeded":    ("budget", 3),
    "unusual_activity":  ("anomaly", 2),
    "service_down":      ("system", 2),
}


def _queue_notifications(account, alert, alert_type: str) -> None:
    """Insert NotificationQueue rows for each enabled, matching preference."""
    from models.notification_preference import NotificationPreference
    from models.notification_queue import NotificationQueue

    category, priority = _ALERT_META.get(alert_type, ("system", 1))
    user_id = account.user_id

    prefs = NotificationPreference.query.filter_by(user_id=user_id, enabled=True).all()
    queued = 0
    for pref in prefs:
        # Honour per-channel alert_type filters if configured
        allowed = pref.alert_types or []
        if allowed and category not in allowed:
            continue

        config = pref.config or {}
        if pref.channel == "email":
            recipient = config.get("address")
        else:
            recipient = config.get("webhook_url")

        if not recipient:
            continue

        db.session.add(
            NotificationQueue(
                alert_id=alert.id,
                user_id=user_id,
                channel=pref.channel,
                recipient=recipient,
                priority=priority,
                status="pending",
            )
        )
        queued += 1

    if queued:
        try:
            db.session.commit()
            logger.info(
                "Queued %d notification(s) for alert %d (type=%s).",
                queued, alert.id, alert_type,
            )
        except Exception:
            db.session.rollback()
            logger.exception(
                "Failed to queue notifications for alert %d.", alert.id
            )
