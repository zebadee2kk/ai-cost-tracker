from datetime import datetime, timezone

from app import db


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    api_provider = db.Column(db.String(100), nullable=False)
    has_api = db.Column(db.Boolean, default=True, nullable=False)
    # JSON: e.g. {"gpt-4": {"input": 0.03, "output": 0.06}, ...}
    pricing_model = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    accounts = db.relationship("Account", back_populates="service", lazy="dynamic")
    usage_records = db.relationship(
        "UsageRecord", back_populates="service", lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "api_provider": self.api_provider,
            "has_api": self.has_api,
            "pricing_model": self.pricing_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Service {self.name}>"
