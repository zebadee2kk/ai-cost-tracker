# Setup & Quick-Start Guide

## Prerequisites

Before starting development, ensure you have:

- Python 3.10+ (for Flask backend) OR Node.js 18+ (for Express backend)
- PostgreSQL 12+ OR SQLite 3 (for MVP)
- Docker & Docker Compose (for containerized development)
- Git for version control
- A code editor (VS Code, PyCharm, WebStorm, etc.)

---

## Initial Setup Instructions

### 1. Clone and Initialize Project

```bash
# Clone the repository
git clone https://github.com/zebadee2kk/ai-cost-tracker.git
cd ai-cost-tracker

# Create .env file from template
cp .env.example .env

# Edit .env with your settings
# ENCRYPTION_KEY=your_generated_key
# DATABASE_URL=postgresql://user:password@localhost/ai_tracker
# SECRET_KEY=your_secret_key_for_jwt
```

### 2. Generate Required Keys

```bash
# Generate encryption key for storing API credentials
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output to ENCRYPTION_KEY in .env

# Generate JWT secret key
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output to SECRET_KEY in .env
```

### 3. Backend Setup (Flask/Python)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file in backend directory
cp ../.env backend/.env

# Initialize database
flask db upgrade

# Create initial admin user (optional)
python -c "from app import create_app, db; from models import User; app = create_app(); app.app_context().push(); User.create_admin('admin', 'admin@example.com', 'password')"

# Run development server
flask run
# Server will start on http://localhost:5000
```

### 4. Frontend Setup (React/Vue)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Update REACT_APP_API_URL in .env
REACT_APP_API_URL=http://localhost:5000/api

# Start development server
npm start
# App will open on http://localhost:3000
```

### 5. Using Docker Compose (Recommended for Full Stack)

```bash
# From project root directory
docker-compose up

# This will start:
# - Backend API on http://localhost:5000
# - Frontend on http://localhost:3000
# - PostgreSQL database on localhost:5432
# - Redis cache (optional)

# To stop:
docker-compose down

# To reset database:
docker-compose down -v
docker-compose up
```

---

## Stopping & Cleaning Up Local Dev Environment

### Stop Running Processes

```bash
# Kill Flask backend (port 5000) and React dev server (port 3000)
kill $(lsof -ti :5000) 2>/dev/null
kill $(lsof -ti :3000) 2>/dev/null

# Verify ports are free
lsof -i :5000 -i :3000 | grep LISTEN
# (no output = all clear)
```

### Free Up Disk Space

The installed dependencies are large (~555 MB) but fully regenerable from lock files.
Delete them when not actively developing:

```bash
# Remove Python virtual environment (~103 MB)
rm -rf backend/venv

# Remove Node.js dependencies (~452 MB)
rm -rf frontend/node_modules
```

> All source code is tracked in git. Nothing above is irreversible.

### Restore After Cleanup

```bash
# Backend
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run

# Frontend (new terminal)
cd frontend
. ~/.nvm/nvm.sh   # load nvm if not in PATH
npm install
npm start
```

> **macOS note:** Use `python3.11 -m venv venv` (not `python -m venv`) to ensure
> the Homebrew Python 3.11 binary is used. Node.js must be installed via nvm —
> `brew install node` is unreliable on macOS 13 (Ventura).

---

## Environment Variables (.env)

```bash
# Backend Configuration
FLASK_ENV=development
FLASK_APP=app.py
SECRET_KEY=your_jwt_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# Database
DATABASE_URL=postgresql://ai_user:ai_password@localhost:5432/ai_tracker
# OR for SQLite (development):
# DATABASE_URL=sqlite:///ai_tracker.db

# API Keys (these should be set by users in the UI, not in .env for production)
OPENAI_API_KEY=sk-your_key_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
GROQ_API_KEY=gsk-your_key_here

# Email Configuration (for alerts)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@aitooltracker.com

# Frontend Configuration
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_ENV=development

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Session/Cache
REDIS_URL=redis://localhost:6379/0  # Optional, for caching

# Security
CORS_ORIGINS=http://localhost:3000,http://localhost:5000
SESSION_TIMEOUT=3600  # 1 hour in seconds
```

---

## Database Initialization

### Creating Initial Service Definitions

```python
# scripts/seed_services.py
from app import create_app, db
from models import Service

app = create_app()
app.app_context().push()

services_data = [
    {
        "name": "ChatGPT",
        "api_provider": "OpenAI",
        "has_api": True,
        "pricing_model": {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }
    },
    {
        "name": "Claude",
        "api_provider": "Anthropic",
        "has_api": True,
        "pricing_model": {
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
        }
    },
    {
        "name": "Groq",
        "api_provider": "Groq",
        "has_api": True,
        "pricing_model": {"free": {"input": 0, "output": 0}}
    },
    {
        "name": "GitHub Copilot",
        "api_provider": "GitHub",
        "has_api": False,
        "pricing_model": {"subscription": 10}
    },
    {
        "name": "Perplexity",
        "api_provider": "Perplexity",
        "has_api": True,
        "pricing_model": {"free": {"queries": 5}, "pro": {"cost": 20}}
    }
]

for service_data in services_data:
    service = Service(**service_data)
    db.session.add(service)

db.session.commit()
print("Services initialized successfully!")
```

Run with:
```bash
python scripts/seed_services.py
```

---

## API Endpoints Overview

### Authentication
```
POST   /api/auth/login              - Login with email/password
POST   /api/auth/logout             - Logout current user
POST   /api/auth/register           - Register new user (if enabled)
GET    /api/auth/me                 - Get current user info
```

### Accounts
```
GET    /api/accounts                - List all tracked accounts
POST   /api/accounts                - Create new account
GET    /api/accounts/{id}           - Get account details
PUT    /api/accounts/{id}           - Update account
DELETE /api/accounts/{id}           - Delete account
POST   /api/accounts/{id}/test      - Test API connection
```

### Usage Data
```
GET    /api/usage                   - Get current usage summary
GET    /api/usage/history           - Get historical usage data
GET    /api/usage/by-service        - Usage breakdown by service
GET    /api/usage/forecast          - Projected usage to month-end
```

### Alerts
```
GET    /api/alerts                  - List all active alerts
POST   /api/alerts                  - Create new alert
PUT    /api/alerts/{id}             - Update alert
DELETE /api/alerts/{id}             - Delete alert
POST   /api/alerts/{id}/acknowledge - Mark alert as read
```

### Services
```
GET    /api/services                - List all available services
GET    /api/services/{id}           - Get service details
PUT    /api/services/{id}/pricing   - Update pricing model
```

### Reports & Export
```
GET    /api/reports/summary         - Monthly summary report
GET    /api/reports/detailed        - Detailed usage report
GET    /api/export/csv              - Export data as CSV
GET    /api/export/json             - Export data as JSON
```

---

## Common Development Tasks

### Adding a New Service

1. **Update Database Schema** (if needed):
```python
# models/service.py - modify as needed
```

2. **Add Service to Seed Data**:
```python
# scripts/seed_services.py - add service definition
```

3. **Create API Client**:
```python
# services/new_service.py
from services.base_service import BaseService

class NewServiceClient(BaseService):
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.newservice.com/v1"
    
    def get_usage(self):
        # Implement usage retrieval
        pass
    
    def validate_credentials(self):
        # Implement credential validation
        pass
```

4. **Register in Sync Job**:
```python
# jobs/sync_usage.py - add to service_clients dict
```

5. **Create Tests**:
```python
# tests/test_new_service.py
```

### Adding a New Alert Type

1. **Update Alert Model**:
```python
# models/alert.py - add new alert type to enum
ALERT_TYPES = [
    "approaching_limit",
    "limit_exceeded",
    "high_cost",
    "new_alert_type"  # Add here
]
```

2. **Implement Logic**:
```python
# utils/alert_generator.py - add alert generation logic
def check_new_alert_type(account):
    # Your logic here
    pass
```

3. **Create Frontend Component**:
```jsx
// frontend/src/components/alerts/NewAlertTypeDisplay.jsx
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test

# E2E tests (if set up)
npm run test:e2e
```

### Database Migrations

```bash
# Create new migration
flask db migrate -m "Add new_field to accounts"

# Review migration file: backend/migrations/versions/xxxx_add_new_field.py

# Apply migration
flask db upgrade

# Downgrade if needed
flask db downgrade
```

---

## Debugging Tips

### Backend Debugging (Flask)

```python
# Add breakpoints in your code
import pdb; pdb.set_trace()

# Or use debugpy for VS Code
import debugpy
debugpy.listen(("0.0.0.0", 5678))
debugpy.wait_for_client()
```

Enable in Flask:
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run
```

### Frontend Debugging

- Use React Developer Tools browser extension
- Chrome DevTools (F12) for network inspection
- Add console.log() statements or use debugger keyword

```javascript
debugger;  // Code execution will pause here if DevTools is open
```

### Checking Logs

```bash
# View backend logs
tail -f logs/app.log

# View Docker logs
docker-compose logs -f backend
docker-compose logs -f frontend

# View database connection issues
# Enable SQL logging in Flask:
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

---

## Performance Optimization

### Caching Strategy

```python
# Cache service pricing for 24 hours
@cache.cached(timeout=86400, key_prefix='service_pricing')
def get_service_pricing(service_id):
    return Service.query.get(service_id).pricing_model

# Cache user's recent usage for 30 minutes
@cache.cached(timeout=1800, key_prefix=f'user_usage_{current_user.id}')
def get_user_usage():
    return calculate_usage()
```

### Database Query Optimization

```python
# Use eager loading to avoid N+1 queries
accounts = Account.query.options(
    joinedload(Account.usage_records),
    joinedload(Account.alerts)
).all()

# Use pagination for large result sets
page = request.args.get('page', 1, type=int)
paginated = UsageRecord.query.paginate(page=page, per_page=50)
```

### Frontend Optimization

```javascript
// Lazy load components
const AnalyticsChart = React.lazy(() => import('./AnalyticsChart'));

// Memoize expensive computations
const MemoizedChart = React.memo(Chart, (prevProps, nextProps) => {
    return prevProps.data === nextProps.data;
});
```

---

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Static files compiled (frontend)
- [ ] HTTPS/TLS certificates installed
- [ ] CORS configuration set correctly
- [ ] Error logging configured (Sentry, etc.)
- [ ] Database backups configured
- [ ] Monitoring alerts set up
- [ ] Health check endpoint verified
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] API documentation generated

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'app'`
- **Solution**: Ensure you're in the `backend` directory and virtual environment is activated

**Issue**: `CORS policy: No 'Access-Control-Allow-Origin' header`
- **Solution**: Check CORS configuration in Flask app, ensure frontend URL is in CORS_ORIGINS

**Issue**: Database connection error
- **Solution**: Verify DATABASE_URL is correct, check if PostgreSQL is running

**Issue**: API key not working
- **Solution**: Verify key is correctly encrypted/decrypted, check service API documentation for format

**Issue**: Frontend shows blank page
- **Solution**: Check browser console for errors, verify REACT_APP_API_URL is correct

---

## Getting Help

1. Check logs: `tail -f logs/app.log`
2. Review API responses: Use Postman or curl to test endpoints
3. Check service API documentation for the latest authentication requirements
4. Review GitHub Issues at https://github.com/zebadee2kk/ai-cost-tracker/issues
5. Contact the development team with logs and steps to reproduce

---

## Next Steps After Setup

1. **Verify the system is running**:
   - Backend: `curl http://localhost:5000/api/health`
   - Frontend: Open `http://localhost:3000` in browser

2. **Create your first user account**:
   - Register via UI or create via script

3. **Add your first service account**:
   - OpenAI recommended for first test (has best API documentation)

4. **Configure alerts**:
   - Set alert thresholds for your needs

5. **Monitor dashboard**:
   - Verify data is syncing correctly

---

## Support & Documentation

- **Backend API Docs**: http://localhost:5000/api/docs (Swagger/OpenAPI)
- **Frontend Storybook**: http://localhost:6006 (if set up)
- **Service API Docs**: See `docs/api-integration-guide.md`
- **Project Plan**: See `docs/ai-tool-tracker-plan.md`
- **GitHub Repository**: https://github.com/zebadee2kk/ai-cost-tracker
