from datetime import datetime, timezone

from app import db


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 'email', 'slack', 'discord', 'teams'
    channel = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    # Channel-specific config: {"address": "..."} for email,
    # {"webhook_url": "..."} for Slack/Discord/Teams.
    config = db.Column(db.JSON, nullable=True)
    # Subset of alert types the user wants on this channel:
    # e.g. ['budget', 'anomaly', 'system']
    alert_types = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "channel", name="uq_notification_preferences_user_channel"
        ),
    )

    # Relationships
    user = db.relationship("User", back_populates="notification_preferences")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel": self.channel,
            "enabled": self.enabled,
            "config": self.config,
            "alert_types": self.alert_types,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<NotificationPreference user={self.user_id} channel={self.channel}>"
