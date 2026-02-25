"""Unit tests for OpenAI service using mock responses."""

import pytest
from unittest.mock import patch, MagicMock
from services.openai_service import OpenAIService


MOCK_USAGE_RESPONSE = {
    "object": "list",
    "total_usage": 540,  # cents
    "data": [
        {
            "timestamp": 1704067200,
            "line_items": [
                {"name": "GPT-4", "cost": 525},
                {"name": "GPT-3.5 Turbo", "cost": 15},
            ],
        }
    ],
}

MOCK_MODELS_RESPONSE = {
    "object": "list",
    "data": [{"id": "gpt-4", "object": "model"}],
}


def test_validate_credentials_success():
    svc = OpenAIService("sk-test")
    with patch.object(svc, "_request", return_value=MOCK_MODELS_RESPONSE):
        assert svc.validate_credentials() is True


def test_validate_credentials_failure():
    from services.base_service import ServiceError
    svc = OpenAIService("sk-bad")
    with patch.object(svc, "_request", side_effect=ServiceError("401")):
        assert svc.validate_credentials() is False


def test_get_usage_parses_total_cost():
    svc = OpenAIService("sk-test")
    with patch.object(svc, "_request", return_value=MOCK_USAGE_RESPONSE):
        result = svc.get_usage()
    assert result["total_cost"] == pytest.approx(5.40, abs=0.001)


def test_get_usage_parses_daily_entries():
    svc = OpenAIService("sk-test")
    with patch.object(svc, "_request", return_value=MOCK_USAGE_RESPONSE):
        result = svc.get_usage()
    assert len(result["daily"]) == 1
    assert result["daily"][0]["date"] == "2024-01-01"


def test_get_usage_empty_response():
    svc = OpenAIService("sk-test")
    with patch.object(svc, "_request", return_value={"total_usage": 0, "data": []}):
        result = svc.get_usage()
    assert result["total_cost"] == 0.0
    assert result["daily"] == []
