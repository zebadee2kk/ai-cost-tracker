# Active Context & Scratchpad

## 📝 Current Focus
- [x] Phase 1 MVP — complete and **running locally** (2026-02-25)
- [x] Runtime bugs fixed — app verified working end-to-end
- [x] npm vulnerabilities resolved — 0 vulnerabilities (2026-02-25)
- [x] Local dev environment cleaned up — processes stopped, venv + node_modules removed (2026-02-25)
- [x] Phase 2 — Anthropic service — Admin API with diagnostic logging (2026-03-02)
- [x] Phase 2 — Groq service — per-request tracking + rate limits + timing (2026-03-02)
- [ ] Phase 2 — Perplexity service — per-request logging + cost calc **← NEXT**
- [ ] Phase 2 — Wire new services into sync job
- [ ] Phase 2 — Add local LLM services (Ollama etc.) as manual-tracking entries
- [ ] Phase 3 — Email/webhook alerts, CSV export

## 🧠 Memory Bank

### What was built in Phase 1
- Full Flask backend: auth (JWT), accounts, services, usage, alerts routes
- 6 SQLAlchemy models with DECIMAL(10,4) cost precision and timezone-aware timestamps
- AES-256 Fernet encryption for all API keys at rest (ENCRYPTION_KEY env var)
- OpenAI billing API integration with exponential backoff retry
- APScheduler background sync job (configurable interval, default 60 min)
- Auto alert generation at 80% / 100% of monthly limit
- React 18 frontend: Dashboard, Analytics (pie chart + forecast), Login, Settings
- Chart.js bar chart (30-day daily cost) and pie chart (cost by service)
- Docker Compose + Dockerfiles for full-stack local dev
- DB seed script: 5 services (ChatGPT, Claude, Groq, GitHub Copilot, Perplexity)
- Unit tests: encryption roundtrip, auth endpoints, account CRUD, OpenAI service mock

### Runtime bugs fixed during first launch (2026-02-25)
1. **`metadata` column name conflict** — SQLAlchemy's Declarative API reserves the name
   `metadata` internally. Renamed Python attribute to `extra_data` while keeping the DB
   column name as `metadata` via `db.Column("metadata", db.JSON, ...)`.
   Affected: `models/usage_record.py`, `jobs/sync_usage.py`.

2. **Python 3.10+ union type syntax** — `BackgroundScheduler | None` is not valid in
   Python 3.9. Changed to `Optional[BackgroundScheduler]` from `typing`.
   Affected: `jobs/sync_usage.py`.

3. **pip not available outside venv** — Homebrew Python 3.11 had a broken pip install
   in the global environment. Resolved by always using `python3.11 -m venv` first;
   pip works correctly inside the venv.

4. **Node.js installation** — `brew install node` / `node@20` repeatedly crashed on
   macOS 13 (Ventura) because it tried to compile Python 3.13 as a dependency.
   Resolved by installing Node via **nvm** (pre-built binary, no compilation):
   `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash`
   then `. ~/.nvm/nvm.sh && nvm install 20`.

### Key architectural decisions
- SQLite for dev/MVP, PostgreSQL for production (DATABASE_URL env switch)
- Stateless JWT (no server-side sessions) — logout handled client-side
- API keys NEVER returned in responses; `has_api_key` boolean flag used instead
- OpenAI billing API returns cost in cents — divided by 100 in `openai_service.py`
- Background sync is opt-in: call `start_scheduler(app)` to enable
- Base service class handles retry/backoff; all service clients inherit from it

### Service integration status
| Service        | Key storage | Usage sync | Notes                                           |
|---------------|-------------|------------|-------------------------------------------------|
| ChatGPT        | ✅ encrypted | ✅ live    | OpenAI billing API                              |
| Claude         | ✅ encrypted | ✅ live    | Anthropic Admin API (`sk-ant-admin-`)           |
| Groq           | ✅ encrypted | ✅ live    | Per-request via `call_with_tracking()` — **DONE 2026-03-02** |
| Perplexity     | ✅ encrypted | ❌ Phase 2 | Per-request logging + cost calc — **NEXT**      |
| GitHub Copilot | ✅ encrypted | ❌ Phase 2 | Manual / subscription tracking                  |
| Local LLMs     | ❌ not seeded | ❌ Phase 2 | Ollama etc. — to be added                      |

### How to restart the app (local dev)
```bash
# Terminal 1 — Backend
cd /path/to/ai-cost-tracker/backend
FLASK_APP=app.py venv/bin/flask run --host=127.0.0.1 --port=5000

# Terminal 2 — Frontend
cd /path/to/ai-cost-tracker/frontend
. ~/.nvm/nvm.sh && npm start
```

### File structure
```
backend/
├── app.py              Flask app factory
├── config.py           Dev/Prod/Test configs
├── requirements.txt
├── migrations/         Alembic migrations (generated on first run)
├── models/             User, Service, Account, UsageRecord, Alert, CostProjection
├── routes/             auth, accounts, services, usage, alerts
├── services/           base_service, openai_service
├── utils/              encryption, cost_calculator, validators, alert_generator
├── jobs/               sync_usage (APScheduler)
├── scripts/            seed_services.py
├── tests/              conftest, test_encryption, test_auth, test_accounts, test_openai_service
└── Dockerfile
frontend/
├── src/
│   ├── App.jsx         Auth context + routing
│   ├── pages/          LoginPage, DashboardPage, AnalyticsPage, SettingsPage
│   ├── components/     OverviewCard, UsageChart, AccountManager, AlertPanel
│   ├── services/       api.js (Axios + JWT interceptors)
│   └── styles/         index.css (dark theme CSS variables)
├── package.json
├── Dockerfile
└── nginx.conf
```

## 🚫 Constraints & Rules
- No external dependencies without approval
- API keys must always be encrypted before DB insert
- Never log or return plaintext API keys
- Costs stored as DECIMAL(10,4), never float in DB
