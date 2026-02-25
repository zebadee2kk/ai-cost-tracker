# AI Cost Tracker

> A unified dashboard to track usage and costs across multiple AI services: OpenAI/ChatGPT, Anthropic Claude, Groq, Perplexity, and more. Monitor token consumption, costs, and usage patterns in real-time.

[![CI/CD](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/zebadee2kk/ai-cost-tracker/branch/main/graph/badge.svg)](https://codecov.io/gh/zebadee2kk/ai-cost-tracker)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Phase](https://img.shields.io/badge/Phase-3%20In%20Progress-blue)](ROADMAP.md)

---

## 🎯 Project Overview

**Problem**: Developers using multiple AI services face scattered usage data, difficulty tracking costs, and risk of exceeding budgets without warning.

**Solution**: AI Cost Tracker provides a centralized dashboard that:
- ✅ Aggregates usage data from multiple AI services automatically
- ✅ Tracks token consumption and costs in real-time
- ✅ Alerts you when approaching spending limits
- ✅ Projects monthly costs based on current usage
- ✅ Supports both API-based sync and manual data entry

---

## ✨ Features

### Phase 1 (Live)

- ✅ OpenAI/ChatGPT automatic usage sync via billing API
- ✅ Real-time and historical usage visualization
- ✅ Cost calculation, month-end forecasting
- ✅ Encrypted API key storage (AES-256 Fernet)
- ✅ JWT authentication and protected routes
- ✅ Alert system with threshold monitoring
- ✅ Docker Compose deployment

### Phase 2 (Complete — Feb 2026)

- ✅ **Anthropic Claude** automatic sync via Admin API
- ✅ **Manual entry** system for Groq, Perplexity, and any service without an API
- ✅ **Idempotent data ingestion** — no duplicate records on repeated syncs
- ✅ Scheduler duplicate-run prevention (Flask debug mode safe)
- ✅ `source` field distinguishing API vs. manual entries

### Phase 3 (Planned)

- 📋 CSV/JSON export
- 📋 Email/webhook alert notifications
- 📋 Usage anomaly detection
- 📋 Multi-user support (teams)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** and **Node.js 18+**
- **PostgreSQL 12+** (or SQLite for development/testing)
- **Docker & Docker Compose** (recommended)

### Option A — Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/zebadee2kk/ai-cost-tracker.git
cd ai-cost-tracker

# 2. Generate required secrets
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# 3. Configure environment
cp .env.example .env
# Paste the generated values into .env

# 4. Start all services
docker-compose up -d

# 5. Apply database migrations (includes Phase 2 idempotency constraint)
docker-compose exec backend flask db upgrade

# 6. Seed initial service data
docker-compose exec backend python scripts/seed_services.py
```

App is available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Health check**: http://localhost:5000/api/health

### Option B — Manual Setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
flask db upgrade          # applies all migrations incl. Phase 2
python scripts/seed_services.py
flask run                 # http://localhost:5000

# Frontend (new terminal)
cd frontend
npm install && npm start  # http://localhost:3000
```

See [docs/setup-quickstart.md](docs/setup-quickstart.md) for full details.

---

## 🤖 Adding AI Service Accounts

### OpenAI / ChatGPT

1. Dashboard → Add Account → select **ChatGPT**
2. Paste your OpenAI API key (`sk-...`)
3. Set optional monthly limit → Save
4. Usage syncs automatically every hour

### Anthropic Claude (Admin API required)

> **Important**: Anthropic's usage reporting requires an **Admin API key**, not a standard API key.

1. In the [Anthropic Console](https://console.anthropic.com), go to **Settings → Organization → Admin API Keys**
2. Create a new Admin key (format: `sk-ant-admin-...`)
3. Dashboard → Add Account → select **Anthropic**
4. Paste the Admin key → Save
5. Usage syncs automatically every hour

**Troubleshooting Anthropic:**
- `AuthenticationError: requires Admin API key` → You're using a standard key (`sk-ant-api-...`). Generate an Admin key instead.
- `403 Forbidden` → Your Anthropic account may not be an organization account. Admin API requires organization access.
- No data returned → Check the date range; data has a ~5 minute delay.

### Groq (Manual Entry)

Groq does not provide a programmatic billing API. To track Groq costs:

1. Dashboard → Add Account → select **Groq** (no API key needed)
2. Check your [Groq Console](https://console.groq.com) → **Dashboard → Usage**
3. Dashboard → select your Groq account → **Add Manual Entry**
4. Enter the date, cost from your dashboard, and optional token count
5. Repeat monthly or as needed

### Perplexity (Manual Entry)

Perplexity does not provide a programmatic billing API. To track Perplexity costs:

1. Dashboard → Add Account → select **Perplexity** (no API key needed)
2. In the [Perplexity portal](https://www.perplexity.ai/settings/api), go to **Settings → Usage Metrics → Invoice history**
3. Click an invoice to see per-key usage
4. Dashboard → select your Perplexity account → **Add Manual Entry**
5. Enter the date and cost from the invoice

---

## 🎯 Supported AI Services

| Service | Status | Tracking Method | Notes |
|---------|--------|-----------------|-------|
| **OpenAI / ChatGPT** | ✅ Live | Automatic API sync | GPT-4, GPT-5.1, embeddings |
| **Anthropic Claude** | ✅ Live | Automatic API sync | Requires Admin API key (`sk-ant-admin-...`) |
| **Groq** | ✅ Live | Manual entry | No billing API; dashboard-only |
| **Perplexity** | ✅ Live | Manual entry | No billing API; invoice tracking |
| **GitHub Copilot** | 📋 Planned | Manual entry | No usage API available |
| **Local LLMs** | 📋 Planned | Manual entry | Ollama, LM Studio, etc. |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│          Frontend (React Dashboard)                 │
│  Auth Context · Dashboard · Analytics · Settings   │
│  AccountManager · ManualEntryModal · AlertPanel    │
└──────────────────┬──────────────────────────────────┘
                   │ Axios + JWT
                   ↓
┌─────────────────────────────────────────────────────┐
│          Backend API (Flask)                        │
│  /api/auth   /api/accounts   /api/usage            │
│  /api/usage/manual   /api/services   /api/alerts   │
└──────┬───────────────────────────────┬──────────────┘
       │                               │
  PostgreSQL                   APScheduler (hourly)
  SQLAlchemy                    → upsert_usage_record()
  Alembic migrations            → OpenAIService
  Fernet encryption             → AnthropicService
```

**Tech stack**: Flask · SQLAlchemy · APScheduler · Flask-JWT-Extended · React 18 · Axios · Chart.js · Docker

---

## 🛠️ Development

### Project Structure

```
ai-cost-tracker/
├── backend/
│   ├── models/           # UsageRecord (+ source/updated_at), Account, Service, ...
│   ├── routes/           # usage.py (incl. /manual CRUD), accounts.py, auth.py, ...
│   ├── services/         # base_service.py, openai_service.py, anthropic_service.py
│   ├── jobs/             # sync_usage.py (upsert_usage_record, scheduler)
│   ├── migrations/       # Alembic — incl. a1b2c3d4e5f6 idempotency constraint
│   ├── tests/            # test_anthropic_service.py, test_idempotent_upsert.py, ...
│   └── utils/            # encryption.py, cost_calculator.py, alert_generator.py
├── frontend/src/
│   ├── components/       # ManualEntryModal.jsx, AccountManager.jsx, ...
│   ├── pages/            # DashboardPage, AnalyticsPage, LoginPage, SettingsPage
│   └── services/         # api.js (incl. createManualEntry, updateManualEntry, ...)
├── docs/                 # Handover docs, research, playbooks
└── docker-compose.yml
```

### Running Tests

```bash
cd backend
pytest tests/ -v                          # run all tests
pytest tests/test_anthropic_service.py -v # Anthropic service unit tests
pytest tests/test_idempotent_upsert.py -v # idempotency integration tests
pytest tests/ --cov=. --cov-report=html   # coverage report
```

**Current status**: 44/47 tests pass (3 pre-existing failures in `test_accounts.py` due to a hardcoded service name in the test helper — unrelated to Phase 2).

### Database Migrations

```bash
# Apply all migrations (including Phase 2 idempotency constraint)
flask db upgrade

# Check migration history
flask db history

# Create a new migration after model changes
flask db migrate -m "description"

# Roll back one migration
flask db downgrade
```

### Key Implementation Notes

**Idempotent upsert** (`jobs/sync_usage.py:upsert_usage_record`):
- Uses `ON CONFLICT DO UPDATE` on PostgreSQL (production)
- Falls back to check-then-update for SQLite (test environment)
- Unique key: `(account_id, service_id, timestamp, request_type)`
- Timestamps are always normalized to midnight UTC for daily records

**Scheduler duplicate prevention** (`jobs/sync_usage.py:start_scheduler`):
- Checks `WERKZEUG_RUN_MAIN == 'true'` before starting in debug mode
- Prevents the Flask reloader's parent process from running a second scheduler instance

**Anthropic Admin API key** (`services/anthropic_service.py`):
- Validated in constructor: must start with `sk-ant-admin`
- Raises `AuthenticationError` (not `ServiceError`) on wrong key type
- Fetches paginated usage from `/v1/organizations/usage_report/messages`
- Estimates costs using per-model pricing with cache-token support

---

## 📋 Current Status (February 2026)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: MVP | ✅ Complete | OpenAI sync, dashboard, auth, alerts |
| Phase 2: Multi-service | ✅ Complete | Anthropic API sync + manual entry for Groq/Perplexity |
| Phase 3: Export & Alerts | 📋 Planned | CSV export, webhooks, anomaly detection |

See [ROADMAP.md](ROADMAP.md) for full details.

---

## 🔐 Security

- **API Keys**: Encrypted at rest using AES-256 Fernet
- **Authentication**: JWT tokens (1-hour expiry by default)
- **Password Hashing**: bcrypt
- **CORS**: Configured for frontend/backend separation
- **Ownership checks**: All usage endpoints verify the requesting user owns the account
- **Environment Secrets**: Never committed to git (use `.env`)

---

## 🤝 Contributing

This is an AI-native project built collaboratively by:
- **Codex**: Phase 1 MVP implementation
- **Perplexity**: Research and API capability analysis
- **Claude Code**: Phase 2 implementation

Pull requests welcome. Please add tests for new features and ensure the existing test suite passes.

---

## 📝 License

MIT — see [LICENSE](LICENSE).

---

## 👤 Author

**Richard Ham** ([@zebadee2kk](https://github.com/zebadee2kk)) — IT Director, Cybersecurity Leader, London UK.

---

**Built with ❤️ for developers who want to understand their AI spending.**

**Status**: 🟢 Active Development | Phase 2 Complete | Production-Ready
