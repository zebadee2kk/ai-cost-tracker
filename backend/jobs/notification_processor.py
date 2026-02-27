"""Notification processor: dispatches queued notifications every 5 minutes.

Architecture
------------
* ``start_notification_processor(app)`` – registers an APScheduler interval
  job that calls ``_process_notifications`` every 5 minutes.
* ``_process_notifications`` fetches all ``pending`` queue items ordered by
  priority (high first), checks rate limits, routes to the correct sender,
  updates the queue row, and appends a ``NotificationHistory`` record.
* ``process_pending_notifications(app)`` is a public entry-point for
  on-demand processing (useful in tests or admin scripts).
"""
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


# ---------------------------------------------------------------------------
# Public scheduler API
# ---------------------------------------------------------------------------

def start_notification_processor(app) -> None:
    """Start the APScheduler background job (every 5 minutes).

    Safe to call multiple times – subsequent calls are no-ops if already
    running.  Skips initialization in the Flask reloader's parent process.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    # Flask debug mode spawns a child via Werkzeug's reloader; only start in
    # the child (or in production) to avoid duplicate jobs.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        app.logger.info(
            "Skipping notification processor init in Flask reloader parent process."
        )
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        func=_process_notifications,
        args=[app],
        trigger="interval",
        minutes=5,
        id="notification_processor",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Notification processor started (interval=5 min).")


def stop_notification_processor() -> None:
    """Gracefully shut down the notification scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def process_pending_notifications(app) -> None:
    """Public entry-point: process all pending notifications immediately."""
    _process_notifications(app)


# ---------------------------------------------------------------------------
# Core processing logic
# ---------------------------------------------------------------------------

def _process_notifications(app) -> None:
    """Fetch and dispatch pending notifications (runs inside app context)."""
    with app.app_context():
        from app import db
        from models.alert import Alert
        from models.notification_queue import NotificationQueue
        from services.notifications.rate_limiter import RateLimiter
        from sqlalchemy.orm import joinedload

        rate_limiter = RateLimiter()

        # Fetch pending items with eager loading to avoid N+1 queries when
        # _build_alert_data() dereferences item.alert and alert.account.
        pending = (
            NotificationQueue.query
            .options(
                joinedload(NotificationQueue.alert).joinedload(Alert.account)
            )
            .filter_by(status="pending")
            .order_by(
                NotificationQueue.priority.desc(),
                NotificationQueue.created_at.asc(),
            )
            .limit(100)
            .all()
        )

        if not pending:
            logger.debug("No pending notifications to process.")
            return

        logger.info("Processing %d pending notification(s).", len(pending))

        # Disable expire_on_commit for the batch loop so that SQLAlchemy does
        # not re-issue per-item SELECT queries after each commit (which would
        # undo the benefit of eager loading above).  The flag is accessed on
        # the underlying Session (not the scoped proxy) and restored on exit.
        session = db.session()
        original_expire = session.expire_on_commit
        session.expire_on_commit = False
        try:
            for item in pending:
                _dispatch_item(app, db, item, rate_limiter)
        finally:
            session.expire_on_commit = original_expire


def _dispatch_item(app, db, item, rate_limiter) -> None:
    """Attempt to deliver a single queue item.

    On success  → status='sent', NotificationHistory(status='sent')
    On failure  → retry_count++; if exhausted status='failed'
    Rate-limited → skip (item remains pending for next run)
    """
    from models.notification_history import NotificationHistory

    # Respect per-user per-channel rate limits
    if not rate_limiter.can_send(item.user_id, item.channel):
        logger.info(
            "Rate-limited user=%d channel=%s notification_id=%d – skipping.",
            item.user_id, item.channel, item.id,
        )
        return

    alert_data = _build_alert_data(item)
    start = time.monotonic()
    success = False
    error_msg: Optional[str] = None

    try:
        if item.channel == "email":
            from services.notifications.email_sender import EmailSender
            sender = EmailSender(
                api_key=app.config.get("SENDGRID_API_KEY", ""),
                from_email=app.config.get("SENDGRID_FROM_EMAIL", ""),
                from_name=app.config.get("SENDGRID_FROM_NAME", "AI Cost Tracker"),
            )
            success = sender.send_alert(item.recipient, alert_data)

        elif item.channel == "slack":
            from services.notifications.slack_sender import SlackSender
            sender = SlackSender()
            success = sender.send_alert(item.recipient, alert_data)

        else:
            logger.warning("Unsupported channel '%s' for notification %d.", item.channel, item.id)
            _mark_failed(db, item, f"Unsupported channel: {item.channel}")
            return

    except Exception as exc:
        logger.exception("Exception while dispatching notification %d.", item.id)
        error_msg = str(exc)

    duration_ms = int((time.monotonic() - start) * 1000)

    if success:
        item.status = "sent"
        item.sent_at = datetime.now(timezone.utc)
        item.error_message = None
        history_status = "sent"
    else:
        item.retry_count += 1
        item.error_message = error_msg or "Send failed"
        if item.retry_count >= item.max_retries:
            item.status = "failed"
        history_status = "failed"

    history = NotificationHistory(
        notification_id=item.id,
        user_id=item.user_id,
        channel=item.channel,
        status=history_status,
        duration_ms=duration_ms,
    )
    db.session.add(history)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception(
            "Failed to commit dispatch result for notification %d.", item.id
        )


def _mark_failed(db, item, reason: str) -> None:
    """Immediately mark a queue item as failed and record in history."""
    from models.notification_history import NotificationHistory

    item.status = "failed"
    item.error_message = reason
    history = NotificationHistory(
        notification_id=item.id,
        user_id=item.user_id,
        channel=item.channel,
        status="failed",
        duration_ms=0,
    )
    db.session.add(history)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to mark notification %d as failed.", item.id)


def _build_alert_data(item) -> Dict[str, Any]:
    """Construct the alert_data dict required by EmailSender / SlackSender."""
    alert = item.alert
    if not alert:
        return {
            "type": "system",
            "level": "warning",
            "account_name": "Unknown",
            "current_cost": 0.0,
            "threshold": 0.0,
            "message": item.error_message or "Notification",
        }

    # Map the existing Alert.alert_type to (notification_type, level)
    type_map = {
        "approaching_limit": ("budget", "warning"),
        "limit_exceeded": ("budget", "emergency"),
        "high_cost": ("budget", "critical"),
        "unusual_activity": ("anomaly", "warning"),
        "service_down": ("system", "critical"),
    }
    notif_type, level = type_map.get(alert.alert_type, ("system", "warning"))
    account = alert.account

    return {
        "type": notif_type,
        "level": level,
        "account_name": account.account_name if account else "Unknown",
        "current_cost": float(alert.threshold_percentage or 0),
        "threshold": 100.0,
        "message": alert.message or "",
        "timestamp": (
            alert.last_triggered.timestamp() if alert.last_triggered else 0
        ),
    }
