"""
Background scheduler: syncs usage from AI APIs into the database.

Runs on APScheduler (interval trigger) inside the Flask app process.
Start it by calling start_scheduler(app) from app.py or run.py.
"""

import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler(app):
    """Start the background scheduler.

    Skips initialization in the Flask reloader's parent process to prevent
    duplicate job execution when running with debug=True.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    # Flask debug mode spawns a child process via Werkzeug's reloader.
    # Only start the scheduler in the child process (or in production).
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        app.logger.info(
            "Skipping scheduler init in Flask reloader parent process "
            "(set WERKZEUG_RUN_MAIN=true or disable debug mode to start)."
        )
        return

    interval_minutes = app.config.get("SYNC_INTERVAL_MINUTES", 60)

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        func=_sync_all_accounts,
        args=[app],
        trigger="interval",
        minutes=interval_minutes,
        id="sync_usage",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Usage sync scheduler started (interval=%d min).", interval_minutes)


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def upsert_usage_record(db, account_id, service_id, timestamp, tokens_used,
                        cost, request_type, source='api', extra_data=None):
    """Insert or update a usage record idempotently.

    Uses PostgreSQL ON CONFLICT DO UPDATE when available, falling back to a
    check-then-insert approach for SQLite (used in tests).

    The unique key is (account_id, service_id, timestamp, request_type).
    Timestamps must be normalized (e.g. midnight UTC) to reliably de-duplicate
    daily records.
    """
    from models.usage_record import UsageRecord

    engine = db.engine

    if engine.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
        from sqlalchemy import func

        stmt = insert(UsageRecord).values(
            account_id=account_id,
            service_id=service_id,
            timestamp=timestamp,
            tokens_used=tokens_used,
            cost=Decimal(str(cost)),
            cost_currency='USD',
            api_calls=1,
            request_type=request_type,
            source=source,
            extra_data=extra_data or {},
            created_at=func.now(),
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_usage_record_idempotency',
            set_={
                'tokens_used': stmt.excluded.tokens_used,
                'cost': stmt.excluded.cost,
                'extra_data': stmt.excluded.extra_data,
                'updated_at': func.now(),
            }
        )
        db.session.execute(stmt)
    else:
        # SQLite fallback (used in tests): check-then-insert/update
        existing = UsageRecord.query.filter_by(
            account_id=account_id,
            service_id=service_id,
            timestamp=timestamp,
            request_type=request_type,
        ).first()

        if existing:
            existing.tokens_used = tokens_used
            existing.cost = Decimal(str(cost))
            existing.extra_data = extra_data or {}
            existing.updated_at = datetime.now(timezone.utc)
        else:
            record = UsageRecord(
                account_id=account_id,
                service_id=service_id,
                timestamp=timestamp,
                tokens_used=tokens_used,
                cost=Decimal(str(cost)),
                cost_currency='USD',
                api_calls=1,
                request_type=request_type,
                source=source,
                extra_data=extra_data or {},
            )
            db.session.add(record)


def _sync_all_accounts(app):
    """Fetch usage for every active account and persist UsageRecords."""
    with app.app_context():
        from app import db
        from models.account import Account
        from utils.encryption import decrypt_api_key
        from utils.alert_generator import check_and_generate_alerts
        from services.openai_service import OpenAIService
        from services.anthropic_service import AnthropicService
        from services.base_service import ServiceError

        accounts = Account.query.filter_by(is_active=True).all()
        logger.info("Syncing usage for %d active accounts.", len(accounts))

        today = date.today()
        month_start = today.replace(day=1).isoformat()

        # Service name -> client class mapping
        service_clients = {
            "ChatGPT": OpenAIService,
            "OpenAI": OpenAIService,
            "Anthropic": AnthropicService,
            "Claude": AnthropicService,
        }

        for account in accounts:
            service_name = account.service.name if account.service else ""
            client_class = service_clients.get(service_name)

            if not client_class:
                logger.debug("No sync client for service '%s', skipping.", service_name)
                continue

            if not account.api_key:
                logger.debug("Account %d has no API key, skipping.", account.id)
                continue

            try:
                plaintext_key = decrypt_api_key(account.api_key)
                client = client_class(plaintext_key)
                usage = client.get_usage(start_date=month_start)
            except Exception as exc:
                logger.error("Failed to sync account %d: %s", account.id, exc)
                continue

            # Upsert one UsageRecord per day returned
            for day_data in usage.get("daily", []):
                # Normalize to midnight UTC to ensure idempotent de-duplication
                ts = datetime.fromisoformat(day_data["date"]).replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                )
                upsert_usage_record(
                    db=db,
                    account_id=account.id,
                    service_id=account.service_id,
                    timestamp=ts,
                    tokens_used=day_data.get("tokens", 0),
                    cost=day_data.get("cost", 0),
                    request_type="daily_sync",
                    source="api",
                    extra_data=day_data.get("metadata", {"line_items": day_data.get("line_items", [])}),
                )

            account.last_sync = datetime.now(timezone.utc)

            # Check alerts based on total cost this month
            if account.monthly_limit:
                monthly_cost = Decimal(str(usage.get("total_cost", 0)))
                check_and_generate_alerts(
                    account, monthly_cost, Decimal(str(account.monthly_limit))
                )

        try:
            db.session.commit()
            logger.info("Usage sync complete.")
        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to commit sync results: %s", exc)
