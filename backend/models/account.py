from datetime import datetime, timezone

from app import db


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)

    account_name = db.Column(db.String(200), nullable=False)
    # Stored encrypted (AES-256 via Fernet); never stored in plaintext
    api_key = db.Column(db.Text, nullable=True)
    auth_token = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    monthly_limit = db.Column(db.Numeric(10, 4), nullable=True)
    session_limit = db.Column(db.Integer, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_sync = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", back_populates="accounts")
    service = db.relationship("Service", back_populates="accounts")
    usage_records = db.relationship(
        "UsageRecord", back_populates="account", lazy="dynamic"
    )
    alerts = db.relationship("Alert", back_populates="account", lazy="dynamic")
    cost_projections = db.relationship(
        "CostProjection", back_populates="account", lazy="dynamic"
    )

    def to_dict(self, include_key=False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "service_id": self.service_id,
            "service_name": self.service.name if self.service else None,
            "account_name": self.account_name,
            "is_active": self.is_active,
            "monthly_limit": float(self.monthly_limit) if self.monthly_limit else None,
            "session_limit": self.session_limit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            # Never expose the raw encrypted key; just indicate whether one is set
            "has_api_key": bool(self.api_key),
        }
        return data

    def __repr__(self):
        return f"<Account {self.account_name}>"
