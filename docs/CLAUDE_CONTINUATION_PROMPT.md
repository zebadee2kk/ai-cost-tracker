# Claude Code Continuation Prompt

**Project:** AI Cost Tracker - Multi-Provider Usage & Cost Monitoring  
**Current Phase:** Provider Service Implementation  
**Your Role:** Continue implementation work on remaining providers  
**Last Updated:** March 2, 2026, 7:55 PM GMT

---

## Quick Context

You're working on an AI cost tracking system that monitors usage and costs across 6 AI providers. **4 of 6 providers are complete**, and you need to finish the remaining 2 (Mistral, Google Gemini) plus diagnose why data isn't appearing in the dashboard.

---

## What's Been Done

### ✅ Completed Work

1. **Provider Services Implemented (4/6)**
   - Anthropic Claude service with admin API
   - Groq service with per-request tracking
   - Perplexity service with local cost calculation
   - OpenAI service (partial - needs rate limit extraction)

2. **Infrastructure Built**
   - Base service class with retry logic
   - Diagnostic logging system (structured logs)
   - Enhanced database schema designed (20+ new fields)
   - Comprehensive documentation (10+ files)

3. **Documentation Created**
   - Provider API research (6 providers)
   - Implementation guides
   - Database schema documentation
   - Handover documentation for AI assistants

### Key Files to Know

```
backend/services/
├── anthropic_service.py      ✅ Reference implementation
├── groq_service.py           ✅ Per-request tracking pattern  
├── perplexity_service.py     ✅ Cost calculation pattern
├── openai_service.py         ⚠️  Needs completion
├── base_service.py           ✅ Base class
└── __init__.py

backend/utils/
└── diagnostic_logger.py      ✅ Structured logging

docs/
├── CURRENT_STATUS.md         📊 Project status (READ FIRST)
├── PROVIDER_SERVICES_HANDOVER.md  📖 Implementation guide
├── DATABASE_SCHEMA_ENHANCED.md    📊 Database structure
└── providers/                📁 Provider-specific docs (6 files)
```

---

## Your Mission

### Primary Objectives

1. **Diagnose Data Pipeline Issue** (Critical - 1-2 hours)
   - Dashboard shows zero usage despite API being live
   - Likely cause: Anthropic admin key confusion
   - Action: Run diagnostics, verify key types

2. **Complete OpenAI Service** (High - 2-3 hours)
   - Add rate limit header extraction
   - Add diagnostic logging integration
   - Implement `call_with_tracking()` method

3. **Implement Mistral Service** (High - 2-3 hours)
   - Research Mistral API (OpenAI-compatible)
   - Copy Groq service as template
   - Test with real API key

4. **Implement Google Gemini Service** (Medium - 1-2 days)
   - GCP project setup required
   - BigQuery integration for usage data
   - Most complex provider

---

## How to Start

### Step 1: Read Context (15 minutes)

Read these files in order:

```bash
# 1. Current status
@docs/CURRENT_STATUS.md

# 2. Implementation guide
@docs/PROVIDER_SERVICES_HANDOVER.md

# 3. Reference implementation
@backend/services/groq_service.py

# 4. Provider research (skim all 6)
@docs/providers/
```

### Step 2: Run Diagnostics (30 minutes)

```bash
# Test provider connectivity
cd backend
python scripts/test_providers.py

# Expected output:
# Anthropic: ✅ VALID or ❌ INVALID
# OpenAI: ✅ VALID or ❌ INVALID
# Groq: ⚠️  NO KEY or ✅ VALID
# Perplexity: ⚠️  NO KEY or ✅ VALID

# Check environment variables
env | grep -E "ANTHROPIC|OPENAI|GROQ|PERPLEXITY"

# Check logs for errors
tail -100 logs/debug.log | grep -i error

# Verify database connectivity
psql -d ai_cost_tracker -c "SELECT COUNT(*) FROM usage_records;"
```

### Step 3: Fix Anthropic Key Issue (1 hour)

**Problem:** Dashboard empty despite API running

**Root Cause Check:**
```bash
# Check key prefix
echo $ANTHROPIC_API_KEY | head -c 15

# Should show: sk-ant-admin-
# If shows: sk-ant-api-03 → WRONG KEY TYPE
```

**Solution:**
1. Go to: https://console.anthropic.com/settings/organization
2. Click: "Generate Admin Key" (NOT "API Key")
3. Copy key starting with `sk-ant-admin-`
4. Update `.env`: `ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-...`
5. Restart: `docker-compose restart backend`
6. Test: `python scripts/test_providers.py`

### Step 4: Choose Next Task

Pick based on priority:

**Option A: Complete OpenAI Service** (quickest win)
- Copy rate limit extraction from `groq_service.py`
- Add diagnostic logging calls
- Test with real OpenAI key
- Estimated: 2-3 hours

**Option B: Implement Mistral Service** (new provider)
- Research Mistral API docs
- Copy `groq_service.py` as template
- Adapt for Mistral specifics
- Estimated: 2-3 hours

**Option C: Apply Database Migration** (infrastructure)
- Backup production database
- Test migration in staging
- Apply enhanced schema
- Estimated: 1 hour + testing

---

## Implementation Patterns

### Pattern 1: Standard Service (Has Usage API)

Use this for **Mistral** if usage API exists:

```python
class MistralService(BaseService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        # Validate key format
        if not api_key.startswith('expected-prefix'):
            raise AuthenticationError("Invalid key format")
        self._auth_headers = {...}
    
    def validate_credentials(self) -> bool:
        # Make minimal API call (max_tokens=1)
        try:
            self._make_request(...)
            return True
        except AuthenticationError:
            return False
    
    def get_usage(self, start_date, end_date, account_id=None) -> dict:
        # Fetch from usage API
        response = self._make_request(...)
        return self._normalize_response(response)
```

### Pattern 2: Per-Request Service (No Usage API)

Use this for **Mistral** if no usage API:

```python
class MistralService(BaseService):
    def call_with_tracking(self, model, messages, **kwargs) -> Dict:
        """Make API call and return usage immediately."""
        response_obj = self._make_request_with_headers(...)
        
        return {
            'response': response_obj['data'],
            'usage': response_obj['data']['usage'],
            'rate_limits': self._extract_rate_limits(response_obj['headers']),
        }
    
    def get_usage(self, start_date, end_date, account_id=None) -> dict:
        return {
            'error': 'no_usage_api',
            'message': 'Use call_with_tracking() for per-request logging'
        }
```

### Pattern 3: Complex Service (GCP Integration)

Use this for **Google Gemini**:

```python
from google.cloud import bigquery
from google.oauth2 import service_account

class GoogleGeminiService(BaseService):
    def __init__(self, credentials_path: str):
        # Load service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        self.bq_client = bigquery.Client(credentials=credentials)
    
    def get_usage(self, start_date, end_date, account_id=None) -> dict:
        # Query BigQuery for usage data
        query = """
            SELECT date, model, input_tokens, output_tokens, cost
            FROM `project.dataset.usage_table`
            WHERE date BETWEEN @start_date AND @end_date
        """
        # Execute and return results
```

---

## Code Templates

### Template: Rate Limit Extraction

```python
def _extract_rate_limits(self, headers: dict) -> dict:
    """Extract rate limit info from response headers."""
    return {
        'limit_tpm': self._parse_int(headers.get('x-ratelimit-limit-tokens')),
        'limit_rpm': self._parse_int(headers.get('x-ratelimit-limit-requests')),
        'remaining_tpm': self._parse_int(headers.get('x-ratelimit-remaining-tokens')),
        'remaining_rpm': self._parse_int(headers.get('x-ratelimit-remaining-requests')),
        'reset_tpm': headers.get('x-ratelimit-reset-tokens'),
        'reset_rpm': headers.get('x-ratelimit-reset-requests'),
    }

def _parse_int(self, value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None
```

### Template: Diagnostic Logging

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
    result = self._make_api_call()

# Log requests
log_provider_request(
    logger, "provider", method, url, 
    headers=headers, params=params, json_body=json_body
)

# Log responses
log_provider_response(
    logger, "provider", status_code, response_time_ms,
    headers=headers, body=body, error=error
)
```

### Template: Cost Calculation

```python
from decimal import Decimal

PRICING = {
    'model-name': {
        'input': Decimal('3.00'),   # Per 1M tokens
        'output': Decimal('15.00'),  # Per 1M tokens
    }
}

def _calculate_cost(self, model: str, usage: dict) -> Decimal:
    pricing = PRICING.get(model, PRICING['_default'])
    
    input_tokens = Decimal(str(usage.get('prompt_tokens', 0)))
    output_tokens = Decimal(str(usage.get('completion_tokens', 0)))
    
    input_cost = (input_tokens / Decimal('1000000')) * pricing['input']
    output_cost = (output_tokens / Decimal('1000000')) * pricing['output']
    
    return input_cost + output_cost
```

---

## Testing Checklist

For each new service:

- [ ] Import test: `python -c "from services.X import XService; print('OK')"`
- [ ] Key validation: Service rejects invalid key format
- [ ] Credential test: `validate_credentials()` returns True with real key
- [ ] API call test: Can make successful API call
- [ ] Rate limit extraction: Headers parsed correctly
- [ ] Diagnostic logging: Logs appear in `logs/debug.log`
- [ ] Error handling: 401/429/500 handled gracefully
- [ ] Database write: Usage data stored in `usage_records` table

---

## Common Pitfalls

### ❌ Wrong Anthropic Key Type
**Problem:** Using `sk-ant-api-` instead of `sk-ant-admin-`  
**Solution:** Generate admin key in Console → Settings → Organization

### ❌ Missing Diagnostic Logging
**Problem:** Can't debug issues without logs  
**Solution:** Use `log_api_call()`, `log_provider_request()`, `log_provider_response()`

### ❌ Not Handling Rate Limits
**Problem:** Service fails when hitting rate limits  
**Solution:** Extract rate limit headers, retry on 429, warn at 80%

### ❌ Hardcoded Pricing
**Problem:** Costs become inaccurate over time  
**Solution:** Use pricing tables with dates, comment when updated

### ❌ Missing Key Validation
**Problem:** Confusing errors when key format is wrong  
**Solution:** Validate key prefix in `__init__()`, clear error message

---

## Success Criteria

You're done when:

- [ ] Provider connectivity test passes for all services
- [ ] Dashboard shows real usage data (not zero)
- [ ] Rate limits tracked and alerted
- [ ] All 6 providers implemented and tested
- [ ] Enhanced database schema applied
- [ ] No authentication errors in logs
- [ ] Cost accuracy matches invoices

---

## Getting Help

If stuck:

1. **Check documentation:**
   - `docs/CURRENT_STATUS.md` - Current state
   - `docs/PROVIDER_SERVICES_HANDOVER.md` - Implementation guide
   - `docs/IMPLEMENTATION_COMPLETE_GUIDE.md` - Troubleshooting

2. **Examine working code:**
   - `backend/services/groq_service.py` - Per-request pattern
   - `backend/services/perplexity_service.py` - Cost calculation
   - `backend/services/anthropic_service.py` - Usage API pattern

3. **Check provider docs:**
   - `docs/providers/[provider]-api-research.md`

4. **Review logs:**
   - `tail -f backend/logs/debug.log`
   - Look for: authentication errors, rate limits, API errors

---

## Example Session

Here's what a typical work session looks like:

```bash
# 1. Pull latest code
git pull origin master

# 2. Read context
cat docs/CURRENT_STATUS.md
cat docs/PROVIDER_SERVICES_HANDOVER.md

# 3. Run diagnostics
python backend/scripts/test_providers.py

# 4. Check for issues
echo $ANTHROPIC_API_KEY | head -c 15  # Check key type
tail -100 backend/logs/debug.log | grep -i error

# 5. Fix Anthropic key if needed
# (regenerate admin key, update .env, restart)

# 6. Implement next provider (e.g., Mistral)
cp backend/services/groq_service.py backend/services/mistral_service.py
# Edit: change class name, API endpoints, key validation

# 7. Test new service
python -c "from services.mistral_service import MistralService; print('OK')"
python backend/scripts/test_providers.py

# 8. Verify in database
psql -d ai_cost_tracker -c "SELECT * FROM usage_records ORDER BY created_at DESC LIMIT 5;"

# 9. Commit
git add backend/services/mistral_service.py
git commit -m "Add Mistral service implementation"
git push
```

---

## Quick Commands Reference

```bash
# Test all providers
python backend/scripts/test_providers.py

# Check specific service import
python -c "from services.groq_service import GroqService; print('OK')"

# View logs
tail -f backend/logs/debug.log

# Check database
psql -d ai_cost_tracker -c "SELECT service_id, COUNT(*) FROM usage_records GROUP BY service_id;"

# Verify schema
psql -d ai_cost_tracker -c "\d usage_records"

# Test API key
curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models
```

---

## Your First Task

Start here:

1. Read `docs/CURRENT_STATUS.md` (5 min)
2. Read `docs/PROVIDER_SERVICES_HANDOVER.md` (10 min)
3. Run `python backend/scripts/test_providers.py` (5 min)
4. Check logs: `tail -100 backend/logs/debug.log | grep -i error` (5 min)
5. Diagnose why dashboard is empty (focus on Anthropic key type)

Then choose your next task based on what you find.

---

**Good luck! The codebase is well-structured, documented, and ready for you to continue. Start with diagnostics, then implement remaining providers following the established patterns.**
