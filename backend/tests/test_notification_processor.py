"""Unit and integration tests for the notification processor job.

Unit tests (TestBuildAlertData, TestDispatchItem)
  – Test internal helpers with mock objects; no DB required.

Integration test (TestProcessPendingIntegration)
  – Uses the conftest `app` fixture (in-memory SQLite) for real DB writes.
"""
import sys
import os
from datetime import datetime, timezone
from types import ModuleType
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Stub APScheduler so notification_processor can be imported without it
# ---------------------------------------------------------------------------
_aps = ModuleType("apscheduler")
_aps.__path__ = []
_aps_sched = ModuleType("apscheduler.schedulers")
_aps_sched.__path__ = []
_aps_bg = ModuleType("apscheduler.schedulers.background")
_aps_bg.BackgroundScheduler = MagicMock
_aps.schedulers = _aps_sched
_aps_sched.background = _aps_bg
for _name, _mod in [
    ("apscheduler", _aps),
    ("apscheduler.schedulers", _aps_sched),
    ("apscheduler.schedulers.background", _aps_bg),
]:
    sys.modules.setdefault(_name, _mod)

# Now import the processor's private functions directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from jobs.notification_processor import (
    _dispatch_item,
    _build_alert_data,
    _mark_failed,
    process_pending_notifications,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def queue_item():
    """Minimal NotificationQueue-like mock."""
    item = MagicMock()
    item.id = 1
    item.user_id = 42
    item.channel = "email"
    item.recipient = "user@example.com"
    item.retry_count = 0
    item.max_retries = 3
    item.status = "pending"
    item.sent_at = None
    item.error_message = None

    alert = MagicMock()
    alert.id = 10
    alert.alert_type = "approaching_limit"
    alert.threshold_percentage = 70
    alert.message = "70% used"
    alert.last_triggered = datetime(2026, 2, 26, tzinfo=timezone.utc)
    alert.account.account_name = "My Account"
    item.alert = alert
    return item


@pytest.fixture()
def mock_db():
    db = MagicMock()
    db.session = MagicMock()
    return db


@pytest.fixture()
def rate_limiter_allow():
    rl = MagicMock()
    rl.can_send.return_value = True
    return rl


@pytest.fixture()
def rate_limiter_deny():
    rl = MagicMock()
    rl.can_send.return_value = False
    return rl


# ---------------------------------------------------------------------------
# Tests for _build_alert_data
# ---------------------------------------------------------------------------

class TestBuildAlertData:
    @pytest.mark.parametrize("alert_type,exp_type,exp_level", [
        ("approaching_limit", "budget",  "warning"),
        ("limit_exceeded",    "budget",  "emergency"),
        ("high_cost",         "budget",  "critical"),
        ("unusual_activity",  "anomaly", "warning"),
        ("service_down",      "system",  "critical"),
    ])
    def test_type_and_level_mapping(self, queue_item, alert_type, exp_type, exp_level):
        queue_item.alert.alert_type = alert_type
        data = _build_alert_data(queue_item)
        assert data["type"] == exp_type
        assert data["level"] == exp_level
        assert data["account_name"] == "My Account"

    def test_no_linked_alert_returns_system(self, queue_item):
        queue_item.alert = None
        data = _build_alert_data(queue_item)
        assert data["type"] == "system"
        assert data["account_name"] == "Unknown"


# ---------------------------------------------------------------------------
# Tests for _dispatch_item
# ---------------------------------------------------------------------------

class TestDispatchItem:
    """Unit tests that mock EmailSender/SlackSender at their source modules."""

    EMAIL_PATH = "services.notifications.email_sender.EmailSender"
    SLACK_PATH = "services.notifications.slack_sender.SlackSender"
    HISTORY_PATH = "models.notification_history.NotificationHistory"

    def _run(self, db, item, rate_limiter, *, success=True, channel="email"):
        app = MagicMock()
        app.config = {}
        item.channel = channel

        mock_sender = MagicMock()
        mock_sender.send_alert.return_value = success

        mock_hist_cls = MagicMock()
        mock_hist_cls.return_value = MagicMock()

        with (
            patch(self.EMAIL_PATH, return_value=mock_sender),
            patch(self.SLACK_PATH, return_value=mock_sender),
            patch(self.HISTORY_PATH, mock_hist_cls),
        ):
            _dispatch_item(app, db, item, rate_limiter)

        return mock_sender, mock_hist_cls

    def test_email_success_marks_sent(self, queue_item, mock_db, rate_limiter_allow):
        self._run(mock_db, queue_item, rate_limiter_allow, success=True, channel="email")
        assert queue_item.status == "sent"
        assert queue_item.sent_at is not None
        assert queue_item.error_message is None
        mock_db.session.add.assert_called()
        mock_db.session.commit.assert_called()

    def test_slack_success_marks_sent(self, queue_item, mock_db, rate_limiter_allow):
        self._run(mock_db, queue_item, rate_limiter_allow, success=True, channel="slack")
        assert queue_item.status == "sent"

    def test_email_failure_increments_retry(self, queue_item, mock_db, rate_limiter_allow):
        self._run(mock_db, queue_item, rate_limiter_allow, success=False, channel="email")
        assert queue_item.retry_count == 1
        # Still under max_retries=3 → stays pending
        assert queue_item.status == "pending"

    def test_email_failure_max_retries_marks_failed(self, queue_item, mock_db, rate_limiter_allow):
        queue_item.retry_count = 2  # one short of max_retries=3
        self._run(mock_db, queue_item, rate_limiter_allow, success=False, channel="email")
        assert queue_item.status == "failed"

    def test_rate_limited_skips_item(self, queue_item, mock_db, rate_limiter_deny):
        original_status = queue_item.status
        self._run(mock_db, queue_item, rate_limiter_deny, success=True, channel="email")
        assert queue_item.status == original_status
        mock_db.session.commit.assert_not_called()

    def test_unsupported_channel_marks_failed(self, queue_item, mock_db, rate_limiter_allow):
        queue_item.channel = "fax"
        app = MagicMock()
        app.config = {}
        mock_hist_cls = MagicMock()
        with patch(self.HISTORY_PATH, mock_hist_cls):
            _dispatch_item(app, mock_db, queue_item, rate_limiter_allow)
        assert queue_item.status == "failed"

    def test_history_recorded_on_success(self, queue_item, mock_db, rate_limiter_allow):
        _, hist_cls = self._run(mock_db, queue_item, rate_limiter_allow, success=True)
        hist_cls.assert_called_once()
        kwargs = hist_cls.call_args.kwargs
        assert kwargs.get("status") == "sent"
        assert kwargs.get("channel") == "email"

    def test_history_recorded_on_failure(self, queue_item, mock_db, rate_limiter_allow):
        _, hist_cls = self._run(mock_db, queue_item, rate_limiter_allow, success=False)
        hist_cls.assert_called_once()
        kwargs = hist_cls.call_args.kwargs
        assert kwargs.get("status") == "failed"

    def test_duration_ms_recorded(self, queue_item, mock_db, rate_limiter_allow):
        _, hist_cls = self._run(mock_db, queue_item, rate_limiter_allow, success=True)
        kwargs = hist_cls.call_args.kwargs
        assert isinstance(kwargs.get("duration_ms"), int)
        assert kwargs["duration_ms"] >= 0


# ---------------------------------------------------------------------------
# Integration: process_pending_notifications via real app context
# ---------------------------------------------------------------------------

class TestProcessPendingIntegration:
    def test_empty_queue_is_noop(self, app):
        """Calling with an empty queue must not raise."""
        process_pending_notifications(app)  # no exception

    def test_processes_queued_item_end_to_end(self, app, client):
        """Queue an item, run processor (email mocked), verify status=sent."""
        from app import db
        from models.service import Service
        from models.account import Account
        from models.alert import Alert
        from models.notification_queue import NotificationQueue

        with app.app_context():
            reg = client.post(
                "/api/auth/register",
                json={"email": "proc_int@example.com", "password": "password123"},
            )
            # re-register if already exists
            if reg.status_code == 409:
                reg = client.post(
                    "/api/auth/login",
                    json={"email": "proc_int@example.com", "password": "password123"},
                )
            user_id = reg.get_json().get("user", {}).get("id")
            if not user_id:
                user_id = reg.get_json().get("user", {}).get("id")

            svc = Service.query.filter_by(name="OpenAI").first()
            if not svc:
                svc = Service(name="OpenAI", api_provider="openai", has_api=True, pricing_model={})
                db.session.add(svc)
                db.session.flush()

            account = Account(user_id=user_id, service_id=svc.id, account_name="Proc Account")
            db.session.add(account)
            db.session.flush()

            alert = Alert(
                account_id=account.id,
                alert_type="approaching_limit",
                threshold_percentage=70,
                is_active=True,
                is_acknowledged=False,
                notification_method="dashboard",
                message="integration test",
            )
            db.session.add(alert)
            db.session.flush()

            q_item = NotificationQueue(
                alert_id=alert.id,
                user_id=user_id,
                channel="email",
                recipient="dest@proc.com",
                priority=1,
                status="pending",
            )
            db.session.add(q_item)
            db.session.commit()
            item_id = q_item.id

        with patch(
            "services.notifications.email_sender.EmailSender"
        ) as MockEmail:
            instance = MagicMock()
            instance.send_alert.return_value = True
            MockEmail.return_value = instance
            process_pending_notifications(app)

        with app.app_context():
            updated = db.session.get(NotificationQueue, item_id)
            assert updated.status == "sent"

    def test_batch_uses_bounded_queries(self, app, client):
        """Eager loading must keep query count well below N+1 for a batch.

        With N+1 behaviour a batch of 10 items would need 1 (queue fetch) +
        10 (alert) + 10 (account) = 21 queries.  With joinedload the same
        batch needs at most ~3 queries (queue+alert+account in one or two
        joined selects, plus per-item commit queries).  We assert fewer than
        5 queries for the *fetch* phase to remain independent of the number
        of dispatch commits.
        """
        from app import db
        from models.service import Service
        from models.account import Account
        from models.alert import Alert
        from models.notification_queue import NotificationQueue
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        # Count SELECT statements issued during _process_notifications
        query_log: list = []

        @event.listens_for(Engine, "before_cursor_execute")
        def _count_query(conn, cursor, statement, parameters, context, executemany):
            if statement.strip().upper().startswith("SELECT"):
                query_log.append(statement)

        try:
            with app.app_context():
                reg = client.post(
                    "/api/auth/register",
                    json={"email": "batch_qcount@example.com", "password": "password123"},
                )
                if reg.status_code == 409:
                    reg = client.post(
                        "/api/auth/login",
                        json={"email": "batch_qcount@example.com", "password": "password123"},
                    )
                user_id = reg.get_json().get("user", {}).get("id") or \
                           reg.get_json().get("id")

                svc = Service.query.filter_by(name="OpenAI").first()
                if not svc:
                    svc = Service(name="OpenAI", api_provider="openai", has_api=True, pricing_model={})
                    db.session.add(svc)
                    db.session.flush()

                account = Account(user_id=user_id, service_id=svc.id, account_name="Batch QC Account")
                db.session.add(account)
                db.session.flush()

                alert = Alert(
                    account_id=account.id,
                    alert_type="approaching_limit",
                    threshold_percentage=80,
                    is_active=True,
                    is_acknowledged=False,
                    notification_method="dashboard",
                    message="batch query count test",
                )
                db.session.add(alert)
                db.session.flush()

                # Enqueue 10 pending items sharing the same alert/account
                item_ids = []
                for i in range(10):
                    qi = NotificationQueue(
                        alert_id=alert.id,
                        user_id=user_id,
                        channel="email",
                        recipient=f"batch{i}@qc.com",
                        priority=1,
                        status="pending",
                    )
                    db.session.add(qi)
                db.session.commit()

            # Clear counter then run the processor (email mocked so no real I/O)
            query_log.clear()

            with patch("services.notifications.email_sender.EmailSender") as MockEmail:
                instance = MagicMock()
                instance.send_alert.return_value = True
                MockEmail.return_value = instance
                process_pending_notifications(app)

        finally:
            event.remove(Engine, "before_cursor_execute", _count_query)

        # With eager loading the main fetch (queue + alert + account) is done
        # in at most 3 SELECT statements regardless of batch size.
        fetch_queries = [q for q in query_log if "notification_queue" in q.lower()
                         or "alerts" in q.lower() or "accounts" in q.lower()]
        assert len(fetch_queries) <= 3, (
            f"Expected ≤3 SELECT queries for batch fetch with eager loading, "
            f"got {len(fetch_queries)}: {fetch_queries}"
        )
