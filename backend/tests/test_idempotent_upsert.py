"""Integration tests for idempotent upsert using the in-memory SQLite DB."""

import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal


@pytest.fixture()
def seed_service_and_account(app, db):
    """Create minimal Service and Account rows needed for UsageRecord FKs.

    Uses a unique run_id so each test gets isolated DB rows regardless of
    whether earlier tests committed data.  Cleans up all created rows at
    teardown via explicit deletes, because db.session.rollback() only
    undoes *uncommitted* changes.
    """
    from models.service import Service
    from models.account import Account
    from models.user import User
    from models.usage_record import UsageRecord

    run_id = uuid.uuid4().hex[:8]

    user = User(
        email=f"upsert-{run_id}@test.com",
        password_hash="hash",
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()

    svc = Service(
        name=f"UpsertTestSvc-{run_id}",
        api_provider="test",
        has_api=True,
        pricing_model={},
    )
    db.session.add(svc)
    db.session.flush()

    acct = Account(
        user_id=user.id,
        service_id=svc.id,
        account_name="Test Account",
        is_active=True,
    )
    db.session.add(acct)
    db.session.commit()

    yield acct, svc

    # Explicit teardown: delete all usage records, then account, svc, user
    UsageRecord.query.filter_by(account_id=acct.id).delete()
    Account.query.filter_by(id=acct.id).delete()
    Service.query.filter_by(id=svc.id).delete()
    User.query.filter_by(id=user.id).delete()
    db.session.commit()


def test_upsert_inserts_new_record(app, db, seed_service_and_account):
    """First upsert should create a new record."""
    from jobs.sync_usage import upsert_usage_record
    from models.usage_record import UsageRecord

    acct, svc = seed_service_and_account
    ts = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)

    upsert_usage_record(
        db=db,
        account_id=acct.id,
        service_id=svc.id,
        timestamp=ts,
        tokens_used=1000,
        cost=Decimal("1.50"),
        request_type="daily_sync",
        source="api",
    )
    db.session.commit()

    records = UsageRecord.query.filter_by(account_id=acct.id).all()
    assert len(records) == 1
    assert records[0].tokens_used == 1000
    assert records[0].cost == Decimal("1.50")
    assert records[0].source == "api"


def test_upsert_updates_existing_record(app, db, seed_service_and_account):
    """Second upsert for same key should update, not insert."""
    from jobs.sync_usage import upsert_usage_record
    from models.usage_record import UsageRecord

    acct, svc = seed_service_and_account
    ts = datetime(2026, 2, 2, 0, 0, 0, tzinfo=timezone.utc)

    # First insert
    upsert_usage_record(
        db=db,
        account_id=acct.id,
        service_id=svc.id,
        timestamp=ts,
        tokens_used=500,
        cost=Decimal("0.75"),
        request_type="daily_sync",
    )
    db.session.commit()

    # Second upsert with updated values
    upsert_usage_record(
        db=db,
        account_id=acct.id,
        service_id=svc.id,
        timestamp=ts,
        tokens_used=600,
        cost=Decimal("0.90"),
        request_type="daily_sync",
    )
    db.session.commit()

    records = UsageRecord.query.filter_by(account_id=acct.id).all()
    assert len(records) == 1, "Should have exactly one record (no duplicate)"
    assert records[0].tokens_used == 600
    assert records[0].cost == Decimal("0.90")


def test_upsert_different_request_types_are_separate(app, db, seed_service_and_account):
    """Records with different request_types are treated as distinct rows."""
    from jobs.sync_usage import upsert_usage_record
    from models.usage_record import UsageRecord

    acct, svc = seed_service_and_account
    ts = datetime(2026, 2, 3, 0, 0, 0, tzinfo=timezone.utc)

    upsert_usage_record(
        db=db, account_id=acct.id, service_id=svc.id,
        timestamp=ts, tokens_used=100, cost=Decimal("0.10"),
        request_type="daily_sync",
    )
    upsert_usage_record(
        db=db, account_id=acct.id, service_id=svc.id,
        timestamp=ts, tokens_used=200, cost=Decimal("0.20"),
        request_type="manual",
    )
    db.session.commit()

    records = UsageRecord.query.filter_by(account_id=acct.id).all()
    assert len(records) == 2


def test_upsert_different_dates_are_separate(app, db, seed_service_and_account):
    """Records for different dates are separate rows."""
    from jobs.sync_usage import upsert_usage_record
    from models.usage_record import UsageRecord

    acct, svc = seed_service_and_account
    ts1 = datetime(2026, 2, 4, 0, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 2, 5, 0, 0, 0, tzinfo=timezone.utc)

    upsert_usage_record(
        db=db, account_id=acct.id, service_id=svc.id,
        timestamp=ts1, tokens_used=100, cost=Decimal("0.10"),
        request_type="daily_sync",
    )
    upsert_usage_record(
        db=db, account_id=acct.id, service_id=svc.id,
        timestamp=ts2, tokens_used=200, cost=Decimal("0.20"),
        request_type="daily_sync",
    )
    db.session.commit()

    records = UsageRecord.query.filter_by(
        account_id=acct.id, request_type="daily_sync"
    ).order_by("timestamp").all()
    assert len(records) == 2
    assert records[0].tokens_used == 100
    assert records[1].tokens_used == 200


def test_upsert_repeated_syncs_no_duplicates(app, db, seed_service_and_account):
    """Running sync multiple times must not create duplicate records."""
    from jobs.sync_usage import upsert_usage_record
    from models.usage_record import UsageRecord

    acct, svc = seed_service_and_account
    ts = datetime(2026, 2, 6, 0, 0, 0, tzinfo=timezone.utc)

    # Simulate 5 sync runs
    for i in range(5):
        upsert_usage_record(
            db=db, account_id=acct.id, service_id=svc.id,
            timestamp=ts, tokens_used=1000 + i, cost=Decimal("1.00"),
            request_type="daily_sync",
        )
        db.session.commit()

    records = UsageRecord.query.filter_by(
        account_id=acct.id, request_type="daily_sync"
    ).all()
    assert len(records) == 1, "Must have exactly 1 record after 5 sync runs"
    assert records[0].tokens_used == 1004  # last value wins
