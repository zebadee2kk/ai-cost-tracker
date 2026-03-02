# Provider Services Implementation Handover

**Date:** March 2, 2026  
**Status:** Groq ✅ Complete | Perplexity ✅ Complete  
**Next:** Integration testing & production deployment

---

## Executive Summary

This document provides complete context for AI coding assistants (Claude Code, GitHub Copilot, VS Code Copilot) to continue development.

**Completed Services:**
1. ✅ **Anthropic** - Admin API with cache tracking
2. ✅ **OpenAI** - Rate limit headers, cost API
3. ✅ **Groq** - Ultra-fast inference, timing metrics
4. ✅ **Perplexity** - Per-request tracking, local cost calculation

**Remaining:**
- Google Gemini (most complex - GCP setup required)
- Mistral (OpenAI-compatible, straightforward)

---

## Implementation Contract

All provider services follow this consistent interface:

### 1. Class Structure

```python
from services.base_service import BaseService, ServiceError, AuthenticationError
from utils.diagnostic_logger import get_diagnostic_logger

logger = get_diagnostic_logger(__name__)

class ProviderService(BaseService):
    """Provider API integration."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        # Validate key format
        # Set up auth headers
    
    def validate_credentials(self) -> bool:
        """Test if API key is valid."""
        # Make minimal API call (max_tokens=1)
        # Return True if 200, False if 401/403
    
    def get_usage(self, start_date, end_date, account_id=None) -> dict:
        """Fetch historical usage data."""
        # If usage API exists: query it
        # If not: return error message explaining per-request tracking
    
    def call_with_tracking(self, model, messages, **kwargs) -> Dict[str, Any]:
        """Make API call and return usage + cost (for providers without usage API)."""
        # Make API call
        # Extract usage from response
        # Calculate cost if not provided
        # Return structured dict
```

### 2. Response Format (call_with_tracking)

**Standard return structure:**

```python
{
    'response': {  # Full API response
        'id': 'chat-abc123',
        'model': 'model-name',
        'choices': [...],
        'usage': {...}
    },
    'usage': {  # Extracted/normalized usage
        'prompt_tokens': 150,
        'completion_tokens': 75,
        'total_tokens': 225,
        # Provider-specific fields:
        'queue_time': 0.002,  # Groq
        'search_queries': 18,  # Perplexity
        'cache_read_tokens': 3000,  # Anthropic, Google
    },
    'cost': 0.0123,  # Calculated USD cost (if applicable)
    'rate_limits': {  # If available from headers
        'limit_tpm': 150000,
        'remaining_tpm': 149775,
    }
}
```

### 3. Key Format Validation

**Enforce in `__init__`:**

| Provider | Prefix | Example |
|----------|--------|----------|
| OpenAI | `sk-` | `sk-abc123...` |
| Anthropic | `sk-ant-admin-` | `sk-ant-admin-abc123...` |
| Groq | `gsk_` | `gsk_abc123...` |
| Perplexity | `pplx-` | `pplx-abc123...` |
| Google | N/A (JSON) | Service account file |
| Mistral | `...` | TBD (check docs) |

**Validation pattern:**

```python
if not api_key.startswith('expected-prefix'):
    logger.error(
        "Invalid API key format",
        key_prefix=api_key[:8],
        required_prefix="expected-prefix",
    )
    raise AuthenticationError(f"Key must start with 'expected-prefix'")
```

### 4. Diagnostic Logging

**Use these helpers from `utils.diagnostic_logger`:**

```python
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
)

logger = get_diagnostic_logger(__name__)

# Wrap API operations
with log_api_call(logger, "provider_name", "operation", **metadata):
    result = make_api_call()

# Log requests
log_provider_request(logger, "provider", method, url, headers, params, json_body)

# Log responses
log_provider_response(logger, "provider", status_code, response_time_ms, headers, body, error)
```

---

## Provider-Specific Details

### Groq (✅ Implemented)

**Key Features:**
- Ultra-fast inference (< 100ms typical)
- Detailed timing breakdowns
- Rate limit headers on every response
- No usage API (per-request tracking only)

**Usage Tracking:**

```python
result = groq_service.call_with_tracking(
    model='llama-3.3-70b-versatile',
    messages=[{'role': 'user', 'content': 'Hello'}]
)

# Store in database immediately:
db.usage_records.insert({
    'timestamp': datetime.now(),
    'service_id': groq_service_id,
    'model_name': result['response']['model'],
    'input_tokens': result['usage']['prompt_tokens'],
    'output_tokens': result['usage']['completion_tokens'],
    'queue_time_ms': result['usage']['queue_time'] * 1000,
    'total_time_ms': result['usage']['total_time'] * 1000,
    'rate_limit_tpm': result['rate_limits']['limit_tpm'],
    'remaining_tpm': result['rate_limits']['remaining_tpm'],
})
```

**Rate Limit Headers:**

```
x-ratelimit-limit-requests: 14400        # RPD (per DAY)
x-ratelimit-limit-tokens: 18000          # TPM (per MINUTE)
x-ratelimit-remaining-requests: 14370
x-ratelimit-remaining-tokens: 17997
x-ratelimit-reset-requests: 2m59.56s
x-ratelimit-reset-tokens: 7.66s
```

### Perplexity (✅ Implemented)

**Key Features:**
- Web-enhanced Sonar models
- Deep Research with citations
- Agent API (third-party models)
- No usage API (per-request tracking + invoice reconciliation)

**Usage Tracking:**

```python
result = perplexity_service.call_with_tracking(
    model='sonar-deep-research',
    messages=[{'role': 'user', 'content': 'Research X'}],
    search_context='high'  # Affects request fee
)

# Store in database immediately:
db.usage_records.insert({
    'timestamp': datetime.now(),
    'service_id': perplexity_service_id,
    'model_name': result['response']['model'],
    'input_tokens': result['usage']['prompt_tokens'],
    'output_tokens': result['usage']['completion_tokens'],
    'search_queries_count': result['usage'].get('search_queries', 0),
    'reasoning_tokens': result['usage'].get('reasoning_tokens', 0),
    'citation_tokens': result['usage'].get('citation_tokens', 0),
    'cost': result['cost'],  # Calculated locally
    'metadata': {'search_context': result['search_context']},
})
```

**Pricing Table (in service):**

See `backend/services/perplexity_service.py` for complete pricing table.

Key models:
- `sonar`: $1/$1 per 1M tokens + $0.005-$0.02 request
- `sonar-pro`: $3/$15 per 1M tokens + $0.005-$0.02 request
- `sonar-deep-research`: Complex (tokens + searches + reasoning + citations)

**Invoice Reconciliation:**

Perplexity invoices show last 4 chars of API key:
```
sonar-pro (743S): $12.34
```

Map `743S` to your keys manually for reconciliation.

---

## Files to Read Before Implementing New Provider

### Essential Reading Order:

1. **`backend/services/base_service.py`** - Base class, retry logic, error handling
2. **`backend/services/anthropic_service.py`** - Reference implementation (most complete)
3. **`backend/services/groq_service.py`** - Per-request tracking pattern
4. **`backend/services/perplexity_service.py`** - Cost calculation pattern
5. **`backend/utils/diagnostic_logger.py`** - Logging utilities
6. **`docs/providers/[provider]-api-research.md`** - Provider-specific research
7. **`docs/DATABASE_SCHEMA_ENHANCED.md`** - Fields available for storage

### Quick Context Commands:

**For Claude Code:**
```
@backend/services/anthropic_service.py
@backend/services/groq_service.py
@docs/providers/[provider]-api-research.md

Implement backend/services/[provider]_service.py following the established pattern.
```

**For GitHub Copilot:**
```python
# Context: Implementing [Provider] service
# Reference: backend/services/groq_service.py (per-request tracking)
# Schema: docs/DATABASE_SCHEMA_ENHANCED.md
# Provider docs: docs/providers/[provider]-api-research.md
```

---

## Verification Commands

### Test New Service

```python
# backend/scripts/test_providers.py

from services.new_provider_service import NewProviderService

def test_new_provider():
    api_key = os.getenv('NEW_PROVIDER_API_KEY')
    
    if not api_key:
        logger.error("No API key found")
        return False
    
    try:
        service = NewProviderService(api_key)
        valid = service.validate_credentials()
        logger.info(f"New Provider: {'✅ VALID' if valid else '❌ INVALID'}")
        return valid
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False
```

### Verify Imports

```bash
cd backend
python -c "from services.groq_service import GroqService; print('Groq: OK')"
python -c "from services.perplexity_service import PerplexityService; print('Perplexity: OK')"
```

### Test Bad Key Rejection

```python
# Should raise AuthenticationError
try:
    service = GroqService("bad-key-format")
    print("❌ FAIL: Should have rejected bad key")
except AuthenticationError:
    print("✅ PASS: Bad key rejected correctly")
```

---

## Integration Points

### Scheduler Jobs

**For providers WITH usage APIs:**

```python
# backend/jobs/sync_usage.py

from services.anthropic_service import AnthropicService

def sync_anthropic_usage(account_id):
    account = Account.query.get(account_id)
    api_key = decrypt(account.api_key)
    
    service = AnthropicService(api_key)
    usage = service.get_usage(
        start_date=(datetime.now() - timedelta(days=7)).isoformat()[:10],
        end_date=datetime.now().isoformat()[:10]
    )
    
    # Store in database
    for day in usage['daily']:
        UsageRecord.create_or_update(...)
```

**For providers WITHOUT usage APIs (Groq, Perplexity):**

```python
# Store immediately after each API call in application code

def call_llm(provider, model, messages):
    if provider == 'groq':
        service = GroqService(api_key)
        result = service.call_with_tracking(model, messages)
        # Store immediately
        UsageRecord.create(result['usage'])
        return result['response']
```

### Dashboard Queries

**See `docs/DATABASE_SCHEMA_ENHANCED.md` for query examples:**

- Cache effectiveness (Anthropic)
- Rate limit pressure (OpenAI, Groq)
- Performance by provider (Groq timing)
- Service tier costs (Anthropic)

---

## Common Pitfalls

### 1. Wrong Key Type (Anthropic)
❌ Using `sk-ant-api-` instead of `sk-ant-admin-`  
✅ Always validate prefix in `__init__`

### 2. Missing Per-Request Logging
❌ Assuming usage API exists for all providers  
✅ Check provider docs, implement `call_with_tracking()` if no API

### 3. Forgetting Rate Limit Headers
❌ Not extracting headers from responses  
✅ Check for `x-ratelimit-*` headers and store

### 4. Hardcoding Costs
❌ Using outdated pricing  
✅ Maintain pricing tables with dates, update regularly

### 5. Not Testing Credential Validation
❌ Skipping `validate_credentials()` implementation  
✅ Always test with minimal call (max_tokens=1)

---

## Next Steps

### Immediate
1. ✅ Test Groq service in staging
2. ✅ Test Perplexity service in staging
3. ⏳ Update scheduler to call Groq/Perplexity via `call_with_tracking()`
4. ⏳ Add Groq/Perplexity to provider test script

### Week 1
5. ⏳ Deploy Groq + Perplexity to production
6. ⏳ Monitor for 24h
7. ⏳ Verify data appearing in dashboard

### Week 2
8. ⏳ Implement Mistral service (OpenAI-compatible)
9. ⏳ Begin Google Gemini research (GCP setup)

---

## Success Criteria

- [ ] All provider tests pass
- [ ] No authentication errors in logs
- [ ] Usage data appears in dashboard within 5 minutes
- [ ] Rate limits tracked and alerted at 80% threshold
- [ ] Costs calculated accurately (cross-reference invoices)
- [ ] Performance metrics visible (Groq timing)
- [ ] Zero data loss (every API call logged)

---

**Handover Complete.** Next AI can continue from here with full context.
