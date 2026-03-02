"""Perplexity API service integration with per-request cost calculation.

Perplexity provides multiple APIs:
1. Sonar API - Web-enhanced chat with search
2. Agent API - Third-party models with tools
3. Search API - Raw search results
4. Embeddings API - Text embeddings

Key Limitation: No usage API endpoint exists (as of March 2026).
Feature request: GitHub issue #266

Tracking Strategy:
- Log every API response immediately
- Calculate costs locally using pricing table
- Reconcile monthly via invoice history (4-char key suffix)

Documentation:
https://docs.perplexity.ai

Key format: pplx-...
"""

import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

from services.base_service import BaseService, ServiceError, AuthenticationError
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
)

logger = get_diagnostic_logger(__name__)

BASE_URL = "https://api.perplexity.ai"

# Pricing per 1M tokens (March 2026)
# Request fees are context-dependent: low/medium/high
PRICING = {
    'sonar': {
        'input': Decimal('1.00'),
        'output': Decimal('1.00'),
        'request_low': Decimal('0.005'),
        'request_medium': Decimal('0.010'),
        'request_high': Decimal('0.020'),
    },
    'sonar-pro': {
        'input': Decimal('3.00'),
        'output': Decimal('15.00'),
        'request_low': Decimal('0.005'),
        'request_medium': Decimal('0.010'),
        'request_high': Decimal('0.020'),
    },
    'sonar-reasoning-pro': {
        'input': Decimal('2.00'),
        'output': Decimal('8.00'),
        'request': Decimal('0.010'),
    },
    'sonar-deep-research': {
        'input': Decimal('2.00'),
        'output': Decimal('8.00'),
        'citations': Decimal('2.00'),
        'reasoning': Decimal('3.00'),
        'searches': Decimal('5.00'),  # Per 1K searches
        'request': Decimal('0.010'),
    },
    # Embeddings
    'pplx-embed-v1-0.6b': {
        'input': Decimal('0.004'),
    },
    'pplx-embed-v1-4b': {
        'input': Decimal('0.03'),
    },
    'pplx-embed-context-v1-0.6b': {
        'input': Decimal('0.008'),
    },
    'pplx-embed-context-v1-4b': {
        'input': Decimal('0.05'),
    },
    # Search API (flat rate)
    'search': {
        'per_request': Decimal('0.005'),  # $5 per 1K requests
    },
}


class PerplexityService(BaseService):
    """Perplexity API integration with per-request tracking.
    
    Since Perplexity has no usage API endpoint, all tracking must be
    done immediately after each API call. The service extracts usage
    from the response and calculates costs locally.
    
    Key Features:
    - Sonar models with web search
    - Deep Research with citations and reasoning
    - Agent API for third-party models
    - Local cost calculation (no cost API)
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        logger.debug(
            "Initializing Perplexity service",
            api_key_prefix=api_key[:8] if len(api_key) >= 8 else "***",
        )

        if not api_key.startswith('pplx-'):
            error_msg = (
                f"Perplexity API key should start with 'pplx-'. "
                f"Received key starting with: {api_key[:5]}..."
            )
            logger.error(
                "Invalid Perplexity API key format",
                key_prefix=api_key[:5],
                required_prefix="pplx-",
            )
            raise AuthenticationError(error_msg)

        self._auth_headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        logger.info("Perplexity service initialized successfully")

    def validate_credentials(self) -> bool:
        """Test if the API key is valid by making a minimal chat completion."""
        logger.info("Validating Perplexity credentials")

        try:
            with log_api_call(logger, "perplexity", "validate_credentials"):
                response = self._perplexity_request(
                    'POST',
                    f"{BASE_URL}/chat/completions",
                    json={
                        'model': 'sonar',
                        'messages': [{'role': 'user', 'content': 'Hi'}],
                        'max_tokens': 1,
                    }
                )

            logger.info(
                "Perplexity credentials validated successfully",
                response_id=response.get('id'),
            )
            return True

        except (AuthenticationError, ServiceError) as exc:
            logger.error(
                "Perplexity credential validation failed",
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
        search_context: str = 'medium',  # low/medium/high
    ) -> Dict[str, Any]:
        """Make a Perplexity API call and return response with calculated cost.
        
        This is the primary method for using Perplexity since there is no usage API.
        Returns a dict with:
        - response: Full API response
        - usage: Token counts and search metrics
        - cost: Calculated cost in USD
        
        Args:
            model: Perplexity model name (e.g., 'sonar', 'sonar-deep-research')
            messages: Chat messages list
            max_tokens: Max output tokens
            temperature: Sampling temperature
            search_context: Context level for request fee (low/medium/high)
        
        Example:
            result = service.call_with_tracking(
                model='sonar-deep-research',
                messages=[{'role': 'user', 'content': 'Research topic X'}],
                search_context='high'
            )
            # Store result['usage'] and result['cost'] in database
        """
        logger.info(
            "Making tracked Perplexity API call",
            model=model,
            message_count=len(messages),
            search_context=search_context,
        )

        request_data = {
            'model': model,
            'messages': messages,
        }
        if max_tokens is not None:
            request_data['max_tokens'] = max_tokens
        if temperature is not None:
            request_data['temperature'] = temperature

        with log_api_call(logger, "perplexity", "chat_completion", model=model):
            response = self._perplexity_request(
                'POST',
                f"{BASE_URL}/chat/completions",
                json=request_data
            )

        usage = response.get('usage', {})

        # Calculate cost locally (Perplexity doesn't return cost)
        cost = self._calculate_cost(model, usage, search_context)

        logger.info(
            "Perplexity API call completed",
            response_id=response.get('id'),
            input_tokens=usage.get('prompt_tokens', 0),
            output_tokens=usage.get('completion_tokens', 0),
            search_queries=usage.get('search_queries', 0),
            cost_usd=float(cost),
        )

        return {
            'response': response,
            'usage': usage,
            'cost': float(cost),
            'search_context': search_context,
        }

    def get_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> dict:
        """Perplexity has no usage API endpoint.
        
        Usage must be tracked per-request via call_with_tracking().
        This method exists for interface consistency but returns a
        message indicating per-request tracking is required.
        
        For historical data, check invoice history at:
        https://www.perplexity.ai/settings/api → Invoices
        (Shows last 4 chars of API key per line item)
        """
        logger.warning(
            "Perplexity has no usage API - use call_with_tracking() for per-request logging"
        )

        return {
            'error': 'no_usage_api',
            'message': (
                'Perplexity does not provide a usage API endpoint. '
                'Use call_with_tracking() to capture usage on each API call '
                'and store in database immediately. '
                'For reconciliation, check invoice history at '
                'https://www.perplexity.ai/settings/api → Invoices '
                '(matches last 4 chars of API key).'
            ),
            'tracking_method': 'per_request_only',
            'reconciliation': 'invoice_history_manual',
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_cost(
        self,
        model: str,
        usage: dict,
        search_context: str = 'medium',
    ) -> Decimal:
        """Calculate USD cost from token counts and usage metrics.
        
        Args:
            model: Model name
            usage: Usage dict from API response with fields:
                - prompt_tokens
                - completion_tokens
                - search_queries (Deep Research only)
                - reasoning_tokens (Deep Research only)
                - citation_tokens (Deep Research only)
            search_context: Context level (low/medium/high)
        
        Returns:
            Decimal cost in USD
        """
        pricing = PRICING.get(model)
        if not pricing:
            logger.warning(
                f"Unknown model '{model}' - cannot calculate cost",
                model=model,
            )
            return Decimal('0')

        input_tokens = Decimal(str(usage.get('prompt_tokens', 0)))
        output_tokens = Decimal(str(usage.get('completion_tokens', 0)))

        # Base token costs (per 1M tokens)
        input_cost = (input_tokens / Decimal('1000000')) * pricing.get('input', Decimal('0'))
        output_cost = (output_tokens / Decimal('1000000')) * pricing.get('output', Decimal('0'))

        # Request fee (context-dependent for Sonar models)
        request_cost = Decimal('0')
        if 'request' in pricing:
            request_cost = pricing['request']
        elif f'request_{search_context}' in pricing:
            request_cost = pricing[f'request_{search_context}']

        # Deep Research additional costs
        citation_cost = Decimal('0')
        reasoning_cost = Decimal('0')
        search_cost = Decimal('0')

        if 'citations' in pricing:
            citation_tokens = Decimal(str(usage.get('citation_tokens', 0)))
            citation_cost = (citation_tokens / Decimal('1000000')) * pricing['citations']

        if 'reasoning' in pricing:
            reasoning_tokens = Decimal(str(usage.get('reasoning_tokens', 0)))
            reasoning_cost = (reasoning_tokens / Decimal('1000000')) * pricing['reasoning']

        if 'searches' in pricing:
            search_queries = Decimal(str(usage.get('search_queries', 0)))
            search_cost = (search_queries / Decimal('1000')) * pricing['searches']

        total = input_cost + output_cost + request_cost + citation_cost + reasoning_cost + search_cost

        logger.debug(
            "Cost calculated",
            model=model,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            search_queries=usage.get('search_queries', 0),
            total_cost=float(total),
        )

        return total

    def _perplexity_request(self, method: str, url: str, **kwargs) -> dict:
        """Make authenticated request to Perplexity API.
        
        Handles:
        - Auth header injection
        - 401 → AuthenticationError
        - 402 → Payment required
        - 429 → Rate limit with retry
        - 5xx → Server error with retry
        """
        json_body = kwargs.pop('json', None)
        params = kwargs.pop('params', None)

        request_start = time.time()

        log_provider_request(
            logger,
            "perplexity",
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
                "perplexity",
                resp.status_code,
                response_time,
                headers=dict(resp.headers),
                body=response_body,
                error=resp.text if resp.status_code >= 400 else None,
            )

            if resp.status_code == 401:
                logger.error(
                    "Perplexity authentication failed (401)",
                    api_key_prefix=self.api_key[:8],
                    url=url,
                )
                raise AuthenticationError(
                    "Invalid Perplexity API key. Ensure key starts with 'pplx-'."
                )
            elif resp.status_code == 402:
                logger.error(
                    "Perplexity payment required (402)",
                    url=url,
                )
                raise ServiceError(
                    "Payment required. Add credits or payment method at "
                    "https://www.perplexity.ai/settings/api"
                )
            elif resp.status_code == 429:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"Perplexity rate limit hit (429), retrying in {wait}s",
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
                    f"Perplexity server error {resp.status_code}, retrying in {wait}s",
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
                    f"Perplexity API error {resp.status_code}",
                    status_code=resp.status_code,
                    error=error_detail,
                    url=url,
                )
                raise ServiceError(
                    f"Perplexity API error {resp.status_code}: {error_detail}"
                )

            return resp.json()

        logger.error(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Perplexity API",
            max_retries=self.MAX_RETRIES,
            url=url,
        )
        raise ServiceError(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Perplexity API."
        )
