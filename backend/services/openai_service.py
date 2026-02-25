"""
OpenAI service integration.

Uses the OpenAI billing/usage API endpoints documented at:
https://platform.openai.com/docs/api-reference/usage

Key endpoints:
  GET /v1/dashboard/billing/usage?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  GET /v1/dashboard/billing/credit_grants
  GET /v1/models  (used for credential validation)
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from services.base_service import BaseService, ServiceError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openai.com"


class OpenAIService(BaseService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._auth_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def validate_credentials(self) -> bool:
        """Validate the API key by listing models (lightweight call)."""
        try:
            self._request("GET", f"{BASE_URL}/v1/models", headers=self._auth_headers)
            return True
        except ServiceError as exc:
            logger.warning("OpenAI credential validation failed: %s", exc)
            return False

    def get_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
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

        try:
            data = self._request(
                "GET",
                f"{BASE_URL}/v1/dashboard/billing/usage",
                headers=self._auth_headers,
                params={"start_date": start_date, "end_date": end_date},
            )
        except ServiceError:
            raise

        return self._parse_usage_response(data)

    def get_subscription(self) -> dict:
        """Return subscription / credit grant information."""
        try:
            return self._request(
                "GET",
                f"{BASE_URL}/v1/dashboard/billing/credit_grants",
                headers=self._auth_headers,
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
