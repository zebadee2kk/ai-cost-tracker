from datetime import datetime, timezone

from app import db


class UsageRecord(db.Model):
    __tablename__ = "usage_records"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True
    )
    service_id = db.Column(
        db.Integer, db.ForeignKey("services.id"), nullable=False, index=True
    )

    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    tokens_used = db.Column(db.Integer, default=0)
    tokens_remaining = db.Column(db.Integer, nullable=True)
    # DECIMAL(10,4) for cost precision
    cost = db.Column(db.Numeric(10, 4), default=0)
    cost_currency = db.Column(db.String(10), default="USD")
    sessions_active = db.Column(db.Integer, nullable=True)
    api_calls = db.Column(db.Integer, default=1)
    request_type = db.Column(db.String(100), nullable=True)
    # Flexible JSON for service-specific data (model name, input/output tokens, etc.)
    # Named 'extra_data' because 'metadata' is reserved by SQLAlchemy's Declarative API
    extra_data = db.Column("metadata", db.JSON, nullable=True, default=dict)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    account = db.relationship("Account", back_populates="usage_records")
    service = db.relationship("Service", back_populates="usage_records")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "service_id": self.service_id,
            "service_name": self.service.name if self.service else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tokens_used": self.tokens_used,
            "tokens_remaining": self.tokens_remaining,
            "cost": float(self.cost) if self.cost is not None else 0.0,
            "cost_currency": self.cost_currency,
            "sessions_active": self.sessions_active,
            "api_calls": self.api_calls,
            "request_type": self.request_type,
            "metadata": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<UsageRecord account={self.account_id} cost={self.cost}>"
