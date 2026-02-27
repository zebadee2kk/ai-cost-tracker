"""Integration tests for /api/notifications/* endpoints.

Covers:
- GET/PUT preferences (own vs. forbidden)
- GET/POST notification queue
- GET history
- POST test notification (email + slack, mocked senders)
- GET rate-limits
- Input validation errors
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix="notif"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _register(client, email=None, password="password123"):
    email = email or _unique_email()
    res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.get_json()
    data = res.get_json()
    return data["token"], data["user"]["id"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def user_token(client):
    return _register(client, _unique_email("user"))


@pytest.fixture()
def other_token(client):
    return _register(client, _unique_email("other"))


@pytest.fixture()
def auth_headers(user_token):
    token, _ = user_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_id(user_token):
    _, uid = user_token
    return uid


@pytest.fixture()
def alert_fixture(app, user_token):
    """Create a Service, Account, and Alert owned by the test user."""
    from app import db
    from models.service import Service
    from models.account import Account
    from models.alert import Alert

    _, uid = user_token
    with app.app_context():
        svc = Service.query.filter_by(name="OpenAI").first()
        if not svc:
            svc = Service(name="OpenAI", api_provider="openai", has_api=True, pricing_model={})
            db.session.add(svc)
            db.session.flush()

        account = Account(
            user_id=uid,
            service_id=svc.id,
            account_name="Test Account",
        )
        db.session.add(account)
        db.session.flush()

        alert = Alert(
            account_id=account.id,
            alert_type="approaching_limit",
            threshold_percentage=70,
            is_active=True,
            is_acknowledged=False,
            notification_method="dashboard",
            message="Test alert",
        )
        db.session.add(alert)
        db.session.commit()

        return {"alert_id": alert.id, "account_id": account.id, "user_id": uid}


# ---------------------------------------------------------------------------
# GET /api/notifications/preferences/<user_id>
# ---------------------------------------------------------------------------

class TestGetPreferences:
    def test_empty_preferences(self, client, auth_headers, user_id):
        res = client.get(f"/api/notifications/preferences/{user_id}", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "preferences" in data
        assert isinstance(data["preferences"], dict)

    def test_requires_auth(self, client, user_id):
        res = client.get(f"/api/notifications/preferences/{user_id}")
        assert res.status_code == 401

    def test_forbidden_other_user(self, client, other_token, user_id):
        token, _ = other_token
        res = client.get(
            f"/api/notifications/preferences/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# PUT /api/notifications/preferences/<user_id>
# ---------------------------------------------------------------------------

class TestUpdatePreferences:
    def test_create_email_preference(self, client, auth_headers, user_id):
        payload = {
            "email": {
                "enabled": True,
                "config": {"address": "me@example.com"},
                "alert_types": ["budget", "system"],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}",
            json=payload,
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert "email" in res.get_json()["message"]

        get_res = client.get(f"/api/notifications/preferences/{user_id}", headers=auth_headers)
        prefs = get_res.get_json()["preferences"]
        assert "email" in prefs
        assert prefs["email"]["enabled"] is True
        assert prefs["email"]["config"]["address"] == "me@example.com"
        assert "budget" in prefs["email"]["alert_types"]

    def test_update_existing_preference(self, client, auth_headers, user_id):
        client.put(
            f"/api/notifications/preferences/{user_id}",
            json={"email": {"enabled": True, "config": {"address": "a@b.com"}, "alert_types": []}},
            headers=auth_headers,
        )
        res = client.put(
            f"/api/notifications/preferences/{user_id}",
            json={"email": {"enabled": False, "config": {"address": "a@b.com"}, "alert_types": []}},
            headers=auth_headers,
        )
        assert res.status_code == 200

        prefs = client.get(
            f"/api/notifications/preferences/{user_id}", headers=auth_headers
        ).get_json()["preferences"]
        assert prefs["email"]["enabled"] is False

    def test_create_slack_preference(self, client, auth_headers, user_id):
        payload = {
            "slack": {
                "enabled": True,
                "config": {"webhook_url": "https://hooks.slack.com/services/test"},
                "alert_types": ["budget"],
            }
        }
        res = client.put(f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers)
        assert res.status_code == 200

    def test_invalid_channel_rejected(self, client, auth_headers, user_id):
        res = client.put(
            f"/api/notifications/preferences/{user_id}",
            json={"telegram": {"enabled": True}},
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_invalid_alert_type_rejected(self, client, auth_headers, user_id):
        res = client.put(
            f"/api/notifications/preferences/{user_id}",
            json={"email": {"enabled": True, "config": {}, "alert_types": ["budget", "spam"]}},
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_forbidden_other_user(self, client, other_token, user_id):
        token, _ = other_token
        res = client.put(
            f"/api/notifications/preferences/{user_id}",
            json={"email": {"enabled": True}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403

    def test_requires_auth(self, client, user_id):
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json={"email": {"enabled": True}}
        )
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/notifications/queue
# ---------------------------------------------------------------------------

class TestGetQueue:
    def test_empty_queue(self, client, auth_headers):
        res = client.get("/api/notifications/queue", headers=auth_headers)
        assert res.status_code == 200
        assert "queue" in res.get_json()

    def test_requires_auth(self, client):
        res = client.get("/api/notifications/queue")
        assert res.status_code == 401

    def test_invalid_status_filter(self, client, auth_headers):
        res = client.get("/api/notifications/queue?status=invalid", headers=auth_headers)
        assert res.status_code == 400

    def test_filter_by_status(self, client, auth_headers):
        res = client.get("/api/notifications/queue?status=pending", headers=auth_headers)
        assert res.status_code == 200
        assert "queue" in res.get_json()


# ---------------------------------------------------------------------------
# POST /api/notifications/queue
# ---------------------------------------------------------------------------

class TestCreateQueueItem:
    def test_create_queue_item(self, client, auth_headers, user_id, alert_fixture):
        assert alert_fixture["user_id"] == user_id
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "email",
                "recipient": "direct@example.com",
                "priority": 1,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        assert res.get_json()["queue_item"]["status"] == "pending"

    def test_create_and_list(self, client, auth_headers, user_id, alert_fixture):
        assert alert_fixture["user_id"] == user_id
        payload = {
            "alert_id": alert_fixture["alert_id"],
            "channel": "email",
            "recipient": "dest@example.com",
            "priority": 2,
        }
        res = client.post("/api/notifications/queue", json=payload, headers=auth_headers)
        assert res.status_code == 201
        item = res.get_json()["queue_item"]
        assert item["channel"] == "email"
        assert item["status"] == "pending"
        assert item["priority"] == 2

    def test_missing_fields_rejected(self, client, auth_headers):
        res = client.post("/api/notifications/queue", json={"channel": "email"}, headers=auth_headers)
        assert res.status_code == 400

    def test_invalid_channel_rejected(self, client, auth_headers, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={"alert_id": alert_fixture["alert_id"], "channel": "pigeon", "recipient": "x"},
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_invalid_priority_rejected(self, client, auth_headers, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "email",
                "recipient": "x@y.com",
                "priority": 99,
            },
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_alert_not_found_rejected(self, client, auth_headers):
        res = client.post(
            "/api/notifications/queue",
            json={"alert_id": 999999, "channel": "email", "recipient": "x@y.com"},
            headers=auth_headers,
        )
        assert res.status_code == 404

    def test_requires_auth(self, client, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={"alert_id": alert_fixture["alert_id"], "channel": "email", "recipient": "x"},
        )
        assert res.status_code == 401

    def test_queue_item_visible_in_list(self, client, auth_headers, user_id, alert_fixture):
        assert alert_fixture["user_id"] == user_id
        client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "email",
                "recipient": "q@example.com",
            },
            headers=auth_headers,
        )
        res = client.get("/api/notifications/queue", headers=auth_headers)
        queue = res.get_json()["queue"]
        assert any(item["recipient"] == "q@example.com" for item in queue)


# ---------------------------------------------------------------------------
# GET /api/notifications/history
# ---------------------------------------------------------------------------

class TestGetHistory:
    def test_empty_history(self, client, auth_headers):
        res = client.get("/api/notifications/history", headers=auth_headers)
        assert res.status_code == 200
        assert "history" in res.get_json()

    def test_requires_auth(self, client):
        res = client.get("/api/notifications/history")
        assert res.status_code == 401

    def test_invalid_channel_filter(self, client, auth_headers):
        res = client.get("/api/notifications/history?channel=fax", headers=auth_headers)
        assert res.status_code == 400

    def test_filter_by_channel(self, client, auth_headers):
        res = client.get("/api/notifications/history?channel=email", headers=auth_headers)
        assert res.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/notifications/test/<channel>
# ---------------------------------------------------------------------------

class TestSendTestNotification:
    def test_email_test_sends_and_logs(self, client, user_token):
        token, uid = user_token
        headers = {"Authorization": f"Bearer {token}"}

        client.put(
            f"/api/notifications/preferences/{uid}",
            json={
                "email": {
                    "enabled": True,
                    "config": {"address": "test@example.com"},
                    "alert_types": [],
                }
            },
            headers=headers,
        )

        with patch("routes.notifications.EmailSender") as MockSender:
            instance = MagicMock()
            instance.send_alert.return_value = True
            MockSender.return_value = instance

            res = client.post("/api/notifications/test/email", headers=headers)

        assert res.status_code == 200
        assert "sent" in res.get_json()["message"]

        hist = client.get("/api/notifications/history", headers=headers)
        assert any(h["channel"] == "email" for h in hist.get_json()["history"])

    def test_email_test_with_explicit_recipient(self, client, auth_headers):
        with patch("routes.notifications.EmailSender") as MockSender:
            instance = MagicMock()
            instance.send_alert.return_value = True
            MockSender.return_value = instance

            res = client.post(
                "/api/notifications/test/email",
                json={"recipient": "override@example.com"},
                headers=auth_headers,
            )
        assert res.status_code == 200

    def test_email_test_no_recipient_returns_400(self, client):
        token, _ = _register(client, _unique_email("norecip"))
        res = client.post(
            "/api/notifications/test/email",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400

    def test_slack_test_sends(self, client, user_token):
        token, uid = user_token
        headers = {"Authorization": f"Bearer {token}"}

        client.put(
            f"/api/notifications/preferences/{uid}",
            json={
                "slack": {
                    "enabled": True,
                    "config": {"webhook_url": "https://hooks.slack.com/services/T00000/B00000/tok"},
                    "alert_types": [],
                }
            },
            headers=headers,
        )

        with patch("routes.notifications.SlackSender") as MockSender:
            instance = MagicMock()
            instance.send_alert.return_value = True
            MockSender.return_value = instance

            res = client.post("/api/notifications/test/slack", headers=headers)

        assert res.status_code == 200

    def test_invalid_channel_rejected(self, client, auth_headers):
        res = client.post("/api/notifications/test/fax", headers=auth_headers)
        assert res.status_code == 400

    def test_unsupported_channel_returns_400(self, client, user_token):
        token, uid = user_token
        headers = {"Authorization": f"Bearer {token}"}

        client.put(
            f"/api/notifications/preferences/{uid}",
            json={
                "discord": {
                    "enabled": True,
                    "config": {"webhook_url": "https://discord.com/test"},
                    "alert_types": [],
                }
            },
            headers=headers,
        )
        res = client.post("/api/notifications/test/discord", headers=headers)
        assert res.status_code == 400

    def test_sender_failure_returns_502(self, client, auth_headers):
        with patch("routes.notifications.EmailSender") as MockSender:
            instance = MagicMock()
            instance.send_alert.return_value = False
            MockSender.return_value = instance

            res = client.post(
                "/api/notifications/test/email",
                json={"recipient": "fail@example.com"},
                headers=auth_headers,
            )
        assert res.status_code == 502

    def test_requires_auth(self, client):
        res = client.post("/api/notifications/test/email")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/notifications/rate-limits
# ---------------------------------------------------------------------------

class TestRateLimits:
    def test_returns_limits_for_all_channels(self, client, auth_headers):
        res = client.get("/api/notifications/rate-limits", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "rate_limits" in data
        limits = data["rate_limits"]
        for channel in ("email", "slack", "discord", "teams"):
            assert channel in limits
            assert "per_hour" in limits[channel]
            assert "per_day" in limits[channel]

    def test_requires_auth(self, client):
        res = client.get("/api/notifications/rate-limits")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Webhook URL validation (SSRF remediation – HIGH-1)
# ---------------------------------------------------------------------------

class TestWebhookValidation:
    """Ensure all three endpoints that accept webhook URLs reject malicious ones."""

    # --- PUT /api/notifications/preferences (place 1) ---

    def test_preferences_valid_slack_webhook_accepted(self, client, auth_headers, user_id):
        payload = {
            "slack": {
                "enabled": True,
                "config": {"webhook_url": "https://hooks.slack.com/services/T/B/tok"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 200

    def test_preferences_malicious_slack_webhook_rejected(self, client, auth_headers, user_id):
        payload = {
            "slack": {
                "enabled": True,
                "config": {"webhook_url": "https://evil.com/services/T/B/tok"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 400
        assert "webhook_url" in res.get_json()["error"].lower() or "invalid" in res.get_json()["error"].lower()

    def test_preferences_http_slack_webhook_rejected(self, client, auth_headers, user_id):
        payload = {
            "slack": {
                "enabled": True,
                "config": {"webhook_url": "http://hooks.slack.com/services/T/B/tok"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 400

    def test_preferences_localhost_slack_webhook_rejected(self, client, auth_headers, user_id):
        payload = {
            "slack": {
                "enabled": True,
                "config": {"webhook_url": "https://localhost/services/T/B/tok"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 400

    def test_preferences_valid_discord_webhook_accepted(self, client, auth_headers, user_id):
        payload = {
            "discord": {
                "enabled": True,
                "config": {"webhook_url": "https://discord.com/api/webhooks/123/abc"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 200

    def test_preferences_malicious_discord_webhook_rejected(self, client, auth_headers, user_id):
        payload = {
            "discord": {
                "enabled": True,
                "config": {"webhook_url": "https://evil.com/api/webhooks/123/abc"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 400

    def test_preferences_valid_teams_webhook_accepted(self, client, auth_headers, user_id):
        payload = {
            "teams": {
                "enabled": True,
                "config": {"webhook_url": "https://myorg.webhook.office.com/webhookb2/abc"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 200

    def test_preferences_internal_ip_teams_webhook_rejected(self, client, auth_headers, user_id):
        payload = {
            "teams": {
                "enabled": True,
                "config": {"webhook_url": "https://192.168.1.1/webhookb2/abc"},
                "alert_types": [],
            }
        }
        res = client.put(
            f"/api/notifications/preferences/{user_id}", json=payload, headers=auth_headers
        )
        assert res.status_code == 400

    # --- POST /api/notifications/queue (place 2) ---

    def test_queue_valid_slack_recipient_accepted(self, client, auth_headers, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "slack",
                "recipient": "https://hooks.slack.com/services/T/B/tok",
                "priority": 1,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201

    def test_queue_malicious_slack_recipient_rejected(self, client, auth_headers, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "slack",
                "recipient": "https://attacker.internal/steal-secrets",
                "priority": 1,
            },
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_queue_localhost_recipient_rejected(self, client, auth_headers, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "slack",
                "recipient": "https://localhost:8080/internal-endpoint",
                "priority": 1,
            },
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_queue_metadata_ip_recipient_rejected(self, client, auth_headers, alert_fixture):
        """AWS metadata endpoint must be rejected."""
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "slack",
                "recipient": "https://169.254.169.254/latest/meta-data/",
                "priority": 1,
            },
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_queue_valid_discord_recipient_accepted(self, client, auth_headers, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "discord",
                "recipient": "https://discord.com/api/webhooks/123/tok",
                "priority": 1,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201

    def test_queue_malicious_discord_recipient_rejected(self, client, auth_headers, alert_fixture):
        res = client.post(
            "/api/notifications/queue",
            json={
                "alert_id": alert_fixture["alert_id"],
                "channel": "discord",
                "recipient": "http://discord.com/api/webhooks/123/tok",
                "priority": 1,
            },
            headers=auth_headers,
        )
        assert res.status_code == 400

    # --- POST /api/notifications/test/<channel> (place 3) ---

    def test_test_endpoint_malicious_slack_recipient_rejected(self, client, user_token):
        token, uid = user_token
        headers = {"Authorization": f"Bearer {token}"}
        res = client.post(
            "/api/notifications/test/slack",
            json={"recipient": "https://evil.internal/exfiltrate"},
            headers=headers,
        )
        assert res.status_code == 400

    def test_test_endpoint_localhost_slack_recipient_rejected(self, client, auth_headers):
        res = client.post(
            "/api/notifications/test/slack",
            json={"recipient": "http://localhost:9200/_cat/indices"},
            headers=auth_headers,
        )
        assert res.status_code == 400

    def test_test_endpoint_valid_slack_proceeds_to_sender(self, client, user_token):
        token, uid = user_token
        headers = {"Authorization": f"Bearer {token}"}
        with patch("routes.notifications.SlackSender") as MockSender:
            instance = MockSender.return_value = unittest_mock_instance()
            instance.send_alert.return_value = True
            res = client.post(
                "/api/notifications/test/slack",
                json={"recipient": "https://hooks.slack.com/services/T/B/tok"},
                headers=headers,
            )
        assert res.status_code == 200


def unittest_mock_instance():
    """Return a pre-configured MagicMock for use in webhook tests."""
    from unittest.mock import MagicMock
    m = MagicMock()
    m.send_alert.return_value = True
    return m
