"""
Background scheduler: syncs usage from AI APIs into the database.

Runs on APScheduler (interval trigger) inside the Flask app process.
Start it by calling start_scheduler(app) from app.py or run.py.
"""

import logging
from datetime import date, datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler(app):
    global _scheduler
    if _scheduler and _scheduler.running:
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


def _sync_all_accounts(app):
    """Fetch usage for every active account and persist UsageRecords."""
    with app.app_context():
        from app import db
        from models.account import Account
        from models.usage_record import UsageRecord
        from utils.encryption import decrypt_api_key
        from utils.alert_generator import check_and_generate_alerts
        from services.openai_service import OpenAIService
        from services.base_service import ServiceError
        from decimal import Decimal

        accounts = Account.query.filter_by(is_active=True).all()
        logger.info("Syncing usage for %d active accounts.", len(accounts))

        today = date.today()
        month_start = today.replace(day=1).isoformat()
        tomorrow = (today.replace(day=today.day) if True else today).isoformat()  # used below

        # Service name -> client class mapping (Phase 1: OpenAI only)
        service_clients = {
            "ChatGPT": OpenAIService,
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

            # Persist one UsageRecord per day returned
            for day_data in usage.get("daily", []):
                record = UsageRecord(
                    account_id=account.id,
                    service_id=account.service_id,
                    timestamp=datetime.fromisoformat(day_data["date"]).replace(tzinfo=timezone.utc),
                    tokens_used=day_data.get("tokens", 0),
                    cost=day_data.get("cost", 0),
                    cost_currency="USD",
                    api_calls=1,
                    request_type="daily_sync",
                    metadata={"line_items": day_data.get("line_items", [])},
                )
                db.session.add(record)

            account.last_sync = datetime.now(timezone.utc)

            # Check alerts based on total cost this month
            if account.monthly_limit:
                monthly_cost = Decimal(str(usage.get("total_cost", 0)))
                check_and_generate_alerts(account, monthly_cost, Decimal(str(account.monthly_limit)))

        try:
            db.session.commit()
            logger.info("Usage sync complete.")
        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to commit sync results: %s", exc)
