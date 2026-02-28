"""
Integration tests for /api/analytics/* endpoints.

Covers:
- GET /trends/<account_id>     – valid periods, metric types, missing account,
                                  no data, 401 unauthenticated
- GET /forecast/<account_id>   – valid horizons, insufficient data, 400 errors
- GET /anomalies/<account_id>  – list, date filter, acknowledged filter
- POST /anomalies/<account_id>/detect – trigger detection
- POST /anomalies/<id>/acknowledge   – acknowledge an anomaly
- GET/PUT /config/<account_id>       – config retrieval and update
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix="analytics"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _register_and_login(client):
    email = _unique_email()
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password1!"},
    )
    assert res.status_code == 201
    token = res.get_json()["token"]
    user_id = res.get_json()["user"]["id"]
    return token, user_id


def _make_account(app, user_id):
    from app import db
    from models.service import Service
    from models.account import Account

    with app.app_context():
        svc = Service.query.filter_by(name="AnalyticsSvc").first()
        if not svc:
            svc = Service(
                name="AnalyticsSvc",
                api_provider="test",
                has_api=False,
                pricing_model={},
            )
            db.session.add(svc)
            db.session.flush()

        acct = Account(
            user_id=user_id,
            service_id=svc.id,
            account_name="Analytics Test Account",
        )
        db.session.add(acct)
        db.session.commit()
        return acct.id, svc.id


def _seed_usage(app, account_id, service_id, n_days=30, cost=5.0):
    from app import db
    from models.usage_record import UsageRecord

    today = datetime.now(timezone.utc).date()
    with app.app_context():
        for i in range(n_days, 0, -1):
            ts = datetime.combine(
                today - timedelta(days=i), datetime.min.time()
            ).replace(hour=12, tzinfo=timezone.utc)
            db.session.add(
                UsageRecord(
                    account_id=account_id,
                    service_id=service_id,
                    timestamp=ts,
                    cost=Decimal(str(cost)),
                    tokens_used=500,
                    source="api",
                )
            )
        db.session.commit()


def _make_anomaly(app, account_id, anomaly_date="2026-03-01", acknowledged=False):
    from app import db
    from models.anomaly_detection import DetectedAnomaly
    from datetime import date

    with app.app_context():
        a = DetectedAnomaly(
            account_id=account_id,
            anomaly_date=date.fromisoformat(anomaly_date),
            daily_cost=Decimal("50"),
            baseline_mean=Decimal("5"),
            baseline_std=Decimal("1"),
            z_score=45.0,
            cost_delta=Decimal("45"),
            severity="critical",
            is_acknowledged=acknowledged,
        )
        db.session.add(a)
        db.session.commit()
        return a.id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def setup(client, app):
    """Returns (token, account_id, service_id) for a fresh user+account."""
    token, user_id = _register_and_login(client)
    account_id, service_id = _make_account(app, user_id)
    return token, account_id, service_id


@pytest.fixture()
def headers(setup):
    token, _, _ = setup
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def account_id(setup):
    _, account_id, _ = setup
    return account_id


@pytest.fixture()
def seeded_setup(client, app, setup):
    token, account_id, service_id = setup
    _seed_usage(app, account_id, service_id, n_days=35, cost=5.0)
    return token, account_id, service_id


# ===========================================================================
# GET /api/analytics/trends/<account_id>
# ===========================================================================

class TestTrendsEndpoint:

    def test_trends_requires_auth(self, client, account_id):
        res = client.get(f"/api/analytics/trends/{account_id}")
        assert res.status_code == 401

    def test_trends_default_period_cost(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/trends/{account_id}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["account_id"] == account_id
        assert data["period"] == "30d"
        assert data["metric"] == "cost"
        assert "daily" in data
        assert "moving_avg_7d" in data
        assert "total" in data

    def test_trends_7d_period(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/trends/{account_id}",
            query_string={"period": "7d"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.get_json()["period"] == "7d"

    def test_trends_90d_period(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/trends/{account_id}",
            query_string={"period": "90d"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.get_json()["period"] == "90d"

    def test_trends_tokens_metric(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/trends/{account_id}",
            query_string={"metric": "tokens"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.get_json()["metric"] == "tokens"

    def test_trends_invalid_period(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/trends/{account_id}",
            query_string={"period": "3d"},
            headers=headers,
        )
        assert res.status_code == 400

    def test_trends_invalid_metric(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/trends/{account_id}",
            query_string={"metric": "revenue"},
            headers=headers,
        )
        assert res.status_code == 400

    def test_trends_account_not_found(self, client, headers):
        res = client.get("/api/analytics/trends/999999", headers=headers)
        assert res.status_code == 404

    def test_trends_no_data_returns_empty(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/trends/{account_id}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["daily"] == []
        assert data["total"] == 0

    def test_trends_moving_avg_30d_only_for_30d_plus(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        # 7d period: moving_avg_30d should be empty
        res = client.get(
            f"/api/analytics/trends/{account_id}",
            query_string={"period": "7d"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.get_json()["moving_avg_30d"] == []

    def test_trends_growth_rate_present(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/trends/{account_id}", headers=headers)
        assert res.status_code == 200
        # growth_rate_pct can be None for <2 points, or a float
        data = res.get_json()
        assert "growth_rate_pct" in data


# ===========================================================================
# GET /api/analytics/forecast/<account_id>
# ===========================================================================

class TestForecastEndpoint:

    def test_forecast_requires_auth(self, client, account_id):
        res = client.get(f"/api/analytics/forecast/{account_id}")
        assert res.status_code == 401

    def test_forecast_default_30_days(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/forecast/{account_id}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["horizon_days"] == 30
        assert "forecast" in data
        assert "r_squared" in data
        assert "confidence_pct" in data

    def test_forecast_60_day_horizon(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/forecast/{account_id}",
            query_string={"horizon": 60},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["horizon_days"] == 60
        assert len(data["forecast"]) == 60

    def test_forecast_90_day_horizon(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/forecast/{account_id}",
            query_string={"horizon": 90},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.get_json()["horizon_days"] == 90

    def test_forecast_invalid_horizon(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/forecast/{account_id}",
            query_string={"horizon": 45},
            headers=headers,
        )
        assert res.status_code == 400

    def test_forecast_non_integer_horizon(self, client, seeded_setup):
        token, account_id, _ = seeded_setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(
            f"/api/analytics/forecast/{account_id}",
            query_string={"horizon": "abc"},
            headers=headers,
        )
        assert res.status_code == 400

    def test_forecast_no_data(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/forecast/{account_id}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["forecast"] == []

    def test_forecast_account_not_found(self, client, headers):
        res = client.get("/api/analytics/forecast/999999", headers=headers)
        assert res.status_code == 404


# ===========================================================================
# Anomaly list, detect, acknowledge
# ===========================================================================

class TestAnomalyEndpoints:

    def test_list_anomalies_empty(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/anomalies/{account_id}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["anomalies"] == []
        assert data["total"] == 0

    def test_list_anomalies_returns_records(self, client, app, setup):
        token, account_id, _ = setup
        _make_anomaly(app, account_id, "2026-03-04")
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/anomalies/{account_id}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] >= 1

    def test_list_anomalies_acknowledged_filter(self, client, app, setup):
        token, account_id, _ = setup
        _make_anomaly(app, account_id, "2026-03-07", acknowledged=False)
        _make_anomaly(app, account_id, "2026-03-08", acknowledged=True)
        headers = {"Authorization": f"Bearer {token}"}

        res_unack = client.get(
            f"/api/analytics/anomalies/{account_id}",
            query_string={"acknowledged": "false"},
            headers=headers,
        )
        assert res_unack.status_code == 200
        for a in res_unack.get_json()["anomalies"]:
            assert a["is_acknowledged"] is False

    def test_trigger_detection_no_data(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.post(
            f"/api/analytics/anomalies/{account_id}/detect",
            json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            headers=headers,
        )
        assert res.status_code == 201
        assert res.get_json()["detected"] == 0

    def test_acknowledge_anomaly(self, client, app, setup):
        token, account_id, _ = setup
        anomaly_id = _make_anomaly(app, account_id, "2026-03-09")
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post(
            f"/api/analytics/anomalies/{anomaly_id}/acknowledge",
            headers=headers,
        )
        assert res.status_code == 200
        assert res.get_json()["anomaly"]["is_acknowledged"] is True

    def test_acknowledge_nonexistent_anomaly(self, client, headers):
        res = client.post(
            "/api/analytics/anomalies/999999/acknowledge",
            headers=headers,
        )
        assert res.status_code == 404


# ===========================================================================
# GET/PUT /api/analytics/config/<account_id>
# ===========================================================================

class TestConfigEndpoints:

    def test_get_config_defaults(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get(f"/api/analytics/config/{account_id}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["sensitivity"] == 2.0
        assert data["baseline_days"] == 30
        assert data["is_enabled"] is True

    def test_put_config_creates_record(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.put(
            f"/api/analytics/config/{account_id}",
            json={"sensitivity": 1.5, "baseline_days": 14, "is_enabled": True},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["sensitivity"] == 1.5
        assert data["baseline_days"] == 14

    def test_put_config_invalid_sensitivity(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.put(
            f"/api/analytics/config/{account_id}",
            json={"sensitivity": 3.0},
            headers=headers,
        )
        assert res.status_code == 400

    def test_put_config_invalid_baseline_days(self, client, setup):
        token, account_id, _ = setup
        headers = {"Authorization": f"Bearer {token}"}
        res = client.put(
            f"/api/analytics/config/{account_id}",
            json={"baseline_days": 5},
            headers=headers,
        )
        assert res.status_code == 400

    def test_config_requires_auth(self, client, account_id):
        res = client.get(f"/api/analytics/config/{account_id}")
        assert res.status_code == 401
