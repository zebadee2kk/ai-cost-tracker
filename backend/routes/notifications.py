"""Notification REST API endpoints.

Routes
------
GET  /api/notifications/preferences/<user_id>  – fetch preferences (own only)
PUT  /api/notifications/preferences/<user_id>  – upsert preferences (own only)
GET  /api/notifications/queue                  – list queue items (own)
POST /api/notifications/queue                  – manually enqueue a notification
GET  /api/notifications/history                – delivery history (own)
POST /api/notifications/test/<channel>         – send an immediate test alert
GET  /api/notifications/rate-limits            – remaining budget per channel
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from models.alert import Alert
from models.notification_history import NotificationHistory
from models.notification_preference import NotificationPreference
from models.notification_queue import NotificationQueue
# Imported at module level so tests can patch routes.notifications.EmailSender /
# SlackSender cleanly.  Both imports survive stubbed environments because the
# sender modules themselves handle missing optional dependencies (sendgrid,
# requests) gracefully.
try:
    from services.notifications.email_sender import EmailSender
except (ImportError, AttributeError):
    EmailSender = None  # type: ignore[assignment,misc]

try:
    from services.notifications.slack_sender import SlackSender
except (ImportError, AttributeError):
    SlackSender = None  # type: ignore[assignment,misc]

notifications_bp = Blueprint("notifications", __name__)

VALID_CHANNELS = {"email", "slack", "discord", "teams"}
VALID_ALERT_TYPES = {"budget", "anomaly", "system"}
VALID_STATUSES = {"pending", "sent", "failed", "cancelled"}


def _current_user_id() -> int:
    return int(get_jwt_identity())


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

@notifications_bp.route("/preferences/<int:user_id>", methods=["GET"])
@jwt_required()
def get_preferences(user_id):
    """Return all notification preferences for a user (own only)."""
    if _current_user_id() != user_id:
        return jsonify({"error": "Forbidden"}), 403

    prefs = NotificationPreference.query.filter_by(user_id=user_id).all()
    result = {
        pref.channel: {
            "enabled": pref.enabled,
            "config": pref.config or {},
            "alert_types": pref.alert_types or [],
        }
        for pref in prefs
    }
    return jsonify({"preferences": result}), 200


@notifications_bp.route("/preferences/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_preferences(user_id):
    """Upsert notification preferences for a user (own only).

    Expected body::

        {
            "email": {
                "enabled": true,
                "config": {"address": "user@example.com"},
                "alert_types": ["budget", "anomaly", "system"]
            },
            "slack": {
                "enabled": false,
                "config": {"webhook_url": "https://hooks.slack.com/..."},
                "alert_types": ["budget"]
            }
        }
    """
    if _current_user_id() != user_id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    updated = []
    for channel, settings in data.items():
        if channel not in VALID_CHANNELS:
            return jsonify({
                "error": f"Invalid channel: '{channel}'. Valid: {sorted(VALID_CHANNELS)}"
            }), 400
        if not isinstance(settings, dict):
            return jsonify({"error": f"Settings for '{channel}' must be an object"}), 400

        alert_types = settings.get("alert_types", [])
        if not isinstance(alert_types, list):
            return jsonify({"error": f"'alert_types' for '{channel}' must be an array"}), 400
        invalid = set(alert_types) - VALID_ALERT_TYPES
        if invalid:
            return jsonify({"error": f"Invalid alert_types: {sorted(invalid)}"}), 400

        pref = NotificationPreference.query.filter_by(
            user_id=user_id, channel=channel
        ).first()

        if pref:
            if "enabled" in settings:
                pref.enabled = bool(settings["enabled"])
            if "config" in settings:
                pref.config = settings["config"]
            if "alert_types" in settings:
                pref.alert_types = alert_types
            pref.updated_at = datetime.now(timezone.utc)
        else:
            pref = NotificationPreference(
                user_id=user_id,
                channel=channel,
                enabled=bool(settings.get("enabled", True)),
                config=settings.get("config", {}),
                alert_types=alert_types,
            )
            db.session.add(pref)

        updated.append(channel)

    db.session.commit()
    return jsonify({"message": f"Updated channels: {updated}"}), 200


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

@notifications_bp.route("/queue", methods=["GET"])
@jwt_required()
def list_queue():
    """List notification queue items for the current user.

    Query params: status, channel, limit (max 200).
    """
    current_id = _current_user_id()
    status_filter = request.args.get("status")
    channel_filter = request.args.get("channel")
    limit = min(int(request.args.get("limit", 50)), 200)

    query = NotificationQueue.query.filter_by(user_id=current_id)

    if status_filter:
        if status_filter not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status: {status_filter}"}), 400
        query = query.filter_by(status=status_filter)

    if channel_filter:
        if channel_filter not in VALID_CHANNELS:
            return jsonify({"error": f"Invalid channel: {channel_filter}"}), 400
        query = query.filter_by(channel=channel_filter)

    items = (
        query
        .order_by(
            NotificationQueue.priority.desc(),
            NotificationQueue.created_at.asc(),
        )
        .limit(limit)
        .all()
    )
    return jsonify({"queue": [item.to_dict() for item in items]}), 200


@notifications_bp.route("/queue", methods=["POST"])
@jwt_required()
def create_queue_item():
    """Manually enqueue a notification.

    Body::

        {"alert_id": 1, "channel": "email", "recipient": "u@example.com", "priority": 2}
    """
    current_id = _current_user_id()
    data = request.get_json() or {}

    missing = [f for f in ("alert_id", "channel", "recipient") if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    channel = data["channel"]
    if channel not in VALID_CHANNELS:
        return jsonify({"error": f"Invalid channel: {channel}"}), 400

    alert = db.session.get(Alert, data["alert_id"])
    if not alert or not alert.account or alert.account.user_id != current_id:
        return jsonify({"error": "Alert not found"}), 404

    priority = int(data.get("priority", 1))
    if priority not in (1, 2, 3):
        return jsonify({"error": "priority must be 1, 2, or 3"}), 400

    item = NotificationQueue(
        alert_id=data["alert_id"],
        user_id=current_id,
        channel=channel,
        recipient=data["recipient"],
        priority=priority,
        status="pending",
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"queue_item": item.to_dict()}), 201


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@notifications_bp.route("/history", methods=["GET"])
@jwt_required()
def list_history():
    """List notification delivery history for the current user.

    Query params: channel, status, limit (max 200).
    """
    current_id = _current_user_id()
    channel_filter = request.args.get("channel")
    status_filter = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)

    query = NotificationHistory.query.filter_by(user_id=current_id)

    if channel_filter:
        if channel_filter not in VALID_CHANNELS:
            return jsonify({"error": f"Invalid channel: {channel_filter}"}), 400
        query = query.filter_by(channel=channel_filter)

    if status_filter:
        query = query.filter_by(status=status_filter)

    items = (
        query
        .order_by(NotificationHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"history": [item.to_dict() for item in items]}), 200


# ---------------------------------------------------------------------------
# Test notification
# ---------------------------------------------------------------------------

@notifications_bp.route("/test/<channel>", methods=["POST"])
@jwt_required()
def send_test_notification(channel):
    """Send an immediate test notification on the specified channel.

    Body (optional)::

        {"recipient": "override@example.com"}

    Falls back to the configured recipient in the user's preferences.
    """
    if channel not in VALID_CHANNELS:
        return jsonify({"error": f"Invalid channel: {channel}"}), 400

    current_id = _current_user_id()
    data = request.get_json(force=True, silent=True) or {}

    pref = NotificationPreference.query.filter_by(
        user_id=current_id, channel=channel
    ).first()

    # Resolve recipient
    if channel == "email":
        recipient = data.get("recipient") or (
            (pref.config or {}).get("address") if pref else None
        )
        if not recipient:
            return jsonify({"error": "No email address configured for this channel"}), 400
    else:
        recipient = data.get("recipient") or (
            (pref.config or {}).get("webhook_url") if pref else None
        )
        if not recipient:
            return jsonify({"error": f"No webhook URL configured for {channel}"}), 400

    test_alert_data = {
        "type": "system",
        "level": "warning",
        "account_name": "Test",
        "current_cost": 0.0,
        "threshold": 0.0,
        "message": "This is a test notification from AI Cost Tracker.",
    }

    from flask import current_app

    if channel == "email":
        if not EmailSender:
            return jsonify({"error": "Email sender not available"}), 503
        sender = EmailSender(
            api_key=current_app.config.get("SENDGRID_API_KEY", ""),
            from_email=current_app.config.get("SENDGRID_FROM_EMAIL", ""),
            from_name=current_app.config.get("SENDGRID_FROM_NAME", "AI Cost Tracker"),
        )
        success = sender.send_alert(recipient, test_alert_data)
    elif channel == "slack":
        if not SlackSender:
            return jsonify({"error": "Slack sender not available"}), 503
        sender = SlackSender()
        success = sender.send_alert(recipient, test_alert_data)
    else:
        return jsonify({"error": f"Test notifications not yet supported for {channel}"}), 400

    if success:
        history_entry = NotificationHistory(
            notification_id=None,
            user_id=current_id,
            channel=channel,
            status="sent",
            duration_ms=0,
        )
        db.session.add(history_entry)
        db.session.commit()
        return jsonify({"message": f"Test {channel} notification sent successfully"}), 200

    return jsonify({"error": f"Failed to send test {channel} notification"}), 502


# ---------------------------------------------------------------------------
# Rate limit status
# ---------------------------------------------------------------------------

@notifications_bp.route("/rate-limits", methods=["GET"])
@jwt_required()
def get_rate_limits():
    """Return remaining send budget per channel for the current user."""
    current_id = _current_user_id()
    from services.notifications.rate_limiter import RateLimiter
    limiter = RateLimiter()
    limits = {ch: limiter.get_remaining(current_id, ch) for ch in VALID_CHANNELS}
    return jsonify({"rate_limits": limits}), 200
