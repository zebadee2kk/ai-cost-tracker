from datetime import datetime, timezone

from app import db


class CostProjection(db.Model):
    __tablename__ = "cost_projections"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True
    )

    # First day of the month this projection covers
    month = db.Column(db.Date, nullable=False)
    projected_cost = db.Column(db.Numeric(10, 4), nullable=False)
    # Populated at month end
    actual_cost = db.Column(db.Numeric(10, 4), nullable=True)
    # 0–100 confidence score based on available data
    confidence_score = db.Column(db.Numeric(5, 2), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    account = db.relationship("Account", back_populates="cost_projections")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "month": self.month.isoformat() if self.month else None,
            "projected_cost": float(self.projected_cost) if self.projected_cost is not None else None,
            "actual_cost": float(self.actual_cost) if self.actual_cost is not None else None,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<CostProjection account={self.account_id} month={self.month}>"
