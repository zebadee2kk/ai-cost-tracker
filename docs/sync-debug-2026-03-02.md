# Sync Debug Report — 2026-03-02

**Context:** Fresh production install on local machine. Three provider accounts added
(ChatGPT, Claude, Perplexity). No usage data appearing in dashboard.

---

## Environment

- Install method: `bash install.sh` (clean slate, no prior `.env`)
- Docker: 29.2.1
- Stack: all three containers healthy (db, backend, frontend)
- Migrations: all 4 ran cleanly on first boot
- Services seeded: ChatGPT, Claude, Groq, GitHub Copilot, Perplexity

---

## Accounts Added & Test Results

| ID | Service     | Account Name | Test Result | Root Cause                          |
|----|-------------|--------------|-------------|-------------------------------------|
| 1  | ChatGPT     | Work         | 200 OK      | Credentials valid — but billing sync fails (see below) |
| 2  | Perplexity  | Personal     | 501         | No API client registered — expected, manual entry only |
| 3  | Claude      | Work         | 400         | Wrong key type — standard key rejected at init         |

---

## Sync Attempt (manual trigger)

Triggered `_sync_all_accounts()` directly ~16 minutes after install.
Result: **0 usage records written**.

### Error log

```
ERROR jobs.sync_usage: Failed to sync account 1:
  Request failed: 403 Client Error: Forbidden for url:
  https://api.openai.com/v1/dashboard/billing/usage?start_date=2026-03-01&end_date=2026-03-03

ERROR jobs.sync_usage: Failed to sync account 3:
  Anthropic integration requires an Admin API key (sk-ant-admin...).
  Standard API keys are not supported for usage reporting.
  Generate an Admin key in Console → Settings → Organization.
```

---

## Root Cause Analysis

### Account 3 — Claude: KNOWN, ACTIONABLE

The `AnthropicService.__init__` validates the key prefix before any network call:

```python
# backend/services/anthropic_service.py:56-61
if not api_key.startswith('sk-ant-admin'):
    raise AuthenticationError(
        "Anthropic integration requires an Admin API key (sk-ant-admin...). ..."
    )
```

**Fix:** User needs to replace the key with an Admin API key from
Anthropic Console → Settings → Organization → Admin API Keys.

---

### Account 1 — ChatGPT: NEEDS INVESTIGATION

`validate_credentials()` passes (uses `GET /v1/models` — works with any API key).
But `get_usage()` calls the legacy billing endpoint which returns 403:

```
GET https://api.openai.com/v1/dashboard/billing/usage
→ 403 Forbidden
```

The endpoint in use ([`backend/services/openai_service.py:62-65`](../backend/services/openai_service.py#L62)):

```python
data = self._request(
    "GET",
    f"{BASE_URL}/v1/dashboard/billing/usage",
    headers=self._auth_headers,
    params={"start_date": start_date, "end_date": end_date},
)
```

**Possible causes (needs Perplexity to investigate):**

1. **Endpoint deprecated** — OpenAI migrated billing/usage to a new API (possibly
   `/v1/usage` or the new Usage dashboard API). `/v1/dashboard/billing/usage` may
   no longer be accessible via standard API keys.

2. **Key permission scope** — The billing endpoint may require an "Owner" or
   "Admin" org-level key, not a regular project key (`sk-proj-...`). If the user's
   key is a project-scoped key, it won't have billing access.

3. **Org requirement** — The endpoint may only work on paid org plans, not
   individual accounts.

The `validate_credentials` / `get_usage` split is misleading — a key can be valid
for inference but not for billing reporting.

---

### Account 2 — Perplexity: BY DESIGN

Perplexity has no usage API (confirmed in `docs/provider-api-research-2026.md`).
The 501 from the test endpoint is correct behaviour — the service registry
intentionally omits it:

```python
# backend/services/__init__.py
SERVICE_CLIENTS = {
    "ChatGPT": OpenAIService,
    "Claude": AnthropicService,
    # Perplexity, Groq: manual entry — not registered
}
```

No action needed on the Perplexity account itself.

---

## Questions for Perplexity to Investigate

### OpenAI (Priority: High)

1. **Is `/v1/dashboard/billing/usage` still a valid endpoint as of March 2026?**
   Check OpenAI changelog and deprecation notices. If deprecated, what replaced it?

2. **What is the current correct endpoint for fetching billing/usage data via API?**
   Candidates to check:
   - `GET /v1/usage` (newer API)
   - `GET /v1/organization/usage`
   - OpenAI Admin API (separate from the inference API)

3. **What key type/permissions are required?**
   - Does it require an org-level admin key vs. a project key?
   - Is there an "Admin API" key concept similar to Anthropic's?
   - Are there scopes/permissions on API keys that control billing access?

4. **Is there a way to test billing access without making a billing call?**
   Currently `validate_credentials` uses `/v1/models` which always passes,
   giving a false sense of success. Should it also verify billing access?

### Action Plan Expected Output

Please return with:
- Confirmed correct OpenAI billing endpoint(s) as of March 2026
- Required key type and how to generate one
- Code diff for `backend/services/openai_service.py` to fix `get_usage()`
- Whether `validate_credentials()` should also validate billing scope
- Any similar issues to watch for with other providers

---

## Files Relevant to the Fix

| File | Purpose |
|------|---------|
| [`backend/services/openai_service.py`](../backend/services/openai_service.py) | OpenAI billing sync — `get_usage()` uses deprecated endpoint |
| [`backend/services/anthropic_service.py`](../backend/services/anthropic_service.py) | Anthropic sync — working correctly, just needs right key |
| [`backend/services/__init__.py`](../backend/services/__init__.py) | Service client registry |
| [`backend/jobs/sync_usage.py`](../backend/jobs/sync_usage.py) | Background scheduler + `_sync_all_accounts()` |
| [`backend/routes/accounts.py`](../backend/routes/accounts.py) | `/api/accounts/{id}/test` endpoint |
| [`docs/provider-api-research-2026.md`](provider-api-research-2026.md) | Prior research on provider APIs |

---

**Date:** 2026-03-02
**Status:** Blocked — awaiting OpenAI billing API investigation
