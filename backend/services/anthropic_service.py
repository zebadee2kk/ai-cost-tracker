"""
Anthropic Claude service integration with diagnostic logging.

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

import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from services.base_service import BaseService, ServiceError, AuthenticationError, RateLimitError
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
    log_sync_attempt,
    log_sync_result,
)

# Get diagnostic logger for this module
logger = get_diagnostic_logger(__name__)

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
    """Anthropic Claude API integration using the Admin API with diagnostic logging.

    Requires an Admin API key (sk-ant-admin...), not a standard API key.
    Standard keys (sk-ant-api...) only work with the inference API,
    not the usage/cost reporting endpoints.

    Admin keys can be generated in:
      Anthropic Console → Settings → Organization → Admin API Keys
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        # Validate API key format
        logger.debug(
            "Initializing Anthropic service",
            api_key_prefix=api_key[:15] if len(api_key) >= 15 else "***",
        )

        if not api_key.startswith('sk-ant-admin'):
            error_msg = (
                "Anthropic integration requires an Admin API key (sk-ant-admin...). "
                f"Received key starting with: {api_key[:12]}... "
                "Standard API keys (sk-ant-api-...) are not supported for usage reporting. "
                "Generate an Admin key in Console → Settings → Organization."
            )
            logger.error(
                "Invalid Anthropic API key format",
                key_prefix=api_key[:12],
                required_prefix="sk-ant-admin",
                actual_format="standard" if api_key.startswith('sk-ant-api') else "unknown",
            )
            raise AuthenticationError(error_msg)

        self._auth_headers = {
            'anthropic-version': ANTHROPIC_VERSION,
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
        }
        
        logger.info(
            "Anthropic service initialized successfully",
            api_version=ANTHROPIC_VERSION,
        )

    def validate_credentials(self) -> bool:
        """Test if the Admin API key is valid by fetching one day of usage."""
        logger.info("Validating Anthropic credentials")
        
        try:
            end = datetime.utcnow()
            start = end - timedelta(days=1)
            
            with log_api_call(logger, "anthropic", "validate_credentials"):
                self._anthropic_request(
                    'GET',
                    f"{BASE_URL}/usage_report/messages",
                    params={
                        'starting_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'ending_at': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'bucket_width': '1d',
                    }
                )
            
            logger.info("Anthropic credentials validated successfully")
            return True
            
        except (AuthenticationError, ServiceError) as exc:
            logger.error(
                "Anthropic credential validation failed",
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
        """Fetch usage data from the Anthropic Admin API with diagnostic logging.

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

        log_sync_attempt(
            logger,
            "anthropic",
            account_id or 0,
            "usage",
            start_date=start_date,
            end_date=end_date,
        )
        
        sync_start_time = time.time()

        try:
            start_dt = datetime.fromisoformat(start_date)
            # end_dt is end-of-day inclusive
            end_dt = datetime.fromisoformat(end_date).replace(
                hour=23, minute=59, second=59
            )

            # Fetch usage per model per day
            with log_api_call(
                logger,
                "anthropic",
                "usage_report/messages",
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
            ):
                all_data = self._fetch_all_pages(
                    f"{BASE_URL}/usage_report/messages",
                    params={
                        'starting_at': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'ending_at': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'bucket_width': '1d',
                        'group_by[]': 'model',
                    }
                )

            logger.info(
                f"Fetched {len(all_data)} usage data points from Anthropic",
                data_points=len(all_data),
                start_date=start_date,
                end_date=end_date,
            )

            daily = self._aggregate_daily_usage(all_data)
            total_tokens = sum(d['tokens'] for d in daily)
            total_cost = sum(Decimal(str(d['cost'])) for d in daily)

            result = {
                'total_tokens': total_tokens,
                'total_cost': float(total_cost),
                'daily': daily,
            }
            
            elapsed = time.time() - sync_start_time
            log_sync_result(
                logger,
                "anthropic",
                account_id or 0,
                success=True,
                records_created=len(daily),
                elapsed_seconds=elapsed,
            )
            
            logger.info(
                "Anthropic usage sync completed successfully",
                total_tokens=total_tokens,
                total_cost=float(total_cost),
                daily_records=len(daily),
                elapsed_seconds=elapsed,
            )

            return result
            
        except Exception as exc:
            elapsed = time.time() - sync_start_time
            log_sync_result(
                logger,
                "anthropic",
                account_id or 0,
                success=False,
                error=str(exc),
                elapsed_seconds=elapsed,
            )
            logger.error(
                "Anthropic usage sync failed",
                exc_info=True,
                error_type=type(exc).__name__,
                error_message=str(exc),
                start_date=start_date,
                end_date=end_date,
            )
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _aggregate_daily_usage(self, data: List[Dict]) -> List[Dict]:
        """Aggregate raw API response entries into per-day summaries."""
        logger.debug(f"Aggregating {len(data)} usage entries", entry_count=len(data))
        
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
                logger.warning(
                    "Skipping entry with no start_time",
                    entry=entry,
                )
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
            
            logger.debug(
                f"Aggregated usage for {day_str}",
                date=day_str,
                tokens=agg['input_tokens'] + agg['output_tokens'],
                cost=float(cost),
                models=list(agg['models']),
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

        logger.info(
            f"Created {len(result)} daily aggregations",
            days=len(result),
        )
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
            pricing_source = models[0] if models[0] in PRICING else '_default'
        else:
            pricing = PRICING['_default']
            pricing_source = '_default (mixed models)'

        input_cost = Decimal(str(input_tokens)) / Decimal('1000000') * Decimal(str(pricing['input']))
        output_cost = Decimal(str(output_tokens)) / Decimal('1000000') * Decimal(str(pricing['output']))
        # Cache creation is billed at 25% extra input rate; cache reads at 10% input rate
        cache_write_cost = Decimal(str(cache_creation_tokens)) / Decimal('1000000') * Decimal(str(pricing['input'])) * Decimal('0.25')
        cache_read_cost = Decimal(str(cache_read_tokens)) / Decimal('1000000') * Decimal(str(pricing['input'])) * Decimal('0.10')

        total = input_cost + output_cost + cache_write_cost + cache_read_cost
        
        logger.debug(
            "Cost estimated",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation=cache_creation_tokens,
            cache_read=cache_read_tokens,
            pricing_source=pricing_source,
            total_cost=float(total),
        )
        
        return total

    def _fetch_all_pages(self, url: str, params: dict) -> List[Dict]:
        """Fetch all paginated results from a usage endpoint."""
        all_data = []
        page = None
        page_count = 0

        logger.debug(
            f"Starting paginated fetch from {url}",
            url=url,
            initial_params=params,
        )

        while True:
            page_count += 1
            if page is not None:
                params = {**params, 'page': page}

            logger.debug(
                f"Fetching page {page_count}",
                page=page,
                url=url,
            )

            response = self._anthropic_request('GET', url, params=params)
            page_data = response.get('data', [])
            all_data.extend(page_data)
            
            logger.debug(
                f"Page {page_count} returned {len(page_data)} items",
                page=page_count,
                items=len(page_data),
                total_so_far=len(all_data),
            )

            if not response.get('has_more'):
                logger.debug(
                    f"No more pages (has_more=False)",
                    total_pages=page_count,
                    total_items=len(all_data),
                )
                break
                
            page = response.get('next_page')
            if page is None:
                logger.debug(
                    "No more pages (next_page=None)",
                    total_pages=page_count,
                    total_items=len(all_data),
                )
                break

        logger.info(
            f"Paginated fetch complete",
            total_pages=page_count,
            total_items=len(all_data),
            url=url,
        )
        
        return all_data

    def _anthropic_request(self, method: str, url: str, **kwargs) -> dict:
        """Make an authenticated request to the Anthropic Admin API with diagnostic logging.

        Handles:
        - Auth header injection
        - 401 → AuthenticationError
        - 429 → RateLimitError with retry
        - 5xx → ServiceError with retry
        """
        params = kwargs.pop('params', None)
        json_body = kwargs.pop('json', None)
        
        request_start = time.time()

        # Log outgoing request
        log_provider_request(
            logger,
            "anthropic",
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

            response_time = (time.time() - request_start) * 1000  # ms
            
            # Log response
            try:
                response_body = resp.json() if resp.text else None
            except:
                response_body = None
            
            log_provider_response(
                logger,
                "anthropic",
                resp.status_code,
                response_time,
                headers=dict(resp.headers),
                body=response_body,
                error=resp.text if resp.status_code >= 400 else None,
            )

            if resp.status_code == 401:
                logger.error(
                    "Anthropic authentication failed (401)",
                    api_key_prefix=self.api_key[:15],
                    url=url,
                )
                raise AuthenticationError(
                    "Invalid or expired Anthropic Admin API key. "
                    "Ensure you are using a sk-ant-admin... key."
                )
            elif resp.status_code == 429:
                wait = self.RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"Anthropic rate limit hit (429), retrying in {wait}s",
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
                    f"Anthropic server error {resp.status_code}, retrying in {wait}s",
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
                    error_detail = resp.json().get('error', {}).get('message', 'Unknown error')
                except Exception:
                    error_detail = resp.text or 'Unknown error'
                
                logger.error(
                    f"Anthropic API error {resp.status_code}",
                    status_code=resp.status_code,
                    error=error_detail,
                    url=url,
                )
                raise ServiceError(
                    f"Anthropic API error {resp.status_code}: {error_detail}"
                )

            return resp.json()

        logger.error(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Anthropic API",
            max_retries=self.MAX_RETRIES,
            url=url,
        )
        raise ServiceError(
            f"Max retries ({self.MAX_RETRIES}) exceeded for Anthropic API."
        )
