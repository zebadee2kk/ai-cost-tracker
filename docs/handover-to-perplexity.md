# Handover to Perplexity: AI Cost Tracker (Status + Next Steps)

## 1) Executive Summary
The project has a functional Phase 1 MVP with a Flask backend, React frontend, JWT auth, encrypted API key storage, account CRUD, usage aggregation endpoints, alerts, analytics views, and Dockerized local dev. OpenAI is the only live API sync integration today; other services are seeded/configured but not yet integrated for real ingestion.

The best next move is to execute a focused **Phase 2 integration plan**: add Anthropic, Groq, and Perplexity service clients; wire them into scheduler sync; normalize usage payloads; and expand tests for multi-service reliability.

---

## 2) Current State: What Is Already Implemented

### Backend (complete MVP surface)
- Flask app factory with CORS, JWT setup, migrations, health endpoint, and common error handlers.
- SQLAlchemy models for users, services, accounts, usage records, alerts, and cost projections.
- Auth endpoints: register/login/me/logout.
- Account endpoints: list/create/get/update/delete + test connection.
- Service endpoints: list/get/update pricing.
- Usage endpoints: current month summary, paginated history, by-service aggregation, month-end forecast.
- Alert endpoints: list/create/update/delete/acknowledge.
- Encryption utility using Fernet for API keys at rest.
- OpenAI API service integration + background scheduler job for periodic sync.
- Cost calculator + alert-generation helper.
- Seed script for baseline services.

### Frontend (complete MVP UI)
- Auth context + protected routes.
- Login/register screen.
- Dashboard with overview cards, chart view, account manager, and alert panel.
- Analytics page with pie chart and forecast rendering.
- Settings page with basic account/about section.
- Axios API layer with JWT interceptors and 401 redirect behavior.

### Test coverage (baseline, backend-focused)
- Encryption utility tests.
- Auth integration tests.
- Account integration tests.
- OpenAI service parser/credential-validation tests.

---

## 3) Constraints & Assumptions To Preserve
- API credentials must remain encrypted at rest and never returned in plaintext.
- Costs in DB should stay DECIMAL-based (avoid float persistence).
- JWT remains stateless for MVP simplicity.
- Existing routes and response shapes should be backward-compatible with current frontend.

---

## 4) Gaps / Risks Identified During Review
1. **Only OpenAI has live usage sync**; Claude/Groq/Perplexity are not implemented yet.
2. **Scheduler duplication risk**: sync inserts daily records each run without visible idempotency checks, so repeated runs can duplicate usage rows for the same account/day.
3. **Minor cleanup debt in scheduler**: unused imports/variables (`ServiceError`, `tomorrow`) suggest unfinished refactor.
4. **Testing gap**: no unit/integration tests yet for usage routes, alerts routes, scheduler behavior, or dedupe behavior.
5. **Frontend/account UX**: connection test currently implemented only for ChatGPT/OpenAI accounts.
6. **Roadmap docs inconsistency**: high-level roadmap file is generic and does not reflect actual MVP completion state.

---

## 5) Recommended Next Steps (Prioritized)

### Priority A — Multi-service sync foundation (Phase 2 core)
1. Implement `AnthropicService`, `GroqService`, and `PerplexityService` in `backend/services/` using `BaseService`.
2. Define a strict normalized `get_usage()` return contract for all service clients:
   - `total_tokens`
   - `total_cost`
   - `daily[]` entries with date, tokens, cost, optional metadata
3. Expand service dispatch mapping in scheduler and account test endpoint to include new services.
4. Add robust error taxonomy for provider failures (auth error, rate limit, transient API failure).

### Priority B — Data correctness and idempotency
1. Prevent duplicate daily usage records on repeated sync:
   - Option 1: unique DB constraint (`account_id`, `service_id`, `timestamp`, `request_type`) and upsert behavior.
   - Option 2: pre-insert existence check + update.
2. Ensure scheduler writes are atomic per account (transaction block) and partial failures are logged cleanly.
3. Validate currency consistency and rounding strategy for all providers.

### Priority C — Test hardening
1. Add unit tests for each new provider parser.
2. Add integration tests for:
   - `/api/usage` endpoints with seeded records.
   - alert generation thresholds and acknowledge flow.
   - scheduler idempotency (re-running sync should not duplicate costs).
3. Add a lightweight CI matrix: lint + backend tests.

### Priority D — Product polish for MVP-to-beta
1. Implement account-level “test connection” for new service types.
2. Add manual-entry workflow for services lacking reliable billing APIs (especially Copilot/local LLMs).
3. Add CSV/JSON export route + button in analytics.
4. Improve setup docs and align `ROADMAP.md` with actual state.

---

## 6) Proposed Workplan (2 Sprints)

### Sprint 1 (Technical foundation)
- Build 3 provider clients.
- Wire into scheduler and test endpoint.
- Introduce dedupe/idempotency in usage record persistence.
- Add unit tests for provider response parsing.

**Definition of Done**
- Multi-provider sync runs successfully without duplicate usage records.
- New accounts can pass connection test for supported providers.
- Backend tests pass in CI.

### Sprint 2 (Reliability + UX)
- Expand integration tests for usage and alerts.
- Add export endpoint + frontend export action.
- Improve observability/logging around sync run outcomes.
- Documentation cleanup (README/ROADMAP/active context alignment).

**Definition of Done**
- Reliable monthly totals/forecasts across >1 provider.
- Clear docs for local setup and current capability map.

---

## 7) Questions for Perplexity Research
1. Current official billing/usage API capabilities and limitations for:
   - Anthropic
   - Groq
   - Perplexity
2. Best-practice approach when provider lacks historical billing endpoint:
   - per-request logging strategy,
   - reconciliation model,
   - confidence scoring.
3. Recommended schema strategy for cross-provider normalization while preserving provider-specific metadata.
4. Idempotent ingestion patterns for daily usage sync in Flask + SQLAlchemy + Postgres.
5. Minimal observability stack for scheduled jobs in this architecture.

---

## 8) Suggested Prompt to Give Perplexity
"Given this project state: Flask + SQLAlchemy backend with OpenAI-only usage sync and React dashboard, propose a concrete implementation design for Anthropic, Groq, and Perplexity integrations. Include exact endpoint capabilities as of now, normalized schema mapping, idempotent ingestion strategy, error/retry handling, and a testing plan with fixtures/mocks. Prioritize practical implementation in an existing codebase using APScheduler and PostgreSQL."

---

## 9) Immediate Starter Tasks for Next Engineer
1. Create provider client stubs + tests.
2. Add idempotent upsert path for daily usage records.
3. Extend account connection test dispatch by provider.
4. Add one end-to-end test that seeds usage and validates dashboard usage endpoint totals.
5. Update roadmap docs to reflect completed MVP and current Phase 2 backlog.
