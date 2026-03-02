"""Groq API service integration with ultra-fast inference tracking.

Groq specializes in extremely fast LLM inference using custom LPU hardware.
Key features to track:
- Detailed timing metrics (queue, prompt, completion)
- Rate limit headers (TPM/RPD)
- No usage API endpoint (per-request tracking only)

Documentation:
https://console.groq.com/docs

Key format: gsk_...
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from services.base_service import BaseService, ServiceError, AuthenticationError
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
)

logger = get_diagnostic_logger(__name__)

BASE_URL = "https://api.groq.com/openai/v1"


class GroqService(BaseService):
    """Groq API integration with timing and rate limit tracking.
    
    Groq does not provide a usage API endpoint, so all tracking must be
    done per-request by extracting usage from response body and rate
    limits from response headers.
    
    Key Features:
    - Ultra-fast inference (often < 100ms total)
    - Detailed timing breakdowns
    - Rate limit headers on every response
    - No public pricing (track tokens only)
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        logger.debug(
            "Initializing Groq service",
            api_key_prefix=api_key[:8] if len(api_key) >= 8 else "***",
        )

        if not api_key.startswith('gsk_'):
            error_msg = (
                f"Groq API key should start with 'gsk_'. "
                f"Received key starting with: {api_key[:4]}..."
            )
            logger.error(
                "Invalid Groq API key format",
                key_prefix=api_key[:4],
                required_prefix="gsk_",
            )
            raise AuthenticationError(error_msg)

        self._auth_headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        logger.info("Groq service initialized successfully")

    def validate_credentials(self) -> bool:
        """Test if the API key is valid by making a minimal chat completion."""
        logger.info("Validating Groq credentials")

        try:
            with log_api_call(logger, "groq", "validate_credentials"):
                response = self._groq_request(
                    'POST',
                    f"{BASE_URL}/chat/completions",
                    json={
                        'model': 'llama-3.3-70b-versatile',
                        'messages': [{'role': 'user', 'content': 'Hi'}],
                        'max_tokens': 1,
                    }
                )

            logger.info(
                "Groq credentials validated successfully",
                response_id=response.get('id'),
            )
            return True

        except (AuthenticationError, ServiceError) as exc:
            logger.error(
                "Groq credential validation failed",
                exc_info=True,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return False

    def call_with_tracking(
        self,
        model: str,
        messages: list,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make a Groq API call and return response with extracted metrics.
        
        This is the primary method for using Groq since there is no usage API.
        Returns a dict with:
        - response: Full API response
        - usage: Token counts and timing metrics
        - rate_limits: Extracted from headers
        
        Example:
            result = service.call_with_tracking(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'user', 'content': 'Hello'}]
            )
            # Store result['usage'] and result['rate_limits'] in database
        """
        logger.info(
            "Making tracked Groq API call",
            model=model,
            message_count=len(messages),
        )

        request_data = {
            'model': model,
            'messages': messages,
        }
        if max_tokens is not None:
            request_data['max_tokens'] = max_tokens
        if temperature is not None:
            request_data['temperature'] = temperature

        with log_api_call(logger, "groq", "chat_completion", model=model):
            response_obj = self._groq_request_with_headers(
                'POST',
                f"{BASE_URL}/chat/completions",
                json=request_data
            )

        response = response_obj['data']
        headers = response_obj['headers']
        usage = response.get('usage', {})

        # Extract rate limits from headers
        rate_limits = self._extract_rate_limits(headers)

        # Warn if quota is low
        if rate_limits.get('remaining_tpm') and rate_limits.get('limit_tpm'):
            remaining_pct = (
                rate_limits['remaining_tpm'] / rate_limits['limit_tpm']
            ) * 100
            if remaining_pct < 20:
                logger.warning(
                    f"Groq TPM quota low: {remaining_pct:.1f}%",
                    remaining=rate_limits['remaining_tpm'],
                    limit=rate_limits['limit_tpm'],
                )

        logger.info(
            "Groq API call completed",
            response_id=response.get('id'),
            input_tokens=usage.get('prompt_tokens', 0),
            output_tokens=usage.get('completion_tokens', 0),
            total_time_ms=usage.get('total_time', 0) * 1000,
        )

        return {
            'response': response,
            'usage': usage,
            'rate_limits': rate_limits,
        }

    def get_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> dict:
        """Groq has no usage API endpoint.
        
        Usage must be tracked per-request via call_with_tracking().
        This method exists for interface consistency but returns a
        message indicating per-request tracking is required.
        """
        logger.warning(
            "Groq has no usage API - use call_with_tracking() for per-request logging"
        )

        return {
            'error': 'no_usage_api',
            'message': (
                'Groq does not provide a usage API endpoint. '
                'Use call_with_tracking() to capture usage on each API call '
                'and store in database immediately.'
            ),
            'tracking_method': 'per_request_only',
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_rate_limits(self, headers: dict) -> dict:
        """Extract rate limit information from response headers.
        
        Groq returns:
        - x-ratelimit-limit-requests: RPD (requests per DAY, not minute)
        - x-ratelimit-limit-tokens: TPM (tokens per MINUTE)
        - x-ratelimit-remaining-requests: RPD remaining
        - x-ratelimit-remaining-tokens: TPM remaining
        - x-ratelimit-reset-requests: Time until RPD reset (e.g., '2m59.56s')
        - x-ratelimit-reset-tokens: Time until TPM reset (e.g., '7.66s')
        """
        return {
            'limit_rpd': self._parse_int(headers.get('x-ratelimit-limit-requests')),
            'limit_tpm': self._parse_int(headers.get('x-ratelimit-limit-tokens')),
            'remaining_rpd': self._parse_int(headers.get('x-ratelimit-remaining-requests')),
            'remaining_tpm': self._parse_int(headers.get('x-ratelimit-remaining-tokens')),
            'reset_rpd': headers.get('x-ratelimit-reset-requests'),
            'reset_tpm': headers.get('x-ratelimit-reset-tokens'),
        }

    def _parse_int(self, value: Any) -> Optional[int]:
        """Safely parse string to int."""
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _groq_request(self, method: str, url: str, **kwargs) -> dict:
        """Make authenticated request to Groq API (response body only)."""
        result = self._groq_request_with_headers(method, url, **kwargs)
        return result['data']

    def _groq_request_with_headers(
        self, method: str, url: str, **kwargs
    ) -> dict:
        """Make authenticated request and return both data and headers.
        
        Returns:
            {
                'data': response JSON,
                'headers': response headers dict
            }
        """
        json_body = kwargs.pop('json', None)
        params = kwargs.pop('params', None)

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

            response_time = (time.time() - request_start) * 1000  # ms

            try:
                response_body = resp.json() if resp.text else None
            except:
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
                    api_key_prefix=self.api_key[:8],
                    url=url,
                )
                raise AuthenticationError(
                    "Invalid Groq API key. Ensure key starts with 'gsk_'."
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
                    error_detail = response_body.get('error', {}).get(
                        'message', 'Unknown error'
                    )
                except:
                    error_detail = resp.text or 'Unknown error'

                logger.error(
                    f"Groq API error {resp.status_code}",
                    status_code=resp.status_code,
                    error=error_detail,
                    url=url,
                )
                raise ServiceError(
                    f"Groq API error {resp.status_code}: {error_detail}"
                )

            return {
                'data': resp.json(),
                'headers': dict(resp.headers),
            }

        logger.error(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Groq API",
            max_retries=self.MAX_RETRIES,
            url=url,
        )
        raise ServiceError(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Groq API."
        )
