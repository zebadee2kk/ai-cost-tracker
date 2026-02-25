# AI Cost Tracker

> A comprehensive dashboard to track and manage usage across multiple AI tools including ChatGPT, Claude, Groq, GitHub Copilot, Perplexity, and more. Monitor token consumption, session limits, costs, and usage patterns in real-time.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

---

## 🎯 Project Overview

**Problem**: As developers using multiple AI coding assistants, we face:
- Scattered usage data across different platforms
- Difficulty tracking costs and token consumption
- No unified view of session limits and quotas
- Risk of exceeding budgets without warning

**Solution**: AI Cost Tracker provides a centralized dashboard that:
- Aggregates usage data from multiple AI services
- Tracks token consumption and costs in real-time
- Alerts you when approaching limits
- Projects monthly costs based on current usage
- Supports both API-based and manual tracking

---

## ✨ Features

### Core Tracking
- 📊 Track usage across 6+ AI services (ChatGPT, Claude, Groq, GitHub Copilot, Perplexity, Codex)
- 🔄 Support for both API-based and web-based account tracking
- 📈 Real-time and historical usage data visualization
- 💰 Cost calculation based on current service pricing models
- 🎯 Monitor session limits and token quotas

### Dashboard
- 🎨 Overview cards for each service showing usage %, tokens remaining, and costs
- 📉 Historical charts (daily/weekly/monthly trends)
- 🚨 Alert system for approaching limits (configurable thresholds)
- 💸 Cost breakdown and month-end projections
- 🔍 Service comparison views
- 📤 Export reports (CSV, JSON)

### Security
- 🔐 Encrypted API key storage (AES-256)
- 🔑 JWT-based authentication
- 🛡️ Secure credential management
- 📝 Audit logs for account modifications

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ or Node.js 18+
- PostgreSQL 12+ (or SQLite for development)
- Docker & Docker Compose (recommended)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/zebadee2kk/ai-cost-tracker.git
cd ai-cost-tracker
```

2. **Generate required secrets**

```bash
# Fernet encryption key for API keys at rest
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# JWT secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

3. **Configure environment**

```bash
cp .env.example .env
# Edit .env — paste both generated keys into ENCRYPTION_KEY and SECRET_KEY
```

4. **Option A — Docker Compose (recommended)**

```bash
docker-compose up
```

5. **Option B — Manual**

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask db init && flask db migrate -m "initial" && flask db upgrade
python scripts/seed_services.py   # pre-loads 5 AI services
flask run                          # http://localhost:5000

# Frontend (new terminal)
cd frontend
npm install && npm start           # http://localhost:3000
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Health check**: http://localhost:5000/api/health

See [docs/setup-quickstart.md](docs/setup-quickstart.md) for full details.

---

## 📚 Documentation

This repository contains comprehensive documentation for building the AI Cost Tracker:

### For Developers

- **[Project Plan](docs/ai-tool-tracker-plan.md)** - Complete requirements, architecture, and implementation guide
  - Requirements specification
  - Database schema and data model
  - System architecture and tech stack
  - Feature specifications
  - Implementation phases (MVP → Production)
  - Security considerations
  - Development checklist

- **[API Integration Guide](docs/api-integration-guide.md)** - Service-specific integration details
  - OpenAI (ChatGPT/Codex) integration
  - Anthropic (Claude) integration
  - Groq integration
  - Perplexity integration
  - GitHub Copilot integration
  - Request/response examples
  - Security best practices

- **[Setup & Quick-Start](docs/setup-quickstart.md)** - Development environment setup
  - Prerequisites and installation
  - Environment configuration
  - Database initialization
  - API endpoints overview
  - Common development tasks
  - Debugging and troubleshooting

### For Claude Code

This repository is structured to be picked up by Claude Code for implementation. The documentation provides:
- Complete technical specifications
- Database schemas with exact field types
- API endpoint definitions
- Security requirements
- Testing strategies
- Deployment guidelines

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│          Frontend (React/Vue Dashboard)             │
│  - Overview cards      - Usage charts               │
│  - Alert management    - Settings                   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│          Backend API (Flask/Express)                │
│  - Authentication      - Account management         │
│  - Usage tracking      - Alert generation           │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ↓          ↓          ↓
   Database    Scheduler   External APIs
  PostgreSQL   (Sync Jobs)  (AI Services)
```

---

## 🎯 Supported AI Services

| Service | API Support | Auth Method | Tracking |
|---------|-------------|-------------|----------|
| ChatGPT/GPT-4 | ✅ | API Key | Tokens, Cost, Requests |
| Claude | ✅ | API Key | Input/Output Tokens, Cost |
| Groq | ✅ | API Key | Tokens, Requests |
| GitHub Copilot | ⚠️ Limited | GitHub Token | Session logs (manual/webhook) |
| Perplexity | ✅ | API Key | Queries, Tokens |
| Codex | ✅ | API Key | Same as OpenAI |

✅ = Full API support  
⚠️ = Limited API / Manual tracking

---

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3.0 (Python 3.10+)
- **Database**: SQLite (dev) / PostgreSQL 16 (prod)
- **ORM**: SQLAlchemy 2.0 + Flask-Migrate (Alembic)
- **Task Scheduler**: APScheduler 3.10
- **Authentication**: Flask-JWT-Extended (1-hour tokens)
- **Encryption**: `cryptography` Fernet — AES-128-CBC for API keys at rest

### Frontend
- **Framework**: React 18
- **Routing**: React Router 6
- **Charts**: Chart.js 4 + react-chartjs-2
- **HTTP Client**: Axios (with JWT interceptors)
- **Styling**: Custom CSS variables (dark theme, no framework dependency)

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: nginx (frontend container)
- **Secrets**: `.env` file (dev) / environment injection (prod)

---

## 📋 Implementation Phases

### Phase 1: MVP — ✅ COMPLETE
- [x] Full project structure (`backend/` + `frontend/`)
- [x] SQLAlchemy models: `Service`, `Account`, `UsageRecord`, `Alert`, `CostProjection`
- [x] AES-256 Fernet encryption for API keys at rest (`utils/encryption.py`)
- [x] JWT authentication — register, login, `/me`, logout (`routes/auth.py`)
- [x] Full account CRUD + connection test endpoint (`routes/accounts.py`)
- [x] Services, Usage, Alerts REST endpoints
- [x] OpenAI billing API integration with exponential backoff (`services/openai_service.py`)
- [x] Extensible base service class for future integrations (`services/base_service.py`)
- [x] APScheduler background sync job (`jobs/sync_usage.py`)
- [x] Cost calculator with pricing table + month-end projections (`utils/cost_calculator.py`)
- [x] Auto alert generation at 80% / 100% of monthly limit
- [x] React frontend: Login, Dashboard, Analytics, Settings pages
- [x] Chart.js daily cost bar chart + service pie chart
- [x] Account manager with add/delete/test-connection
- [x] Alert panel with dismiss
- [x] Docker + Docker Compose for full-stack local dev
- [x] Database seed script (5 AI services pre-configured)
- [x] Unit & integration tests (encryption, auth, accounts, OpenAI service)

### Phase 2: Multi-Service Support ⏳
- [ ] Anthropic Claude integration (`services/anthropic_service.py`)
- [ ] Groq integration (`services/groq_service.py`)
- [ ] Perplexity integration (`services/perplexity_service.py`)
- [ ] GitHub Copilot manual tracking
- [ ] Wire new services into `jobs/sync_usage.py`
- [ ] Enhanced account management UI

### Phase 3: Advanced Features ⏳
- [ ] Email/webhook alert notifications
- [ ] CSV/JSON data export
- [ ] Usage anomaly detection
- [ ] API rate limit monitoring
- [ ] Advanced multi-service comparison charts

### Phase 4: Polish & Production ⏳
- [ ] Performance optimization (query caching, pagination)
- [ ] Comprehensive E2E tests
- [ ] Production deployment guide (AWS/Railway/Heroku)
- [ ] OpenAPI/Swagger docs (`/api/docs`)

---

## 🔐 Security

- **API Keys**: Encrypted at rest using AES-256
- **Authentication**: JWT tokens with configurable expiration
- **HTTPS**: TLS for all communications
- **Rate Limiting**: Protection against abuse
- **Audit Logs**: Track all account modifications
- **GDPR Compliant**: Data export and deletion capabilities

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**RicheeRich** ([@zebadee2kk](https://github.com/zebadee2kk))
- London based developer
- 25 years IT/cybersec industry experience
- Recent Vibecoder

---

## 🙏 Acknowledgments

- Inspired by the need to track multiple AI tool subscriptions
- Built for developers using AI coding assistants
- Designed to work with Claude Code for rapid development

---

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Issues](https://github.com/zebadee2kk/ai-cost-tracker/issues)
- 💬 [Discussions](https://github.com/zebadee2kk/ai-cost-tracker/discussions)

---

## 🗺️ Roadmap

- [ ] Slack integration for alerts
- [ ] Multi-user support (teams)
- [ ] Mobile app (iOS/Android)
- [ ] ML-based usage prediction
- [ ] Zapier/IFTTT integration
- [ ] Budget optimization suggestions
- [ ] Model performance comparison

---

**Built with ❤️ for developers who vibe with AI**
