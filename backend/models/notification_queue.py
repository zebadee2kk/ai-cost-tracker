from datetime import datetime, timezone

from app import db


class NotificationQueue(db.Model):
    __tablename__ = "notification_queue"

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(
        db.Integer,
        db.ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = db.Column(db.String(50), nullable=False)
    # Email address or webhook URL
    recipient = db.Column(db.Text, nullable=False)
    # 1=low, 2=medium, 3=high
    priority = db.Column(db.Integer, nullable=False, default=1)
    # 'pending', 'sent', 'failed', 'cancelled'
    status = db.Column(db.String(20), nullable=False, default="pending")
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    max_retries = db.Column(db.Integer, nullable=False, default=3)
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.Index("ix_notification_queue_status_priority", "status", "priority"),
    )

    # Relationships
    alert = db.relationship("Alert")
    user = db.relationship("User")
    history = db.relationship(
        "NotificationHistory", back_populates="notification", lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "recipient": self.recipient,
            "priority": self.priority,
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f"<NotificationQueue id={self.id} channel={self.channel} status={self.status}>"
        )
