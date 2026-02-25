"""Unit tests for AnthropicService using mock responses."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from services.anthropic_service import AnthropicService
from services.base_service import AuthenticationError, ServiceError


VALID_ADMIN_KEY = "sk-ant-admin-test-key-valid"
INVALID_STANDARD_KEY = "sk-ant-api-standard-key"

MOCK_USAGE_RESPONSE = {
    "data": [
        {
            "start_time": "2026-02-01T00:00:00Z",
            "end_time": "2026-02-02T00:00:00Z",
            "input_tokens": 100000,
            "output_tokens": 50000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "model": "claude-sonnet-4-5",
            "service_tier": "standard",
        },
        {
            "start_time": "2026-02-02T00:00:00Z",
            "end_time": "2026-02-03T00:00:00Z",
            "input_tokens": 200000,
            "output_tokens": 80000,
            "cache_creation_input_tokens": 10000,
            "cache_read_input_tokens": 5000,
            "model": "claude-haiku-4-5",
            "service_tier": "standard",
        },
    ],
    "has_more": False,
    "next_page": None,
}

MOCK_USAGE_MULTIPAGE_PAGE1 = {
    "data": [
        {
            "start_time": "2026-02-01T00:00:00Z",
            "end_time": "2026-02-02T00:00:00Z",
            "input_tokens": 100000,
            "output_tokens": 50000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "model": "claude-sonnet-4-5",
        }
    ],
    "has_more": True,
    "next_page": 2,
}

MOCK_USAGE_MULTIPAGE_PAGE2 = {
    "data": [
        {
            "start_time": "2026-02-02T00:00:00Z",
            "end_time": "2026-02-03T00:00:00Z",
            "input_tokens": 50000,
            "output_tokens": 20000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "model": "claude-sonnet-4-5",
        }
    ],
    "has_more": False,
    "next_page": None,
}


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------

def test_requires_admin_api_key():
    """Standard API keys should be rejected with AuthenticationError."""
    with pytest.raises(AuthenticationError, match="Admin API key"):
        AnthropicService(INVALID_STANDARD_KEY)


def test_accepts_admin_api_key():
    """Admin API keys should be accepted."""
    svc = AnthropicService(VALID_ADMIN_KEY)
    assert svc.api_key == VALID_ADMIN_KEY


def test_auth_headers_set():
    """Auth headers should include x-api-key and anthropic-version."""
    svc = AnthropicService(VALID_ADMIN_KEY)
    assert svc._auth_headers['x-api-key'] == VALID_ADMIN_KEY
    assert 'anthropic-version' in svc._auth_headers


# ---------------------------------------------------------------------------
# validate_credentials tests
# ---------------------------------------------------------------------------

def test_validate_credentials_success():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value={"data": [], "has_more": False}):
        assert svc.validate_credentials() is True


def test_validate_credentials_auth_failure():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', side_effect=AuthenticationError("bad key")):
        assert svc.validate_credentials() is False


def test_validate_credentials_service_error():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', side_effect=ServiceError("500")):
        assert svc.validate_credentials() is False


# ---------------------------------------------------------------------------
# get_usage tests
# ---------------------------------------------------------------------------

def test_get_usage_parses_total_tokens():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value=MOCK_USAGE_RESPONSE):
        result = svc.get_usage("2026-02-01", "2026-02-02")

    # Day 1: 100k + 50k = 150k tokens; Day 2: 200k + 80k = 280k tokens
    assert result['total_tokens'] == 430000


def test_get_usage_returns_daily_list():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value=MOCK_USAGE_RESPONSE):
        result = svc.get_usage("2026-02-01", "2026-02-02")

    assert len(result['daily']) == 2
    assert result['daily'][0]['date'] == '2026-02-01'
    assert result['daily'][1]['date'] == '2026-02-02'


def test_get_usage_metadata_fields():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value=MOCK_USAGE_RESPONSE):
        result = svc.get_usage("2026-02-01", "2026-02-02")

    day1 = result['daily'][0]
    assert day1['metadata']['input_tokens'] == 100000
    assert day1['metadata']['output_tokens'] == 50000
    assert 'claude-sonnet-4-5' in day1['metadata']['models']


def test_get_usage_calculates_cost():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value=MOCK_USAGE_RESPONSE):
        result = svc.get_usage("2026-02-01", "2026-02-02")

    # Day 1: 100k input @ $3/1M = $0.30, 50k output @ $15/1M = $0.75 => $1.05
    day1_cost = result['daily'][0]['cost']
    assert abs(day1_cost - 1.05) < 0.01


def test_get_usage_empty_response():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value={"data": [], "has_more": False}):
        result = svc.get_usage("2026-02-01", "2026-02-02")

    assert result['total_tokens'] == 0
    assert result['total_cost'] == 0.0
    assert result['daily'] == []


def test_get_usage_default_date_range():
    """get_usage with no args should not raise."""
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value={"data": [], "has_more": False}):
        result = svc.get_usage()
    assert 'daily' in result


def test_get_usage_cache_tokens_in_metadata():
    svc = AnthropicService(VALID_ADMIN_KEY)
    with patch.object(svc, '_anthropic_request', return_value=MOCK_USAGE_RESPONSE):
        result = svc.get_usage("2026-02-01", "2026-02-02")

    day2 = result['daily'][1]
    assert day2['metadata']['cache_creation_tokens'] == 10000
    assert day2['metadata']['cache_read_tokens'] == 5000


# ---------------------------------------------------------------------------
# Pagination tests
# ---------------------------------------------------------------------------

def test_get_usage_handles_pagination():
    """Should fetch all pages and aggregate results."""
    svc = AnthropicService(VALID_ADMIN_KEY)
    call_count = {'n': 0}

    def side_effect(method, url, **kwargs):
        call_count['n'] += 1
        if call_count['n'] == 1:
            return MOCK_USAGE_MULTIPAGE_PAGE1
        return MOCK_USAGE_MULTIPAGE_PAGE2

    with patch.object(svc, '_anthropic_request', side_effect=side_effect):
        result = svc.get_usage("2026-02-01", "2026-02-02")

    assert call_count['n'] == 2
    # Day 1: 150k tokens, Day 2: 70k tokens
    assert result['total_tokens'] == 220000


# ---------------------------------------------------------------------------
# _anthropic_request error handling tests
# ---------------------------------------------------------------------------

def test_anthropic_request_raises_auth_error_on_401():
    svc = AnthropicService(VALID_ADMIN_KEY)
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch.object(svc.session, 'request', return_value=mock_resp):
        with pytest.raises(AuthenticationError):
            svc._anthropic_request('GET', 'https://example.com/test')


def test_anthropic_request_raises_service_error_on_400():
    svc = AnthropicService(VALID_ADMIN_KEY)
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {'error': {'message': 'Bad request'}}

    with patch.object(svc.session, 'request', return_value=mock_resp):
        with pytest.raises(ServiceError, match="Bad request"):
            svc._anthropic_request('GET', 'https://example.com/test')


def test_anthropic_request_retries_on_429():
    """Should retry on rate limit and eventually raise RateLimitError."""
    svc = AnthropicService(VALID_ADMIN_KEY)
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"data": [], "has_more": False}

    responses = [mock_resp_429, mock_resp_200]

    with patch.object(svc.session, 'request', side_effect=responses):
        with patch('time.sleep'):  # Don't actually sleep in tests
            result = svc._anthropic_request('GET', 'https://example.com/test')

    assert result == {"data": [], "has_more": False}


def test_anthropic_request_raises_after_max_retries_on_500():
    svc = AnthropicService(VALID_ADMIN_KEY)
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch.object(svc.session, 'request', return_value=mock_resp):
        with patch('time.sleep'):
            with pytest.raises(ServiceError, match="Max retries"):
                svc._anthropic_request('GET', 'https://example.com/test')


# ---------------------------------------------------------------------------
# Cost estimation tests
# ---------------------------------------------------------------------------

def test_estimate_cost_known_model():
    svc = AnthropicService(VALID_ADMIN_KEY)
    cost = svc._estimate_cost(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        models=['claude-sonnet-4-5'],
    )
    # $3.00 input + $15.00 output = $18.00
    assert abs(float(cost) - 18.00) < 0.001


def test_estimate_cost_unknown_model_uses_default():
    svc = AnthropicService(VALID_ADMIN_KEY)
    cost = svc._estimate_cost(
        input_tokens=1_000_000,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        models=['claude-unknown-model'],
    )
    # Default input pricing: $3.00/1M
    assert abs(float(cost) - 3.00) < 0.001


def test_estimate_cost_includes_cache_tokens():
    svc = AnthropicService(VALID_ADMIN_KEY)
    cost = svc._estimate_cost(
        input_tokens=0,
        output_tokens=0,
        cache_creation_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        models=['claude-sonnet-4-5'],
    )
    # Cache write: $3.00 * 0.25 = $0.75; cache read: $3.00 * 0.10 = $0.30
    assert abs(float(cost) - 1.05) < 0.001
