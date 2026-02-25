"""Unit tests for EmailSender.

Tests cover:
- Subject line generation for all alert types and levels.
- HTML body rendering for budget, anomaly, and system alert types.
- Successful send (SendGrid returns 202).
- Failed send (SendGrid returns 4xx).
- Exception path (network error).
- Missing sendgrid package graceful degradation.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub heavy dependencies so tests run without the full project venv.
# ---------------------------------------------------------------------------

# 1. Prevent services/__init__.py from loading OpenAI/Anthropic clients
#    (those pull in `requests`/`openai` not available in the test runner).
_services_stub = ModuleType("services")
_services_stub.__path__ = []          # mark as package
_services_notifications_stub = ModuleType("services.notifications")
_services_notifications_stub.__path__ = []
_services_stub.notifications = _services_notifications_stub
sys.modules.setdefault("services", _services_stub)
sys.modules.setdefault("services.notifications", _services_notifications_stub)

# 2. Stub sendgrid so EmailSender can be imported without the real package.
_sg_stub = ModuleType("sendgrid")
_sg_stub.SendGridAPIClient = MagicMock
_sg_helpers = ModuleType("sendgrid.helpers")
_sg_mail = ModuleType("sendgrid.helpers.mail")
_sg_mail.Mail = MagicMock
_sg_mail.Email = MagicMock
_sg_mail.To = MagicMock
_sg_mail.Content = MagicMock
_sg_stub.helpers = _sg_helpers
_sg_helpers.mail = _sg_mail
sys.modules.setdefault("sendgrid", _sg_stub)
sys.modules.setdefault("sendgrid.helpers", _sg_helpers)
sys.modules.setdefault("sendgrid.helpers.mail", _sg_mail)

# Now we can safely import our module.
import importlib
import importlib.util
import os as _os

_spec = importlib.util.spec_from_file_location(
    "services.notifications.email_sender",
    _os.path.join(_os.path.dirname(__file__), "..", "services", "notifications", "email_sender.py"),
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["services.notifications.email_sender"] = _mod
_spec.loader.exec_module(_mod)
EmailSender = _mod.EmailSender

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

_BUDGET_DATA = {
    "type": "budget",
    "level": "warning",
    "account_name": "Acme Corp",
    "current_cost": 75.00,
    "threshold": 100.00,
    "message": "You are approaching your budget limit.",
}

_ANOMALY_DATA = {
    "type": "anomaly",
    "level": "critical",
    "account_name": "Acme Corp",
    "current_cost": 200.00,
    "threshold": 0,
    "message": "Daily cost is 4 standard deviations above the mean.",
}

_SYSTEM_DATA = {
    "type": "system",
    "level": "emergency",
    "account_name": "",
    "current_cost": 0,
    "threshold": 0,
    "message": "API key has expired – please rotate credentials.",
}


# ---------------------------------------------------------------------------
# Subject-line tests
# ---------------------------------------------------------------------------

class TestBuildSubject:
    def setup_method(self):
        self.sender = EmailSender.__new__(EmailSender)
        self.sender.client = None
        self.sender.from_email = "from@example.com"
        self.sender.from_name = "Tester"

    def test_budget_warning_subject(self):
        subject = self.sender._build_subject(_BUDGET_DATA)
        assert "[WARNING]" in subject
        assert "Acme Corp" in subject
        assert "Warning" in subject

    def test_budget_critical_subject(self):
        data = {**_BUDGET_DATA, "level": "critical"}
        subject = self.sender._build_subject(data)
        assert "[CRITICAL]" in subject

    def test_budget_emergency_subject(self):
        data = {**_BUDGET_DATA, "level": "emergency"}
        subject = self.sender._build_subject(data)
        assert "[EMERGENCY]" in subject

    def test_anomaly_subject(self):
        subject = self.sender._build_subject(_ANOMALY_DATA)
        assert "Unusual Usage" in subject
        assert "Acme Corp" in subject

    def test_system_subject_includes_message_snippet(self):
        subject = self.sender._build_subject(_SYSTEM_DATA)
        assert "System Alert" in subject
        assert "API key has expired" in subject

    def test_unknown_level_defaults_to_alert_prefix(self):
        data = {**_BUDGET_DATA, "level": "unknown"}
        subject = self.sender._build_subject(data)
        assert "[ALERT]" in subject


# ---------------------------------------------------------------------------
# HTML rendering tests
# ---------------------------------------------------------------------------

class TestRenderHtml:
    def setup_method(self):
        self.sender = EmailSender.__new__(EmailSender)

    def test_budget_html_contains_cost(self):
        html = self.sender._render_html(_BUDGET_DATA)
        assert "75.00" in html
        assert "100.00" in html
        assert "75.0%" in html

    def test_budget_html_emergency_uses_red(self):
        data = {**_BUDGET_DATA, "level": "emergency"}
        html = self.sender._render_html(data)
        assert "#f44336" in html

    def test_budget_html_warning_uses_yellow(self):
        html = self.sender._render_html(_BUDGET_DATA)
        assert "#ffc107" in html

    def test_anomaly_html_contains_account(self):
        html = self.sender._render_html(_ANOMALY_DATA)
        assert "Acme Corp" in html
        assert "200.00" in html

    def test_system_html_contains_message(self):
        html = self.sender._render_html(_SYSTEM_DATA)
        assert "API key has expired" in html

    def test_unknown_type_falls_back_to_system_template(self):
        data = {**_SYSTEM_DATA, "type": "unknown_future_type"}
        html = self.sender._render_html(data)
        assert "<html>" in html


# ---------------------------------------------------------------------------
# send_alert integration tests (mocked SendGrid)
# ---------------------------------------------------------------------------

class TestSendAlert:
    def _make(self):
        sender = EmailSender.__new__(EmailSender)
        sender.from_email = "from@example.com"
        sender.from_name = "Tester"
        sender._sg_from = MagicMock()
        mock_client = MagicMock()
        sender.client = mock_client
        return sender, mock_client

    def test_send_returns_true_on_202(self):
        sender, mock_client = self._make()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response

        result = sender.send_alert("to@example.com", _BUDGET_DATA)
        assert result is True
        assert mock_client.send.called

    def test_send_returns_true_on_200(self):
        sender, mock_client = self._make()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.send.return_value = mock_response

        result = sender.send_alert("to@example.com", _BUDGET_DATA)
        assert result is True

    def test_send_returns_true_on_201(self):
        sender, mock_client = self._make()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_client.send.return_value = mock_response

        result = sender.send_alert("to@example.com", _BUDGET_DATA)
        assert result is True

    def test_send_returns_false_on_4xx(self):
        sender, mock_client = self._make()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.body = "Bad Request"
        mock_client.send.return_value = mock_response

        result = sender.send_alert("to@example.com", _BUDGET_DATA)
        assert result is False

    def test_send_returns_false_on_exception(self):
        sender, mock_client = self._make()
        mock_client.send.side_effect = Exception("Network error")

        result = sender.send_alert("to@example.com", _BUDGET_DATA)
        assert result is False

    def test_send_returns_false_when_client_not_initialised(self):
        sender = EmailSender.__new__(EmailSender)
        sender.client = None
        sender.from_email = "from@example.com"
        sender.from_name = "Tester"

        result = sender.send_alert("to@example.com", _BUDGET_DATA)
        assert result is False

    def test_all_alert_types_send_without_error(self):
        """Smoke-test: all alert types reach SendGrid without raising."""
        for alert_data in [_BUDGET_DATA, _ANOMALY_DATA, _SYSTEM_DATA]:
            sender, mock_client = self._make()
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.send.return_value = mock_response

            result = sender.send_alert("to@example.com", alert_data)
            assert result is True, f"send_alert failed for type={alert_data['type']}"

    def test_all_budget_levels_send_without_error(self):
        for level in ("warning", "critical", "emergency"):
            data = {**_BUDGET_DATA, "level": level}
            sender, mock_client = self._make()
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.send.return_value = mock_response

            result = sender.send_alert("to@example.com", data)
            assert result is True, f"send_alert failed for level={level}"
