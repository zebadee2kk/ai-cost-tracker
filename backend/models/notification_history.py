from datetime import datetime, timezone

from app import db


class NotificationHistory(db.Model):
    __tablename__ = "notification_history"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(
        db.Integer,
        db.ForeignKey("notification_queue.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    # Time taken to deliver the notification in milliseconds
    duration_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.Index("ix_notification_history_created_at", "created_at"),
        db.Index("ix_notification_history_user_channel", "user_id", "channel"),
    )

    # Relationships
    notification = db.relationship("NotificationQueue", back_populates="history")
    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f"<NotificationHistory id={self.id} channel={self.channel} status={self.status}>"
        )
