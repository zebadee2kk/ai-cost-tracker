"""Base class for all AI service integrations."""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised for API-level errors from an AI service."""


class BaseService(ABC):
    """
    All service integrations inherit from this class.

    Provides:
    - HTTP helpers with exponential backoff retry
    - Abstract interface: validate_credentials(), get_usage()
    """

    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2  # seconds

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Return True if the API key is valid, False otherwise."""

    @abstractmethod
    def get_usage(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        """
        Fetch usage data for the given date range.

        Returns a dict with at minimum:
            {
                "total_tokens": int,
                "total_cost": float,
                "daily": [{"date": "YYYY-MM-DD", "tokens": int, "cost": float}, ...]
            }
        """

    def _request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> dict:
        """HTTP request with exponential backoff on 429/5xx."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = self.session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=15,
                )
                if resp.status_code == 429:
                    wait = self.RETRY_BACKOFF_BASE ** attempt
                    logger.warning("Rate limited by %s, retrying in %ss", url, wait)
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    wait = self.RETRY_BACKOFF_BASE ** attempt
                    logger.warning("Server error from %s (%s), retrying in %ss", url, resp.status_code, wait)
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.Timeout:
                logger.warning("Timeout on attempt %d for %s", attempt, url)
                if attempt == self.MAX_RETRIES:
                    raise ServiceError(f"Request to {url} timed out after {self.MAX_RETRIES} attempts.")
            except requests.exceptions.RequestException as exc:
                raise ServiceError(f"Request failed: {exc}") from exc

        raise ServiceError(f"Max retries ({self.MAX_RETRIES}) exceeded for {url}.")
