# Production Readiness & Safety Audit (v1 pre-live)

Date: 2026-03-01
Scope: Full-stack configuration and backend safety posture for enabling **real provider APIs**.

---

## Executive Summary

The project is close to production-ready, but **not yet safe to go live without a small set of mandatory hardening actions**.

### Go/No-Go

- **NO-GO** until all **P0** actions below are complete.
- **GO (conditional)** once P0 actions are complete and verified in a fresh deploy.

---

## What Was Reviewed

- Backend runtime/config defaults, auth, encryption, notification/webhook handling.
- Docker/dev deployment defaults and secret handling posture.
- Frontend token handling and API behavior.
- Existing tests for auth/accounts/encryption/webhook validation.

---

## Findings

## ✅ Strengths already in place

1. **API keys are encrypted at rest** via Fernet utilities and only decrypted when needed.
2. **Accounts API does not return stored API keys**, only a boolean (`has_api_key`).
3. **JWT-protected routes** are implemented for account/user-sensitive endpoints.
4. **Webhook validation includes SSRF guardrails** (host/path allowlists + https enforcement).
5. **Notification rate limiting exists** and is configurable via environment variables.

---

## 🚨 P0 (must do before real APIs)

### P0-1) Replace all placeholder/default secrets in deployed environment

Risk:
- `SECRET_KEY` default is insecure and predictable (`change-me-in-production`).
- Default/fallback test-like values can lead to token forgery and broader compromise.

Required actions:
- Set long random values for:
  - `SECRET_KEY`
  - `JWT_SECRET_KEY` (now supported independently; recommended to set separately)
  - `ENCRYPTION_KEY`
- Ensure these are injected at runtime (not committed in git).

Verification:
- Backend logs and env inspection confirm none of these keys are fallback/default.

---

### P0-2) Remove hardcoded database credentials from production compose/deploy config

Risk:
- Compose currently uses known db credentials (`ai_user` / `ai_password`) and a fixed DB URL in service env.
- If reused in production-like infra, this is credential exposure and weak-access risk.

Required actions:
- Parameterize db credentials via environment variables or secret manager.
- Do not keep production credentials in `docker-compose.yml`.
- Rotate any credentials that were already used in deployed environments.

Verification:
- `docker-compose.yml` (or deployment manifests) reference `${...}` env vars for DB creds.

---

### P0-3) Force HTTPS/TLS and secure origin configuration

Risk:
- Frontend and backend defaults are localhost/http oriented; production with mixed/insecure origins risks token interception.

Required actions:
- Serve frontend over HTTPS only.
- Serve backend over HTTPS or behind TLS-terminating reverse proxy.
- Restrict `CORS_ORIGINS` to explicit production origin(s) only.

Verification:
- Browser network confirms HTTPS for frontend and API requests.
- CORS allows only approved domain(s).

---

### P0-4) Confirm Anthropic key type for live sync

Risk:
- Anthropic usage sync requires **Admin API key** (`sk-ant-admin...`), not standard inference key.
- Live rollout can silently fail if wrong key type is entered.

Required actions:
- For Anthropic accounts, use org-level admin key only.
- Add onboarding note in operator runbook so this is explicit.

Verification:
- Run `/api/accounts/{id}/test` for Anthropic account and confirm success.

---

## ⚠️ P1 (strongly recommended in next hardening pass)

### P1-1) Split JWT secret from Flask secret everywhere

Status:
- Code now supports dedicated `JWT_SECRET_KEY` env var fallbacking to `SECRET_KEY`.

Action:
- Set separate values in production immediately.

---

### P1-2) Add startup fail-fast checks in production mode

Current:
- Missing `ENCRYPTION_KEY` logs warning; app still starts.

Recommendation:
- In production, hard-fail startup if any required secrets are missing/default:
  - `SECRET_KEY`
  - `JWT_SECRET_KEY`
  - `ENCRYPTION_KEY`

---

### P1-3) Harden token storage strategy (frontend)

Current:
- JWT stored in `localStorage`, vulnerable to exfiltration if XSS is introduced.

Recommendation:
- Move to secure HttpOnly cookie-based session/JWT strategy when possible.
- At minimum, add CSP + dependency hygiene + strict sanitization review.

---

### P1-4) Align test runner/module import behavior in CI

Current:
- Full `pytest` run in this environment reports many import/setup errors (`from app import create_app`).

Recommendation:
- Standardize test invocation (`python -m pytest`) and module path config in CI.
- Add a lightweight smoke test workflow that blocks merges on app import + critical route checks.

---

## Operational Checklist Before Enabling Real APIs

1. [ ] Generate and set production secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`).
2. [ ] Move DB creds and app secrets to secret manager / secure env injection.
3. [ ] Rotate any credentials that were used with defaults.
4. [ ] Restrict CORS to exact production frontend origin.
5. [ ] Confirm HTTPS end-to-end.
6. [ ] Verify provider creds using `/api/accounts/{id}/test` for each configured account.
7. [ ] Run targeted regression tests for auth/accounts/encryption/webhook validation.
8. [ ] Execute one full sync job in staging-like production env and verify logs/metrics.

---

## Evidence Collected During This Audit

- Reviewed code paths for config/auth/encryption/accounts/services/notifications/webhook validation.
- Ran targeted backend tests successfully:
  - `python -m pytest tests/test_encryption.py -q`
  - `python -m pytest tests/test_auth.py tests/test_accounts.py tests/test_webhook_validator.py -q`
- Full suite invocation in this environment has import/setup issues that should be addressed in CI standardization.

---

## Notes for Claude Code Follow-up

If follow-up coding is requested, prioritize this exact order:

1. ✅ Add production fail-fast guardrails for missing/default secrets.
   — `validate_production_secrets()` in `config.py`, called from `create_app()` when `FLASK_ENV=production`
2. ✅ Parameterize DB credentials and document secure production `.env` contract.
   — `docker-compose.yml` uses `${POSTGRES_USER:-ai_user}` etc.; `.env.example` updated
3. ✅ Add/verify deployment docs for HTTPS + strict CORS.
   — `docs/production-deployment.md` created (Caddy + nginx, CORS guidance, go-live checklist)
4. ✅ Stabilize CI test invocation/import path.
   — CI now uses `python -m pytest`; `JWT_SECRET_KEY` added to CI env

**All follow-up items resolved:** 2026-03-01 (Claude Code)

