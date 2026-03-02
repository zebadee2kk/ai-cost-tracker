# Handover to Perplexity

**Project:** AI Cost Tracker — Multi-Provider Usage & Cost Monitoring
**Date:** March 2, 2026, ~9:00 PM GMT
**Previous AI:** Claude (Claude Code / claude-sonnet-4-6)
**Your Mission:** Apply the database migration, test all providers end-to-end, and implement Google Gemini

---

## TL;DR

```bash
# 1. Configure API keys in .env (uncomment and fill in)
# 2. Start the stack
docker-compose up -d

# 3. Run diagnostics
cd backend
python scripts/test_providers.py

# 4. Apply the database migration
flask db upgrade

# 5. Test connectivity for each account
# (via UI or API: POST /api/accounts/<id>/test)

# 6. Trigger a sync for OpenAI/Anthropic accounts
# (via UI or API: POST /api/accounts/<id>/sync)
```

---

## What Changed This Session

### New Files
| File | Description |
|------|-------------|
| `backend/scripts/test_providers.py` | Diagnostic script — tests all provider API connections |
| `backend/services/mistral_service.py` | Mistral AI integration — per-request tracking, local cost calc |

### Modified Files
| File | Change |
|------|--------|
| `backend/services/openai_service.py` | Added `_openai_request()` with full diagnostic logging + `_extract_rate_limits()` |
| `backend/services/__init__.py` | Registered Groq, Perplexity, Mistral in SERVICE_CLIENTS (enables `/test` endpoint for all) |
| `backend/routes/accounts.py` | Added `POST /api/accounts/<id>/sync` — manual sync trigger |
| `docs/CURRENT_STATUS.md` | Updated to reflect 5/6 providers complete |

---

## Project Status: 5/6 Providers Complete

### ✅ Done
| Service | File | Tracking Method |
|---------|------|----------------|
| Anthropic | `anthropic_service.py` | Pull — Admin API (`sk-ant-admin-...` required) |
| OpenAI | `openai_service.py` | Pull — Billing API |
| Groq | `groq_service.py` | Push — `call_with_tracking()` |
| Perplexity | `perplexity_service.py` | Push — `call_with_tracking()` |
| Mistral | `mistral_service.py` | Push — `call_with_tracking()` |

### ⏳ TODO
- Google Gemini — most complex (GCP project + Vertex AI + BigQuery)
- Database migration not yet applied to production
- End-to-end test with real API keys (Docker not running)

---

## Priority Tasks (in order)

### 1. Start the Stack and Configure Keys (30 min) 🔴

```bash
# Edit .env — uncomment and fill in your real API keys:
# ANTHROPIC_API_KEY=sk-ant-admin-YOUR-ADMIN-KEY   ← MUST be admin key
# OPENAI_API_KEY=sk-...
# GROQ_API_KEY=gsk_...
# PERPLEXITY_API_KEY=pplx-...
# MISTRAL_API_KEY=your-mistral-key

docker-compose up -d
docker-compose ps  # verify all 3 services healthy
```

**Important:** Anthropic requires an **Admin API key** (`sk-ant-admin-...`).
Standard API keys (`sk-ant-api-...`) only work for inference, not usage reporting.
Generate admin keys at: Console → Settings → Organization → Admin API Keys.

### 2. Run Diagnostic Tests (10 min) 🔴

```bash
cd backend
python scripts/test_providers.py --verbose

# Expected with valid keys:
#   anthropic   ✓ OK
#   openai      ✓ OK
#   groq        ✓ OK
#   perplexity  ✓ OK
#   mistral     ✓ OK
```

### 3. Apply Database Migration (30 min) 🟡

```bash
cd backend
flask db upgrade

# Verify
psql -d ai_tracker -c "\d usage_records"
# Should show new columns: input_tokens, output_tokens, cache_creation_tokens,
# rate_limit_tpm, rate_limit_rpm, queue_time_ms, etc.
```

The migration file is at:
`backend/migrations/versions/202603_enhanced_usage_tracking.py`

**Always backup before migrating:**
```bash
pg_dump ai_tracker > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 4. Test Sync End-to-End (30 min) 🟡

```bash
# Create a test account via API or UI, then:
# POST /api/accounts/<id>/sync  → triggers immediate sync for OpenAI/Anthropic
# POST /api/accounts/<id>/test  → validates API key connectivity

# Check dashboard shows data at http://localhost:3000
# Check logs: docker-compose logs -f backend
```

### 5. Implement Google Gemini Service (1-2 days) 🟢

**Complexity:** High — requires GCP project setup before coding.

**Steps:**
1. Create GCP project at https://console.cloud.google.com
2. Enable Vertex AI API and Cloud Billing API
3. Create service account with `roles/billing.viewer` and `roles/bigquery.dataViewer`
4. Download service account JSON key
5. Enable BigQuery export for Vertex AI usage
6. Implement `backend/services/google_gemini_service.py`

**Reference:** `docs/providers/google-gemini-api-research.md`

**Template to follow:** `backend/services/anthropic_service.py` (pull-based pattern)

---

## Key Architecture Notes

### Pull-Based Services (OpenAI, Anthropic)
- Scheduled sync every 60 min via `backend/jobs/sync_usage.py`
- Manual sync available: `POST /api/accounts/<id>/sync`
- Data stored in `usage_records` table

### Per-Request Services (Groq, Perplexity, Mistral)
- **No usage history API** — must capture at call time
- Use `call_with_tracking()` method
- Returns `{"response": ..., "tracking": {...}}` envelope
- Caller persists `tracking` dict immediately
- Dashboard data comes from manual entries (`POST /api/usage/manual`)

### API Key Types
| Provider | Key Format | Notes |
|----------|-----------|-------|
| Anthropic | `sk-ant-admin-...` | Admin key required (NOT `sk-ant-api-...`) |
| OpenAI | `sk-...` | Standard API key |
| Groq | `gsk_...` | Standard API key |
| Perplexity | `pplx-...` | Standard API key |
| Mistral | no prefix | Any non-empty string |

---

## Common Pitfalls

### Dashboard Shows Zero
1. Docker not running (`docker-compose up -d`)
2. No API keys configured in `.env`
3. Anthropic key is `sk-ant-api-...` not `sk-ant-admin-...`
4. Scheduler hasn't run yet — use manual sync endpoint

### Mistral "AuthenticationError: empty key"
- Mistral keys have no prefix — just check the key isn't empty

### Migration Fails
- Take a backup first
- Check `flask db current` to see current migration state
- If conflict: `flask db stamp head` then retry

---

## Quick Reference

```bash
# Start stack
docker-compose up -d

# Test all providers
cd backend && python scripts/test_providers.py

# Check logs
docker-compose logs -f backend

# Apply migration
cd backend && flask db upgrade

# Check database
psql $DATABASE_URL -c "SELECT service_id, COUNT(*) FROM usage_records GROUP BY service_id;"

# Test specific provider import
python3 -c "from services.mistral_service import MistralService; print('OK')"

# Run existing test suite
cd backend && python -m pytest tests/ -v
```

---

## File Reference

```
backend/
├── scripts/
│   └── test_providers.py         ✅ NEW — diagnostic connectivity tests
├── services/
│   ├── anthropic_service.py      ✅ Admin API pull
│   ├── openai_service.py         ✅ Billing API pull (updated this session)
│   ├── groq_service.py           ✅ Per-request push
│   ├── perplexity_service.py     ✅ Per-request push
│   ├── mistral_service.py        ✅ NEW — per-request push
│   ├── base_service.py           ✅ Base class
│   └── __init__.py               ✅ All 5 providers registered
├── routes/
│   └── accounts.py               ✅ Added /sync endpoint
├── jobs/
│   └── sync_usage.py             ✅ Background scheduler (60 min)
└── migrations/versions/
    └── 202603_enhanced_usage_tracking.py  ⏳ Not yet applied
```

---

**Welcome! The hardest parts are done. Start with `docker-compose up -d`, configure your `.env` keys, run the diagnostic script, and apply the migration. Then the dashboard should show real data.**
