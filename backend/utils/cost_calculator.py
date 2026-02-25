"""
Cost calculation engine.

Pricing is per 1,000 tokens (input / output) in USD.
Values match the seed data in scripts/seed_services.py.
"""

from decimal import Decimal
from typing import Optional

# Pricing table: service_name -> model -> {input, output} per 1K tokens
PRICING: dict[str, dict[str, dict[str, float]]] = {
    "ChatGPT": {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    },
    "Claude": {
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    },
    "Groq": {
        "mixtral-8x7b-32768": {"input": 0.0, "output": 0.0},
        "llama2-70b-4096": {"input": 0.0, "output": 0.0},
        "gemma-7b-it": {"input": 0.0, "output": 0.0},
    },
    "Perplexity": {
        "sonar-small-chat": {"input": 0.0, "output": 0.0},
        "sonar-medium-chat": {"input": 0.0, "output": 0.0},
    },
}


def calculate_cost(
    service_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing_model: Optional[dict] = None,
) -> Decimal:
    """
    Calculate cost in USD for a single API call.

    Looks up the pricing model by service name and model name.
    Falls back to the provided pricing_model dict (from the Service DB record).
    Returns Decimal(0) if pricing is unknown.
    """
    # Try built-in table first
    service_pricing = PRICING.get(service_name, {})
    model_pricing = service_pricing.get(model)

    # Fall back to the pricing_model stored in the DB
    if model_pricing is None and pricing_model:
        model_pricing = pricing_model.get(model)

    if model_pricing is None:
        return Decimal("0")

    input_cost = Decimal(str(model_pricing.get("input", 0))) * Decimal(input_tokens) / Decimal(1000)
    output_cost = Decimal(str(model_pricing.get("output", 0))) * Decimal(output_tokens) / Decimal(1000)
    return (input_cost + output_cost).quantize(Decimal("0.0001"))


def calculate_total_cost_for_period(usage_records) -> Decimal:
    """Sum costs for a list of UsageRecord objects."""
    return sum(
        (Decimal(str(r.cost)) for r in usage_records if r.cost is not None),
        Decimal("0"),
    )


def project_monthly_cost(
    daily_cost_so_far: Decimal,
    days_elapsed: int,
    total_days_in_month: int,
) -> tuple[Decimal, Decimal]:
    """
    Linear extrapolation of cost to month-end.

    Returns (projected_total, confidence_score 0-100).
    """
    if days_elapsed <= 0:
        return Decimal("0"), Decimal("0")

    daily_average = daily_cost_so_far / Decimal(days_elapsed)
    projected = (daily_average * Decimal(total_days_in_month)).quantize(Decimal("0.0001"))

    # Confidence rises with more data; maxes at 100 on last day
    confidence = Decimal(min(days_elapsed / total_days_in_month * 100, 100)).quantize(
        Decimal("0.01")
    )
    return projected, confidence
