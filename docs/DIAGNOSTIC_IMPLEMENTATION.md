# Diagnostic Logging Implementation Guide

**For AI Coding Assistants: Claude Code, GitHub Copilot, Codex**

---

## Quick Context

This guide helps AI coding assistants implement diagnostic logging across all provider services in the AI Cost Tracker.

### What's Been Implemented

✅ **Diagnostic Logger Utility** - `backend/utils/diagnostic_logger.py`  
✅ **Anthropic Service Updated** - Full diagnostic logging integrated  
✅ **Documentation** - Comprehensive troubleshooting guide  

### What Needs Implementation

⏳ **OpenAI Service** - Add diagnostic logging  
⏳ **Google Service** - Add diagnostic logging  
⏳ **Perplexity Service** - Create service + logging  
⏳ **Groq Service** - Create service + logging  
⏳ **Mistral Service** - Create service + logging  

---

## Implementation Pattern

All provider services follow this pattern:

### 1. Import Diagnostic Logger

```python
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
    log_sync_attempt,
    log_sync_result,
    log_rate_limit_status,
)

# Get logger at module level
logger = get_diagnostic_logger(__name__)
```

### 2. Log API Initialization

```python
def __init__(self, api_key: str):
    super().__init__(api_key)
    
    logger.debug(
        "Initializing {Provider} service",
        api_key_prefix=api_key[:15] if len(api_key) >= 15 else "***",
    )
    
    # Validate key format
    if not api_key.startswith('expected-prefix'):
        logger.error(
            "Invalid {Provider} API key format",
            key_prefix=api_key[:12],
            expected_prefix="expected-prefix",
        )
        raise AuthenticationError("...")
    
    logger.info(
        "{Provider} service initialized successfully",
        api_version="...",
    )
```

### 3. Wrap Public Methods with Sync Logging

```python
def get_usage(self, start_date, end_date, account_id=None):
    log_sync_attempt(
        logger,
        "provider_name",
        account_id or 0,
        "usage",
        start_date=start_date,
        end_date=end_date,
    )
    
    sync_start_time = time.time()
    
    try:
        # Fetch data
        with log_api_call(
            logger,
            "provider_name",
            "endpoint_name",
            account_id=account_id,
        ):
            data = self._fetch_data()
        
        # Process and return
        elapsed = time.time() - sync_start_time
        log_sync_result(
            logger,
            "provider_name",
            account_id or 0,
            success=True,
            records_created=len(data),
            elapsed_seconds=elapsed,
        )
        return data
        
    except Exception as exc:
        elapsed = time.time() - sync_start_time
        log_sync_result(
            logger,
            "provider_name",
            account_id or 0,
            success=False,
            error=str(exc),
            elapsed_seconds=elapsed,
        )
        logger.error(
            "Data fetch failed",
            exc_info=True,
            error_type=type(exc).__name__,
        )
        raise
```

### 4. Log All HTTP Requests

```python
def _make_request(self, method, url, **kwargs):
    request_start = time.time()
    
    # Log outgoing request
    log_provider_request(
        logger,
        "provider_name",
        method,
        url,
        headers=kwargs.get('headers'),
        params=kwargs.get('params'),
        json_body=kwargs.get('json'),
    )
    
    # Make request
    try:
        response = self.session.request(method, url, **kwargs)
    except Exception as exc:
        logger.error(
            f"Request to {url} failed (network error)",
            exc_info=True,
        )
        raise
    
    # Log response
    response_time = (time.time() - request_start) * 1000
    
    try:
        response_body = response.json() if response.text else None
    except:
        response_body = None
    
    log_provider_response(
        logger,
        "provider_name",
        response.status_code,
        response_time,
        headers=dict(response.headers),
        body=response_body,
        error=response.text if response.status_code >= 400 else None,
    )
    
    return response
```

### 5. Track Rate Limits (If Available)

```python
# Extract from headers (OpenAI, Groq)
if 'x-ratelimit-remaining-tokens' in headers:
    log_rate_limit_status(
        logger,
        "provider_name",
        "TPM",
        limit_value=int(headers['x-ratelimit-limit-tokens']),
        current_usage=(
            int(headers['x-ratelimit-limit-tokens']) - 
            int(headers['x-ratelimit-remaining-tokens'])
        ),
        remaining=int(headers['x-ratelimit-remaining-tokens']),
        reset_time=headers.get('x-ratelimit-reset-tokens'),
    )
```

---

## Provider-Specific Implementation

### OpenAI Service

**File:** `backend/services/openai_service.py`

**Key Changes Needed:**

1. Import diagnostic logger utilities
2. Add initialization logging
3. Wrap `get_usage()` with sync logging
4. Log all HTTP requests in `_openai_request()`
5. Extract and log rate limits from every response
6. Add pagination logging in `_fetch_all_pages()`

**Rate Limit Headers to Track:**
```python
rate_limit_keys = [
    'x-ratelimit-limit-requests',
    'x-ratelimit-limit-tokens', 
    'x-ratelimit-remaining-requests',
    'x-ratelimit-remaining-tokens',
    'x-ratelimit-reset-requests',
    'x-ratelimit-reset-tokens',
]
```

**Example:**
```python
# In _openai_request()
for key in rate_limit_keys:
    if key in response.headers:
        # Log each rate limit type separately
        if 'tokens' in key:
            log_rate_limit_status(
                logger,
                "openai",
                "TPM" if 'remaining' in key else "TPM_LIMIT",
                # ... extract values
            )
```

---

### Google Gemini Service

**File:** `backend/services/google_service.py` (create if not exists)

**Key Differences:**
- Uses Service Account credentials (JSON file)
- Token tracking via response metadata, not headers
- Logging via Cloud Logging API
- BigQuery for historical usage

**Implementation Notes:**

1. Log credential loading
2. Track per-request token counts
3. Log BigQuery query execution
4. No rate limit headers (use retry logic)

**Example:**
```python
import google.auth
from google.cloud import aiplatform

def __init__(self, credentials_path: str):
    logger.debug(
        "Initializing Google Gemini service",
        credentials_path=credentials_path,
    )
    
    try:
        credentials, project = google.auth.load_credentials_from_file(
            credentials_path
        )
        logger.info(
            "Google credentials loaded successfully",
            project_id=project,
        )
    except Exception as exc:
        logger.error(
            "Failed to load Google credentials",
            exc_info=True,
        )
        raise
```

---

### Perplexity Service

**File:** `backend/services/perplexity_service.py` (create new)

**Key Characteristics:**
- No usage API endpoint (manual logging only)
- Multiple APIs: Sonar, Agent, Search, Embeddings
- Tool costs (web_search, fetch_url)
- Credit-based billing

**Implementation Strategy:**

```python
import requests
from datetime import datetime
from utils.diagnostic_logger import get_diagnostic_logger, log_api_call

logger = get_diagnostic_logger(__name__)

class PerplexityService(BaseService):
    """Perplexity API integration with per-request tracking.
    
    NOTE: Perplexity has no usage API. All tracking must be done
    via logging every API response immediately.
    """
    
    BASE_URL = "https://api.perplexity.ai"
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        
        if not api_key.startswith('pplx-'):
            logger.error(
                "Invalid Perplexity API key format",
                key_prefix=api_key[:5],
            )
            raise AuthenticationError("Key must start with pplx-")
    
    def call_sonar_with_tracking(self, model, messages, account_id):
        """Make a Sonar API call and log usage immediately."""
        
        with log_api_call(
            logger,
            "perplexity",
            "sonar",
            account_id=account_id,
            model=model,
        ):
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": model, "messages": messages},
            )
            
            data = response.json()
            usage = data.get("usage", {})
            
            # Calculate cost
            cost = self._calculate_cost(model, usage)
            
            # Store immediately
            self._store_usage(
                account_id=account_id,
                model=model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                search_queries=usage.get("search_queries", 0),
                cost_usd=cost,
            )
            
            logger.info(
                "Perplexity usage tracked",
                model=model,
                tokens=usage.get("total_tokens", 0),
                cost=cost,
            )
            
            return data
```

---

### Groq Service

**File:** `backend/services/groq_service.py` (create new)

**Key Characteristics:**
- OpenAI-compatible API
- Rate limit headers (RPD, TPM)
- Timing metrics in response
- Ultra-fast inference

**Implementation:**

```python
class GroqService(BaseService):
    """Groq API integration with rate limit tracking."""
    
    BASE_URL = "https://api.groq.com/openai/v1"
    
    def _extract_rate_limits(self, headers):
        """Extract and log rate limits from response headers."""
        
        # TPM (Tokens Per Minute)
        if 'x-ratelimit-limit-tokens' in headers:
            log_rate_limit_status(
                logger,
                "groq",
                "TPM",
                limit_value=int(headers['x-ratelimit-limit-tokens']),
                current_usage=(
                    int(headers['x-ratelimit-limit-tokens']) -
                    int(headers['x-ratelimit-remaining-tokens'])
                ),
                remaining=int(headers['x-ratelimit-remaining-tokens']),
                reset_time=headers.get('x-ratelimit-reset-tokens'),
            )
        
        # RPD (Requests Per Day)
        if 'x-ratelimit-limit-requests' in headers:
            log_rate_limit_status(
                logger,
                "groq",
                "RPD",
                limit_value=int(headers['x-ratelimit-limit-requests']),
                current_usage=(
                    int(headers['x-ratelimit-limit-requests']) -
                    int(headers['x-ratelimit-remaining-requests'])
                ),
                remaining=int(headers['x-ratelimit-remaining-requests']),
                reset_time=headers.get('x-ratelimit-reset-requests'),
            )
```

---

## Testing Procedure

### 1. Unit Tests

```python
# tests/test_diagnostic_logging.py
import pytest
from utils.diagnostic_logger import get_diagnostic_logger, log_api_call

def test_logger_initialization():
    logger = get_diagnostic_logger(__name__)
    assert logger is not None
    assert logger.logger.name.startswith('diagnostic.')

def test_api_call_context_manager():
    logger = get_diagnostic_logger(__name__)
    
    with log_api_call(logger, "test_provider", "test_endpoint") as correlation_id:
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID format

def test_error_logging():
    logger = get_diagnostic_logger(__name__)
    
    try:
        with log_api_call(logger, "test", "endpoint"):
            raise ValueError("Test error")
    except ValueError:
        pass  # Error should be logged but not suppressed
```

### 2. Integration Tests

```python
# tests/integration/test_anthropic_logging.py
import os
from services.anthropic_service import AnthropicService

def test_anthropic_with_logging(caplog):
    """Test that Anthropic service logs all operations."""
    
    # Arrange
    api_key = os.environ.get('ANTHROPIC_ADMIN_API_KEY')
    service = AnthropicService(api_key)
    
    # Act
    with caplog.at_level(logging.DEBUG):
        service.validate_credentials()
    
    # Assert
    assert "Initializing Anthropic service" in caplog.text
    assert "API call started" in caplog.text
    assert "API call succeeded" in caplog.text
    assert "correlation_id" in caplog.text
```

### 3. Manual Testing

```bash
# Enable DEBUG logging
export LOG_LEVEL=DEBUG

# Start services
docker-compose up -d

# Trigger a sync
curl -X POST http://localhost:5000/api/sync/anthropic/123

# Watch logs in real-time
docker-compose logs -f backend | jq .

# Check for specific events
docker-compose logs backend | jq 'select(.message | contains("API call"))'
```

---

## Debugging Workflow

### Issue: Service Not Syncing

**Step 1: Check if sync was attempted**
```bash
docker-compose logs backend | jq 'select(.message | contains("Starting sync"))'
```

**Step 2: Look for errors**
```bash
docker-compose logs backend | jq 'select(.level == "ERROR")'
```

**Step 3: Check authentication**
```bash
docker-compose logs backend | jq 'select(.message | contains("Invalid") or contains("401"))'
```

**Step 4: Verify HTTP requests**
```bash
docker-compose logs backend | jq 'select(.message | contains("HTTP Request"))'
```

### Issue: Slow Performance

```bash
# Find slow operations (>5s)
docker-compose logs backend | jq 'select(.context.elapsed_seconds > 5)'

# Check response times
docker-compose logs backend | jq '.context.response_time_ms' | jq -s 'add/length'
```

---

## Code Review Checklist

When implementing diagnostic logging in a new service:

- [ ] Imported all necessary logging functions
- [ ] Created module-level logger instance
- [ ] Logged service initialization with key prefix
- [ ] Validated API key format with error logging
- [ ] Wrapped public methods with `log_sync_attempt/result`
- [ ] Used `log_api_call` context manager for API operations
- [ ] Logged all HTTP requests with `log_provider_request`
- [ ] Logged all HTTP responses with `log_provider_response`
- [ ] Extracted and logged rate limits (if available)
- [ ] Added timing metrics for slow operations
- [ ] Logged pagination progress
- [ ] Captured exception context with `exc_info=True`
- [ ] Added DEBUG logs for data aggregation
- [ ] Verified correlation IDs link related logs
- [ ] Tested with DEBUG log level enabled
- [ ] Confirmed logs are valid JSON
- [ ] Redacted sensitive information (API keys)
- [ ] Added provider-specific context fields

---

## AI Assistant Prompts

### For Claude Code

```
Implement diagnostic logging in backend/services/openai_service.py following the pattern from anthropic_service.py.

Key requirements:
- Import diagnostic logger utilities
- Log initialization with key validation  
- Wrap get_usage() with sync logging
- Log all HTTP requests/responses
- Extract rate limits from headers
- Add pagination logging
- Preserve existing functionality

Refer to:
- backend/utils/diagnostic_logger.py (utilities)
- backend/services/anthropic_service.py (reference)
- docs/DIAGNOSTIC_IMPLEMENTATION.md (patterns)
```

### For GitHub Copilot

```python
# TODO: Add diagnostic logging to this service
# Pattern: Import logger utilities, wrap methods with log_sync_attempt/result,
# log all HTTP requests, extract rate limits
# Reference: backend/services/anthropic_service.py

from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    # ... other imports
)

logger = get_diagnostic_logger(__name__)

class OpenAIService(BaseService):
    # Copilot will suggest the rest based on anthropic_service.py
```

---

## Next Steps

1. **Update OpenAI service** with diagnostic logging
2. **Create Google service** with logging from start
3. **Create Perplexity service** with per-request tracking
4. **Create Groq service** with rate limit tracking
5. **Create Mistral service** with logging
6. **Add integration tests** for all services
7. **Set up log aggregation** (Loki/ELK)
8. **Create monitoring dashboards** (Grafana)

---

## Questions?

Refer to:
- `docs/diagnostic-logging-guide.md` - Usage and troubleshooting
- `backend/utils/diagnostic_logger.py` - API reference
- `backend/services/anthropic_service.py` - Full implementation example
