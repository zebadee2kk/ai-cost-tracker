# Handover to Claude Code

**Project:** AI Cost Tracker  
**Date:** March 2, 2026, 7:55 PM GMT  
**Your Mission:** Complete provider implementations and diagnose data pipeline

---

## TL;DR - Start Here

```bash
# Read these 3 files first (20 minutes)
@docs/CURRENT_STATUS.md              # What's been done
@docs/CLAUDE_CONTINUATION_PROMPT.md  # How to continue
@docs/PROVIDER_SERVICES_HANDOVER.md  # Technical details

# Then run diagnostics (5 minutes)
cd backend
python scripts/test_providers.py

# Check logs for errors
tail -100 logs/debug.log | grep -i error

# Verify Anthropic key type (common issue)
echo $ANTHROPIC_API_KEY | head -c 15
# Should show: sk-ant-admin-
# If shows: sk-ant-api- → WRONG KEY, regenerate admin key
```

---

## Project Status: 4/6 Providers Complete

### ✅ Done
- Anthropic service (with admin API)
- Groq service (per-request tracking)
- Perplexity service (local cost calculation)
- OpenAI service (partial)
- Enhanced database schema designed
- Diagnostic logging infrastructure
- Comprehensive documentation

### ⏳ TODO
- Complete OpenAI service (add rate limits)
- Implement Mistral service
- Implement Google Gemini service
- Apply database migration
- Diagnose why dashboard shows zero data

---

## Critical Issue: No Data in Dashboard

**Symptom:** Dashboard shows zero usage despite API running

**Most Likely Cause:** Anthropic admin key confusion

**Quick Fix:**
```bash
# 1. Check current key type
echo $ANTHROPIC_API_KEY | head -c 15

# 2. If wrong (sk-ant-api-), regenerate:
# Go to: https://console.anthropic.com/settings/organization
# Generate Admin Key (NOT API Key)

# 3. Update .env
ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-YOUR-KEY-HERE

# 4. Restart
docker-compose restart backend

# 5. Test
python backend/scripts/test_providers.py
```

---

## File Structure

```
ai-cost-tracker/
├── backend/
│   ├── services/
│   │   ├── anthropic_service.py      ✅ Complete
│   │   ├── groq_service.py           ✅ Complete
│   │   ├── perplexity_service.py     ✅ Complete
│   │   ├── openai_service.py         ⚠️  Partial
│   │   ├── base_service.py           ✅ Base class
│   │   └── __init__.py
│   ├── utils/
│   │   └── diagnostic_logger.py      ✅ Logging utility
│   ├── scripts/
│   │   └── test_providers.py         ⚠️  Needs update
│   └── migrations/
│       └── versions/
│           └── 202603_enhanced_usage_tracking.py  ⏳ Not applied
└── docs/
    ├── CURRENT_STATUS.md             📊 READ FIRST
    ├── CLAUDE_CONTINUATION_PROMPT.md 📖 Your guide
    ├── HANDOVER_TO_CLAUDE.md         📄 This file
    ├── PROVIDER_SERVICES_HANDOVER.md 📖 Technical specs
    ├── DATABASE_SCHEMA_ENHANCED.md   📊 Schema details
    └── providers/                    📁 6 provider docs
```

---

## Next Tasks (Priority Order)

### 1. Diagnose Data Pipeline (1-2 hours) 🔴
**Priority:** CRITICAL  
**Files:** `backend/scripts/test_providers.py`, logs  
**Goal:** Figure out why no data appears in dashboard

**Steps:**
1. Run connectivity tests
2. Check Anthropic key type (admin vs. standard)
3. Verify database writes
4. Review error logs
5. Test manual sync

### 2. Complete OpenAI Service (2-3 hours) 🟡
**Priority:** HIGH  
**Files:** `backend/services/openai_service.py`  
**Template:** `backend/services/groq_service.py` (copy rate limit extraction)

**TODO:**
- Add `_extract_rate_limits()` method
- Add diagnostic logging calls
- Implement `call_with_tracking()`
- Test with real OpenAI key

### 3. Implement Mistral Service (2-3 hours) 🟡
**Priority:** HIGH  
**Files:** Create `backend/services/mistral_service.py`  
**Template:** Copy from `groq_service.py`

**Steps:**
1. Research Mistral API (check if OpenAI-compatible)
2. Copy Groq service as starting point
3. Adjust endpoints and key format
4. Test with real Mistral key

### 4. Implement Google Gemini (1-2 days) 🟢
**Priority:** MEDIUM  
**Files:** Create `backend/services/google_gemini_service.py`  
**Complexity:** High (GCP setup required)

**Steps:**
1. Set up GCP project
2. Enable Vertex AI API
3. Create service account
4. Configure BigQuery export
5. Implement service using GCP client library

### 5. Apply Database Migration (1 hour) 🟢
**Priority:** MEDIUM  
**Files:** `backend/migrations/versions/202603_enhanced_usage_tracking.py`

**Steps:**
1. Backup production database
2. Test in staging
3. Apply migration
4. Verify new columns

---

## Code Patterns to Follow

### All Services Must Have:

1. **Key Validation in `__init__()`**
   ```python
   if not api_key.startswith('expected-prefix'):
       raise AuthenticationError("Clear error message")
   ```

2. **Credential Test in `validate_credentials()`**
   ```python
   def validate_credentials(self) -> bool:
       try:
           # Make minimal API call (max_tokens=1)
           return True
       except AuthenticationError:
           return False
   ```

3. **Diagnostic Logging Throughout**
   ```python
   from utils.diagnostic_logger import get_diagnostic_logger, log_api_call
   logger = get_diagnostic_logger(__name__)
   
   with log_api_call(logger, "provider", "operation"):
       result = self._make_request(...)
   ```

4. **Consistent Response Format**
   ```python
   return {
       'response': {...},      # Full API response
       'usage': {...},         # Normalized tokens
       'cost': 0.0123,         # USD (if calculated)
       'rate_limits': {...}    # If available
   }
   ```

---

## Testing Commands

```bash
# Test all providers
python backend/scripts/test_providers.py

# Test specific service import
python -c "from services.groq_service import GroqService; print('✅')"

# Check bad key rejection
python -c "from services.groq_service import GroqService; GroqService('bad-key')"
# Should raise: AuthenticationError

# Verify database
psql -d ai_cost_tracker -c "SELECT COUNT(*) FROM usage_records;"

# Check logs
tail -f backend/logs/debug.log | grep -E "groq|perplexity|anthropic"
```

---

## Resources

### Essential Documentation
1. **CURRENT_STATUS.md** - What's done, what's next
2. **CLAUDE_CONTINUATION_PROMPT.md** - Detailed continuation guide
3. **PROVIDER_SERVICES_HANDOVER.md** - Technical implementation specs
4. **DATABASE_SCHEMA_ENHANCED.md** - Database structure

### Reference Implementations
- **Groq** - Per-request tracking pattern
- **Perplexity** - Local cost calculation
- **Anthropic** - Usage API pattern

### Provider Documentation
- `docs/providers/anthropic-api-research.md`
- `docs/providers/openai-api-research.md`
- `docs/providers/groq-api-research.md`
- `docs/providers/perplexity-api-research.md`
- `docs/providers/google-gemini-api-research.md`
- `docs/providers/provider-comparison-matrix.md`

---

## Common Issues & Solutions

### Issue: "Dashboard shows zero data"
**Check:** Anthropic key type (admin vs. standard)  
**Fix:** Regenerate admin key in Console → Settings → Organization

### Issue: "Import error for new service"
**Check:** Service added to `backend/services/__init__.py`?  
**Fix:** Add import statement

### Issue: "Rate limits not tracked"
**Check:** Headers extracted from response?  
**Fix:** Copy `_extract_rate_limits()` from Groq service

### Issue: "Costs don't match invoice"
**Check:** Pricing table up to date?  
**Fix:** Update pricing table, add date comment

---

## Success Criteria

You're done when:

- [ ] All provider tests pass
- [ ] Dashboard shows real data (not zero)
- [ ] 6/6 providers implemented
- [ ] Rate limits tracked for all providers
- [ ] No authentication errors in logs
- [ ] Database migration applied
- [ ] Costs accurate to invoices

---

## Getting Started Checklist

1. [ ] Pull latest code: `git pull origin master`
2. [ ] Read `docs/CURRENT_STATUS.md` (5 min)
3. [ ] Read `docs/CLAUDE_CONTINUATION_PROMPT.md` (15 min)
4. [ ] Run `python backend/scripts/test_providers.py`
5. [ ] Check logs: `tail -100 backend/logs/debug.log`
6. [ ] Verify Anthropic key: `echo $ANTHROPIC_API_KEY | head -c 15`
7. [ ] Choose next task from priority list above

---

## Contact

If completely blocked:
1. Review troubleshooting in `docs/IMPLEMENTATION_COMPLETE_GUIDE.md`
2. Check working examples in `backend/services/`
3. Review provider-specific docs in `docs/providers/`

---

**Welcome to the project! Start with diagnostics, then move to implementing remaining providers. The codebase is well-structured and ready for you to continue.**
