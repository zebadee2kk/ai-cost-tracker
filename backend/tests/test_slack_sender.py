"""Unit tests for SlackSender and RateLimiter.

Tests cover:
- Successful Slack delivery (HTTP 200, body "ok").
- Failed delivery (non-200 or wrong body).
- Timeout handling.
- Exception propagation path.
- Payload structure (blocks, attachments, colors).
- RateLimiter.can_send respects hourly and daily limits.
- RateLimiter.get_remaining arithmetic.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub heavy dependencies so tests run without the full project venv.
# ---------------------------------------------------------------------------

# 1. Prevent services/__init__.py from loading OpenAI/Anthropic clients.
_services_stub = ModuleType("services")
_services_stub.__path__ = []
_services_notifications_stub = ModuleType("services.notifications")
_services_notifications_stub.__path__ = []
_services_stub.notifications = _services_notifications_stub
sys.modules.setdefault("services", _services_stub)
sys.modules.setdefault("services.notifications", _services_notifications_stub)

# 2. Stub `requests` so slack_sender works without the real package.
_requests_stub = ModuleType("requests")
_requests_stub.post = MagicMock()

class _TimeoutStub(Exception):
    pass

_requests_stub.Timeout = _TimeoutStub
sys.modules.setdefault("requests", _requests_stub)

# 3. Stub `models` hierarchy so rate_limiter's lazy import resolves cleanly.
#    rate_limiter does: from models.notification_history import NotificationHistory
_models_stub = ModuleType("models")
_models_stub.__path__ = []
_models_nh_stub = ModuleType("models.notification_history")
_mock_nh_class = MagicMock(name="NotificationHistory")
_models_nh_stub.NotificationHistory = _mock_nh_class
_models_stub.notification_history = _models_nh_stub
# Also stub app / flask_sqlalchemy that model files import
_app_stub = ModuleType("app")
_app_stub.db = MagicMock()
sys.modules.setdefault("app", _app_stub)
sys.modules.setdefault("models", _models_stub)
sys.modules.setdefault("models.notification_history", _models_nh_stub)

# 3. Load the notification modules directly from their file paths.
import importlib
import importlib.util
import os as _os

def _load(name, rel_path):
    spec = importlib.util.spec_from_file_location(
        name,
        _os.path.join(_os.path.dirname(__file__), "..", rel_path),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_slack_mod = _load(
    "services.notifications.slack_sender",
    "services/notifications/slack_sender.py",
)
_rl_mod = _load(
    "services.notifications.rate_limiter",
    "services/notifications/rate_limiter.py",
)

SlackSender = _slack_mod.SlackSender
RateLimiter = _rl_mod.RateLimiter
DEFAULT_LIMITS = _rl_mod.DEFAULT_LIMITS

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

WEBHOOK_URL = "https://hooks.slack.com/services/T000/B000/XXXX"

_BUDGET_DATA = {
    "type": "budget",
    "level": "warning",
    "account_name": "Acme Corp",
    "current_cost": 75.00,
    "threshold": 100.00,
    "message": "You are approaching your budget limit.",
    "timestamp": 1700000000,
}

_ANOMALY_DATA = {
    "type": "anomaly",
    "level": "critical",
    "account_name": "Acme Corp",
    "current_cost": 200.00,
    "threshold": 0,
    "message": "Spike detected.",
    "timestamp": 1700000000,
}

_SYSTEM_DATA = {
    "type": "system",
    "level": "emergency",
    "account_name": "",
    "current_cost": 0,
    "threshold": 0,
    "message": "API key expired.",
    "timestamp": 1700000000,
}


# ---------------------------------------------------------------------------
# SlackSender – send_alert
# ---------------------------------------------------------------------------

def _ok_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "ok"
    return mock_resp


class TestSlackSenderSendAlert:
    def _sender(self):
        return SlackSender(timeout=5)

    def test_returns_true_on_success(self):
        sender = self._sender()
        with patch("services.notifications.slack_sender.requests.post", return_value=_ok_response()):
            result = sender.send_alert(WEBHOOK_URL, _BUDGET_DATA)
        assert result is True

    def test_returns_false_on_non_200(self):
        sender = self._sender()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "channel_not_found"
        with patch("services.notifications.slack_sender.requests.post", return_value=mock_resp):
            result = sender.send_alert(WEBHOOK_URL, _BUDGET_DATA)
        assert result is False

    def test_returns_false_when_body_is_not_ok(self):
        """HTTP 200 but Slack returned an error payload."""
        sender = self._sender()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "invalid_payload"
        with patch("services.notifications.slack_sender.requests.post", return_value=mock_resp):
            result = sender.send_alert(WEBHOOK_URL, _BUDGET_DATA)
        assert result is False

    def test_returns_false_on_timeout(self):
        sender = self._sender()
        import services.notifications.slack_sender as slack_mod
        with patch("services.notifications.slack_sender.requests.post",
                   side_effect=slack_mod.requests.Timeout):
            result = sender.send_alert(WEBHOOK_URL, _BUDGET_DATA)
        assert result is False

    def test_returns_false_on_generic_exception(self):
        sender = self._sender()
        with patch("services.notifications.slack_sender.requests.post",
                   side_effect=RuntimeError("boom")):
            result = sender.send_alert(WEBHOOK_URL, _BUDGET_DATA)
        assert result is False

    def test_correct_timeout_passed_to_requests(self):
        sender = self._sender()
        with patch("services.notifications.slack_sender.requests.post",
                   return_value=_ok_response()) as mock_post:
            sender.send_alert(WEBHOOK_URL, _BUDGET_DATA)
        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 5

    def test_sends_to_correct_url(self):
        sender = self._sender()
        with patch("services.notifications.slack_sender.requests.post",
                   return_value=_ok_response()) as mock_post:
            sender.send_alert(WEBHOOK_URL, _BUDGET_DATA)
        args, _ = mock_post.call_args
        assert args[0] == WEBHOOK_URL

    def test_all_alert_types_succeed(self):
        sender = self._sender()
        for alert_data in [_BUDGET_DATA, _ANOMALY_DATA, _SYSTEM_DATA]:
            with patch("services.notifications.slack_sender.requests.post",
                       return_value=_ok_response()):
                result = sender.send_alert(WEBHOOK_URL, alert_data)
            assert result is True, f"Failed for type={alert_data['type']}"


# ---------------------------------------------------------------------------
# SlackSender – _build_payload
# ---------------------------------------------------------------------------

class TestSlackSenderBuildPayload:
    def _sender(self):
        return SlackSender()

    def test_budget_payload_has_cost_and_threshold(self):
        sender = self._sender()
        payload = sender._build_payload(_BUDGET_DATA)
        all_text = str(payload)
        assert "75.00" in all_text
        assert "100.00" in all_text

    def test_budget_payload_has_percentage(self):
        sender = self._sender()
        payload = sender._build_payload(_BUDGET_DATA)
        assert "75.0%" in str(payload)

    def test_warning_color_is_yellow(self):
        sender = self._sender()
        payload = sender._build_payload(_BUDGET_DATA)
        attachment_color = payload["attachments"][0]["color"]
        assert attachment_color == "#FFC107"

    def test_critical_color_is_orange(self):
        sender = self._sender()
        data = {**_BUDGET_DATA, "level": "critical"}
        payload = sender._build_payload(data)
        assert payload["attachments"][0]["color"] == "#FF9800"

    def test_emergency_color_is_red(self):
        sender = self._sender()
        data = {**_BUDGET_DATA, "level": "emergency"}
        payload = sender._build_payload(data)
        assert payload["attachments"][0]["color"] == "#F44336"

    def test_payload_has_dashboard_button(self):
        sender = self._sender()
        payload = sender._build_payload(_BUDGET_DATA)
        payload_str = str(payload)
        assert "View Dashboard" in payload_str
        assert "ai-cost-tracker.com" in payload_str

    def test_header_block_present(self):
        sender = self._sender()
        payload = sender._build_payload(_BUDGET_DATA)
        block_types = [b["type"] for b in payload["blocks"]]
        assert "header" in block_types

    def test_anomaly_header_text(self):
        sender = self._sender()
        payload = sender._build_payload(_ANOMALY_DATA)
        header_block = next(b for b in payload["blocks"] if b["type"] == "header")
        assert "Unusual Usage" in header_block["text"]["text"]

    def test_system_header_text(self):
        sender = self._sender()
        payload = sender._build_payload(_SYSTEM_DATA)
        header_block = next(b for b in payload["blocks"] if b["type"] == "header")
        assert "System Alert" in header_block["text"]["text"]

    def test_timestamp_present_in_attachment(self):
        sender = self._sender()
        payload = sender._build_payload(_BUDGET_DATA)
        assert payload["attachments"][0]["ts"] == 1700000000


# ---------------------------------------------------------------------------
# RateLimiter helpers
# ---------------------------------------------------------------------------

class _SqlCol:
    """Minimal SQLAlchemy column stub: supports ==, >= and similar comparisons."""
    def __eq__(self, other): return MagicMock()
    def __ne__(self, other): return MagicMock()
    def __ge__(self, other): return MagicMock()
    def __le__(self, other): return MagicMock()
    def __gt__(self, other): return MagicMock()
    def __lt__(self, other): return MagicMock()
    def __hash__(self): return id(self)


def _make_nh_mock(counts):
    """Build a NotificationHistory-like mock that returns *counts* from .count()."""
    nh = MagicMock()
    nh.user_id = _SqlCol()
    nh.channel = _SqlCol()
    nh.created_at = _SqlCol()
    nh.query.filter.return_value.count.side_effect = list(counts)
    return nh


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    """Tests for RateLimiter using mocked NotificationHistory queries."""

    def _limiter(self, limits=None):
        return RateLimiter(limits=limits)

    def _patch_nh(self, counts):
        """Context manager: replace NotificationHistory with a configured mock."""
        mock_nh = _make_nh_mock(counts)
        return patch.object(
            sys.modules["models.notification_history"],
            "NotificationHistory",
            mock_nh,
        )

    def test_can_send_returns_true_when_under_limits(self):
        limiter = self._limiter()
        with self._patch_nh([5, 20]):
            result = limiter.can_send(user_id=1, channel="email")
        assert result is True

    def test_can_send_returns_false_when_hourly_limit_reached(self):
        limiter = self._limiter()
        with self._patch_nh([10, 20]):
            result = limiter.can_send(user_id=1, channel="email")
        assert result is False

    def test_can_send_returns_false_when_daily_limit_reached(self):
        limiter = self._limiter()
        with self._patch_nh([3, 50]):
            result = limiter.can_send(user_id=1, channel="email")
        assert result is False

    def test_slack_has_higher_limits_than_email(self):
        """Slack allows 20/hour vs email's 10/hour."""
        assert DEFAULT_LIMITS["slack"]["per_hour"] > DEFAULT_LIMITS["email"]["per_hour"]

    def test_unknown_channel_uses_fallback_limit(self):
        limiter = self._limiter()
        with self._patch_nh([3, 20]):
            result = limiter.can_send(user_id=1, channel="carrier_pigeon")
        assert result is True

    def test_custom_limits_override_defaults(self):
        custom = {"email": {"per_hour": 2, "per_day": 5}}
        limiter = self._limiter(limits=custom)
        with self._patch_nh([2, 3]):
            result = limiter.can_send(user_id=1, channel="email")
        assert result is False

    def test_get_remaining_returns_correct_values(self):
        limiter = self._limiter()
        with self._patch_nh([3, 15]):
            remaining = limiter.get_remaining(user_id=1, channel="email")
        assert remaining["per_hour"] == 7   # 10 - 3
        assert remaining["per_day"] == 35   # 50 - 15

    def test_get_remaining_never_negative(self):
        """If counts somehow exceed limits, remaining should clamp to 0."""
        limiter = self._limiter()
        with self._patch_nh([15, 60]):
            remaining = limiter.get_remaining(user_id=1, channel="email")
        assert remaining["per_hour"] == 0
        assert remaining["per_day"] == 0
