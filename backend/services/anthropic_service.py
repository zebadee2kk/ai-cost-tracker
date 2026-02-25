"""
Anthropic Claude service integration.

Uses the Anthropic Admin API (usage and cost reports) documented at:
https://platform.claude.com/docs/en/build-with-claude/usage-cost-api

Key requirements:
- Admin API key required: sk-ant-admin...  (NOT a standard API key)
- Only available for organization accounts
- Admin keys are generated in: Console → Settings → Organization

Endpoints used:
  GET /v1/organizations/usage_report/messages  - Token usage breakdown
  GET /v1/organizations/cost_report            - USD cost breakdown
"""

import logging
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from services.base_service import BaseService, ServiceError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.anthropic.com/v1/organizations"
ANTHROPIC_VERSION = "2023-06-01"

# Pricing per 1M tokens (February 2026)
PRICING = {
    'claude-opus-4-6': {'input': 15.00, 'output': 75.00},
    'claude-opus-4-5': {'input': 5.00, 'output': 25.00},
    'claude-sonnet-4-5': {'input': 3.00, 'output': 15.00},
    'claude-haiku-4-5': {'input': 1.00, 'output': 5.00},
    # Fallback average pricing for unknown/mixed models
    '_default': {'input': 3.00, 'output': 15.00},
}


class AnthropicService(BaseService):
    """Anthropic Claude API integration using the Admin API.

    Requires an Admin API key (sk-ant-admin...), not a standard API key.
    Standard keys (sk-ant-api...) only work with the inference API,
    not the usage/cost reporting endpoints.

    Admin keys can be generated in:
      Anthropic Console → Settings → Organization → Admin API Keys
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        if not api_key.startswith('sk-ant-admin'):
            raise AuthenticationError(
                "Anthropic integration requires an Admin API key (sk-ant-admin...). "
                "Standard API keys are not supported for usage reporting. "
                "Generate an Admin key in Console → Settings → Organization."
            )

        self._auth_headers = {
            'anthropic-version': ANTHROPIC_VERSION,
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
        }

    def validate_credentials(self) -> bool:
        """Test if the Admin API key is valid by fetching one day of usage."""
        try:
            end = datetime.utcnow()
            start = end - timedelta(days=1)
            self._anthropic_request(
                'GET',
                f"{BASE_URL}/usage_report/messages",
                params={
                    'starting_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'ending_at': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'bucket_width': '1d',
                }
            )
            return True
        except (AuthenticationError, ServiceError) as exc:
            logger.warning("Anthropic credential validation failed: %s", exc)
            return False

    def get_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """Fetch usage data from the Anthropic Admin API.

        Dates should be in YYYY-MM-DD format.
        Defaults to the current calendar month.

        Returns a normalized dict:
            {
                "total_tokens": int,
                "total_cost": float,
                "daily": [
                    {
                        "date": "YYYY-MM-DD",
                        "tokens": int,
                        "cost": float,
                        "metadata": {
                            "input_tokens": int,
                            "output_tokens": int,
                            "cache_creation_tokens": int,
                            "cache_read_tokens": int,
                            "models": List[str],
                        }
                    }
                ]
            }
        """
        today = date.today()
        if not start_date:
            start_date = today.replace(day=1).isoformat()
        if not end_date:
            end_date = today.isoformat()

        start_dt = datetime.fromisoformat(start_date)
        # end_dt is end-of-day inclusive
        end_dt = datetime.fromisoformat(end_date).replace(
            hour=23, minute=59, second=59
        )

        # Fetch usage per model per day
        all_data = self._fetch_all_pages(
            f"{BASE_URL}/usage_report/messages",
            params={
                'starting_at': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'ending_at': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bucket_width': '1d',
                'group_by[]': 'model',
            }
        )

        daily = self._aggregate_daily_usage(all_data)
        total_tokens = sum(d['tokens'] for d in daily)
        total_cost = sum(Decimal(str(d['cost'])) for d in daily)

        return {
            'total_tokens': total_tokens,
            'total_cost': float(total_cost),
            'daily': daily,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _aggregate_daily_usage(self, data: List[Dict]) -> List[Dict]:
        """Aggregate raw API response entries into per-day summaries."""
        daily: Dict[str, Dict] = defaultdict(lambda: {
            'input_tokens': 0,
            'output_tokens': 0,
            'cache_creation_tokens': 0,
            'cache_read_tokens': 0,
            'models': set(),
        })

        for entry in data:
            day_key = entry.get('start_time', '')[:10]  # Extract YYYY-MM-DD
            if not day_key:
                continue

            daily[day_key]['input_tokens'] += entry.get('input_tokens', 0)
            daily[day_key]['output_tokens'] += entry.get('output_tokens', 0)
            daily[day_key]['cache_creation_tokens'] += entry.get(
                'cache_creation_input_tokens', 0
            )
            daily[day_key]['cache_read_tokens'] += entry.get(
                'cache_read_input_tokens', 0
            )
            model = entry.get('model')
            if model:
                daily[day_key]['models'].add(model)

        result = []
        for day_str, agg in sorted(daily.items()):
            cost = self._estimate_cost(
                agg['input_tokens'],
                agg['output_tokens'],
                agg['cache_creation_tokens'],
                agg['cache_read_tokens'],
                list(agg['models']),
            )
            result.append({
                'date': day_str,
                'tokens': agg['input_tokens'] + agg['output_tokens'],
                'cost': float(round(cost, 6)),
                'metadata': {
                    'input_tokens': agg['input_tokens'],
                    'output_tokens': agg['output_tokens'],
                    'cache_creation_tokens': agg['cache_creation_tokens'],
                    'cache_read_tokens': agg['cache_read_tokens'],
                    'models': list(agg['models']),
                },
            })

        return result

    def _estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int,
        models: List[str],
    ) -> Decimal:
        """Estimate USD cost from token counts.

        Uses model-specific pricing where available, falling back to the
        default (Sonnet-tier) pricing for mixed or unknown model usage.
        """
        if len(models) == 1:
            pricing = PRICING.get(models[0], PRICING['_default'])
        else:
            pricing = PRICING['_default']

        input_cost = Decimal(str(input_tokens)) / Decimal('1000000') * Decimal(str(pricing['input']))
        output_cost = Decimal(str(output_tokens)) / Decimal('1000000') * Decimal(str(pricing['output']))
        # Cache creation is billed at 25% extra input rate; cache reads at 10% input rate
        cache_write_cost = Decimal(str(cache_creation_tokens)) / Decimal('1000000') * Decimal(str(pricing['input'])) * Decimal('0.25')
        cache_read_cost = Decimal(str(cache_read_tokens)) / Decimal('1000000') * Decimal(str(pricing['input'])) * Decimal('0.10')

        return input_cost + output_cost + cache_write_cost + cache_read_cost

    def _fetch_all_pages(self, url: str, params: dict) -> List[Dict]:
        """Fetch all paginated results from a usage endpoint."""
        all_data = []
        page = None

        while True:
            if page is not None:
                params = {**params, 'page': page}

            response = self._anthropic_request('GET', url, params=params)
            all_data.extend(response.get('data', []))

            if not response.get('has_more'):
                break
            page = response.get('next_page')
            if page is None:
                break

        return all_data

    def _anthropic_request(self, method: str, url: str, **kwargs) -> dict:
        """Make an authenticated request to the Anthropic Admin API.

        Handles:
        - Auth header injection
        - 401 → AuthenticationError
        - 429 → RateLimitError with retry
        - 5xx → ServiceError with retry
        """
        params = kwargs.pop('params', None)
        json_body = kwargs.pop('json', None)

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
                raise ServiceError(f"Request to {url} failed: {exc}") from exc

            if resp.status_code == 401:
                raise AuthenticationError(
                    "Invalid or expired Anthropic Admin API key. "
                    "Ensure you are using a sk-ant-admin... key."
                )
            elif resp.status_code == 429:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "Anthropic rate limit hit, retrying in %ds (attempt %d/%d)",
                    wait, attempt, self.MAX_RETRIES
                )
                time.sleep(wait)
                continue
            elif resp.status_code >= 500:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "Anthropic server error %d, retrying in %ds (attempt %d/%d)",
                    resp.status_code, wait, attempt, self.MAX_RETRIES
                )
                time.sleep(wait)
                continue
            elif resp.status_code >= 400:
                try:
                    error_detail = resp.json().get('error', {}).get('message', 'Unknown error')
                except Exception:
                    error_detail = resp.text or 'Unknown error'
                raise ServiceError(
                    f"Anthropic API error {resp.status_code}: {error_detail}"
                )

            return resp.json()

        raise ServiceError(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Anthropic API."
        )
