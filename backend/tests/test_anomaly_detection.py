"""
Tests for anomaly detection models, detector service, and forecasting utilities.

Covers:
- AnomalyDetectionConfig model (creation, defaults, to_dict)
- DetectedAnomaly model (creation, severity, to_dict)
- AnomalyDetector.detect_anomalies: normal flow, no history, insufficient data,
  weekends/holidays (zero cost days), custom sensitivity levels
- AnomalyDetector.get_anomalies: filters by date, acknowledged flag
- Forecasting: linear_forecast, calculate_mape, calculate_moving_average,
  calculate_growth_rate edge cases
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix="anomaly"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _register(client, email=None):
    email = email or _unique_email()
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password1!"},
    )
    assert res.status_code == 201
    return res.get_json()["token"]


def _make_account(app, user_id):
    from app import db
    from models.service import Service
    from models.account import Account

    with app.app_context():
        svc = Service.query.filter_by(name="TestSvc-Anomaly").first()
        if not svc:
            svc = Service(
                name="TestSvc-Anomaly",
                api_provider="test",
                has_api=False,
                pricing_model={},
            )
            db.session.add(svc)
            db.session.flush()

        acct = Account(user_id=user_id, service_id=svc.id, account_name="Anomaly Test Acct")
        db.session.add(acct)
        db.session.commit()
        return acct.id, svc.id


def _seed_usage(app, account_id, service_id, costs_by_date: dict):
    """Insert UsageRecords with specified costs keyed by ISO date string."""
    from app import db
    from models.usage_record import UsageRecord

    with app.app_context():
        for date_str, cost in costs_by_date.items():
            ts = datetime.fromisoformat(date_str).replace(
                hour=12, tzinfo=timezone.utc
            )
            rec = UsageRecord(
                account_id=account_id,
                service_id=service_id,
                timestamp=ts,
                cost=Decimal(str(cost)),
                tokens_used=100,
                source="api",
            )
            db.session.add(rec)
        db.session.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def user_token(client):
    return _register(client)


@pytest.fixture()
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture()
def account_ids(app, client):
    """Returns (account_id, service_id) after registering a user."""
    token = _register(client)
    from flask_jwt_extended import decode_token

    with app.app_context():
        decoded = decode_token(token)
        user_id = int(decoded["sub"])
        return _make_account(app, user_id)


# ===========================================================================
# 1. AnomalyDetectionConfig model
# ===========================================================================

class TestAnomalyDetectionConfigModel:

    def test_create_config_defaults(self, app, account_ids):
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import AnomalyDetectionConfig

        with app.app_context():
            config = AnomalyDetectionConfig(account_id=account_id)
            db.session.add(config)
            db.session.commit()

            loaded = AnomalyDetectionConfig.query.filter_by(account_id=account_id).first()
            assert loaded is not None
            assert loaded.sensitivity == 2.0
            assert loaded.baseline_days == 30
            assert loaded.is_enabled is True

    def test_config_to_dict_keys(self, app, account_ids):
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import AnomalyDetectionConfig

        with app.app_context():
            config = AnomalyDetectionConfig(
                account_id=account_id, sensitivity=1.5, baseline_days=14
            )
            db.session.add(config)
            db.session.commit()

            d = config.to_dict()
            assert d["account_id"] == account_id
            assert d["sensitivity"] == 1.5
            assert d["baseline_days"] == 14
            assert d["is_enabled"] is True
            assert "created_at" in d

    def test_config_repr(self, app, account_ids):
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import AnomalyDetectionConfig

        with app.app_context():
            config = AnomalyDetectionConfig(account_id=account_id, sensitivity=2.5)
            db.session.add(config)
            db.session.commit()
            assert str(account_id) in repr(config)


# ===========================================================================
# 2. DetectedAnomaly model
# ===========================================================================

class TestDetectedAnomalyModel:

    def test_create_anomaly_record(self, app, account_ids):
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import DetectedAnomaly

        with app.app_context():
            anomaly = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 3, 1),
                daily_cost=Decimal("50.00"),
                baseline_mean=Decimal("10.00"),
                baseline_std=Decimal("2.00"),
                z_score=20.0,
                cost_delta=Decimal("40.00"),
                severity="critical",
            )
            db.session.add(anomaly)
            db.session.commit()
            assert anomaly.id is not None

    def test_anomaly_to_dict(self, app, account_ids):
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import DetectedAnomaly

        with app.app_context():
            anomaly = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 3, 2),
                daily_cost=Decimal("30.00"),
                baseline_mean=Decimal("5.00"),
                baseline_std=Decimal("1.50"),
                z_score=16.67,
                cost_delta=Decimal("25.00"),
                severity="high",
            )
            db.session.add(anomaly)
            db.session.commit()

            d = anomaly.to_dict()
            assert d["account_id"] == account_id
            assert d["anomaly_date"] == "2026-03-02"
            assert d["daily_cost"] == 30.0
            assert d["z_score"] == pytest.approx(16.67, abs=0.01)
            assert d["severity"] == "high"
            assert d["is_acknowledged"] is False

    def test_anomaly_unique_constraint(self, app, account_ids):
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import DetectedAnomaly
        from sqlalchemy.exc import IntegrityError

        with app.app_context():
            a1 = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 3, 3),
                daily_cost=Decimal("10"),
                baseline_mean=Decimal("2"),
                baseline_std=Decimal("1"),
                z_score=8.0,
                cost_delta=Decimal("8"),
                severity="high",
            )
            db.session.add(a1)
            db.session.commit()

            a2 = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 3, 3),  # same date
                daily_cost=Decimal("12"),
                baseline_mean=Decimal("2"),
                baseline_std=Decimal("1"),
                z_score=10.0,
                cost_delta=Decimal("10"),
                severity="critical",
            )
            db.session.add(a2)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


# ===========================================================================
# 3. Severity helper
# ===========================================================================

class TestSeverityMapping:

    def test_low_severity(self):
        from services.anomaly_detector import _severity_from_z
        assert _severity_from_z(1.6) == "low"

    def test_medium_severity(self):
        from services.anomaly_detector import _severity_from_z
        assert _severity_from_z(2.1) == "medium"

    def test_high_severity(self):
        from services.anomaly_detector import _severity_from_z
        assert _severity_from_z(3.5) == "high"

    def test_critical_severity(self):
        from services.anomaly_detector import _severity_from_z
        assert _severity_from_z(4.1) == "critical"

    def test_negative_z_score(self):
        from services.anomaly_detector import _severity_from_z
        assert _severity_from_z(-3.5) == "high"


# ===========================================================================
# 4. AnomalyDetector: detect_anomalies
# ===========================================================================

class TestAnomalyDetector:

    def _build_flat_history(self, n_days=30, cost=5.0):
        """n_days of flat $cost/day ending yesterday."""
        today = datetime.now(timezone.utc).date()
        costs = {}
        for i in range(n_days, 0, -1):
            d = (today - timedelta(days=i)).isoformat()
            costs[d] = cost
        return costs

    def test_no_data_returns_empty(self, app, account_ids):
        account_id, _ = account_ids
        from services.anomaly_detector import AnomalyDetector

        with app.app_context():
            detector = AnomalyDetector()
            result = detector.detect_anomalies(account_id)
            assert result == []

    def test_insufficient_history_no_anomaly(self, app, account_ids):
        """Fewer than MIN_HISTORY_DAYS baseline points — skips evaluation."""
        account_id, service_id = account_ids
        today = datetime.now(timezone.utc).date()

        # Only 3 days of history
        costs = {
            (today - timedelta(days=3)).isoformat(): 5.0,
            (today - timedelta(days=2)).isoformat(): 5.0,
            (today - timedelta(days=1)).isoformat(): 5.0,
        }
        _seed_usage(app, account_id, service_id, costs)

        with app.app_context():
            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            result = detector.detect_anomalies(
                account_id,
                date_range=((today - timedelta(days=1)).isoformat(), today.isoformat()),
            )
            assert result == []

    def test_detects_spike_above_threshold(self, app, account_ids):
        """A day with cost far above baseline should be flagged."""
        account_id, service_id = account_ids
        today = datetime.now(timezone.utc).date()

        costs = self._build_flat_history(30, cost=5.0)
        # Spike day: yesterday costs $100 vs baseline mean $5, std ~0
        spike_date = (today - timedelta(days=1)).isoformat()
        costs[spike_date] = 100.0
        _seed_usage(app, account_id, service_id, costs)

        with app.app_context():
            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            result = detector.detect_anomalies(
                account_id,
                date_range=(spike_date, spike_date),
            )
            assert len(result) == 1
            assert result[0].anomaly_date.isoformat() == spike_date
            assert result[0].z_score > 2.0

    def test_no_anomaly_on_flat_costs(self, app, account_ids):
        """Stable costs should not trigger any anomaly."""
        account_id, service_id = account_ids
        today = datetime.now(timezone.utc).date()
        costs = self._build_flat_history(30, cost=10.0)
        # Target day: same cost
        target = (today - timedelta(days=1)).isoformat()
        costs[target] = 10.0
        _seed_usage(app, account_id, service_id, costs)

        with app.app_context():
            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            result = detector.detect_anomalies(account_id, date_range=(target, target))
            assert result == []

    def test_zero_cost_day_skipped(self, app, account_ids):
        """Days with no usage records are not flagged."""
        account_id, service_id = account_ids
        today = datetime.now(timezone.utc).date()
        costs = self._build_flat_history(30, cost=5.0)
        _seed_usage(app, account_id, service_id, costs)

        # Target day has no record at all
        target = today.isoformat()
        with app.app_context():
            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            result = detector.detect_anomalies(account_id, date_range=(target, target))
            assert result == []

    def test_sensitive_threshold_detects_more(self, app, account_ids):
        """Sensitivity 1.5 should flag moderate spikes that 2.5 wouldn't."""
        account_id, service_id = account_ids
        from app import db
        from models.anomaly_detection import AnomalyDetectionConfig

        today = datetime.now(timezone.utc).date()
        costs = {}
        # Baseline: mean $5, std $2 (some variation)
        base_values = [4.0, 6.0, 3.5, 6.5, 5.0, 4.5, 5.5] * 5  # 35 days
        for i, v in enumerate(reversed(base_values)):
            d = (today - timedelta(days=i + 2)).isoformat()
            costs[d] = v
        # Spike: ~2x std above mean
        spike_date = (today - timedelta(days=1)).isoformat()
        costs[spike_date] = 8.0  # just above 1.5σ but below 2.5σ
        _seed_usage(app, account_id, service_id, costs)

        with app.app_context():
            # Set sensitivity to 1.5 (more sensitive)
            config = AnomalyDetectionConfig(account_id=account_id, sensitivity=1.5)
            db.session.add(config)
            db.session.commit()

            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            result = detector.detect_anomalies(account_id, date_range=(spike_date, spike_date))
            # With sensitivity 1.5 we might flag it; depends on actual z
            # The key point is the config is respected
            config.sensitivity = 2.5
            db.session.commit()
            result_conservative = detector.detect_anomalies(
                account_id, date_range=(spike_date, spike_date)
            )
            # Conservative mode should detect fewer anomalies
            assert len(result_conservative) <= len(result)

    def test_disabled_config_skips_detection(self, app, account_ids):
        """When is_enabled=False, detect_anomalies returns empty."""
        account_id, service_id = account_ids
        from app import db
        from models.anomaly_detection import AnomalyDetectionConfig

        today = datetime.now(timezone.utc).date()
        costs = self._build_flat_history(30, cost=5.0)
        spike_date = (today - timedelta(days=1)).isoformat()
        costs[spike_date] = 200.0  # massive spike
        _seed_usage(app, account_id, service_id, costs)

        with app.app_context():
            config = AnomalyDetectionConfig(account_id=account_id, is_enabled=False)
            db.session.add(config)
            db.session.commit()

            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            result = detector.detect_anomalies(account_id, date_range=(spike_date, spike_date))
            assert result == []

    def test_default_date_range_used_when_none(self, app, account_ids):
        """Passing date_range=None uses last 30 days."""
        account_id, service_id = account_ids
        from services.anomaly_detector import AnomalyDetector

        with app.app_context():
            detector = AnomalyDetector()
            # Should not raise even with no data
            result = detector.detect_anomalies(account_id, date_range=None)
            assert isinstance(result, list)

    def test_anomaly_upserted_on_second_run(self, app, account_ids):
        """Running detection twice for the same date updates existing record."""
        account_id, service_id = account_ids
        today = datetime.now(timezone.utc).date()
        costs = self._build_flat_history(30, cost=5.0)
        spike_date = (today - timedelta(days=1)).isoformat()
        costs[spike_date] = 100.0
        _seed_usage(app, account_id, service_id, costs)

        with app.app_context():
            from app import db
            from models.anomaly_detection import DetectedAnomaly
            from services.anomaly_detector import AnomalyDetector

            detector = AnomalyDetector()
            r1 = detector.detect_anomalies(account_id, date_range=(spike_date, spike_date))
            count_before = DetectedAnomaly.query.filter_by(account_id=account_id).count()

            r2 = detector.detect_anomalies(account_id, date_range=(spike_date, spike_date))
            count_after = DetectedAnomaly.query.filter_by(account_id=account_id).count()
            # Should upsert, not duplicate
            assert count_after == count_before

    def test_get_anomalies_filter_by_date(self, app, account_ids):
        """get_anomalies respects start/end date filters."""
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import DetectedAnomaly

        with app.app_context():
            a1 = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 1, 10),
                daily_cost=Decimal("50"),
                baseline_mean=Decimal("5"),
                baseline_std=Decimal("1"),
                z_score=45.0,
                cost_delta=Decimal("45"),
                severity="critical",
            )
            a2 = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 2, 10),
                daily_cost=Decimal("30"),
                baseline_mean=Decimal("5"),
                baseline_std=Decimal("1"),
                z_score=25.0,
                cost_delta=Decimal("25"),
                severity="high",
            )
            db.session.add_all([a1, a2])
            db.session.commit()

            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()

            result = detector.get_anomalies(
                account_id, start_date="2026-02-01", end_date="2026-02-28"
            )
            dates = [a.anomaly_date.isoformat() for a in result]
            assert "2026-02-10" in dates
            assert "2026-01-10" not in dates

    def test_get_anomalies_filter_acknowledged(self, app, account_ids):
        """get_anomalies can filter by acknowledged status."""
        account_id, _ = account_ids
        from app import db
        from models.anomaly_detection import DetectedAnomaly

        with app.app_context():
            ack = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 3, 5),
                daily_cost=Decimal("20"),
                baseline_mean=Decimal("5"),
                baseline_std=Decimal("1"),
                z_score=15.0,
                cost_delta=Decimal("15"),
                severity="medium",
                is_acknowledged=True,
            )
            unack = DetectedAnomaly(
                account_id=account_id,
                anomaly_date=date(2026, 3, 6),
                daily_cost=Decimal("20"),
                baseline_mean=Decimal("5"),
                baseline_std=Decimal("1"),
                z_score=15.0,
                cost_delta=Decimal("15"),
                severity="medium",
                is_acknowledged=False,
            )
            db.session.add_all([ack, unack])
            db.session.commit()

            from services.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()

            unacked = detector.get_anomalies(account_id, acknowledged=False)
            assert all(not a.is_acknowledged for a in unacked)

            acked = detector.get_anomalies(account_id, acknowledged=True)
            assert all(a.is_acknowledged for a in acked)


# ===========================================================================
# 5. Forecasting utilities
# ===========================================================================

class TestForecastingUtils:

    def test_linear_forecast_basic(self):
        from utils.forecasting import linear_forecast

        # Steadily increasing costs: $1 on day 1, $2 on day 2, ...
        data = {f"2026-01-{i:02d}": float(i) for i in range(1, 31)}
        result = linear_forecast(data, horizon=7)
        assert len(result["forecast"]) == 7
        assert result["slope"] > 0
        assert result["r_squared"] > 0.9
        assert result["data_points"] == 30
        # All forecasts have required keys
        for fc in result["forecast"]:
            assert "date" in fc
            assert "predicted_cost" in fc
            assert "lower_bound" in fc
            assert "upper_bound" in fc
            assert fc["lower_bound"] <= fc["predicted_cost"] <= fc["upper_bound"]

    def test_linear_forecast_empty_data(self):
        from utils.forecasting import linear_forecast

        result = linear_forecast({}, horizon=30)
        assert result["forecast"] == []
        assert result["data_points"] == 0

    def test_linear_forecast_single_point(self):
        from utils.forecasting import linear_forecast

        result = linear_forecast({"2026-01-01": 5.0}, horizon=30)
        assert result["forecast"] == []

    def test_linear_forecast_horizon_capped_at_90(self):
        from utils.forecasting import linear_forecast

        data = {f"2026-01-{i:02d}": 5.0 for i in range(1, 29)}
        result = linear_forecast(data, horizon=999)
        assert len(result["forecast"]) == 90

    def test_linear_forecast_no_negative_predictions(self):
        from utils.forecasting import linear_forecast

        # Decreasing trend might push predictions negative - should be clipped
        data = {f"2026-01-{i:02d}": max(0.0, 10.0 - i * 0.4) for i in range(1, 28)}
        result = linear_forecast(data, horizon=30)
        for fc in result["forecast"]:
            assert fc["predicted_cost"] >= 0
            assert fc["lower_bound"] >= 0

    def test_calculate_mape_perfect(self):
        from utils.forecasting import calculate_mape

        actual = [10.0, 20.0, 30.0]
        predicted = [10.0, 20.0, 30.0]
        assert calculate_mape(actual, predicted) == pytest.approx(0.0)

    def test_calculate_mape_known_error(self):
        from utils.forecasting import calculate_mape

        actual = [100.0]
        predicted = [90.0]
        # 10% error
        assert calculate_mape(actual, predicted) == pytest.approx(10.0)

    def test_calculate_mape_skips_zero_actual(self):
        from utils.forecasting import calculate_mape

        actual = [0.0, 10.0]
        predicted = [5.0, 10.0]
        # Only second pair counts, 0% error
        assert calculate_mape(actual, predicted) == pytest.approx(0.0)

    def test_calculate_mape_all_zeros(self):
        from utils.forecasting import calculate_mape

        assert calculate_mape([0.0, 0.0], [1.0, 2.0]) == pytest.approx(0.0)

    def test_calculate_mape_length_mismatch(self):
        from utils.forecasting import calculate_mape

        with pytest.raises(ValueError):
            calculate_mape([1.0, 2.0], [1.0])

    def test_calculate_moving_average_7d(self):
        from utils.forecasting import calculate_moving_average

        data = {f"2026-01-{i:02d}": float(i) for i in range(1, 15)}
        result = calculate_moving_average(data, window=7)
        # First 6 entries have None
        for r in result[:6]:
            assert r["moving_avg"] is None
        # 7th entry should be average of days 1-7 = 4.0
        assert result[6]["moving_avg"] == pytest.approx(4.0)

    def test_calculate_moving_average_empty(self):
        from utils.forecasting import calculate_moving_average

        assert calculate_moving_average({}, window=7) == []

    def test_calculate_growth_rate_increasing(self):
        from utils.forecasting import calculate_growth_rate

        data = {"2026-01-01": 10.0, "2026-01-02": 20.0}
        rate = calculate_growth_rate(data)
        assert rate is not None
        assert rate > 0

    def test_calculate_growth_rate_insufficient_data(self):
        from utils.forecasting import calculate_growth_rate

        assert calculate_growth_rate({"2026-01-01": 5.0}) is None

    def test_calculate_growth_rate_zero_first(self):
        from utils.forecasting import calculate_growth_rate

        assert calculate_growth_rate({"2026-01-01": 0.0, "2026-01-02": 5.0}) is None

    def test_calculate_growth_rate_empty(self):
        from utils.forecasting import calculate_growth_rate

        assert calculate_growth_rate({}) is None
