"""
OpenAI service integration.

Uses the OpenAI billing/usage API endpoints documented at:
https://platform.openai.com/docs/api-reference/usage

Key endpoints:
  GET /v1/dashboard/billing/usage?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  GET /v1/dashboard/billing/credit_grants
  GET /v1/models  (used for credential validation)
"""

import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from services.base_service import BaseService, AuthenticationError, RateLimitError, ServiceError
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
    log_sync_attempt,
    log_sync_result,
)

logger = get_diagnostic_logger(__name__)

BASE_URL = "https://api.openai.com"


class OpenAIService(BaseService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._auth_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        logger.debug(
            "OpenAI service initialized",
            api_key_prefix=api_key[:7] if len(api_key) >= 7 else "***",
        )

    def validate_credentials(self) -> bool:
        """Validate the API key by listing models (lightweight call)."""
        logger.info("Validating OpenAI credentials")
        try:
            with log_api_call(logger, "openai", "validate_credentials"):
                self._openai_request("GET", f"{BASE_URL}/v1/models")
            logger.info("OpenAI credentials validated successfully")
            return True
        except (AuthenticationError, ServiceError) as exc:
            logger.warning(
                "OpenAI credential validation failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return False

    def get_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> dict:
        """
        Fetch billing usage from OpenAI for a date range.

        Dates should be in YYYY-MM-DD format.
        Defaults to the current calendar month.
        """
        today = date.today()
        if not start_date:
            start_date = today.replace(day=1).isoformat()
        if not end_date:
            # tomorrow so today's data is included
            end_date = (today + timedelta(days=1)).isoformat()

        log_sync_attempt(
            logger,
            "openai",
            account_id or 0,
            "usage",
            start_date=start_date,
            end_date=end_date,
        )

        sync_start = time.time()

        try:
            with log_api_call(
                logger,
                "openai",
                "dashboard/billing/usage",
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
            ):
                data = self._openai_request(
                    "GET",
                    f"{BASE_URL}/v1/dashboard/billing/usage",
                    params={"start_date": start_date, "end_date": end_date},
                )
        except ServiceError:
            elapsed = time.time() - sync_start
            log_sync_result(
                logger, "openai", account_id or 0, success=False,
                error="ServiceError", elapsed_seconds=elapsed,
            )
            raise

        result = self._parse_usage_response(data)
        elapsed = time.time() - sync_start
        log_sync_result(
            logger,
            "openai",
            account_id or 0,
            success=True,
            records_created=len(result.get("daily", [])),
            elapsed_seconds=elapsed,
        )
        return result

    def get_subscription(self) -> dict:
        """Return subscription / credit grant information."""
        try:
            with log_api_call(logger, "openai", "dashboard/billing/credit_grants"):
                return self._openai_request(
                    "GET",
                    f"{BASE_URL}/v1/dashboard/billing/credit_grants",
                )
        except ServiceError:
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_usage_response(self, raw: dict) -> dict:
        """
        Normalise the OpenAI billing/usage response into our standard shape:
        {
            "total_tokens": int,
            "total_cost": float,         # USD, cents -> dollars
            "daily": [{"date": str, "tokens": int, "cost": float}]
        }

        OpenAI returns cost in *cents* (total_usage field), and the daily
        breakdown via line_items within each entry.
        """
        total_usage_cents = raw.get("total_usage", 0)  # in cents
        total_cost_usd = total_usage_cents / 100.0

        daily = []
        for entry in raw.get("data", []):
            # timestamp is unix epoch (start of day)
            ts = entry.get("timestamp", 0)
            entry_date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()

            entry_cost_usd = sum(
                item.get("cost", 0) for item in entry.get("line_items", [])
            ) / 100.0

            daily.append(
                {
                    "date": entry_date,
                    "tokens": 0,  # OpenAI billing API doesn't return token counts here
                    "cost": round(entry_cost_usd, 6),
                    "line_items": entry.get("line_items", []),
                }
            )

        return {
            "total_tokens": 0,
            "total_cost": round(total_cost_usd, 6),
            "daily": daily,
        }

    def _extract_rate_limits(self, headers: dict) -> dict:
        """Extract rate limit info from response headers."""
        return {
            "limit_tpm": self._parse_int(headers.get("x-ratelimit-limit-tokens")),
            "limit_rpm": self._parse_int(headers.get("x-ratelimit-limit-requests")),
            "remaining_tpm": self._parse_int(headers.get("x-ratelimit-remaining-tokens")),
            "remaining_rpm": self._parse_int(headers.get("x-ratelimit-remaining-requests")),
            "reset_tpm": headers.get("x-ratelimit-reset-tokens"),
            "reset_rpm": headers.get("x-ratelimit-reset-requests"),
        }

    def _openai_request(self, method: str, url: str, **kwargs) -> dict:
        """Make an authenticated OpenAI request with diagnostic logging.

        Handles:
        - Auth header injection
        - 401 → AuthenticationError
        - 429 → RateLimitError with retry
        - 5xx → ServiceError with retry
        """
        params = kwargs.pop("params", None)
        json_body = kwargs.pop("json", None)

        request_start = time.time()

        log_provider_request(
            logger,
            "openai",
            method,
            url,
            headers=self._auth_headers,
            params=params,
            json_body=json_body,
        )

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    headers=self._auth_headers,
                    params=params,
                    json=json_body,
                    timeout=15,
                )
            except Exception as exc:
                logger.error(
                    f"Request to {url} failed (network error)",
                    exc_info=True,
                    url=url,
                    attempt=attempt,
                )
                raise ServiceError(f"Request to {url} failed: {exc}") from exc

            response_time = (time.time() - request_start) * 1000

            try:
                response_body = resp.json() if resp.text else None
            except Exception:
                response_body = None

            log_provider_response(
                logger,
                "openai",
                resp.status_code,
                response_time,
                headers=dict(resp.headers),
                body=response_body,
                error=resp.text if resp.status_code >= 400 else None,
            )

            if resp.status_code == 401:
                logger.error(
                    "OpenAI authentication failed (401)",
                    api_key_prefix=self.api_key[:7],
                    url=url,
                )
                raise AuthenticationError(
                    "Invalid or expired OpenAI API key."
                )
            elif resp.status_code == 429:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"OpenAI rate limit hit (429), retrying in {wait}s",
                    attempt=attempt,
                    max_retries=self.MAX_RETRIES,
                    wait_seconds=wait,
                    url=url,
                )
                time.sleep(wait)
                continue
            elif resp.status_code >= 500:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"OpenAI server error {resp.status_code}, retrying in {wait}s",
                    status_code=resp.status_code,
                    attempt=attempt,
                    max_retries=self.MAX_RETRIES,
                    wait_seconds=wait,
                    url=url,
                )
                time.sleep(wait)
                continue
            elif resp.status_code >= 400:
                try:
                    error_detail = resp.json().get("error", {}).get("message", "Unknown error")
                except Exception:
                    error_detail = resp.text or "Unknown error"

                logger.error(
                    f"OpenAI API error {resp.status_code}",
                    status_code=resp.status_code,
                    error=error_detail,
                    url=url,
                )
                raise ServiceError(f"OpenAI API error {resp.status_code}: {error_detail}")

            return resp.json()

        logger.error(
            f"Max retries ({self.MAX_RETRIES}) exceeded for OpenAI API",
            max_retries=self.MAX_RETRIES,
            url=url,
        )
        raise ServiceError(f"Max retries ({self.MAX_RETRIES}) exceeded for OpenAI API.")

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None
