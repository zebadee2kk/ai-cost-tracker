"""
Groq service integration with diagnostic logging.

Groq uses an OpenAI-compatible API but has NO usage/cost report endpoint.
All usage must be captured at call time via call_with_tracking().

Key facts:
- API key format: gsk-...
- Base URL: https://api.groq.com/openai/v1
- Rate limit headers returned on every response (RPD + TPM)
- Unique timing fields in usage: queue_time, prompt_time, completion_time, total_time
- No public pricing — track tokens only

Rate limit header semantics:
  x-ratelimit-limit-requests    → RPD (requests per DAY)
  x-ratelimit-remaining-requests → RPD remaining
  x-ratelimit-limit-tokens      → TPM (tokens per MINUTE)
  x-ratelimit-remaining-tokens  → TPM remaining
  x-ratelimit-reset-requests    → time until RPD resets (e.g. "2m59.56s")
  x-ratelimit-reset-tokens      → time until TPM resets (e.g. "7.66s")
"""

import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from services.base_service import BaseService, ServiceError, AuthenticationError, RateLimitError
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
    log_sync_attempt,
    log_sync_result,
)

logger = get_diagnostic_logger(__name__)

BASE_URL = "https://api.groq.com/openai/v1"


class GroqService(BaseService):
    """Groq API integration with per-request usage and rate-limit tracking.

    Groq exposes no usage history endpoint, so get_usage() always returns an
    empty result.  Actual tracking happens through call_with_tracking(), which
    returns a structured dict containing token counts, timing metrics, and
    extracted rate-limit state that the caller should persist immediately.
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        logger.debug(
            "Initializing Groq service",
            api_key_prefix=api_key[:7] if len(api_key) >= 7 else "***",
        )

        if not api_key.startswith("gsk-"):
            error_msg = (
                "Groq integration requires an API key starting with 'gsk-'. "
                f"Received key starting with: {api_key[:7]}... "
                "Generate a key at https://console.groq.com/keys"
            )
            logger.error(
                "Invalid Groq API key format",
                key_prefix=api_key[:7],
                required_prefix="gsk-",
            )
            raise AuthenticationError(error_msg)

        self._auth_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info("Groq service initialized successfully")

    # ------------------------------------------------------------------
    # BaseService interface
    # ------------------------------------------------------------------

    def validate_credentials(self) -> bool:
        """Test if the API key is valid by listing available models."""
        logger.info("Validating Groq credentials")

        try:
            with log_api_call(logger, "groq", "validate_credentials"):
                self._groq_request("GET", f"{BASE_URL}/models")

            logger.info("Groq credentials validated successfully")
            return True

        except (AuthenticationError, ServiceError) as exc:
            logger.error(
                "Groq credential validation failed",
                exc_info=True,
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
        """Return an empty usage result — Groq has no usage history API.

        Use call_with_tracking() to capture usage at request time instead.
        """
        log_sync_attempt(
            logger,
            "groq",
            account_id or 0,
            "usage",
            start_date=start_date,
            end_date=end_date,
        )

        logger.warning(
            "Groq has no usage history API — returning empty result. "
            "Use call_with_tracking() to capture usage per request.",
            account_id=account_id,
        )

        log_sync_result(
            logger,
            "groq",
            account_id or 0,
            success=True,
            records_created=0,
            note="no_usage_api",
        )

        return {
            "total_tokens": 0,
            "total_cost": 0.0,
            "daily": [],
            "note": "Groq has no usage history API. Track usage via call_with_tracking().",
        }

    # ------------------------------------------------------------------
    # Groq-specific: per-request tracking
    # ------------------------------------------------------------------

    def call_with_tracking(
        self,
        model: str,
        messages: List[Dict[str, str]],
        account_id: Optional[int] = None,
        **extra_params,
    ) -> Dict[str, Any]:
        """Make a Groq chat completion request and return usage + rate-limit data.

        The caller is responsible for persisting the returned tracking data.

        Args:
            model: Groq model identifier (e.g. "llama-3.3-70b-versatile")
            messages: List of chat messages in OpenAI format
            account_id: Optional account ID for logging correlation
            **extra_params: Additional params forwarded to the API (temperature, etc.)

        Returns:
            Dict with keys:
                response      – raw API response body
                tracking      – structured tracking payload:
                    model, input_tokens, output_tokens, total_tokens
                    queue_time_ms, prompt_time_ms, completion_time_ms, total_time_ms
                    rate_limit_rpd, rate_limit_tpm
                    remaining_rpd, remaining_tpm
                    reset_rpd_seconds, reset_tpm_seconds
                    timestamp
        """
        payload = {"model": model, "messages": messages, **extra_params}

        logger.info(
            "Groq chat completion call started",
            model=model,
            account_id=account_id,
            message_count=len(messages),
        )

        request_start = time.time()

        with log_api_call(logger, "groq", "chat/completions", model=model, account_id=account_id):
            resp = self._groq_raw_request("POST", f"{BASE_URL}/chat/completions", json=payload)

        elapsed_ms = (time.time() - request_start) * 1000

        data = resp["body"]
        headers = resp["headers"]
        usage = data.get("usage", {})

        rate_limits = self._extract_rate_limits(headers)
        timing = self._extract_timing(usage, elapsed_ms)

        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        tracking = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "account_id": account_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.get("total_tokens", input_tokens + output_tokens),
            **timing,
            **rate_limits,
        }

        logger.info(
            "Groq chat completion call succeeded",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_time_ms=timing.get("total_time_ms"),
            remaining_tpm=rate_limits.get("remaining_tpm"),
            remaining_rpd=rate_limits.get("remaining_rpd"),
        )

        self._warn_if_quota_low(rate_limits, model)

        return {"response": data, "tracking": tracking}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_rate_limits(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Extract and parse rate-limit headers from a Groq response."""
        return {
            "rate_limit_rpd": self._parse_int(headers.get("x-ratelimit-limit-requests")),
            "rate_limit_tpm": self._parse_int(headers.get("x-ratelimit-limit-tokens")),
            "remaining_rpd": self._parse_int(headers.get("x-ratelimit-remaining-requests")),
            "remaining_tpm": self._parse_int(headers.get("x-ratelimit-remaining-tokens")),
            "reset_rpd_seconds": self._parse_duration(headers.get("x-ratelimit-reset-requests")),
            "reset_tpm_seconds": self._parse_duration(headers.get("x-ratelimit-reset-tokens")),
        }

    def _extract_timing(self, usage: Dict[str, Any], wall_ms: float) -> Dict[str, Any]:
        """Convert Groq timing fields (seconds) to milliseconds."""
        return {
            "queue_time_ms": self._sec_to_ms(usage.get("queue_time")),
            "prompt_time_ms": self._sec_to_ms(usage.get("prompt_time")),
            "completion_time_ms": self._sec_to_ms(usage.get("completion_time")),
            "total_time_ms": self._sec_to_ms(usage.get("total_time")) or round(wall_ms, 2),
        }

    def _warn_if_quota_low(self, rate_limits: Dict[str, Any], model: str) -> None:
        """Log a warning when remaining quota drops below 20%."""
        for quota_type, limit_key, remaining_key in [
            ("TPM", "rate_limit_tpm", "remaining_tpm"),
            ("RPD", "rate_limit_rpd", "remaining_rpd"),
        ]:
            limit = rate_limits.get(limit_key)
            remaining = rate_limits.get(remaining_key)
            if limit and remaining is not None and limit > 0:
                pct = (remaining / limit) * 100
                if pct < 20:
                    logger.warning(
                        f"Groq {quota_type} quota low",
                        model=model,
                        quota_type=quota_type,
                        remaining=remaining,
                        limit=limit,
                        remaining_pct=round(pct, 1),
                    )

    def _groq_request(self, method: str, url: str, **kwargs) -> dict:
        """Make an authenticated Groq request, returning only the parsed body."""
        return self._groq_raw_request(method, url, **kwargs)["body"]

    def _groq_raw_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated Groq request, returning body + response headers.

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
            "groq",
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
                    timeout=30,
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
                "groq",
                resp.status_code,
                response_time,
                headers=dict(resp.headers),
                body=response_body,
                error=resp.text if resp.status_code >= 400 else None,
            )

            if resp.status_code == 401:
                logger.error(
                    "Groq authentication failed (401)",
                    api_key_prefix=self.api_key[:7],
                    url=url,
                )
                raise AuthenticationError(
                    "Invalid or expired Groq API key. "
                    "Ensure you are using a key starting with gsk-."
                )

            elif resp.status_code == 429:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"Groq rate limit hit (429), retrying in {wait}s",
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
                    f"Groq server error {resp.status_code}, retrying in {wait}s",
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
                    f"Groq API error {resp.status_code}",
                    status_code=resp.status_code,
                    error=error_detail,
                    url=url,
                )
                raise ServiceError(f"Groq API error {resp.status_code}: {error_detail}")

            return {"body": resp.json(), "headers": dict(resp.headers)}

        logger.error(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Groq API",
            max_retries=self.MAX_RETRIES,
            url=url,
        )
        raise ServiceError(f"Max retries ({self.MAX_RETRIES}) exceeded for Groq API.")

    # ------------------------------------------------------------------
    # Type-coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_duration(value: Optional[str]) -> Optional[float]:
        """Parse Groq duration strings like '2m59.56s' or '7.66s' into seconds."""
        if not value:
            return None
        try:
            if "m" in value:
                parts = value.split("m")
                minutes = float(parts[0])
                seconds = float(parts[1].rstrip("s")) if len(parts) > 1 and parts[1].rstrip("s") else 0.0
                return round(minutes * 60 + seconds, 3)
            return round(float(value.rstrip("s")), 3)
        except (ValueError, IndexError):
            logger.warning("Could not parse Groq duration", raw_value=value)
            return None

    @staticmethod
    def _sec_to_ms(value: Optional[float]) -> Optional[float]:
        """Convert seconds to milliseconds, returning None for missing values."""
        if value is None:
            return None
        return round(value * 1000, 2)
