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

2. **Using Docker Compose (Recommended)**

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Generate encryption keys as described in docs/setup-quickstart.md

# Start all services
docker-compose up
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

3. **Manual Setup**

See [docs/setup-quickstart.md](docs/setup-quickstart.md) for detailed manual installation instructions.

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
- **Framework**: Flask (Python) or Express.js (Node.js)
- **Database**: PostgreSQL / SQLite
- **ORM**: SQLAlchemy / Sequelize
- **Task Scheduler**: APScheduler / node-cron
- **Authentication**: JWT

### Frontend
- **Framework**: React or Vue.js
- **State Management**: Redux / Pinia
- **Charts**: Chart.js or D3.js
- **Styling**: Tailwind CSS

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Secrets Management**: Environment variables / Vault

---

## 📋 Implementation Phases

### Phase 1: MVP (Core Functionality)
- [x] Database schema and setup
- [ ] Backend API with CRUD operations
- [ ] Authentication (JWT)
- [ ] OpenAI service integration
- [ ] Basic dashboard UI
- [ ] Manual data entry

### Phase 2: Multi-Service Support
- [ ] Additional service integrations (Claude, Groq, Perplexity)
- [ ] Account management UI
- [ ] Background sync scheduler
- [ ] Historical data tracking
- [ ] Cost projection algorithm

### Phase 3: Advanced Features
- [ ] Email/webhook notifications
- [ ] Advanced analytics and charts
- [ ] CSV/JSON export
- [ ] Usage anomaly detection

### Phase 4: Polish & Production
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Production deployment
- [ ] User documentation

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
