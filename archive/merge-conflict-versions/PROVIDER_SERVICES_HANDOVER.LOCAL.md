# Provider Services Handover

**Date:** March 2, 2026
**Status:** Groq complete → Perplexity next
**Audience:** Next AI assistant (Perplexity, Claude, Copilot)

---

## What Has Been Built

### Completed services

| File | Provider | Method | Status |
|------|----------|--------|--------|
| `backend/services/anthropic_service.py` | Anthropic | Admin API pull | ✅ Done |
| `backend/services/openai_service.py` | OpenAI | Billing API pull | ✅ Done |
| `backend/services/groq_service.py` | Groq | Per-request push | ✅ Done 2026-03-02 |
| `backend/services/perplexity_service.py` | Perplexity | Per-request push | ❌ **TODO** |

### Established pattern

Every service follows the same structure. Use `anthropic_service.py` as the primary reference and `groq_service.py` as the direct analog for per-request services:

```
services/
└── <provider>_service.py
    ├── class <Provider>Service(BaseService)
    │   ├── __init__           validate key format, store auth headers
    │   ├── validate_credentials()   lightweight API call → bool
    │   ├── get_usage()              pull history or return empty + warning
    │   └── call_with_tracking()    push: make call, return {response, tracking}
    └── private helpers
        ├── _<provider>_raw_request()   auth + retry + full diagnostic logging
        ├── _extract_*()                parse provider-specific fields
        └── _parse_*/sec_to_ms etc.     type-coercion utilities
```

### Diagnostic logging imports (required in every service)

```python
from utils.diagnostic_logger import (
    get_diagnostic_logger,
    log_api_call,
    log_provider_request,
    log_provider_response,
    log_sync_attempt,
    log_sync_result,
)
logger = get_diagnostic_logger(__name__)
```

### `call_with_tracking()` return contract

Both Groq and (to be) Perplexity return the same envelope:

```python
{
    "response": { ...raw provider response... },
    "tracking": {
        "timestamp": "ISO-8601",
        "model": str,
        "account_id": int | None,
        "input_tokens": int,
        "output_tokens": int,
        "total_tokens": int,
        # provider-specific fields below
        ...
    }
}
```

The **caller** is responsible for persisting `tracking` — services have no DB dependency.

---

## Task: Implement `backend/services/perplexity_service.py`

### Key facts

- **API key format:** `pplx-...`
- **Base URL:** `https://api.perplexity.ai`
- **Auth:** `Authorization: Bearer <key>` header
- **No usage history API** (same as Groq) — must capture at request time
- **No rate limit headers** (unlike Groq/OpenAI) — nothing to extract
- **Cost must be calculated client-side** — Perplexity does not return cost

### Perplexity response `usage` fields

```json
{
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "total_tokens": 225,
    "search_queries": 3,
    "reasoning_tokens": 0,
    "citation_tokens": 42
  }
}
```

`search_queries`, `reasoning_tokens`, and `citation_tokens` are Perplexity-specific and
must be captured — they affect cost for `sonar-deep-research`.

### Pricing table (March 2026)

| Model | Input ($/1M) | Output ($/1M) | Request | Searches (each) | Citations ($/1M) | Reasoning ($/1M) |
|-------|-------------|--------------|---------|-----------------|-----------------|-----------------|
| `sonar` | $1.00 | $1.00 | $0.01 | — | — | — |
| `sonar-pro` | $3.00 | $15.00 | $0.01 | — | — | — |
| `sonar-deep-research` | $2.00 | $8.00 | — | $0.005 | $2.00 | $3.00 |
| `sonar-reasoning` | $1.00 | $5.00 | $0.005 | — | — | — |

Reference: `docs/providers/perplexity-api-research.md`

### `tracking` dict shape to return

```python
{
    "timestamp": datetime.utcnow().isoformat(),
    "model": model,
    "account_id": account_id,
    "input_tokens": int,
    "output_tokens": int,
    "total_tokens": int,
    "search_queries": int,       # Perplexity-specific
    "reasoning_tokens": int,     # Perplexity-specific
    "citation_tokens": int,      # Perplexity-specific
    "cost": float,               # Calculated locally — Perplexity must do this
    "cost_breakdown": {          # Itemised for the DB cost_breakdown JSON column
        "input_cost": float,
        "output_cost": float,
        "request_cost": float,
        "search_cost": float,
        "citation_cost": float,
        "reasoning_cost": float,
    },
}
```

### `validate_credentials()` approach

Make a minimal chat completion with a cheap model:

```python
# POST https://api.perplexity.ai/chat/completions
{"model": "sonar", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
```

Return `True` on 2xx, `False` on 401/403.

### `get_usage()` approach

Same pattern as Groq — return empty result with a warning log:

```python
return {
    "total_tokens": 0,
    "total_cost": 0.0,
    "daily": [],
    "note": "Perplexity has no usage history API. Track usage via call_with_tracking().",
}
```

---

## Files to Read Before Implementing

1. [backend/services/groq_service.py](../backend/services/groq_service.py) — closest analog (per-request, no usage API)
2. [backend/services/anthropic_service.py](../backend/services/anthropic_service.py) — diagnostic logging pattern reference
3. [backend/services/base_service.py](../backend/services/base_service.py) — `BaseService`, exceptions, `MAX_RETRIES`
4. [backend/utils/diagnostic_logger.py](../backend/utils/diagnostic_logger.py) — all logging helpers
5. [docs/providers/perplexity-api-research.md](providers/perplexity-api-research.md) — API research notes

---

## After Perplexity: What Remains

1. **Wire services into sync job** (`backend/jobs/sync_usage.py`) — per-request services need a different hook than pull-based ones
2. **Mistral service** — OpenAI-compatible, simpler than Perplexity
3. **Google Gemini service** — most complex (Vertex AI / Cloud Logging)
4. **Frontend updates** — display `search_queries`, `citation_tokens`, timing metrics

---

## Verification

Once `perplexity_service.py` is written, confirm:

```bash
cd backend
python3 -c "from services.perplexity_service import PerplexityService; print('Import OK')"

# Reject bad key prefix
python3 -c "
from services.perplexity_service import PerplexityService
try:
    PerplexityService('sk-bad-key')
    print('FAIL')
except Exception as e:
    print(f'OK: {type(e).__name__}')
"
```
