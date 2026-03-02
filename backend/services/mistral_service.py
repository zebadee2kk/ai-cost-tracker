"""
Mistral AI service integration with per-request cost calculation.

Mistral provides an OpenAI-compatible API but has NO usage/cost report endpoint.
All usage must be captured at call time via call_with_tracking().

Key facts:
- Base URL: https://api.mistral.ai/v1
- Auth: Authorization: Bearer <key>  (keys have no fixed prefix)
- OpenAI-compatible: /v1/chat/completions, /v1/models
- No usage history API — per-request tracking required
- No documented rate-limit headers (returns 429 with Retry-After on limit)

Documentation: https://docs.mistral.ai/api
API Key management: https://admin.mistral.ai/organization/api-keys
"""

import time
from datetime import datetime
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

BASE_URL = "https://api.mistral.ai/v1"

# Pricing per 1M tokens (March 2026)
# Source: https://mistral.ai/pricing
# Last updated: 2026-03-02
PRICING: Dict[str, Dict[str, Decimal]] = {
    "mistral-nemo": {
        "input": Decimal("0.02"),
        "output": Decimal("0.02"),
    },
    "ministral-8b": {
        "input": Decimal("0.10"),
        "output": Decimal("0.10"),
    },
    "ministral-8b-latest": {
        "input": Decimal("0.10"),
        "output": Decimal("0.10"),
    },
    "mistral-small-2503": {
        "input": Decimal("0.10"),
        "output": Decimal("0.30"),
    },
    "mistral-small-latest": {
        "input": Decimal("0.10"),
        "output": Decimal("0.30"),
    },
    "mistral-medium-3": {
        "input": Decimal("0.40"),
        "output": Decimal("2.00"),
    },
    "mistral-medium-latest": {
        "input": Decimal("0.40"),
        "output": Decimal("2.00"),
    },
    "mistral-large-2411": {
        "input": Decimal("2.00"),
        "output": Decimal("6.00"),
    },
    "mistral-large-latest": {
        "input": Decimal("2.00"),
        "output": Decimal("6.00"),
    },
    "codestral-2501": {
        "input": Decimal("0.30"),
        "output": Decimal("0.90"),
    },
    "codestral-latest": {
        "input": Decimal("0.30"),
        "output": Decimal("0.90"),
    },
    # Fallback pricing for unknown or new models
    "_default": {
        "input": Decimal("0.40"),
        "output": Decimal("2.00"),
    },
}


class MistralService(BaseService):
    """Mistral AI integration with per-request usage tracking and local cost calculation.

    Mistral exposes no usage history endpoint, so get_usage() always returns an
    empty result.  Actual tracking happens through call_with_tracking(), which
    returns a structured dict containing token counts and calculated cost that
    the caller should persist immediately.
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        if not api_key:
            raise AuthenticationError(
                "Mistral API key is empty. "
                "Generate a key at https://admin.mistral.ai/organization/api-keys"
            )

        self._auth_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(
            "Mistral service initialized",
            api_key_prefix=api_key[:7] if len(api_key) >= 7 else "***",
        )
        logger.info("Mistral service initialized successfully")

    # ------------------------------------------------------------------
    # BaseService interface
    # ------------------------------------------------------------------

    def validate_credentials(self) -> bool:
        """Test if the API key is valid by listing available models."""
        logger.info("Validating Mistral credentials")

        try:
            with log_api_call(logger, "mistral", "validate_credentials"):
                self._mistral_request("GET", f"{BASE_URL}/models")

            logger.info("Mistral credentials validated successfully")
            return True

        except (AuthenticationError, ServiceError) as exc:
            logger.error(
                "Mistral credential validation failed",
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
        """Return an empty usage result — Mistral has no usage history API.

        Use call_with_tracking() to capture usage at request time instead.
        """
        log_sync_attempt(
            logger,
            "mistral",
            account_id or 0,
            "usage",
            start_date=start_date,
            end_date=end_date,
        )

        logger.warning(
            "Mistral has no usage history API — returning empty result. "
            "Use call_with_tracking() to capture usage per request.",
            account_id=account_id,
        )

        log_sync_result(
            logger,
            "mistral",
            account_id or 0,
            success=True,
            records_created=0,
            note="no_usage_api",
        )

        return {
            "total_tokens": 0,
            "total_cost": 0.0,
            "daily": [],
            "note": "Mistral has no usage history API. Track usage via call_with_tracking().",
        }

    # ------------------------------------------------------------------
    # Mistral-specific: per-request tracking
    # ------------------------------------------------------------------

    def call_with_tracking(
        self,
        model: str,
        messages: List[Dict[str, str]],
        account_id: Optional[int] = None,
        **extra_params,
    ) -> Dict[str, Any]:
        """Make a Mistral chat completion request and return usage + cost data.

        The caller is responsible for persisting the returned tracking data.

        Args:
            model: Mistral model identifier (e.g. "mistral-large-latest")
            messages: List of chat messages in OpenAI format
            account_id: Optional account ID for logging correlation
            **extra_params: Additional params forwarded to the API (temperature, etc.)

        Returns:
            Dict with keys:
                response  – raw API response body
                tracking  – structured tracking payload:
                    timestamp, model, account_id
                    input_tokens, output_tokens, total_tokens
                    cost (USD, calculated locally)
                    cost_breakdown (dict with input_cost, output_cost)
        """
        payload = {"model": model, "messages": messages, **extra_params}

        logger.info(
            "Mistral chat completion call started",
            model=model,
            account_id=account_id,
            message_count=len(messages),
        )

        request_start = time.time()

        with log_api_call(logger, "mistral", "chat/completions", model=model, account_id=account_id):
            data = self._mistral_request("POST", f"{BASE_URL}/chat/completions", json=payload)

        elapsed_ms = (time.time() - request_start) * 1000

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        cost, cost_breakdown = self._calculate_cost(model, input_tokens, output_tokens)

        tracking = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "account_id": account_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": float(cost),
            "cost_breakdown": cost_breakdown,
            "total_time_ms": round(elapsed_ms, 2),
        }

        logger.info(
            "Mistral chat completion call succeeded",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_time_ms=round(elapsed_ms, 2),
            cost_usd=float(cost),
        )

        return {"response": data, "tracking": tracking}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> tuple:
        """Calculate USD cost from token counts.

        Returns (total_cost: Decimal, breakdown: dict).
        """
        pricing = PRICING.get(model, PRICING["_default"])
        if model not in PRICING:
            logger.warning(
                f"Unknown Mistral model '{model}' — using default pricing",
                model=model,
            )

        input_cost = (Decimal(str(input_tokens)) / Decimal("1000000")) * pricing["input"]
        output_cost = (Decimal(str(output_tokens)) / Decimal("1000000")) * pricing["output"]
        total = input_cost + output_cost

        breakdown = {
            "input_cost": float(round(input_cost, 8)),
            "output_cost": float(round(output_cost, 8)),
        }

        logger.debug(
            "Mistral cost calculated",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=float(total),
        )

        return total, breakdown

    def _mistral_request(self, method: str, url: str, **kwargs) -> dict:
        """Make an authenticated Mistral request with diagnostic logging.

        Handles:
        - Auth header injection
        - 401 → AuthenticationError
        - 429 → RateLimitError with Retry-After backoff
        - 5xx → ServiceError with retry
        """
        params = kwargs.pop("params", None)
        json_body = kwargs.pop("json", None)

        request_start = time.time()

        log_provider_request(
            logger,
            "mistral",
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
                "mistral",
                resp.status_code,
                response_time,
                headers=dict(resp.headers),
                body=response_body,
                error=resp.text if resp.status_code >= 400 else None,
            )

            if resp.status_code == 401:
                logger.error(
                    "Mistral authentication failed (401)",
                    api_key_prefix=self.api_key[:7],
                    url=url,
                )
                raise AuthenticationError(
                    "Invalid or expired Mistral API key. "
                    "Generate a new key at https://admin.mistral.ai/organization/api-keys"
                )
            elif resp.status_code == 429:
                # Respect Retry-After header if present; otherwise use backoff
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"Mistral rate limit hit (429), retrying in {wait}s",
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
                    f"Mistral server error {resp.status_code}, retrying in {wait}s",
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
                    error_detail = resp.json().get("message", "Unknown error")
                except Exception:
                    error_detail = resp.text or "Unknown error"

                logger.error(
                    f"Mistral API error {resp.status_code}",
                    status_code=resp.status_code,
                    error=error_detail,
                    url=url,
                )
                raise ServiceError(f"Mistral API error {resp.status_code}: {error_detail}")

            return resp.json()

        logger.error(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Mistral API",
            max_retries=self.MAX_RETRIES,
            url=url,
        )
        raise ServiceError(f"Max retries ({self.MAX_RETRIES}) exceeded for Mistral API.")
