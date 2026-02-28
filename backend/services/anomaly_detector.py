"""
Anomaly detection service.

Uses a rolling 30-day statistical baseline (mean + std dev) with z-score
calculation to identify unusual daily spending spikes.

Sensitivity levels (sigma multipliers):
  1.5 – more sensitive, more alerts
  2.0 – default balanced threshold
  2.5 – conservative, fewer false positives

Usage:
    detector = AnomalyDetector()
    anomalies = detector.detect_anomalies(account_id=1, date_range=("2026-01-01", "2026-03-01"))
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

import numpy as np

from app import db
from models.anomaly_detection import AnomalyDetectionConfig, DetectedAnomaly, SENSITIVITY_LEVELS

logger = logging.getLogger(__name__)

# Default sensitivity when no config exists for an account
DEFAULT_SENSITIVITY = 2.0
DEFAULT_BASELINE_DAYS = 30

# Minimum history required before anomaly detection can run
MIN_HISTORY_DAYS = 7


def _severity_from_z(z_score: float) -> str:
    """Map a z-score magnitude to a human-readable severity level."""
    abs_z = abs(z_score)
    if abs_z >= 4.0:
        return "critical"
    if abs_z >= 3.0:
        return "high"
    if abs_z >= 2.0:
        return "medium"
    return "low"


class AnomalyDetector:
    """
    Statistical anomaly detector for daily AI service costs.

    For each day in the requested range the detector:
    1. Fetches the rolling ``baseline_days`` window *before* the target day.
    2. Computes mean and std dev of costs in that window.
    3. Calculates the z-score of the target day's cost.
    4. If |z-score| > sensitivity threshold, records a DetectedAnomaly.
    """

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_anomalies(
        self,
        account_id: int,
        date_range: Optional[Tuple[str, str]] = None,
    ) -> List[DetectedAnomaly]:
        """
        Detect cost anomalies for *account_id* within *date_range*.

        Parameters
        ----------
        account_id : int
        date_range : (start_date_str, end_date_str) | None
            ISO-8601 date strings.  Defaults to last 30 days.

        Returns
        -------
        list[DetectedAnomaly]
            Newly created or updated anomaly records (already committed).
        """
        config = self._get_config(account_id)
        sensitivity = config.sensitivity if config else DEFAULT_SENSITIVITY
        baseline_days = config.baseline_days if config else DEFAULT_BASELINE_DAYS

        # Skip if detection is disabled for this account
        if config and not config.is_enabled:
            return []

        start_dt, end_dt = self._parse_date_range(date_range)

        # Fetch all cost data needed (baseline window + target range)
        fetch_start = start_dt - timedelta(days=baseline_days + 1)
        daily_costs = self._fetch_daily_costs(account_id, fetch_start, end_dt)

        if not daily_costs:
            logger.debug("No usage data for account %d; skipping anomaly detection.", account_id)
            return []

        anomalies = []
        current = start_dt
        while current <= end_dt:
            anomaly = self._evaluate_day(
                account_id=account_id,
                target_date=current,
                daily_costs=daily_costs,
                sensitivity=sensitivity,
                baseline_days=baseline_days,
            )
            if anomaly:
                anomalies.append(anomaly)
            current += timedelta(days=1)

        if anomalies:
            logger.info(
                "Detected %d anomaly(ies) for account %d between %s and %s.",
                len(anomalies),
                account_id,
                start_dt.isoformat(),
                end_dt.isoformat(),
            )
            self._queue_anomaly_notifications(account_id, anomalies)

        return anomalies

    def get_anomalies(
        self,
        account_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        acknowledged: Optional[bool] = None,
    ) -> List[DetectedAnomaly]:
        """
        Query previously detected anomalies for an account (read-only).
        """
        q = DetectedAnomaly.query.filter_by(account_id=account_id)
        if start_date:
            q = q.filter(DetectedAnomaly.anomaly_date >= start_date)
        if end_date:
            q = q.filter(DetectedAnomaly.anomaly_date <= end_date)
        if acknowledged is not None:
            q = q.filter_by(is_acknowledged=acknowledged)
        return q.order_by(DetectedAnomaly.anomaly_date.desc()).all()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_config(self, account_id: int) -> Optional[AnomalyDetectionConfig]:
        return AnomalyDetectionConfig.query.filter_by(account_id=account_id).first()

    def _parse_date_range(
        self, date_range: Optional[Tuple[str, str]]
    ) -> Tuple[date, date]:
        today = datetime.now(timezone.utc).date()
        if date_range:
            start_dt = (
                datetime.strptime(date_range[0], "%Y-%m-%d").date()
                if isinstance(date_range[0], str)
                else date_range[0]
            )
            end_dt = (
                datetime.strptime(date_range[1], "%Y-%m-%d").date()
                if isinstance(date_range[1], str)
                else date_range[1]
            )
        else:
            end_dt = today
            start_dt = today - timedelta(days=30)
        return start_dt, end_dt

    def _fetch_daily_costs(
        self, account_id: int, start: date, end: date
    ) -> dict:
        """
        Return a dict of {date: total_cost} for the account in [start, end].
        """
        from models.usage_record import UsageRecord
        from sqlalchemy import func

        rows = (
            db.session.query(
                func.date(UsageRecord.timestamp).label("day"),
                func.sum(UsageRecord.cost).label("total_cost"),
            )
            .filter(
                UsageRecord.account_id == account_id,
                func.date(UsageRecord.timestamp) >= start.isoformat(),
                func.date(UsageRecord.timestamp) <= end.isoformat(),
            )
            .group_by(func.date(UsageRecord.timestamp))
            .all()
        )

        result = {}
        for row in rows:
            day_key = (
                datetime.strptime(row.day, "%Y-%m-%d").date()
                if isinstance(row.day, str)
                else row.day
            )
            result[day_key] = float(row.total_cost or 0)
        return result

    def _evaluate_day(
        self,
        account_id: int,
        target_date: date,
        daily_costs: dict,
        sensitivity: float,
        baseline_days: int,
    ) -> Optional[DetectedAnomaly]:
        """
        Compute z-score for *target_date* using rolling baseline window.

        Returns a DetectedAnomaly (persisted) if the day is anomalous, else None.
        """
        daily_cost = daily_costs.get(target_date)
        if daily_cost is None:
            # No data for this day - not an anomaly
            return None

        # Build baseline from the preceding `baseline_days` days
        baseline_values = []
        for i in range(1, baseline_days + 1):
            d = target_date - timedelta(days=i)
            if d in daily_costs:
                baseline_values.append(daily_costs[d])

        if len(baseline_values) < MIN_HISTORY_DAYS:
            # Insufficient history - skip
            return None

        arr = np.array(baseline_values, dtype=float)
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))  # sample std dev

        # If std is zero (all costs identical), no spike possible
        if std == 0:
            return None

        z_score = (daily_cost - mean) / std

        if abs(z_score) <= sensitivity:
            return None

        # --- Anomaly detected ---
        cost_delta = daily_cost - mean
        severity = _severity_from_z(z_score)
        description = (
            f"Daily cost ${daily_cost:.4f} deviated {z_score:+.2f}σ from "
            f"30-day baseline (mean=${mean:.4f}, std=${std:.4f})."
        )

        # Upsert: one record per account per day
        existing = DetectedAnomaly.query.filter_by(
            account_id=account_id, anomaly_date=target_date
        ).first()

        if existing:
            existing.daily_cost = Decimal(str(daily_cost))
            existing.baseline_mean = Decimal(str(mean))
            existing.baseline_std = Decimal(str(std))
            existing.z_score = z_score
            existing.cost_delta = Decimal(str(cost_delta))
            existing.severity = severity
            existing.description = description
            db.session.commit()
            return existing

        anomaly = DetectedAnomaly(
            account_id=account_id,
            anomaly_date=target_date,
            daily_cost=Decimal(str(daily_cost)),
            baseline_mean=Decimal(str(mean)),
            baseline_std=Decimal(str(std)),
            z_score=z_score,
            cost_delta=Decimal(str(cost_delta)),
            severity=severity,
            description=description,
        )
        db.session.add(anomaly)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception(
                "Failed to persist anomaly for account %d on %s.", account_id, target_date
            )
            return None

        return anomaly

    def _queue_anomaly_notifications(
        self, account_id: int, anomalies: List[DetectedAnomaly]
    ) -> None:
        """
        For each new (unacknowledged) anomaly, create alert + notification queue entries.
        Uses the existing alert_generator infrastructure.
        """
        from models.account import Account
        from models.alert import Alert
        from utils.alert_generator import _queue_notifications

        account = Account.query.get(account_id)
        if not account:
            return

        for anomaly in anomalies:
            if anomaly.is_acknowledged:
                continue

            # Check for existing unacknowledged alert for this anomaly date
            existing_alert = Alert.query.filter_by(
                account_id=account_id,
                alert_type="unusual_activity",
                is_acknowledged=False,
            ).first()

            now = datetime.now(timezone.utc)
            if existing_alert:
                existing_alert.last_triggered = now
                existing_alert.message = anomaly.description
                db.session.commit()
            else:
                alert = Alert(
                    account_id=account_id,
                    alert_type="unusual_activity",
                    threshold_percentage=0,
                    is_active=True,
                    is_acknowledged=False,
                    last_triggered=now,
                    notification_method="dashboard",
                    message=anomaly.description or f"Cost anomaly detected: {anomaly.severity} severity.",
                )
                db.session.add(alert)
                db.session.flush()
                db.session.commit()
                _queue_notifications(account, alert, "unusual_activity")
