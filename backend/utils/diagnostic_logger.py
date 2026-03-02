"""
Diagnostic logging utilities for AI Cost Tracker.

Provides structured logging helpers for debugging provider integrations,
API calls, sync operations, and error conditions.

Usage:
    from utils.diagnostic_logger import get_diagnostic_logger, log_api_call
    
    logger = get_diagnostic_logger(__name__)
    
    with log_api_call(logger, "openai", "usage_fetch"):
        # Your API call here
        pass
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

# Configure root logger for structured output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def get_diagnostic_logger(name: str) -> logging.Logger:
    """Get a logger instance with diagnostic capabilities.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)
    
    # Add custom methods for structured logging
    if not hasattr(logger, '_diagnostic_enhanced'):
        _enhance_logger(logger)
        logger._diagnostic_enhanced = True
    
    return logger


def _enhance_logger(logger: logging.Logger):
    """Add custom logging methods to a logger instance."""
    
    def debug(msg: str, **kwargs):
        """Log debug message with optional structured data."""
        if logger.isEnabledFor(logging.DEBUG):
            extra_data = _format_extra_data(kwargs)
            logger._log(logging.DEBUG, f"{msg}{extra_data}", args=())
    
    def info(msg: str, **kwargs):
        """Log info message with optional structured data."""
        if logger.isEnabledFor(logging.INFO):
            extra_data = _format_extra_data(kwargs)
            logger._log(logging.INFO, f"{msg}{extra_data}", args=())
    
    def warning(msg: str, **kwargs):
        """Log warning message with optional structured data."""
        if logger.isEnabledFor(logging.WARNING):
            extra_data = _format_extra_data(kwargs)
            logger._log(logging.WARNING, f"{msg}{extra_data}", args=())
    
    def error(msg: str, exc_info: bool = False, **kwargs):
        """Log error message with optional structured data."""
        if logger.isEnabledFor(logging.ERROR):
            extra_data = _format_extra_data(kwargs)
            logger._log(logging.ERROR, f"{msg}{extra_data}", args=(), exc_info=exc_info)
    
    # Replace standard methods
    logger.debug = debug
    logger.info = info
    logger.warning = warning
    logger.error = error


def _format_extra_data(data: Dict[str, Any]) -> str:
    """Format extra data as JSON string for log output."""
    if not data:
        return ""
    
    # Filter out None values and convert to JSON
    filtered = {k: v for k, v in data.items() if v is not None}
    if not filtered:
        return ""
    
    try:
        json_str = json.dumps(filtered, default=str, separators=(',', ':'))
        return f" | {json_str}"
    except Exception:
        return f" | {filtered}"


@contextmanager
def log_api_call(
    logger: logging.Logger,
    provider: str,
    operation: str,
    **context
):
    """Context manager for logging API calls with timing.
    
    Usage:
        with log_api_call(logger, "openai", "fetch_usage", account_id=123):
            response = api.get_usage()
    
    Args:
        logger: Logger instance
        provider: Provider name (anthropic, openai, google, etc.)
        operation: Operation being performed
        **context: Additional context to log
    """
    start_time = time.time()
    
    logger.info(
        f"API call started: {provider}.{operation}",
        provider=provider,
        operation=operation,
        **context
    )
    
    try:
        yield
        elapsed = time.time() - start_time
        logger.info(
            f"API call succeeded: {provider}.{operation}",
            provider=provider,
            operation=operation,
            elapsed_seconds=round(elapsed, 3),
            success=True,
            **context
        )
    except Exception as exc:
        elapsed = time.time() - start_time
        logger.error(
            f"API call failed: {provider}.{operation}",
            exc_info=True,
            provider=provider,
            operation=operation,
            elapsed_seconds=round(elapsed, 3),
            success=False,
            error_type=type(exc).__name__,
            error_message=str(exc),
            **context
        )
        raise


def log_provider_request(
    logger: logging.Logger,
    provider: str,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
):
    """Log outgoing provider API request details.
    
    Args:
        logger: Logger instance
        provider: Provider name
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers: Request headers (sensitive keys will be masked)
        params: Query parameters
        json_body: Request body
    """
    # Mask sensitive headers
    safe_headers = _mask_sensitive_headers(headers or {})
    
    logger.debug(
        f"Provider request: {method} {url}",
        provider=provider,
        method=method,
        url=url,
        headers=safe_headers,
        params=params,
        body_size=len(json.dumps(json_body)) if json_body else 0,
    )


def log_provider_response(
    logger: logging.Logger,
    provider: str,
    status_code: int,
    response_time_ms: float,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
    error: Optional[str] = None,
):
    """Log provider API response details.
    
    Args:
        logger: Logger instance
        provider: Provider name
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        headers: Response headers
        body: Response body (will be truncated if large)
        error: Error message if request failed
    """
    log_level = logging.DEBUG if status_code < 400 else logging.ERROR
    
    # Extract useful headers
    useful_headers = {}
    if headers:
        for key in ['x-ratelimit-limit-requests', 'x-ratelimit-remaining-requests',
                    'x-ratelimit-limit-tokens', 'x-ratelimit-remaining-tokens',
                    'retry-after', 'content-type']:
            if key in headers:
                useful_headers[key] = headers[key]
    
    log_data = {
        "provider": provider,
        "status_code": status_code,
        "response_time_ms": round(response_time_ms, 2),
        "headers": useful_headers,
    }
    
    if error:
        log_data["error"] = error[:500]  # Truncate long errors
    
    if body and isinstance(body, dict):
        # Log relevant response fields without full body
        if 'usage' in body:
            log_data["usage"] = body['usage']
        if 'data' in body and isinstance(body['data'], list):
            log_data["data_count"] = len(body['data'])
    
    if log_level == logging.ERROR:
        logger.error(
            f"Provider response: {status_code}",
            **log_data
        )
    else:
        logger.debug(
            f"Provider response: {status_code}",
            **log_data
        )


def log_sync_attempt(
    logger: logging.Logger,
    provider: str,
    account_id: int,
    sync_type: str,
    **context
):
    """Log the start of a sync operation.
    
    Args:
        logger: Logger instance
        provider: Provider name
        account_id: Account ID being synced
        sync_type: Type of sync (usage, cost, rate_limits)
        **context: Additional context (dates, filters, etc.)
    """
    logger.info(
        f"Sync attempt started: {provider}/{sync_type}",
        provider=provider,
        account_id=account_id,
        sync_type=sync_type,
        timestamp=datetime.utcnow().isoformat(),
        **context
    )


def log_sync_result(
    logger: logging.Logger,
    provider: str,
    account_id: int,
    success: bool,
    records_created: int = 0,
    records_updated: int = 0,
    elapsed_seconds: float = 0,
    error: Optional[str] = None,
    **context
):
    """Log the result of a sync operation.
    
    Args:
        logger: Logger instance
        provider: Provider name
        account_id: Account ID synced
        success: Whether sync succeeded
        records_created: Number of records created
        records_updated: Number of records updated
        elapsed_seconds: Time taken
        error: Error message if failed
        **context: Additional context
    """
    log_level = logging.INFO if success else logging.ERROR
    
    log_data = {
        "provider": provider,
        "account_id": account_id,
        "success": success,
        "records_created": records_created,
        "records_updated": records_updated,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "timestamp": datetime.utcnow().isoformat(),
        **context
    }
    
    if error:
        log_data["error"] = error
    
    msg = f"Sync {'succeeded' if success else 'failed'}: {provider}"
    
    if log_level == logging.ERROR:
        logger.error(msg, **log_data)
    else:
        logger.info(msg, **log_data)


def _mask_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Mask sensitive header values for logging.
    
    Args:
        headers: Original headers dict
        
    Returns:
        Headers dict with sensitive values masked
    """
    sensitive_keys = {
        'authorization', 'x-api-key', 'api-key', 
        'anthropic-api-key', 'openai-api-key',
        'google-api-key', 'bearer'
    }
    
    masked = {}
    for key, value in headers.items():
        if key.lower() in sensitive_keys:
            # Show first/last 4 chars
            if len(value) > 8:
                masked[key] = f"{value[:4]}...{value[-4:]}"
            else:
                masked[key] = "***"
        else:
            masked[key] = value
    
    return masked


def set_log_level(level: str):
    """Set global log level for diagnostic logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger().setLevel(numeric_level)
    
    # Also set for all provider loggers
    for name in ['anthropic_service', 'openai_service', 'google_service']:
        logging.getLogger(f'services.{name}').setLevel(numeric_level)
