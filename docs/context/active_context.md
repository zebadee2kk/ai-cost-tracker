# Active Context & Scratchpad

## 📝 Current Focus
- [x] Phase 1 MVP — complete (all 51 files created, 2026-02-25)
- [ ] Phase 2 — Anthropic, Groq, Perplexity service integrations
- [ ] Phase 2 — Wire new services into sync job
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

### Key architectural decisions
- SQLite for dev/MVP, PostgreSQL for production (DATABASE_URL env switch)
- Stateless JWT (no server-side sessions) — logout handled client-side
- API keys NEVER returned in responses; `has_api_key` boolean flag used instead
- OpenAI billing API returns cost in cents — divided by 100 in `openai_service.py`
- Background sync is opt-in: call `start_scheduler(app)` to enable
- Base service class handles retry/backoff; all service clients inherit from it

### File structure
```
backend/
├── app.py              Flask app factory
├── config.py           Dev/Prod/Test configs
├── requirements.txt
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
