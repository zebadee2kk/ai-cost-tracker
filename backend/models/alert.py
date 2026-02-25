from datetime import datetime, timezone

from app import db

ALERT_TYPES = [
    "approaching_limit",
    "limit_exceeded",
    "high_cost",
    "service_down",
    "unusual_activity",
]

NOTIFICATION_METHODS = ["dashboard", "email", "webhook"]


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True
    )

    alert_type = db.Column(db.String(50), nullable=False)
    threshold_percentage = db.Column(db.Integer, default=80)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    last_triggered = db.Column(db.DateTime(timezone=True), nullable=True)
    notification_method = db.Column(db.String(50), default="dashboard")
    message = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    account = db.relationship("Account", back_populates="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account_name": self.account.account_name if self.account else None,
            "alert_type": self.alert_type,
            "threshold_percentage": self.threshold_percentage,
            "is_active": self.is_active,
            "is_acknowledged": self.is_acknowledged,
            "last_triggered": (
                self.last_triggered.isoformat() if self.last_triggered else None
            ),
            "notification_method": self.notification_method,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Alert {self.alert_type} account={self.account_id}>"
