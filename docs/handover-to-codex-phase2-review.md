# Handover to Codex: Phase 2 Review & Verification

**Date**: February 25, 2026
**From**: Claude Code (Phase 2 implementation)
**To**: Codex (review, testing, and Phase 3 readiness)
**Branch**: `claude/multi-service-cost-tracker-WQTIj`

---

## 1. What Was Delivered (Phase 2)

Phase 2 adds multi-service support and data integrity to the Phase 1 MVP.

### Sprint 2.1: Foundation & Anthropic Integration

| File | Change | Purpose |
|------|--------|---------|
| `backend/services/base_service.py` | Added `AuthenticationError`, `RateLimitError` | Error taxonomy for provider-specific failures |
| `backend/migrations/versions/a1b2c3d4e5f6_add_idempotency_constraint.py` | New migration | Unique constraint `uq_usage_record_idempotency` on `(account_id, service_id, timestamp, request_type)`; adds `source` and `updated_at` columns |
| `backend/models/usage_record.py` | New columns + `to_dict` update | `source` (`'api'`/`'manual'`), `updated_at` |
| `backend/jobs/sync_usage.py` | Rewrite | Scheduler duplicate-run fix; `upsert_usage_record()` function; Anthropic added to service dispatch |
| `backend/services/anthropic_service.py` | New file | Full Admin API client with pagination, cost estimation, auth key validation |
| `backend/services/__init__.py` | New file | `SERVICE_CLIENTS` registry; `get_service_client()` helper |
| `backend/tests/test_anthropic_service.py` | New file | 21 unit tests covering constructor, usage parsing, pagination, HTTP errors, cost math |
| `backend/tests/test_idempotent_upsert.py` | New file | 5 DB integration tests for upsert correctness |

### Sprint 2.2: Manual Entry System

| File | Change | Purpose |
|------|--------|---------|
| `backend/routes/usage.py` | Added 3 routes | `POST/PUT/DELETE /api/usage/manual` with ownership validation, input sanitisation |
| `frontend/src/components/ManualEntryModal.jsx` | New file | Modal form: date, cost, tokens, notes; provider help text for Groq/Perplexity |
| `frontend/src/services/api.js` | 3 new exports | `createManualEntry`, `updateManualEntry`, `deleteManualEntry` |

### Documentation

| File | Change |
|------|--------|
| `README.md` | Full rewrite — Phase 2 complete, Anthropic setup instructions, service table, architecture |
| `ROADMAP.md` | Updated Phase 2 sprint status to Complete |

---

## 2. Test Results

```
44 passed, 3 failed (pre-existing), 0 errors
```

**New tests passing** (26):
- `tests/test_anthropic_service.py` — 21 tests
- `tests/test_idempotent_upsert.py` — 5 tests

**Pre-existing failures** (3) — `tests/test_accounts.py`:
- `test_list_accounts`, `test_delete_account`, `test_cannot_access_other_users_account`
- **Root cause**: `_seed_service()` helper in that file inserts a `Service(name="TestService")` and commits it. Since the `app` fixture is session-scoped and the `db` fixture only rolls back *uncommitted* data, the "TestService" persists and causes `UNIQUE constraint failed: services.name` on subsequent tests.
- **Not caused by Phase 2** — these tests were failing before this branch.
- **Fix needed**: Update `_seed_service()` to use a unique name per test (e.g. `uuid`) or use explicit teardown.

**To run tests**:
```bash
cd backend
pytest tests/ -v
pytest tests/test_anthropic_service.py tests/test_idempotent_upsert.py -v   # Phase 2 only
```

---

## 3. Things to Verify / Check

### 3.1 Pre-existing test failures to fix

File: `backend/tests/test_accounts.py`, function `_seed_service(db)`

```python
# Current (broken on repeat runs):
def _seed_service(db):
    svc = Service(name="TestService", ...)
    db.session.commit()
    return svc.id

# Suggested fix — use a unique name + explicit teardown:
import uuid
def _seed_service(db):
    name = f"TestSvc-{uuid.uuid4().hex[:8]}"
    svc = Service(name=name, ...)
    db.session.commit()
    return svc.id, svc   # caller should delete svc at teardown
```

### 3.2 ManualEntryModal not yet wired into AccountManager

`ManualEntryModal.jsx` is built and the API client functions exist, but the "Add Manual Entry" button has not been added to `AccountManager.jsx` yet. The modal exists as a standalone component ready to integrate.

**Suggested integration point** in `AccountManager.jsx`:
```jsx
import ManualEntryModal from './ManualEntryModal';

// In account list rendering, add alongside Test/Delete buttons:
<button className="btn-ghost" onClick={() => setManualEntryAccount(acc)}>
  + Manual Entry
</button>

// Add state and modal rendering:
const [manualEntryAccount, setManualEntryAccount] = useState(null);
{manualEntryAccount && (
  <ManualEntryModal
    account={manualEntryAccount}
    onClose={() => setManualEntryAccount(null)}
    onSuccess={refresh}
  />
)}
```

### 3.3 Connection test now supports Anthropic ✅ (fixed in this branch)

`backend/routes/accounts.py` `/api/accounts/:id/test` has been updated to use `get_service_client()` from `services/__init__.py`, replacing the hardcoded `if service_name == "ChatGPT"` check. It now works for any service registered in `SERVICE_CLIENTS` (OpenAI and Anthropic). No further changes needed here.

### 3.4 Seed script — "Claude" entry already present ✅

`backend/scripts/seed_services.py` already seeds an Anthropic service as `name="Claude"`, which matches the `SERVICE_CLIENTS` key in `services/__init__.py`. No changes needed.

> **Note**: The pricing in the seed script reflects older model rates. The `AnthropicService` class has its own internal 2026 pricing table used for cost estimation. Consider updating the seed script pricing if you want the UI's service pricing display to reflect current rates.

### 3.5 Migration must be applied before tests that touch usage_records

The new migration (`a1b2c3d4e5f6`) adds `source NOT NULL DEFAULT 'api'` and `updated_at` columns. In the test environment (`sqlite:///:memory:`), migrations are not run — instead `db.create_all()` is called, which reads the current model. Since the model now includes `source` and `updated_at`, tests should work correctly. But if any test fixture creates `UsageRecord` without specifying `source`, SQLAlchemy will use the Python-level default `'api'`, which is correct.

**Verify**: Run `pytest tests/test_idempotent_upsert.py -v` to confirm the SQLite fallback path works end-to-end.

### 3.6 Decimal handling in upsert

`upsert_usage_record()` wraps cost in `Decimal(str(cost))` before insert. Verify that the OpenAI sync path still works — OpenAI returns `float` costs from `_parse_usage_response()`, and the upsert will convert them correctly via `str()`.

---

## 4. Known Gaps / Phase 3 Backlog

These items were not part of Phase 2 scope but are the highest-priority next steps:

| Priority | Item | File(s) to change |
|----------|------|-------------------|
| High | Fix pre-existing `test_accounts.py` failures | `tests/test_accounts.py` |
| High | Wire `ManualEntryModal` into `AccountManager.jsx` | `frontend/src/components/AccountManager.jsx` |
| Medium | Visual badge: manual vs. API entries in usage history | `frontend/src/pages/AnalyticsPage.jsx` or `UsageChart.jsx` |
| Medium | GitHub Actions CI pipeline | `.github/workflows/ci.yml` |
| Medium | CSV/JSON export endpoint | `backend/routes/usage.py` + frontend button |
| Low | Groq/Perplexity service stubs (not in `SERVICE_CLIENTS`, manual only) | Documented in `services/__init__.py` |
| Low | Phase 3 alert enhancements (email, Slack) | New utils |

---

## 5. Architecture Notes for Future Phases

### Service client pattern

All services inherit `BaseService` and implement:
- `validate_credentials() -> bool`
- `get_usage(start_date, end_date) -> dict`

Return shape is normalized:
```python
{
    "total_tokens": int,
    "total_cost": float,
    "daily": [
        {
            "date": "YYYY-MM-DD",
            "tokens": int,
            "cost": float,
            "metadata": {...}   # provider-specific extras
        }
    ]
}
```

Add new services by:
1. Creating `backend/services/<name>_service.py` extending `BaseService`
2. Adding to `SERVICE_CLIENTS` dict in `backend/services/__init__.py`
3. Adding to `service_clients` in `backend/jobs/sync_usage.py:_sync_all_accounts`

### Idempotency

`upsert_usage_record()` handles all persistence. **Never use `db.session.add(UsageRecord(...))` directly in sync jobs** — always go through `upsert_usage_record()` to guarantee no duplicates.

### Manual entries

Manual entries have `source='manual'` and `request_type='manual'`. The `PUT/DELETE /api/usage/manual/:id` endpoints guard on `entry.source == 'manual'` to prevent accidental modification of API-synced records.

---

## 6. How to Validate the Full System

```bash
# 1. Start the stack
docker-compose up -d
docker-compose exec backend flask db upgrade
docker-compose exec backend python scripts/seed_services.py

# 2. Run backend tests
docker-compose exec backend pytest tests/ -v

# 3. Manual smoke test — OpenAI
#    - Register user, add OpenAI account with valid key
#    - GET /api/accounts/:id/test → should return {"ok": true}
#    - Wait for sync or trigger manually

# 4. Manual smoke test — Anthropic (requires Admin key)
#    - Add Anthropic account with sk-ant-admin-... key
#    - GET /api/accounts/:id/test → should succeed
#    - Check /api/usage shows data

# 5. Manual smoke test — Manual entry (Groq / Perplexity)
#    - Add a Groq account (no API key)
#    - POST /api/usage/manual {"account_id": X, "date": "2026-02-25", "cost": "1.50"}
#    - GET /api/usage → should include the manual entry cost
#    - PUT /api/usage/manual/:id {"cost": "2.00"} → should update
#    - DELETE /api/usage/manual/:id → should remove

# 6. Verify idempotency
#    - Run sync twice manually
#    - SELECT COUNT(*) FROM usage_records WHERE account_id = X AND timestamp = '...'
#    - Should be 1 (not 2)
```

---

## 7. Quick File Reference

```
backend/
├── services/
│   ├── base_service.py          ← ServiceError, AuthenticationError, RateLimitError, BaseService
│   ├── openai_service.py        ← Reference implementation
│   ├── anthropic_service.py     ← NEW: Admin API, paginated usage, cost estimation
│   └── __init__.py              ← NEW: SERVICE_CLIENTS registry, get_service_client()
├── jobs/
│   └── sync_usage.py            ← UPDATED: upsert_usage_record(), WERKZEUG fix, Anthropic dispatch
├── models/
│   └── usage_record.py          ← UPDATED: source, updated_at columns
├── routes/
│   ├── usage.py                 ← UPDATED: POST/PUT/DELETE /manual endpoints
│   └── accounts.py              ← UPDATED: test endpoint now uses get_service_client()
├── migrations/versions/
│   ├── 8f80d9282c6b_initial.py  ← Original schema
│   └── a1b2c3d4e5f6_add_idempotency_constraint.py  ← NEW: unique constraint + source/updated_at
├── tests/
│   ├── test_anthropic_service.py   ← NEW: 21 unit tests
│   └── test_idempotent_upsert.py   ← NEW: 5 DB integration tests

frontend/src/
├── components/
│   └── ManualEntryModal.jsx        ← NEW: manual entry form with provider help text
└── services/
    └── api.js                      ← UPDATED: createManualEntry, updateManualEntry, deleteManualEntry
```

---

## 8. Handover Checklist

- [x] All Phase 2 code committed to `claude/multi-service-cost-tracker-WQTIj`
- [x] 44/47 tests passing (3 pre-existing failures documented above)
- [x] README updated to reflect Phase 2 completion + Anthropic setup guide
- [x] ROADMAP.md updated with sprint completion status
- [x] Connection test (`/api/accounts/:id/test`) updated to use `get_service_client()` — works for OpenAI + Anthropic
- [x] This handover document created
- [ ] Pre-existing `test_accounts.py` failures fixed **(Codex action)**
- [ ] ManualEntryModal wired into AccountManager **(Codex action)**
- [ ] Branch merged to main via PR **(Codex action)**

---

**Good luck! The foundation is solid — Phase 3 is ready to begin once the above gaps are closed.**
