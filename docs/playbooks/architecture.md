# Architecture Playbook - AI Cost Tracker

⚠️ **IMPORTANT**: This is a reference document. The complete architecture specification is in:

## 📚 Primary Documentation

**[docs/ai-tool-tracker-plan.md](../ai-tool-tracker-plan.md)** - Complete architecture details including:
- System architecture diagram (Section 3.2)
- Technology stack (Section 3.1)
- Database schema (Section 2.1)
- Service integration details (Section 4)
- File structure (Section 9)

---

## Quick Architecture Overview

### 🏗️ System Components

```
Frontend (React/Vue)
        ↓
   Backend API (Flask/Python)
        ↓
   ├─ Database (PostgreSQL)
   ├─ Task Scheduler (Background Jobs)
   └─ External APIs (OpenAI, Claude, Groq, etc.)
```

### 🛠️ Tech Stack

- **Backend**: Flask (Python 3.10+) with SQLAlchemy ORM
- **Frontend**: React with Chart.js for visualizations
- **Database**: PostgreSQL (production) / SQLite (development)
- **Styling**: Tailwind CSS
- **Authentication**: JWT tokens
- **Containerization**: Docker & Docker Compose
- **Security**: AES-256 encryption for API keys

### 📊 Data Flow

1. **User adds account** → API key encrypted → Stored in database
2. **Background job runs** → Fetches usage from service APIs → Stores usage_records
3. **User views dashboard** → Backend aggregates data → Charts displayed
4. **Alert triggered** → Threshold exceeded → Notification sent

### 📁 Directory Structure

```text
ai-cost-tracker/
├── backend/
│   ├── models/          # SQLAlchemy models (services, accounts, usage_records)
│   ├── routes/          # API endpoints (auth, accounts, usage, alerts)
│   ├── services/        # Service integrations (openai, anthropic, groq, etc.)
│   ├── utils/           # Helper functions (encryption, cost_calculator, alert_generator)
│   ├── jobs/            # Background sync jobs
│   ├── migrations/      # Database migrations
│   ├── app.py           # Flask app initialization
│   ├── config.py        # Configuration management
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/  # React components (OverviewCard, UsageChart, AlertPanel)
│   │   ├── pages/       # Page components (DashboardPage, SettingsPage)
│   │   ├── services/    # API client for backend communication
│   │   └── store/       # State management (Redux/Pinia)
│   └── package.json
├── docs/               # Documentation (DO NOT MODIFY - Contains specs)
├── docker-compose.yml  # Docker orchestration
├── Dockerfile          # Container definition
└── README.md           # Project overview
```

### 🔐 Security Architecture

- **API Keys**: Encrypted at rest with AES-256 using Fernet
- **Authentication**: JWT tokens with 1-hour expiration
- **Database**: No plaintext sensitive data
- **HTTPS**: TLS for all communications
- **CORS**: Configured for specific origins only

### 📡 API Endpoints

See `docs/setup-quickstart.md` for complete API endpoint specifications.

**Key endpoints**:
- `/api/auth/*` - Authentication
- `/api/accounts/*` - Account management
- `/api/usage/*` - Usage data retrieval
- `/api/alerts/*` - Alert configuration
- `/api/services/*` - Service information

---

## 📌 Design Principles

1. **Modularity**: Each service integration is isolated in its own module
2. **Security First**: All credentials encrypted, no secrets in code
3. **Separation of Concerns**: Backend handles business logic, frontend handles presentation
4. **DRY**: Base service class for common API client functionality
5. **Error Handling**: Comprehensive error handling at every layer

---

➡️ **For complete details, refer to [docs/ai-tool-tracker-plan.md](../ai-tool-tracker-plan.md)**
