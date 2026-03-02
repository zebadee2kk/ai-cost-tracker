"""
Diagnostic Logging System for AI Cost Tracker

Provides comprehensive, structured logging for all provider API interactions.
Designed to help diagnose sync failures, track performance, and monitor rate limits.

Usage:
    from utils.diagnostic_logger import get_diagnostic_logger, log_api_call

    logger = get_diagnostic_logger(__name__)
    
    with log_api_call(logger, "anthropic", "usage_report", account_id=123):
        response = call_anthropic_api()
        
Key Features:
- Structured JSON logging for easy parsing
- Request/response correlation IDs
- Performance timing
- Error context preservation
- Rate limit tracking
- Provider-specific metadata
"""

import json
import logging
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional
from uuid import uuid4

# Configure structured logging format
DIAGNOSTIC_LOG_FORMAT = (
    '%(asctime)s - %(name)s - %(levelname)s - '
    '[%(correlation_id)s] - %(message)s - %(context)s'
)


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', None),
            'context': getattr(record, 'context', {}),
        }
        
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info),
            }
        
        return json.dumps(log_data)


class DiagnosticLogger:
    """Enhanced logger with structured logging and context tracking."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"diagnostic.{name}")
        self.correlation_id = None
        
    def _log(self, level: int, msg: str, context: Optional[Dict] = None, exc_info=None):
        """Internal logging method with context injection."""
        extra = {
            'correlation_id': self.correlation_id or 'no-correlation-id',
            'context': context or {},
        }
        self.logger.log(level, msg, extra=extra, exc_info=exc_info)
    
    def debug(self, msg: str, **context):
        self._log(logging.DEBUG, msg, context)
    
    def info(self, msg: str, **context):
        self._log(logging.INFO, msg, context)
    
    def warning(self, msg: str, **context):
        self._log(logging.WARNING, msg, context)
    
    def error(self, msg: str, exc_info=None, **context):
        self._log(logging.ERROR, msg, context, exc_info=exc_info)
    
    def critical(self, msg: str, exc_info=None, **context):
        self._log(logging.CRITICAL, msg, context, exc_info=exc_info)


def get_diagnostic_logger(name: str) -> DiagnosticLogger:
    """Get a diagnostic logger instance.
    
    Args:
        name: Logger name (usually __name__ of the module)
        
    Returns:
        DiagnosticLogger instance with structured logging
    """
    logger = DiagnosticLogger(name)
    
    # Configure structured formatter if not already configured
    if not logger.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.DEBUG)
    
    return logger


@contextmanager
def log_api_call(
    logger: DiagnosticLogger,
    provider: str,
    endpoint: str,
    **metadata
):
    """Context manager for logging API calls with automatic timing and error handling.
    
    Usage:
        with log_api_call(logger, "anthropic", "usage_report", account_id=123):
            response = call_api()
            
    Args:
        logger: DiagnosticLogger instance
        provider: Provider name (anthropic, openai, google, etc.)
        endpoint: API endpoint or operation name
        **metadata: Additional context (account_id, model, etc.)
    """
    correlation_id = str(uuid4())
    logger.correlation_id = correlation_id
    start_time = time.time()
    
    context = {
        'provider': provider,
        'endpoint': endpoint,
        'correlation_id': correlation_id,
        **metadata
    }
    
    logger.info(
        f"API call started: {provider}.{endpoint}",
        **context
    )
    
    try:
        yield correlation_id
        elapsed = time.time() - start_time
        logger.info(
            f"API call succeeded: {provider}.{endpoint}",
            elapsed_seconds=elapsed,
            **context
        )
    except Exception as exc:
        elapsed = time.time() - start_time
        logger.error(
            f"API call failed: {provider}.{endpoint}",
            exc_info=True,
            error_type=type(exc).__name__,
            error_message=str(exc),
            elapsed_seconds=elapsed,
            **context
        )
        raise


def log_provider_request(
    logger: DiagnosticLogger,
    provider: str,
    method: str,
    url: str,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    json_body: Optional[Dict] = None,
):
    """Log outgoing API request details.
    
    Args:
        logger: DiagnosticLogger instance
        provider: Provider name
        method: HTTP method
        url: Request URL
        headers: Request headers (API keys will be redacted)
        params: Query parameters
        json_body: JSON request body
    """
    # Redact sensitive headers
    safe_headers = {}
    if headers:
        for key, value in headers.items():
            if key.lower() in ('authorization', 'x-api-key', 'api-key'):
                safe_headers[key] = f"{value[:15]}..." if len(value) > 15 else "***"
            else:
                safe_headers[key] = value
    
    logger.debug(
        f"HTTP Request: {method} {url}",
        provider=provider,
        method=method,
        url=url,
        headers=safe_headers,
        params=params,
        json_body=json_body,
    )


def log_provider_response(
    logger: DiagnosticLogger,
    provider: str,
    status_code: int,
    response_time_ms: float,
    headers: Optional[Dict] = None,
    body: Optional[Dict] = None,
    error: Optional[str] = None,
):
    """Log API response details.
    
    Args:
        logger: DiagnosticLogger instance
        provider: Provider name
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        headers: Response headers
        body: Response body (truncated if large)
        error: Error message if request failed
    """
    level = logging.INFO if 200 <= status_code < 300 else logging.ERROR
    
    # Extract rate limit headers if present
    rate_limits = {}
    if headers:
        rate_limit_keys = [
            'x-ratelimit-limit-requests',
            'x-ratelimit-limit-tokens',
            'x-ratelimit-remaining-requests',
            'x-ratelimit-remaining-tokens',
            'x-ratelimit-reset-requests',
            'x-ratelimit-reset-tokens',
            'retry-after',
        ]
        for key in rate_limit_keys:
            if key in headers:
                rate_limits[key] = headers[key]
    
    # Truncate body if too large
    truncated_body = body
    if body and isinstance(body, dict):
        body_str = json.dumps(body)
        if len(body_str) > 5000:
            truncated_body = f"{body_str[:5000]}... (truncated)"
    
    context = {
        'provider': provider,
        'status_code': status_code,
        'response_time_ms': response_time_ms,
        'rate_limits': rate_limits,
        'body': truncated_body,
    }
    
    if error:
        context['error'] = error
    
    logger._log(
        level,
        f"HTTP Response: {status_code} from {provider}",
        context
    )


def log_sync_attempt(
    logger: DiagnosticLogger,
    provider: str,
    account_id: int,
    sync_type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Log the start of a sync operation.
    
    Args:
        logger: DiagnosticLogger instance
        provider: Provider name
        account_id: Account ID being synced
        sync_type: Type of sync (usage, cost, rate_limits)
        start_date: Start date for sync range
        end_date: End date for sync range
    """
    logger.info(
        f"Starting sync: {provider} account {account_id}",
        provider=provider,
        account_id=account_id,
        sync_type=sync_type,
        start_date=start_date,
        end_date=end_date,
    )


def log_sync_result(
    logger: DiagnosticLogger,
    provider: str,
    account_id: int,
    success: bool,
    records_created: int = 0,
    error: Optional[str] = None,
    elapsed_seconds: Optional[float] = None,
):
    """Log the result of a sync operation.
    
    Args:
        logger: DiagnosticLogger instance
        provider: Provider name
        account_id: Account ID that was synced
        success: Whether sync succeeded
        records_created: Number of usage records created
        error: Error message if sync failed
        elapsed_seconds: Total sync duration
    """
    level = logging.INFO if success else logging.ERROR
    
    logger._log(
        level,
        f"Sync {'completed' if success else 'failed'}: {provider} account {account_id}",
        {
            'provider': provider,
            'account_id': account_id,
            'success': success,
            'records_created': records_created,
            'error': error,
            'elapsed_seconds': elapsed_seconds,
        }
    )


def log_rate_limit_status(
    logger: DiagnosticLogger,
    provider: str,
    limit_type: str,
    limit_value: Any,
    current_usage: Any,
    remaining: Any,
    reset_time: Optional[str] = None,
):
    """Log rate limit status for monitoring.
    
    Args:
        logger: DiagnosticLogger instance
        provider: Provider name
        limit_type: Type of limit (RPM, TPM, RPD, etc.)
        limit_value: Maximum limit value
        current_usage: Current usage
        remaining: Remaining quota
        reset_time: When the limit resets
    """
    usage_percent = (current_usage / limit_value * 100) if limit_value > 0 else 0
    level = logging.WARNING if usage_percent > 80 else logging.INFO
    
    logger._log(
        level,
        f"Rate limit status: {provider} {limit_type}",
        {
            'provider': provider,
            'limit_type': limit_type,
            'limit_value': limit_value,
            'current_usage': current_usage,
            'remaining': remaining,
            'usage_percent': round(usage_percent, 1),
            'reset_time': reset_time,
        }
    )


def log_data_validation(
    logger: DiagnosticLogger,
    provider: str,
    validation_type: str,
    passed: bool,
    details: Optional[Dict] = None,
):
    """Log data validation results.
    
    Args:
        logger: DiagnosticLogger instance
        provider: Provider name
        validation_type: What was validated
        passed: Whether validation passed
        details: Additional validation details
    """
    level = logging.INFO if passed else logging.WARNING
    
    logger._log(
        level,
        f"Validation {'passed' if passed else 'failed'}: {provider} {validation_type}",
        {
            'provider': provider,
            'validation_type': validation_type,
            'passed': passed,
            'details': details or {},
        }
    )


def diagnostic_wrapper(provider: str, operation: str):
    """Decorator for automatically logging function calls.
    
    Usage:
        @diagnostic_wrapper("anthropic", "fetch_usage")
        def fetch_anthropic_usage():
            ...
    
    Args:
        provider: Provider name
        operation: Operation name
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_diagnostic_logger(func.__module__)
            
            with log_api_call(logger, provider, operation):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Example usage and testing
if __name__ == "__main__":
    # Configure root logger
    logging.basicConfig(level=logging.DEBUG)
    
    # Test diagnostic logging
    logger = get_diagnostic_logger(__name__)
    
    # Simulate an API call
    with log_api_call(logger, "anthropic", "usage_report", account_id=123):
        log_provider_request(
            logger,
            "anthropic",
            "GET",
            "https://api.anthropic.com/v1/organizations/usage_report/messages",
            headers={"x-api-key": "sk-ant-admin-secret123"},
            params={"starting_at": "2026-03-01", "ending_at": "2026-03-02"},
        )
        
        time.sleep(0.1)  # Simulate API call
        
        log_provider_response(
            logger,
            "anthropic",
            200,
            120.5,
            headers={
                "x-ratelimit-limit-requests": "60",
                "x-ratelimit-remaining-requests": "45",
            },
            body={"data": [{"tokens": 1000}]},
        )
    
    # Test rate limit logging
    log_rate_limit_status(
        logger,
        "openai",
        "TPM",
        150000,
        120000,
        30000,
        reset_time="60s"
    )
    
    # Test error logging
    try:
        raise ValueError("Test error")
    except ValueError:
        logger.error("Caught test error", exc_info=True, test_context="example")
