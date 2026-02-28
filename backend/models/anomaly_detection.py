"""
Anomaly detection models.

AnomalyDetectionConfig - per-account sensitivity thresholds.
DetectedAnomaly        - individual anomaly events detected by the detector service.
"""

from datetime import datetime, timezone

from app import db

# Allowed sensitivity levels (sigma multipliers)
SENSITIVITY_LEVELS = [1.5, 2.0, 2.5]

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]


class AnomalyDetectionConfig(db.Model):
    """Per-account configuration for anomaly detection sensitivity."""

    __tablename__ = "anomaly_detection_configs"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Z-score sigma threshold: 1.5 (sensitive), 2.0 (default), 2.5 (conservative)
    sensitivity = db.Column(db.Float, nullable=False, default=2.0)
    # Rolling window in days for baseline calculation
    baseline_days = db.Column(db.Integer, nullable=False, default=30)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    account = db.relationship("Account", backref=db.backref("anomaly_config", uselist=False))

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "sensitivity": self.sensitivity,
            "baseline_days": self.baseline_days,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<AnomalyDetectionConfig account={self.account_id} "
            f"sensitivity={self.sensitivity}>"
        )


class DetectedAnomaly(db.Model):
    """Individual anomaly event detected for an account on a specific date."""

    __tablename__ = "detected_anomalies"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Date of the anomalous usage record (truncated to day)
    anomaly_date = db.Column(db.Date, nullable=False, index=True)

    # Cost on the anomalous day
    daily_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    # Baseline (rolling mean) against which the day was compared
    baseline_mean = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    baseline_std = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    # Actual z-score computed for the day
    z_score = db.Column(db.Float, nullable=False, default=0.0)
    # Dollar difference vs baseline mean
    cost_delta = db.Column(db.Numeric(10, 4), nullable=False, default=0)

    # Severity derived from z-score magnitude
    severity = db.Column(db.String(20), nullable=False, default="low")

    # Whether an alert/notification has already been sent for this anomaly
    is_acknowledged = db.Column(db.Boolean, nullable=False, default=False)
    # Optional human-readable description
    description = db.Column(db.Text, nullable=True)

    detected_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        # One anomaly record per account per day
        db.UniqueConstraint(
            "account_id", "anomaly_date", name="uq_detected_anomaly_account_date"
        ),
    )

    # Relationships
    account = db.relationship(
        "Account", backref=db.backref("detected_anomalies", lazy="dynamic")
    )

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account_name": self.account.account_name if self.account else None,
            "anomaly_date": self.anomaly_date.isoformat() if self.anomaly_date else None,
            "daily_cost": float(self.daily_cost) if self.daily_cost is not None else 0.0,
            "baseline_mean": (
                float(self.baseline_mean) if self.baseline_mean is not None else 0.0
            ),
            "baseline_std": (
                float(self.baseline_std) if self.baseline_std is not None else 0.0
            ),
            "z_score": self.z_score,
            "cost_delta": float(self.cost_delta) if self.cost_delta is not None else 0.0,
            "severity": self.severity,
            "is_acknowledged": self.is_acknowledged,
            "description": self.description,
            "detected_at": (
                self.detected_at.isoformat() if self.detected_at else None
            ),
        }

    def __repr__(self):
        return (
            f"<DetectedAnomaly account={self.account_id} "
            f"date={self.anomaly_date} severity={self.severity}>"
        )
