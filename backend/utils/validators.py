"""Input validation helpers."""

import re
from typing import Any


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    return True, ""


def require_fields(data: dict, fields: list[str]) -> list[str]:
    """Return a list of missing required fields."""
    return [f for f in fields if not data.get(f)]


def sanitize_string(value: Any, max_length: int = 255) -> str:
    """Strip whitespace and truncate to max_length."""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()[:max_length]
