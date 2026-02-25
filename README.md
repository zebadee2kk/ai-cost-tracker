# AI Cost Tracker

> A comprehensive dashboard to track and manage usage across multiple AI tools including ChatGPT, Claude, Groq, GitHub Copilot, Perplexity, and more. Monitor token consumption, session limits, costs, and usage patterns in real-time.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Phase](https://img.shields.io/badge/Phase-2%20In%20Progress-blue)](ROADMAP.md)

---

## 🎯 Project Overview

**Problem**: As developers using multiple AI coding assistants, we face:
- Scattered usage data across different platforms
- Difficulty tracking costs and token consumption
- No unified view of session limits and quotas
- Risk of exceeding budgets without warning

**Solution**: AI Cost Tracker provides a centralized dashboard that:
- ✅ Aggregates usage data from multiple AI services
- ✅ Tracks token consumption and costs in real-time
- ✅ Alerts you when approaching limits
- ✅ Projects monthly costs based on current usage
- ✅ Supports both API-based and manual tracking

---

## ✨ Features

### Current (Phase 1 - Live)

#### Core Tracking
- ✅ OpenAI/ChatGPT integration with automatic usage sync
- ✅ Real-time and historical usage data visualization
- ✅ Cost calculation based on actual API usage
- ✅ Monthly and historical trend tracking
- ✅ Encrypted API key storage (AES-256 Fernet)

#### Dashboard
- ✅ Overview cards showing current month spend and total usage
- ✅ Usage charts with time-series visualization
- ✅ Account manager (add, edit, delete, test connection)
- ✅ Alert panel with threshold monitoring
- ✅ Analytics page with cost breakdown and forecasting
- ✅ Service comparison views

#### Security & Auth
- ✅ JWT-based authentication
- ✅ User registration and login
- ✅ Protected routes and API endpoints
- ✅ Encrypted credential storage

### Coming Soon (Phase 2 - In Progress)

- 🔜 Anthropic Claude API integration
- 🔜 Manual entry system for Groq and Perplexity
- 🔜 Idempotent data ingestion (no duplicates)
- 🔜 Enhanced test coverage (>80%)
- 🔜 CSV/JSON export functionality

### Future (Phase 3+)

- 📋 Email/webhook notifications
- 📋 Advanced analytics and anomaly detection
- 📋 Multi-user support (teams)
- 📋 Budget optimization suggestions
- 📋 Additional service integrations

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** and **Node.js 18+**
- **PostgreSQL 12+** (or SQLite for development)
- **Docker & Docker Compose** (recommended)

### Installation

#### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/zebadee2kk/ai-cost-tracker.git
cd ai-cost-tracker

# Copy environment template
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
# Edit .env file - Generate encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add the key to .env as ENCRYPTION_KEY=...

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend flask db upgrade

# Seed initial service data
docker-compose exec backend python scripts/seed_services.py
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **API Health**: http://localhost:5000/health

#### Option 2: Manual Setup

Detailed manual installation instructions are available in [docs/setup-quickstart.md](docs/setup-quickstart.md).

### First Steps

1. **Create an account**: Navigate to http://localhost:3000/register
2. **Login**: Use your credentials to access the dashboard
3. **Add an API account**:
   - Click "Add Account" in the dashboard
   - Select "OpenAI" (currently the only automated service)
   - Enter your OpenAI API key
   - Test the connection
4. **View usage**: Dashboard will automatically sync usage data

---

## 📚 Documentation

### Essential Reading

- **[ROADMAP.md](ROADMAP.md)** - Project phases, current status, and future plans
- **[Setup Quickstart](docs/setup-quickstart.md)** - Detailed installation guide
- **[API Integration Guide](docs/api-integration-guide.md)** - Service integration documentation

### For Developers

- **[Project Plan](docs/ai-tool-tracker-plan.md)** - Complete technical specification
- **[Research: API Capabilities 2026](docs/research-api-capabilities-2026.md)** - Provider API research
- **[Handover to Claude: Phase 2](docs/handover-to-claude-phase2.md)** - Implementation guide for Phase 2

### Architecture Documentation

See [docs/playbooks/](docs/playbooks/) for development playbooks and patterns.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│          Frontend (React Dashboard)                 │
│  - Auth Context        - Dashboard                  │
│  - Account Manager     - Analytics                  │
│  - Alert Panel         - Settings                   │
└──────────────────┬──────────────────────────────────┘
                   │ Axios API Client (JWT)
                   ↓
┌─────────────────────────────────────────────────────┐
│          Backend API (Flask)                        │
│  - JWT Auth            - Account CRUD               │
│  - Usage Tracking      - Alert Generation           │
│  - Cost Calculation    - Service Integration        │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ↓          ↓          ↓
   PostgreSQL   APScheduler  External APIs
  (SQLAlchemy)  (Daily Sync)  (OpenAI, etc.)
   - Encrypted   - Usage      - Token usage
   - Migrations    polling    - Cost data
```

**Tech Stack**:
- **Backend**: Flask, SQLAlchemy, APScheduler, Flask-JWT-Extended
- **Frontend**: React, Axios, React Router, Chart.js
- **Database**: PostgreSQL (production) / SQLite (dev)
- **Security**: AES-256 Fernet encryption, JWT tokens
- **Deployment**: Docker, Docker Compose

---

## 🎯 Supported AI Services

| Service | Status | API Support | Tracking Method | Notes |
|---------|--------|-------------|-----------------|-------|
| **OpenAI/ChatGPT** | ✅ Live | Full API | Automatic sync | GPT-4, GPT-5.1, embeddings |
| **Anthropic Claude** | 🔜 Phase 2 | Admin API | Automatic sync | Requires Admin API key |
| **Groq** | 🔜 Phase 2 | ❌ None | Manual entry | Dashboard viewing only |
| **Perplexity** | 🔜 Phase 2 | ❌ None | Manual entry | Invoice-based tracking |
| **GitHub Copilot** | 📋 Planned | ⚠️ Limited | Manual entry | No usage API available |
| **Local LLMs** | 📋 Planned | N/A | Manual entry | Ollama, LM Studio, etc. |

**Legend**:
- ✅ Live and working
- 🔜 In development (Phase 2)
- 📋 Planned for future phases
- ⚠️ Limited API availability
- ❌ No API available

---

## 🛠️ Development

### Project Structure

```
ai-cost-tracker/
├── backend/              # Flask backend
│   ├── models/           # SQLAlchemy models
│   ├── routes/           # API endpoints
│   ├── services/         # Service integrations (OpenAI, Claude, etc.)
│   ├── jobs/             # Background scheduler jobs
│   ├── utils/            # Utilities (encryption, cost calc)
│   ├── tests/            # Backend tests
│   └── migrations/       # Alembic migrations
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API client
│   │   └── contexts/     # React contexts (Auth)
│   └── public/
├── docs/                 # Documentation
│   ├── playbooks/        # Development guides
│   └── context/          # Additional context
├── docker-compose.yml    # Docker orchestration
└── .env.example          # Environment template
```

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
### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=backend

# Frontend tests (when implemented)
cd frontend
npm test
```

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

---

## 📋 Current Status (February 2026)

### ✅ Phase 1: MVP - COMPLETE

**Delivered**:
- Functional backend API with all CRUD operations
- React dashboard with authentication
- OpenAI integration with automatic sync
- Cost tracking and forecasting
- Alert system
- Docker deployment ready

**Test Coverage**: ~60% (backend focus)

### 🔜 Phase 2: Multi-Service Integration - IN PROGRESS

**Current Sprint**: Foundation & Anthropic Integration

**Next Steps** (see [ROADMAP.md](ROADMAP.md)):
1. Add database constraint for idempotent ingestion
2. Fix scheduler duplicate runs
3. Implement Anthropic Claude service
4. Build manual entry system for Groq/Perplexity
5. Expand test coverage to >80%

**Target Completion**: March 2026

---

## 🔐 Security

- **API Keys**: Encrypted at rest using AES-256 Fernet
- **Authentication**: JWT tokens with configurable expiration
- **Password Hashing**: Werkzeug secure password hashing
- **CORS**: Configured for frontend/backend separation
- **Environment Secrets**: Never committed to git
- **Database**: SQL injection protection via SQLAlchemy ORM

**Security Best Practices**:
- Rotate encryption keys periodically
- Use HTTPS in production
- Implement rate limiting (recommended)
- Regular dependency updates
- Monitor for security advisories

---

## 🤝 Contributing

Contributions are welcome! This is an AI-native project built collaboratively by:
- **Codex**: Phase 1 MVP implementation
- **Perplexity**: Research and planning
- **Claude Code**: Phase 2 implementation

### Contributing Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes with clear messages
4. Write/update tests for your changes
5. Ensure all tests pass
6. Push to your branch
7. Open a Pull Request with description

### Areas We Need Help

- Additional service integrations (when APIs available)
- Frontend UI/UX improvements
- Test coverage expansion
- Documentation improvements
- Performance optimization

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Richard Ham** ([@zebadee2kk](https://github.com/zebadee2kk))

- 🏢 IT Director & Cybersecurity Leader
- 📍 London, UK
- 💼 25+ years IT management experience
- 🤖 AI-native development enthusiast
- 🔧 Vibe coding practitioner

**Tech Philosophy**: Building with AI assistance (Claude, ChatGPT, Perplexity, Ollama) to rapidly prototype and deliver production-ready systems.

---

## 🙏 Acknowledgments

- Built with extensive AI pair programming (Claude Code, GitHub Copilot)
- Research conducted via Perplexity AI
- Inspired by the need to manage multiple AI subscriptions
- Designed for transparency in AI tool costs

**AI Team**:
- Codex: MVP implementation and architecture
- Perplexity: Research, planning, and documentation
- Claude Code: Phase 2 implementation

---

## 📞 Support

- 📖 **[Documentation](docs/)** - Comprehensive guides
- 🐛 **[Issues](https://github.com/zebadee2kk/ai-cost-tracker/issues)** - Bug reports and features
- 💬 **[Discussions](https://github.com/zebadee2kk/ai-cost-tracker/discussions)** - Questions and ideas
- 🗺️ **[Roadmap](ROADMAP.md)** - Project direction

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Built with ❤️ for developers who vibe with AI**

**Status**: 🟢 Active Development | Phase 2 In Progress | Production-Ready MVP
