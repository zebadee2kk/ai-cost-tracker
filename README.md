# AI Cost Tracker

> A unified dashboard to track usage and costs across multiple AI services: OpenAI/ChatGPT, Anthropic Claude, Groq, Perplexity, and more. Monitor token consumption, costs, and usage patterns in real-time with automated alerts.

[![CI/CD](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/zebadee2kk/ai-cost-tracker/branch/main/graph/badge.svg)](https://codecov.io/gh/zebadee2kk/ai-cost-tracker)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Phase](https://img.shields.io/badge/Phase-3%20Sprint%202%20Complete-brightgreen)](docs/phase3-status.md)

---

## 🎯 Project Overview

**Problem**: Developers using multiple AI services face scattered usage data, difficulty tracking costs, and risk of exceeding budgets without warning.

**Solution**: AI Cost Tracker provides a centralized dashboard that:
- ✅ Aggregates usage data from multiple AI services automatically
- ✅ Tracks token consumption and costs in real-time
- ✅ Alerts you when approaching spending limits via email and Slack
- ✅ Projects monthly costs based on current usage
- ✅ Exports data in CSV/JSON formats
- ✅ Supports both API-based sync and manual data entry
- ✅ Provides visual indicators to distinguish API vs manual entries

---

## ✨ Features

### Phase 1 (Complete — Dec 2025)

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

### Phase 3 (In Progress — Feb 2026)

#### ✅ Sprint 1 — Data Export & Visualization (Complete)
- ✅ **CSV/JSON Export**: Streaming endpoint with date/service/account filtering
- ✅ **Visual Source Indicators**: Color-coded badges and chart styling for API vs Manual data
- ✅ **Source Filtering**: Toggle between All/API Only/Manual Only views

#### ✅ Sprint 2 — Advanced Alerts & Notifications (Complete - Feb 27, 2026)
- ✅ **Database Models**: notification_preferences, notification_queue, notification_history
- ✅ **Email Notifications**: SendGrid integration with HTML templates (budget/anomaly/system alerts)
- ✅ **Slack Notifications**: Webhook support with Block Kit formatting
- ✅ **Discord/Teams Support**: Webhook validation for multiple channels
- ✅ **Rate Limiting**: Per-user, per-channel hourly and daily limits (10/hour email, 20/hour Slack)
- ✅ **CI/CD Pipeline**: GitHub Actions with automated testing, security scanning, Docker builds
- ✅ **Notification API**: REST endpoints for preferences, queue, history, testing, rate-limits
- ✅ **Background Processor**: APScheduler-based dispatcher (every 5 min)
- ✅ **Alert Integration**: Budget thresholds (70%, 90%, 100%) trigger notifications
- ✅ **Frontend UI**: NotificationSettingsPage with channel configuration
- ✅ **Security Hardening**: SSRF protection, N+1 query elimination, input validation

#### 📋 Sprint 3 — Advanced Analytics (Planned - March 2026)
- 📋 Cost anomaly detection with statistical models
- 📋 Usage trend analysis and forecasting
- 📋 Multi-user support with team dashboards
- 📋 Custom report scheduling

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
# Edit .env and add:
# - Generated ENCRYPTION_KEY and SECRET_KEY
# - SENDGRID_API_KEY (for email notifications)
# - SLACK_WEBHOOK_URL (for Slack notifications)

# 4. Start all services
docker-compose up -d

# 5. Apply database migrations (includes Phase 3 notification tables)
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
flask db upgrade          # applies all migrations incl. Phase 3
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

## 📊 Data Export

Export your usage data for external analysis:

1. Navigate to **Dashboard → History** tab
2. Select **Export** format (CSV or JSON)
3. Filter by date range, service, account, or data source (API/Manual)
4. Click **Download** — file streams directly to your browser

**Features:**
- Streaming downloads (handles large datasets efficiently)
- UTF-8 BOM for Excel compatibility (CSV)
- Comprehensive metadata (service, account, source, timestamps)

---

## 🔔 Notification Settings

Configure alerts to stay informed about your AI spending:

### Email Notifications (SendGrid)

1. Add `SENDGRID_API_KEY` to your `.env` file
2. Configure sender: `SENDGRID_FROM_EMAIL` and `SENDGRID_FROM_NAME`
3. Dashboard → Settings → Notifications → Enable Email
4. Set alert thresholds (budget warnings, anomaly detection)

### Slack Notifications

1. Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) in your Slack workspace
2. Add `SLACK_WEBHOOK_URL` to your `.env` file
3. Dashboard → Settings → Notifications → Enable Slack
4. Alerts post to your configured channel with interactive buttons

**Alert Types:**
- **Budget Alerts**: Warning (70%), Critical (90%), Emergency (100%)
- **Anomaly Alerts**: Unusual spending patterns detected
- **System Alerts**: Sync failures, integration errors

**Rate Limits (configurable):**
- Email: 10/hour, 50/day per user
- Slack: 20/hour, 100/day per user

**Security Features:**
- SSRF protection with webhook URL validation
- Strict allowlists for Slack, Discord, Teams webhooks
- HTTPS-only webhook URLs

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
│  Auth · Dashboard · Analytics · Settings           │
│  Export · Notifications · Source Filtering         │
└──────────────────┬──────────────────────────────────┘
                   │ Axios + JWT
                   ↓
┌─────────────────────────────────────────────────────┐
│          Backend API (Flask)                        │
│  /api/auth   /api/accounts   /api/usage            │
│  /api/usage/manual   /api/usage/export             │
│  /api/services   /api/alerts                       │
│  /api/notifications (complete)                     │
└──────┬──────────────────────────────┬───────────────┘
       │                              │
  PostgreSQL                   APScheduler (every 5 min)
  + notification tables         → sync_usage_job
  + rate limiting               → notification_processor
  SQLAlchemy ORM                → OpenAIService
  Alembic migrations            → AnthropicService
  Fernet encryption             → EmailSender
                                → SlackSender
```

**Tech Stack:**
- **Backend**: Flask · SQLAlchemy · APScheduler · Flask-JWT-Extended · SendGrid · Requests
- **Frontend**: React 18 · Axios · Chart.js · React Router
- **Database**: PostgreSQL (production) · SQLite (testing)
- **CI/CD**: GitHub Actions · Codecov · Trivy · Bandit · Docker Hub
- **Deployment**: Docker · Docker Compose

---

## 🛠️ Development

### Project Structure

```
ai-cost-tracker/
├── backend/
│   ├── models/           # User, Account, Service, UsageRecord, Notification*
│   ├── routes/           # auth, accounts, usage, services, alerts, notifications
│   ├── services/
│   │   ├── api/          # openai_service, anthropic_service
│   │   └── notifications/ # email_sender, slack_sender, rate_limiter
│   ├── jobs/             # sync_usage, notification_processor
│   ├── migrations/       # Alembic (Phase 1-3 schemas)
│   ├── tests/            # 121+ passing tests
│   └── utils/            # encryption, cost_calculator, alert_generator, webhook_validator
├── frontend/src/
│   ├── components/       # ExportButton, SourceBadge, SourceFilter, Modals
│   ├── pages/            # Dashboard, Analytics, Login, Settings, NotificationSettings
│   └── services/         # api.js (HTTP client)
├── docs/
│   ├── phase3-roadmap.md               # Full Phase 3 plan
│   ├── phase3-status.md                # Sprint tracking
│   ├── phase3-ci-guide.md              # CI/CD documentation
│   ├── phase3-notifications-spec.md    # Notification system spec
│   ├── sprint-2-retrospective.md       # Sprint 2 lessons learned
│   ├── pr-17-code-review-results.md    # QA findings
│   └── pr-20-remediation-verification.md # Security verification
├── .github/workflows/
│   └── ci.yml            # Automated testing, security, Docker builds
└── docker-compose.yml
```

### Running Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test suites
pytest tests/test_export.py -v                   # Export endpoints
pytest tests/test_email_sender.py -v             # Email notifications
pytest tests/test_slack_sender.py -v             # Slack notifications
pytest tests/test_webhook_validator.py -v        # Security validation
pytest tests/test_notification_processor.py -v   # Background processor
pytest tests/test_notifications_api.py -v        # Notification API
pytest tests/test_anthropic_service.py -v        # Anthropic sync
pytest tests/test_idempotent_upsert.py -v        # Data integrity
```

**Frontend tests:**
```bash
cd frontend
npm test                    # Run all Jest tests
npm test -- --coverage      # With coverage report
```

### Database Migrations

```bash
# Apply all migrations (includes Phase 3 notification tables)
flask db upgrade

# Check migration history
flask db history

# Create a new migration after model changes
flask db migrate -m "description"

# Roll back one migration
flask db downgrade
```

### CI/CD Pipeline

Every push triggers:
1. **Backend Tests**: pytest with PostgreSQL service, 80% coverage threshold
2. **Frontend Tests**: Jest with 70% coverage threshold
3. **Security Scans**: Bandit (Python), npm audit (JS), Trivy (Docker)
4. **Coverage Upload**: Results sent to Codecov
5. **Docker Builds**: Images pushed to Docker Hub (main branch only)

**Required Secrets** (GitHub repository settings):
- `CODECOV_TOKEN`: Coverage reporting
- `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`: Image publishing
- `SLACK_WEBHOOK_URL`: CI failure notifications (optional)

### Key Implementation Notes

**Idempotent Upsert** (`jobs/sync_usage.py`):
- Uses `ON CONFLICT DO UPDATE` on PostgreSQL
- Unique constraint: `(account_id, service_id, timestamp, request_type)`
- Timestamps normalized to midnight UTC for daily records
- Prevents duplicate data on repeated syncs

**Notification Rate Limiting** (`services/notifications/rate_limiter.py`):
- Per-user, per-channel limits enforced via `notification_history` table
- Configurable hourly/daily thresholds in `.env`
- `get_remaining()` method for UI quota displays

**Export Streaming** (`routes/usage.py`):
- Generator pattern with `yield_per(500)` cursor
- X-Accel-Buffering header for nginx compatibility
- Handles datasets of any size without memory issues

**Webhook Security** (`utils/webhook_validator.py`):
- SSRF protection with strict allowlists
- Slack: `hooks.slack.com/services/*` only
- Discord: `discord.com/api/webhooks/*` only
- Teams: `*.webhook.office.com/*` only
- HTTPS-only enforcement

---

## 📋 Current Status (February 27, 2026)

| Phase | Status | Completion | Notes |
|-------|--------|------------|-------|
| Phase 1: MVP | ✅ Complete | 100% | OpenAI sync, dashboard, auth, alerts |
| Phase 2: Multi-service | ✅ Complete | 100% | Anthropic API + manual entry system |
| Phase 3: Export & Alerts | 🔨 Active | 70% | Sprint 1 ✅, Sprint 2 ✅, Sprint 3 📋 |

**Recent Milestones:**
- **Feb 27, 2026** — 🎉 **Sprint 2 COMPLETE**: Full notification system delivered 7 days ahead of schedule
- **Feb 27, 2026** — Security hardening complete: SSRF + N+1 query issues resolved
- **Feb 26, 2026** — Notification API and background processor operational
- **Feb 25, 2026** — CI/CD pipeline deployed with automated testing and security scanning
- **Feb 25, 2026** — Sprint 1 complete: CSV/JSON export, visual source indicators
- **Feb 2026** — Phase 2 complete: Anthropic Claude integration, manual entry system

**Sprint 2 Achievement Summary:**
- 8 PRs merged (PRs #14-21)
- 119+ new tests added
- 3 security issues found and fixed
- ~3,000+ lines of code added
- 100% QA approval rate

**Next Up (Sprint 3 - Starting March 2):**
- Cost anomaly detection
- Usage trend forecasting
- Multi-user support with teams
- Custom report scheduling

See [docs/phase3-status.md](docs/phase3-status.md) for live progress tracking and [docs/sprint-2-retrospective.md](docs/sprint-2-retrospective.md) for detailed lessons learned.

---

## 📚 Documentation

- [Phase 3 Roadmap](docs/phase3-roadmap.md) — Feature specifications and timeline
- [Phase 3 Status](docs/phase3-status.md) — Sprint progress and blockers
- [Sprint 2 Retrospective](docs/sprint-2-retrospective.md) — Lessons learned and metrics
- [CI/CD Guide](docs/phase3-ci-guide.md) — Testing, security, deployment
- [Notification Spec](docs/phase3-notifications-spec.md) — Alert system architecture
- [PR #17 Code Review](docs/pr-17-code-review-results.md) — Security findings
- [PR #20 Verification](docs/pr-20-remediation-verification.md) — Security verification
- [Setup Quickstart](docs/setup-quickstart.md) — Installation and configuration

---

## 🔐 Security

- **API Keys**: Encrypted at rest using AES-256 Fernet
- **Authentication**: JWT tokens (1-hour expiry by default)
- **Password Hashing**: bcrypt
- **CORS**: Configured for frontend/backend separation
- **Ownership Checks**: All endpoints verify user permissions
- **Security Scanning**: Automated Bandit + npm audit in CI/CD
- **Dependency Updates**: Trivy scans for vulnerable packages
- **SSRF Protection**: Webhook URL validation with strict allowlists
- **Input Validation**: Defensive parsing prevents injection attacks
- **Environment Secrets**: Never committed to git (use `.env`)

**Security Audit Trail:**
- Feb 27, 2026: SSRF vulnerability identified and fixed (PR #20)
- Feb 27, 2026: N+1 query issue identified and fixed (PR #20)
- Feb 27, 2026: Input validation hardened (PR #20)
- All findings verified by Codex QA (PR #21)

**Vulnerability Disclosure**: Please report security issues to the repository owner privately.

---

## 🤝 Contributing

This is an **AI-native project** built collaboratively by multiple AI agents:

| Agent | Role | Contributions |
|-------|------|---------------|
| **Codex** (ChatGPT) | Initial Implementation | Phase 1 MVP, Phase 2 multi-service support |
| **Perplexity** | Research & Planning | API analysis, roadmap planning, documentation |
| **Claude Code** | Feature Development | Phase 3 export, notifications, CI/CD pipeline, security fixes |
| **Codex** | Quality Assurance | PR reviews, security audits, testing |

**Human oversight**: Richard Ham ([@zebadee2kk](https://github.com/zebadee2kk)) — Project management and architecture decisions

### How to Contribute

Pull requests welcome! Please:
1. Add tests for new features (pytest for backend, Jest for frontend)
2. Ensure existing test suite passes (`pytest tests/` and `npm test`)
3. Update documentation in `docs/` for significant changes
4. Follow the existing code style (Black for Python, ESLint for JavaScript)
5. Add yourself to the contributors list in this README

---

## 🗺️ Roadmap

### ✅ Phase 1 — MVP (Complete)
OpenAI integration, core dashboard, authentication, basic alerts

### ✅ Phase 2 — Multi-Service (Complete)
Anthropic Claude, manual entry system, idempotent data sync

### 🔨 Phase 3 — Export & Advanced Alerts (70% Complete)
- ✅ Sprint 1: CSV/JSON export with streaming, visual source indicators
- ✅ Sprint 2: Complete notification system (email, Slack, Discord, Teams), CI/CD, security hardening
- 📋 Sprint 3: Anomaly detection, usage forecasting, multi-user support, custom reports

### 📋 Phase 4 — Analytics & Teams (Planned)
- Advanced ML-based anomaly detection
- Predictive cost modeling
- Team dashboards with role-based access
- Custom report templates
- Webhook integrations for third-party tools

See [docs/phase3-roadmap.md](docs/phase3-roadmap.md) for detailed specifications.

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Richard Ham** ([@zebadee2kk](https://github.com/zebadee2kk))  
IT Director | Cybersecurity Leader | London, UK

**Connect:**
- GitHub: [@zebadee2kk](https://github.com/zebadee2kk)
- LinkedIn: [Richard Ham](https://www.linkedin.com/in/richard-ham/)

---

## 🙏 Acknowledgments

- **OpenAI** for the ChatGPT API and GPT models
- **Anthropic** for Claude AI and usage reporting APIs
- **SendGrid** for reliable email delivery infrastructure
- **Slack** for webhook-based notification support
- **Codecov** for test coverage reporting
- The open-source community for the excellent tools that power this project
- All the AI agents who collaborated on this project

---

**Built with ❤️ for developers who want to understand and control their AI spending.**

**Status**: 🟢 Active Development | Phase 3 Sprint 2 Complete | Production-Ready

**Last Updated**: February 27, 2026
