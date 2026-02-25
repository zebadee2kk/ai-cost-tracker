"""Rate limiter for outbound notifications.

Prevents notification spam by enforcing per-user, per-channel hourly and
daily send limits.  Limits are checked against the ``notification_history``
table so they survive process restarts.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

logger = logging.getLogger(__name__)

# Default limits (max notifications per user per channel per time window).
DEFAULT_LIMITS: Dict[str, Dict[str, int]] = {
    "email": {"per_hour": 10, "per_day": 50},
    "slack": {"per_hour": 20, "per_day": 100},
    "discord": {"per_hour": 20, "per_day": 100},
    "teams": {"per_hour": 20, "per_day": 100},
}

# Fallback when channel is not in DEFAULT_LIMITS.
_FALLBACK_LIMIT = {"per_hour": 10, "per_day": 50}


class RateLimiter:
    """Check and enforce per-user, per-channel notification rate limits.

    Args:
        limits: Optional override for channel limits.  Keys are channel
            names; values are dicts with ``per_hour`` and ``per_day`` keys.
    """

    def __init__(self, limits: Dict[str, Dict[str, int]] | None = None):
        self.limits = limits if limits is not None else DEFAULT_LIMITS

    def can_send(self, user_id: int, channel: str) -> bool:
        """Return True if the user has not exceeded rate limits for *channel*.

        Queries ``notification_history`` to count recent sends.

        Args:
            user_id: ID of the user whose limits are checked.
            channel: Notification channel ('email', 'slack', 'discord', 'teams').

        Returns:
            True if a notification may be sent; False if rate-limited.
        """
        from models.notification_history import NotificationHistory

        channel_limits = self.limits.get(channel, _FALLBACK_LIMIT)
        now = datetime.now(timezone.utc)

        # Hourly check
        one_hour_ago = now - timedelta(hours=1)
        hourly_count = (
            NotificationHistory.query.filter(
                NotificationHistory.user_id == user_id,
                NotificationHistory.channel == channel,
                NotificationHistory.created_at >= one_hour_ago,
            ).count()
        )
        if hourly_count >= channel_limits["per_hour"]:
            logger.info(
                "Rate limit (hourly) hit for user=%s channel=%s count=%s limit=%s",
                user_id,
                channel,
                hourly_count,
                channel_limits["per_hour"],
            )
            return False

        # Daily check
        one_day_ago = now - timedelta(days=1)
        daily_count = (
            NotificationHistory.query.filter(
                NotificationHistory.user_id == user_id,
                NotificationHistory.channel == channel,
                NotificationHistory.created_at >= one_day_ago,
            ).count()
        )
        if daily_count >= channel_limits["per_day"]:
            logger.info(
                "Rate limit (daily) hit for user=%s channel=%s count=%s limit=%s",
                user_id,
                channel,
                daily_count,
                channel_limits["per_day"],
            )
            return False

        return True

    def get_remaining(self, user_id: int, channel: str) -> Dict[str, int]:
        """Return remaining sends allowed within the current hour and day.

        Args:
            user_id: ID of the user to check.
            channel: Notification channel name.

        Returns:
            Dict with ``per_hour`` and ``per_day`` remaining counts.
        """
        from models.notification_history import NotificationHistory

        channel_limits = self.limits.get(channel, _FALLBACK_LIMIT)
        now = datetime.now(timezone.utc)

        hourly_count = NotificationHistory.query.filter(
            NotificationHistory.user_id == user_id,
            NotificationHistory.channel == channel,
            NotificationHistory.created_at >= now - timedelta(hours=1),
        ).count()

        daily_count = NotificationHistory.query.filter(
            NotificationHistory.user_id == user_id,
            NotificationHistory.channel == channel,
            NotificationHistory.created_at >= now - timedelta(days=1),
        ).count()

        return {
            "per_hour": max(0, channel_limits["per_hour"] - hourly_count),
            "per_day": max(0, channel_limits["per_day"] - daily_count),
        }
