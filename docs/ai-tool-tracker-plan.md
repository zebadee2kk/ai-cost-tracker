# AI Tool Usage Tracker - Complete Project Plan

## Project Overview

**Objective**: Build a comprehensive dashboard to track and manage usage across multiple AI tools including ChatGPT, Claude, Groq, GitHub Copilot, Perplexity, and others. Monitor token consumption, session limits, costs, and usage patterns in real-time.

**Target User**: Developer using multiple AI coding assistants who needs centralized visibility into usage, costs, and limits.

**Timeline**: To be determined based on complexity and feature prioritization.

---

## 1. Requirements Specification

### 1.1 Functional Requirements

#### Core Tracking
- Track usage across 6+ AI services (ChatGPT, Claude, Groq, GitHub Copilot, Perplexity, Codex)
- Support both API-based and web-based account tracking
- Record metrics: tokens used, sessions active, remaining quota, cost incurred
- Display real-time and historical usage data
- Monitor session limits and token limits per service
- Calculate costs based on service pricing models

#### Dashboard Features
- Overview card for each service showing: current usage %, tokens remaining, cost this month
- Historical charts showing daily/weekly/monthly usage trends
- Alert system for approaching limits (e.g., 80% of monthly quota)
- Cost breakdown and projection to month-end
- Service comparison views
- Export usage reports (CSV, JSON)

#### Account Management
- Add/remove tracking for multiple accounts per service
- Store account credentials securely (API keys, authentication tokens)
- Support multiple API keys per service (for different projects/accounts)
- Edit service pricing models and limits
- Manage API configuration per service

#### Data Input Methods
- Manual entry for services without API access
- API integration where available (ChatGPT, Claude, Groq, Perplexity)
- GitHub Copilot integration (if API available, else manual tracking)
- CSV import for bulk historical data
- Webhook/script hooks for custom integrations

### 1.2 Non-Functional Requirements
- Dashboard loads and displays data within 2 seconds
- Support up to 50 tracked accounts across services
- Secure storage of credentials and sensitive data
- Minimal maintenance overhead
- Easy to add new services in future

---

## 2. Data Model & Schema

### 2.1 Database Schema

```
TABLE: services
  - id (PK)
  - name (VARCHAR) - ChatGPT, Claude, Groq, GitHub Copilot, Perplexity, etc.
  - api_provider (VARCHAR) - OpenAI, Anthropic, Groq, GitHub, Perplexity, etc.
  - has_api (BOOLEAN) - whether service provides usage API
  - pricing_model (JSON) - cost per token, per request, per month, etc.
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

TABLE: accounts
  - id (PK)
  - service_id (FK -> services)
  - account_name (VARCHAR) - user-friendly name (e.g., "Work Account", "Personal")
  - api_key (VARCHAR) - encrypted API key
  - auth_token (VARCHAR) - encrypted auth token if different from API key
  - is_active (BOOLEAN)
  - monthly_limit (DECIMAL) - user's personal limit for this account
  - session_limit (INTEGER) - concurrent sessions allowed
  - created_at (TIMESTAMP)
  - last_sync (TIMESTAMP)
  - updated_at (TIMESTAMP)

TABLE: usage_records
  - id (PK)
  - account_id (FK -> accounts)
  - service_id (FK -> services)
  - timestamp (TIMESTAMP)
  - tokens_used (INTEGER)
  - tokens_remaining (INTEGER)
  - cost (DECIMAL)
  - cost_currency (VARCHAR) - USD, GBP, EUR, etc.
  - sessions_active (INTEGER)
  - api_calls (INTEGER) - number of API calls made
  - request_type (VARCHAR) - coding assistance, chat, analysis, etc.
  - metadata (JSON) - additional data from service
  - created_at (TIMESTAMP)

TABLE: alerts
  - id (PK)
  - account_id (FK -> accounts)
  - alert_type (VARCHAR) - approaching_limit, limit_exceeded, high_cost, etc.
  - threshold_percentage (INTEGER) - e.g., 80 for 80% usage
  - is_active (BOOLEAN)
  - last_triggered (TIMESTAMP)
  - notification_method (VARCHAR) - email, webhook, dashboard
  - created_at (TIMESTAMP)

TABLE: cost_projections
  - id (PK)
  - account_id (FK -> accounts)
  - month (DATE) - first day of month
  - projected_cost (DECIMAL)
  - actual_cost (DECIMAL) - once month ends
  - confidence_score (DECIMAL) - 0-100, based on data available
  - created_at (TIMESTAMP)
```

### 2.2 Data Types & Precision
- Costs: DECIMAL(10,4) for precision to 4 decimal places
- Tokens: INTEGER (can handle up to 2.1 billion tokens)
- Timestamps: ISO 8601 format with timezone
- Credentials: Encrypted at rest using AES-256

---

## 3. Architecture & Tech Stack

### 3.1 Technology Choices

**Backend**:
- Framework: Flask (Python) or Express.js (Node.js)
- Database: PostgreSQL (production) or SQLite (development/MVP)
- ORM: SQLAlchemy (Python) or Sequelize (Node.js)
- Task Scheduler: APScheduler (Python) or node-cron (Node.js)
- Authentication: JWT tokens for web dashboard access

**Frontend**:
- Framework: React or Vue.js
- State Management: Redux (React) or Pinia (Vue)
- Charts: Chart.js or D3.js for usage visualization
- Styling: Tailwind CSS or Bootstrap
- HTTP Client: Axios or Fetch API

**Infrastructure**:
- Hosting: Docker containers (local or cloud deployment)
- Environment: Docker Compose for local development
- Logging: Winston (Node.js) or Python logging
- Secrets Management: .env files (development), AWS Secrets Manager or HashiCorp Vault (production)

### 3.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│          Frontend (React/Vue Dashboard)             │
│  - Overview cards for each service                  │
│  - Usage charts and trends                          │
│  - Alert management                                 │
│  - Settings and account management                  │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│          Backend API (Flask/Express)                │
│  - Authentication & Authorization                   │
│  - Account management endpoints                     │
│  - Usage data retrieval and calculation             │
│  - Alert generation and notification               │
│  - Report generation                               │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ↓          ↓          ↓
┌──────────────┐ ┌──────────────────┐ ┌──────────────┐
│  Database    │ │ Task Scheduler   │ │  API Clients │
│ (PostgreSQL) │ │ (Background Jobs)│ │ (OAuth/Keys) │
└──────────────┘ └──────────────────┘ └──────────────┘
        ↑
        │
   ┌────┴────┬─────────┬────────┬──────────┬──────────┐
   ↓         ↓         ↓        ↓          ↓          ↓
OpenAI   Anthropic  Groq    GitHub     Perplexity  Custom
APIs     APIs       APIs    Copilot    APIs        APIs
```

---

## 4. Service Integration Details

### 4.1 Supported Services & Integration Methods

| Service | API Available | Auth Method | Data Points | Notes |
|---------|---------------|-------------|-------------|-------|
| ChatGPT/GPT-4 | OpenAI API | API Key | tokens used, requests, cost | Billing via OpenAI dashboard |
| Claude | Anthropic API | API Key | tokens used (input/output), requests | Separate billing |
| Groq | Groq API | API Key | tokens used, requests, latency | Free tier available |
| GitHub Copilot | Limited (VS Code Extension) | GitHub Token | Session logs via extension | Manual sync or extension hook |
| Perplexity | Perplexity API | API Key | queries used, tokens | Pro subscription model |
| Codex | OpenAI API | API Key | Same as ChatGPT | Part of OpenAI suite |

### 4.2 API Integration Specifications

**OpenAI (ChatGPT/Codex)**:
- Endpoint: `https://api.openai.com/v1/usage`
- Authentication: Bearer token in header
- Rate limit: 3,500 requests/min
- Data refresh: Daily (can be increased)
- Cost calculation: Based on model used (gpt-4, gpt-3.5-turbo, etc.)

**Anthropic (Claude)**:
- Endpoint: `https://api.anthropic.com/v1/` (check current docs)
- Authentication: API key header
- Rate limit: Depends on plan
- Data refresh: Daily
- Cost calculation: Per-token pricing (input tokens cheaper than output)

**Groq**:
- Endpoint: `https://api.groq.com/v1/`
- Authentication: API key
- Rate limit: High (depends on tier)
- Data refresh: Real-time capable
- Cost calculation: Usually free tier, paid plan available

**Perplexity**:
- Endpoint: Check current API documentation
- Authentication: API key
- Rate limit: Per subscription tier
- Data refresh: Real-time or batch
- Cost calculation: Query-based or subscription

**GitHub Copilot**:
- No official usage API
- Alternative: GitHub REST API for organization-level usage (if available)
- Fallback: Manual entry or VS Code extension webhook

---

## 5. Feature Specifications

### 5.1 Dashboard Features

**Overview Card (Per Service)**:
- Service name and icon
- Current monthly spend (vs. limit)
- Tokens used today/this month
- % of quota consumed (visual progress bar)
- Status indicator (OK, Warning, Critical)
- Quick action buttons (view details, configure limits)

**Usage Charts**:
- Daily usage trend (last 30 days)
- Cost breakdown by service
- Token distribution (input vs output for Claude)
- API call frequency
- Comparison view (usage side-by-side)

**Alerts Section**:
- List of active alerts
- Alert history (last 30 days)
- Threshold configuration per service
- Notification settings (email, webhook, dashboard)

**Account Management**:
- Add new service account (form with API key input)
- Edit account details (name, limits, pricing)
- Test API connection (validate credentials)
- Delete account
- View account usage history

**Settings**:
- Monthly budget limits per service
- Alert thresholds (default 80%, configurable)
- Preferred currency (USD, GBP, EUR, etc.)
- Data retention policy
- Export/backup options

### 5.2 Alert System

**Alert Types**:
1. **Approaching Limit**: Triggered at 80% of monthly quota
2. **Limit Exceeded**: Triggered when quota is exceeded
3. **High Daily Cost**: Triggered if daily spend exceeds threshold
4. **Service Down**: Triggered if API unavailable for 5+ minutes
5. **Unusual Activity**: Triggered if usage spikes 2x normal pattern

**Notification Methods**:
- Dashboard notification (bell icon with count)
- Email notification (configurable frequency)
- Webhook POST to user-specified endpoint
- Optional Slack integration (future)

---

## 6. Implementation Phases

### Phase 1: MVP (Core Functionality)
- [ ] Database setup and schema creation
- [ ] Backend API with basic CRUD operations
- [ ] Authentication (simple JWT)
- [ ] Single service integration (OpenAI/ChatGPT)
- [ ] Basic dashboard with overview cards
- [ ] Manual data entry for other services
- [ ] Simple alert system (dashboard only)

**Deliverable**: Working dashboard tracking 1-2 services

### Phase 2: Multi-Service Support
- [ ] Integrate remaining services (Claude, Groq, Perplexity, GitHub Copilot)
- [ ] Enhanced account management UI
- [ ] Automated background sync (scheduler)
- [ ] Historical data storage and retrieval
- [ ] Cost projection algorithm

**Deliverable**: Full multi-service tracking with historical data

### Phase 3: Advanced Features
- [ ] Email/webhook notifications
- [ ] Advanced charting and analytics
- [ ] CSV/JSON export functionality
- [ ] Comparison views and reports
- [ ] Usage anomaly detection
- [ ] API rate limit monitoring

**Deliverable**: Production-ready dashboard with all features

### Phase 4: Polish & Optimization
- [ ] Performance optimization (caching, query optimization)
- [ ] Enhanced security (credential encryption, audit logs)
- [ ] Comprehensive error handling
- [ ] User documentation
- [ ] Deployment automation (Docker, CI/CD)

---

## 7. Security Considerations

### 7.1 Credential Management
- All API keys encrypted at rest using AES-256
- Keys never logged or exposed in error messages
- Use environment variables for backend secrets
- Implement rate limiting on API endpoints
- API keys rotatable via dashboard

### 7.2 Access Control
- JWT-based authentication for dashboard
- Single-user or multi-user modes (configurable)
- Session timeouts (default 1 hour)
- Audit log of all account modifications

### 7.3 Data Protection
- HTTPS/TLS for all communications
- No sensitive data in browser local storage
- Database backups encrypted
- GDPR compliance: Ability to export/delete all user data

---

## 8. Development Checklist

### Backend
- [ ] Project initialization and dependency setup
- [ ] Database migrations and schema creation
- [ ] Authentication system (JWT)
- [ ] Core CRUD endpoints (services, accounts, usage records)
- [ ] OpenAI API integration
- [ ] Anthropic Claude API integration
- [ ] Groq API integration
- [ ] Perplexity API integration
- [ ] GitHub Copilot integration (manual/webhook)
- [ ] Background job scheduler for data sync
- [ ] Alert generation logic
- [ ] Cost calculation engine
- [ ] Export/report generation
- [ ] Error handling and logging
- [ ] API documentation (OpenAPI/Swagger)

### Frontend
- [ ] React/Vue project setup
- [ ] Authentication flow (login/logout)
- [ ] Dashboard layout and navigation
- [ ] Overview cards component
- [ ] Usage charts component (Chart.js integration)
- [ ] Account management views
- [ ] Settings panel
- [ ] Alert display and management
- [ ] Data refresh mechanisms (polling/WebSocket)
- [ ] Error boundaries and error messages
- [ ] Responsive design (mobile-friendly)
- [ ] Dark mode support

### DevOps
- [ ] Docker configuration
- [ ] Docker Compose setup (local dev)
- [ ] Environment configuration (.env template)
- [ ] Database initialization scripts
- [ ] Deployment documentation
- [ ] CI/CD pipeline (GitHub Actions or similar)

---

## 9. File Structure (Backend - Python/Flask Example)

```
ai-tool-tracker/
├── backend/
│   ├── app.py                 # Flask app initialization
│   ├── config.py              # Configuration management
│   ├── requirements.txt        # Python dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── account.py
│   │   ├── usage_record.py
│   │   └── alert.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── services.py
│   │   ├── accounts.py
│   │   ├── usage.py
│   │   └── alerts.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── openai_service.py
│   │   ├── anthropic_service.py
│   │   ├── groq_service.py
│   │   ├── perplexity_service.py
│   │   ├── github_service.py
│   │   └── base_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── cost_calculator.py
│   │   ├── alert_generator.py
│   │   └── validators.py
│   ├── jobs/
│   │   ├── __init__.py
│   │   └── sync_usage.py      # Scheduled background job
│   ├── migrations/            # Alembic migrations
│   └── logs/
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── OverviewCard.jsx
│   │   │   ├── UsageChart.jsx
│   │   │   ├── AccountManager.jsx
│   │   │   └── AlertPanel.jsx
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── SettingsPage.jsx
│   │   │   └── AnalyticsPage.jsx
│   │   ├── services/
│   │   │   └── api.js         # API client
│   │   ├── store/
│   │   │   └── index.js       # State management
│   │   └── styles/
│   │       └── index.css
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```

---

## 10. Testing Strategy

### Unit Tests
- Service integration logic (mocked API responses)
- Cost calculation functions
- Alert generation logic
- Data validation and sanitization

### Integration Tests
- API endpoints with sample data
- Database transactions and rollbacks
- Service authentication flows

### End-to-End Tests
- Full user flow: login → add account → view dashboard → set alerts
- Data sync and update verification
- Alert notifications triggered correctly

---

## 11. Deployment & Maintenance

### Local Development
```bash
docker-compose up
# Backend: http://localhost:5000
# Frontend: http://localhost:3000
```

### Production Deployment
- Option 1: Docker containers on cloud VM (AWS EC2, DigitalOcean, Linode)
- Option 2: Managed services (Heroku, Railway, Vercel)
- Database: Managed PostgreSQL (AWS RDS, DigitalOcean, Azure)
- Monitoring: Sentry for error tracking, DataDog or New Relic for APM

### Maintenance Tasks
- Monthly: Review and update service pricing models
- Quarterly: Review alert thresholds and adjust as needed
- Ongoing: Monitor API status and handle service outages

---

## 12. Future Enhancements

- **Slack Integration**: Send alerts directly to Slack
- **Multi-User Support**: Teams and shared accounts
- **Advanced Analytics**: ML-based usage prediction
- **Mobile App**: Native mobile dashboard
- **Zapier/IFTTT Integration**: Automate workflows
- **Budget Optimization**: Suggestions to reduce costs
- **Model Comparison**: Compare costs/performance across models
- **Custom Integrations**: Webhook support for any API

---

## 13. Success Metrics

- Dashboard loads in < 2 seconds
- All APIs syncing data within 5 minutes
- Alert accuracy > 95%
- System uptime > 99%
- User can add new service account in < 2 minutes

---

## 14. Questions for Clarification

Before implementation, confirm:

1. Preferred backend framework (Flask/Express)?
2. Frontend preference (React/Vue)?
3. Database preference (PostgreSQL/SQLite)?
4. Single-user or multi-user system?
5. Cloud deployment or local-only?
6. Email notification service to use (SendGrid, Mailgun)?
7. Budget for any paid services?
8. Data retention requirements (how long to keep historical data)?
