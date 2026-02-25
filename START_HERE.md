# 🚀 START HERE - Guide for Claude Code

Welcome! This guide will help you (Claude Code) build the AI Cost Tracker application from scratch.

---

## 📌 Step 1: Read the Documentation

**Before writing any code**, read these files in order:

1. **[docs/ai-tool-tracker-plan.md](docs/ai-tool-tracker-plan.md)** (19KB)
   - Complete project plan with all requirements
   - Database schema with exact field types
   - System architecture and tech stack
   - Feature specifications
   - Implementation phases
   - Security requirements
   - File structure template

2. **[docs/api-integration-guide.md](docs/api-integration-guide.md)** (7.5KB)
   - Service-specific API specifications
   - OpenAI, Anthropic, Groq, Perplexity, GitHub Copilot details
   - Authentication methods
   - Request/response examples
   - Security best practices

3. **[docs/setup-quickstart.md](docs/setup-quickstart.md)** (13KB)
   - Environment setup instructions
   - API endpoints specification
   - Development workflow
   - Debugging tips
   - Troubleshooting guide

---

## 🎯 Implementation Plan

### Phase 1: MVP (Start Here) ✅

#### 1.1 Project Setup
- [ ] Create backend directory structure (see `docs/ai-tool-tracker-plan.md` Section 9)
- [ ] Create frontend directory structure
- [ ] Set up `.env.example` file with all required environment variables
- [ ] Create `requirements.txt` with Python dependencies
- [ ] Create `package.json` with Node.js dependencies
- [ ] Set up Docker and docker-compose.yml

#### 1.2 Database Layer
- [ ] Create SQLAlchemy models based on schema in Section 2.1:
  - `models/service.py` - Service definitions
  - `models/account.py` - Account tracking
  - `models/usage_record.py` - Usage data
  - `models/alert.py` - Alert configurations
  - `models/cost_projection.py` - Cost forecasting
- [ ] Create Alembic migrations
- [ ] Create seed script for initial services

#### 1.3 Backend API - Core
- [ ] `app.py` - Flask app initialization with CORS, error handlers
- [ ] `config.py` - Configuration management
- [ ] `utils/encryption.py` - AES-256 encryption for API keys
- [ ] `utils/validators.py` - Input validation

#### 1.4 Backend API - Authentication
- [ ] `routes/auth.py` - Login, logout, register endpoints
- [ ] JWT token generation and validation
- [ ] Password hashing with bcrypt

#### 1.5 Backend API - Accounts
- [ ] `routes/accounts.py` - CRUD endpoints for accounts
- [ ] Encrypt API keys before storing
- [ ] Test API connection endpoint

#### 1.6 Backend API - Services Integration
- [ ] `services/base_service.py` - Base class for all integrations
- [ ] `services/openai_service.py` - OpenAI API client (START WITH THIS)
  - Use specs from `docs/api-integration-guide.md` Section 1
  - Implement usage retrieval
  - Implement credential validation
- [ ] Error handling with exponential backoff

#### 1.7 Backend API - Usage
- [ ] `routes/usage.py` - Usage data endpoints
- [ ] Cost calculation logic in `utils/cost_calculator.py`
- [ ] Aggregation functions for dashboard

#### 1.8 Background Jobs
- [ ] `jobs/sync_usage.py` - Scheduled job to fetch usage from APIs
- [ ] Set up APScheduler
- [ ] Implement job for OpenAI sync

#### 1.9 Frontend - Setup
- [ ] Create React app with TypeScript (optional)
- [ ] Set up Tailwind CSS
- [ ] Create `services/api.js` - Axios client for backend
- [ ] Set up Redux or Context API for state management

#### 1.10 Frontend - Authentication
- [ ] `pages/LoginPage.jsx` - Login form
- [ ] Token storage and management
- [ ] Protected route wrapper

#### 1.11 Frontend - Dashboard
- [ ] `pages/DashboardPage.jsx` - Main dashboard layout
- [ ] `components/OverviewCard.jsx` - Service overview card
  - Display service name, usage %, tokens remaining, cost
  - Status indicator (OK, Warning, Critical)
- [ ] `components/UsageChart.jsx` - Chart.js integration
  - Daily usage trend for last 30 days

#### 1.12 Frontend - Account Management
- [ ] `components/AccountManager.jsx` - Add/edit accounts
- [ ] Form for adding OpenAI API key
- [ ] Test connection button
- [ ] Display account status

#### 1.13 Testing
- [ ] Unit tests for encryption utility
- [ ] Unit tests for OpenAI service
- [ ] Integration tests for auth endpoints
- [ ] Integration tests for account endpoints

#### 1.14 Documentation
- [ ] Update README.md with actual setup steps
- [ ] Create .env.example with all variables

---

### Phase 2: Multi-Service Support ⏳

(Implement after Phase 1 is complete and tested)

- [ ] Add Anthropic Claude integration
- [ ] Add Groq integration
- [ ] Add Perplexity integration
- [ ] Add GitHub Copilot integration (manual tracking)
- [ ] Enhanced account management UI
- [ ] Historical data visualization
- [ ] Cost projection algorithm

---

### Phase 3: Advanced Features ⏳

(Implement after Phase 2)

- [ ] Alert system with email notifications
- [ ] Advanced charting with multiple data views
- [ ] CSV/JSON export functionality
- [ ] Usage anomaly detection
- [ ] API rate limit monitoring

---

## 📖 Key Implementation Details

### Database Schema Reference

See `docs/ai-tool-tracker-plan.md` Section 2.1 for complete schema.

**Critical fields**:
- Costs: `DECIMAL(10,4)` for precision
- API Keys: `VARCHAR` encrypted with AES-256
- Tokens: `INTEGER`
- Timestamps: ISO 8601 with timezone

### API Endpoints to Implement

**Authentication**:
```
POST /api/auth/login      - Login with email/password
POST /api/auth/logout     - Logout
GET  /api/auth/me         - Get current user
```

**Accounts**:
```
GET    /api/accounts           - List all accounts
POST   /api/accounts           - Create account
GET    /api/accounts/{id}      - Get account details
PUT    /api/accounts/{id}      - Update account
DELETE /api/accounts/{id}      - Delete account
POST   /api/accounts/{id}/test - Test API connection
```

**Usage**:
```
GET /api/usage              - Current usage summary
GET /api/usage/history      - Historical usage data
GET /api/usage/by-service   - Usage breakdown by service
```

See `docs/setup-quickstart.md` for complete endpoint specification.

### Security Checklist

- [ ] All API keys encrypted with AES-256
- [ ] JWT tokens expire after 1 hour
- [ ] CORS configured for specific origins
- [ ] No secrets in code or git
- [ ] SQL injection protection via SQLAlchemy ORM
- [ ] Input validation on all endpoints
- [ ] HTTPS/TLS in production

### Environment Variables Required

```bash
# Backend
FLASK_ENV=development
FLASK_APP=app.py
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
DATABASE_URL=postgresql://user:password@localhost:5432/ai_tracker

# Frontend
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_ENV=development
```

---

## 🛠️ Commands to Run

### Initial Setup
```bash
# Generate encryption keys
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_hex(32))"

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
python scripts/seed_services.py

# Frontend setup
cd frontend
npm install

# Run with Docker
docker-compose up
```

### Testing
```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

---

## ⚠️ Important Notes

1. **Follow the Spec Exactly**: The documentation contains precise specifications. Don't deviate.

2. **Security First**: Always encrypt API keys before storing. Use environment variables for secrets.

3. **Error Handling**: Every API call must have proper error handling with try/catch.

4. **Testing**: Write tests as you go. Don't skip this.

5. **Start Simple**: Implement OpenAI integration first. Get it working before adding other services.

6. **Database Schema**: Use the exact field types and names from the documentation.

7. **No Shortcuts**: Don't use mock data in production code. Keep mocks in tests only.

---

## 🐛 Troubleshooting

If something isn't clear:
1. Re-read the relevant documentation section
2. Check `docs/setup-quickstart.md` troubleshooting section
3. Verify you're following the correct implementation phase
4. Check that environment variables are set correctly

---

## ✅ Definition of Done

**Phase 1 MVP is complete when**:
- [ ] User can register and login
- [ ] User can add an OpenAI API key
- [ ] System fetches usage data from OpenAI API
- [ ] Dashboard displays current usage and costs
- [ ] User can view historical usage in a chart
- [ ] All tests pass
- [ ] Docker Compose runs the full stack
- [ ] README has accurate setup instructions

---

## 🚀 Ready to Start?

1. Read all three documentation files
2. Create the project structure
3. Start with Phase 1.1 (Project Setup)
4. Work through each checklist item in order
5. Test thoroughly at each step

Good luck! The documentation has everything you need. 🚀
