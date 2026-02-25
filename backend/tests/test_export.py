"""Unit and integration tests for the /api/usage/export endpoint.

Coverage targets:
 - CSV and JSON format responses
 - Date-range filtering
 - Service and account filtering
 - Source filtering (api / manual / all)
 - Parameter validation (bad dates, bad format, bad source)
 - Authentication enforcement
 - Account ownership enforcement (403 for other-user accounts)
"""
import csv
import json
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client, email, password="password123"):
    res = client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert res.status_code == 201, res.data
    return res.get_json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_account(client, token, service_id=1):
    """Create a test account and return its id."""
    res = client.post(
        "/api/accounts",
        json={
            "account_name": "Test Account",
            "service_id": service_id,
            "api_key": "sk-test-key",
        },
        headers=_auth(token),
    )
    return res.get_json().get("id") or res.get_json().get("account", {}).get("id")


def _seed_record(app, account_id, service_id, source="api", date_str="2026-02-15", cost=1.5, tokens=1000):
    """Insert a UsageRecord directly into the DB."""
    from app import db
    from models.usage_record import UsageRecord

    ts = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    record = UsageRecord(
        account_id=account_id,
        service_id=service_id,
        timestamp=ts,
        tokens_used=tokens,
        cost=Decimal(str(cost)),
        cost_currency="USD",
        api_calls=1,
        request_type="manual" if source == "manual" else "completion",
        source=source,
        extra_data={"notes": "Test note"} if source == "manual" else {},
    )
    with app.app_context():
        db.session.add(record)
        db.session.commit()
        return record.id


# ---------------------------------------------------------------------------
# Tests: authentication
# ---------------------------------------------------------------------------

def test_export_requires_auth(client):
    """Unauthenticated requests must be rejected with 401."""
    res = client.get("/api/usage/export")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Tests: parameter validation
# ---------------------------------------------------------------------------

def test_export_invalid_format(client, app):
    token = _register_and_login(client, "export-fmt@test.com")
    res = client.get("/api/usage/export?format=xml", headers=_auth(token))
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_export_invalid_start_date(client, app):
    token = _register_and_login(client, "export-date1@test.com")
    res = client.get("/api/usage/export?start_date=02/01/2026", headers=_auth(token))
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data
    assert "start_date" in data.get("message", "")


def test_export_invalid_end_date(client, app):
    token = _register_and_login(client, "export-date2@test.com")
    res = client.get("/api/usage/export?end_date=not-a-date", headers=_auth(token))
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_export_invalid_source(client, app):
    token = _register_and_login(client, "export-src@test.com")
    res = client.get("/api/usage/export?source=unknown", headers=_auth(token))
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


# ---------------------------------------------------------------------------
# Tests: authorization
# ---------------------------------------------------------------------------

def test_export_forbidden_account(client, app):
    """A user cannot export another user's account data."""
    token_a = _register_and_login(client, "export-owner@test.com")
    token_b = _register_and_login(client, "export-other@test.com")

    # Create account owned by user A
    acc_id = _create_account(client, token_a)
    if acc_id is None:
        pytest.skip("Could not create account (service seed may be missing)")

    # User B tries to access it
    res = client.get(
        f"/api/usage/export?account_id={acc_id}", headers=_auth(token_b)
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Tests: CSV export
# ---------------------------------------------------------------------------

def test_csv_export_empty(client, app):
    """Export with no records returns valid CSV with header only."""
    token = _register_and_login(client, "export-csv-empty@test.com")
    res = client.get("/api/usage/export?format=csv", headers=_auth(token))
    assert res.status_code == 200
    assert "csv" in res.content_type
    assert "attachment" in res.headers.get("Content-Disposition", "")

    content = res.data.decode("utf-8-sig")  # strip BOM
    reader = csv.DictReader(StringIO(content))
    rows = [r for r in reader if r.get("Date") and not r["Date"].startswith("#")]
    assert rows == []


def test_csv_export_default_format(client, app):
    """Default format (no ?format=) should return CSV."""
    token = _register_and_login(client, "export-csv-default@test.com")
    res = client.get("/api/usage/export", headers=_auth(token))
    assert res.status_code == 200
    assert "csv" in res.content_type


def test_csv_export_headers(client, app):
    """CSV must contain all required column headers."""
    token = _register_and_login(client, "export-csv-hdr@test.com")
    res = client.get("/api/usage/export?format=csv", headers=_auth(token))
    assert res.status_code == 200

    content = res.data.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content))
    required = {"Date", "Service", "Account", "Request Type", "Tokens", "Cost (USD)", "Data Source", "Notes"}
    assert required.issubset(set(reader.fieldnames or []))


def test_csv_export_content_disposition(client, app):
    """Content-Disposition header must be 'attachment' with a .csv filename."""
    token = _register_and_login(client, "export-cd-csv@test.com")
    res = client.get("/api/usage/export?format=csv", headers=_auth(token))
    cd = res.headers.get("Content-Disposition", "")
    assert "attachment" in cd
    assert ".csv" in cd


# ---------------------------------------------------------------------------
# Tests: JSON export
# ---------------------------------------------------------------------------

def test_json_export_structure(client, app):
    """JSON export must contain export_metadata and records keys."""
    token = _register_and_login(client, "export-json-struct@test.com")
    res = client.get("/api/usage/export?format=json", headers=_auth(token))
    assert res.status_code == 200

    data = json.loads(res.data)
    assert "export_metadata" in data
    assert "records" in data
    assert isinstance(data["records"], list)


def test_json_export_metadata_fields(client, app):
    """JSON export_metadata must include generated_at, date_range, filters."""
    token = _register_and_login(client, "export-json-meta@test.com")
    res = client.get(
        "/api/usage/export?format=json&start_date=2026-01-01&end_date=2026-02-28",
        headers=_auth(token),
    )
    assert res.status_code == 200
    meta = json.loads(res.data)["export_metadata"]
    assert "generated_at" in meta
    assert meta["date_range"]["start"] == "2026-01-01"
    assert meta["date_range"]["end"] == "2026-02-28"


def test_json_export_content_disposition(client, app):
    """Content-Disposition header must be 'attachment' with a .json filename."""
    token = _register_and_login(client, "export-cd-json@test.com")
    res = client.get("/api/usage/export?format=json", headers=_auth(token))
    cd = res.headers.get("Content-Disposition", "")
    assert "attachment" in cd
    assert ".json" in cd


# ---------------------------------------------------------------------------
# Tests: date-range filtering
# ---------------------------------------------------------------------------

def test_export_date_range_valid(client, app):
    """Valid date range parameters produce 200 without error."""
    token = _register_and_login(client, "export-dr@test.com")
    res = client.get(
        "/api/usage/export?start_date=2026-02-01&end_date=2026-02-28",
        headers=_auth(token),
    )
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Tests: source filtering
# ---------------------------------------------------------------------------

def test_export_source_all(client, app):
    """source=all should be accepted and return 200."""
    token = _register_and_login(client, "export-src-all@test.com")
    res = client.get("/api/usage/export?source=all", headers=_auth(token))
    assert res.status_code == 200


def test_export_source_api(client, app):
    """source=api should be accepted and return 200."""
    token = _register_and_login(client, "export-src-api@test.com")
    res = client.get("/api/usage/export?source=api", headers=_auth(token))
    assert res.status_code == 200


def test_export_source_manual(client, app):
    """source=manual should be accepted and return 200."""
    token = _register_and_login(client, "export-src-manual@test.com")
    res = client.get("/api/usage/export?source=manual", headers=_auth(token))
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Tests: x-accel-buffering header (streaming indicator)
# ---------------------------------------------------------------------------

def test_export_xaccel_header(client, app):
    """X-Accel-Buffering: no must be set on streaming responses."""
    token = _register_and_login(client, "export-xaccel@test.com")
    res = client.get("/api/usage/export", headers=_auth(token))
    assert res.headers.get("X-Accel-Buffering", "").lower() == "no"
