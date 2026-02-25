# Phase 3: GitHub Actions CI/CD Pipeline - Implementation Guide

**Feature Priority**: P1 (High)  
**Estimated Effort**: 1 week  
**Sprint**: 3.1  
**Dependencies**: None

---

## 1. Problem Statement

### Current Challenges
- No automated testing on pull requests
- Manual verification required before merging
- No visibility into test coverage trends
- Risk of breaking changes reaching production
- No automated Docker image builds
- Manual deployment process error-prone

### Goals
- Automate testing on every PR and push
- Enforce minimum test coverage (>80%)
- Catch security vulnerabilities early
- Automate Docker image publishing
- Provide fast feedback to developers (<5 min)

---

## 2. Best Practices

### CI/CD Principles[cite:11][cite:14]

**Test Automation**:
- Run tests on every PR and commit to main
- Fail fast: stop pipeline on first failure
- Parallel execution when possible
- Cache dependencies for speed

**Coverage Requirements**:
- Backend: >80% line coverage minimum
- Frontend: >70% line coverage minimum
- Track coverage trends over time
- Fail PR if coverage decreases

**Security Scanning**[cite:14]:
- Python: Bandit for backend code
- JavaScript: npm audit for frontend dependencies
- Docker: Trivy for container image scanning
- Dependency vulnerability checking

**Build Optimization**:
- Matrix builds for multiple Python versions (optional)
- Dependency caching (pip, npm)
- Artifact retention for debugging
- Docker layer caching

---

## 3. Technology Stack

### GitHub Actions Components

| Action | Purpose | Cost |
|--------|---------|------|
| **actions/checkout@v4** | Clone repository | Free |
| **actions/setup-python@v5** | Install Python | Free |
| **actions/setup-node@v4** | Install Node.js | Free |
| **codecov/codecov-action@v4** | Upload coverage | Free (public repos) |
| **docker/build-push-action@v5** | Build/push Docker images | Free |
| **aquasecurity/trivy-action@master** | Security scanning | Free |

### GitHub Actions Limits (Free Tier)

- **2,000 minutes/month** for private repos
- **Unlimited** for public repos
- **Storage**: 500 MB artifacts
- **Concurrency**: 20 jobs (public) / 5 jobs (private)

**Expected Usage**: ~30 min/day = 900 min/month (well within limits)

---

## 4. Pipeline Architecture

### Workflow Structure

```
Pull Request / Push to main
  │
  ├───── Lint & Format Check
  │       ├─ Backend: flake8, black --check
  │       └─ Frontend: eslint, prettier --check
  │
  ├───── Backend Tests
  │       ├─ Setup PostgreSQL service
  │       ├─ Install dependencies
  │       ├─ Run pytest with coverage
  │       ├─ Fail if coverage <80%
  │       └─ Upload to Codecov
  │
  ├───── Frontend Tests
  │       ├─ Install dependencies
  │       ├─ Run Jest tests
  │       ├─ Check build succeeds
  │       └─ Upload coverage
  │
  ├───── Security Scan
  │       ├─ Bandit (Python)
  │       ├─ npm audit (JavaScript)
  │       └─ Trivy (Docker images)
  │
  └───── Docker Build
          ├─ Build backend image
          ├─ Build frontend image
          └─ Push to Docker Hub (main branch only)
```

---

## 5. Implementation

### File: `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

env:
  PYTHON_VERSION: '3.10'
  NODE_VERSION: '18'

jobs:
  # Job 1: Lint and Format Check
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      # Backend linting
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install backend lint tools
        run: |
          cd backend
          pip install flake8 black
      
      - name: Run flake8
        run: |
          cd backend
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 . --count --max-line-length=120 --statistics
      
      - name: Check black formatting
        run: |
          cd backend
          black --check .
      
      # Frontend linting
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run ESLint
        run: |
          cd frontend
          npm run lint
      
      - name: Check Prettier formatting
        run: |
          cd frontend
          npm run format:check

  # Job 2: Backend Tests
  backend-tests:
    name: Backend Tests
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db
          SECRET_KEY: test-secret-key-for-ci
          ENCRYPTION_KEY: test-encryption-key-32-bytes-long
        run: |
          cd backend
          pytest tests/ -v --cov=. --cov-report=xml --cov-report=term --cov-fail-under=80
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml
          flags: backend
          name: backend-coverage
          fail_ci_if_error: false
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
      
      - name: Upload coverage artifact
        uses: actions/upload-artifact@v4
        with:
          name: backend-coverage
          path: backend/htmlcov/
          retention-days: 7

  # Job 3: Frontend Tests
  frontend-tests:
    name: Frontend Tests
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage --watchAll=false
      
      - name: Check build
        run: |
          cd frontend
          npm run build
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./frontend/coverage/coverage-final.json
          flags: frontend
          name: frontend-coverage
          fail_ci_if_error: false
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  # Job 4: Security Scan
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      # Python security scan with Bandit
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install Bandit
        run: pip install bandit[toml]
      
      - name: Run Bandit
        run: |
          cd backend
          bandit -r . -f json -o bandit-report.json --exclude ./tests,./venv || true
          bandit -r . --exclude ./tests,./venv
      
      - name: Upload Bandit report
        uses: actions/upload-artifact@v4
        with:
          name: bandit-security-report
          path: backend/bandit-report.json
          retention-days: 30
      
      # JavaScript security scan
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Run npm audit
        run: |
          cd frontend
          npm audit --audit-level=high || true
      
      # Docker image scan with Trivy
      - name: Build Docker image for scanning
        run: |
          docker build -t ai-cost-tracker-backend:test -f backend/Dockerfile backend/
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'ai-cost-tracker-backend:test'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  # Job 5: Docker Build and Push
  docker:
    name: Docker Build & Push
    runs-on: ubuntu-latest
    needs: [lint, backend-tests, frontend-tests, security]
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master')
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-backend:latest
            ${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-backend:${{ github.sha }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-backend:buildcache
          cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-backend:buildcache,mode=max
      
      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-frontend:latest
            ${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-frontend:${{ github.sha }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-frontend:buildcache
          cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/ai-cost-tracker-frontend:buildcache,mode=max
```

---

## 6. Required GitHub Secrets

### Setup Instructions

1. Navigate to **Settings → Secrets and variables → Actions**
2. Add the following secrets:

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `CODECOV_TOKEN` | Codecov upload token | Sign up at [codecov.io](https://codecov.io), add repo |
| `DOCKER_USERNAME` | Docker Hub username | Your Docker Hub account |
| `DOCKER_PASSWORD` | Docker Hub token/password | Generate at [hub.docker.com/settings/security](https://hub.docker.com/settings/security) |

### Optional Secrets

| Secret Name | Use Case |
|-------------|----------|
| `SLACK_WEBHOOK` | Send build notifications to Slack |
| `DEPLOY_SSH_KEY` | Automated deployment to server |

---

## 7. Frontend Configuration

### Update `frontend/package.json`

Add missing scripts:

```json
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "lint": "eslint src/ --ext .js,.jsx",
    "lint:fix": "eslint src/ --ext .js,.jsx --fix",
    "format": "prettier --write \"src/**/*.{js,jsx,json,css}\"",
    "format:check": "prettier --check \"src/**/*.{js,jsx,json,css}\""
  },
  "devDependencies": {
    "eslint": "^8.57.0",
    "prettier": "^3.2.5"
  }
}
```

### Create `.eslintrc.json`

```json
{
  "extends": ["react-app"],
  "rules": {
    "no-console": "warn",
    "no-unused-vars": "warn"
  }
}
```

### Create `.prettierrc`

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2
}
```

---

## 8. Backend Configuration

### Update `backend/requirements.txt`

Add test dependencies:

```txt
# Existing dependencies...

# Testing (dev)
pytest>=8.0.0
pytest-cov>=4.1.0
pytest-flask>=1.3.0

# Linting (dev)
flake8>=7.0.0
black>=24.0.0
bandit[toml]>=1.7.6
```

### Create `backend/.flake8`

```ini
[flake8]
max-line-length = 120
exclude = 
    venv,
    migrations,
    __pycache__,
    *.pyc
ignore = E203, W503
```

### Create `backend/pyproject.toml`

```toml
[tool.black]
line-length = 120
target-version = ['py310']
exclude = '''
/(
    \.git
  | \.venv
  | migrations
  | __pycache__
)/
'''

[tool.bandit]
exclude_dirs = ["tests", "venv"]
skips = ["B101"]  # Skip assert_used warnings in tests
```

---

## 9. Badge Configuration

### Add to README.md

```markdown
[![CI/CD](https://github.com/zebadee2kk/ai-cost-tracker/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/zebadee2kk/ai-cost-tracker/actions)
[![codecov](https://codecov.io/gh/zebadee2kk/ai-cost-tracker/branch/master/graph/badge.svg)](https://codecov.io/gh/zebadee2kk/ai-cost-tracker)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
```

---

## 10. Testing the Pipeline

### Local Pre-commit Testing

```bash
# Backend
cd backend
flake8 .
black --check .
pytest tests/ -v --cov=.

# Frontend
cd frontend
npm run lint
npm run format:check
npm test -- --coverage --watchAll=false
npm run build
```

### Trigger CI Manually

```bash
# Create test branch
git checkout -b test/ci-pipeline

# Make trivial change
echo "# CI Test" >> README.md

# Push and create PR
git add .
git commit -m "test: Trigger CI pipeline"
git push origin test/ci-pipeline

# Create PR on GitHub
# Verify all checks pass
```

---

## 11. Monitoring & Alerts

### GitHub Actions Notifications

**Built-in**:
- Email notifications on workflow failure
- GitHub UI shows status on PRs
- Status badges in README

**Optional Slack Integration**:

Add to workflow:

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'CI Pipeline Failed!'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Codecov Configuration

Create `codecov.yml` in repo root:

```yaml
coverage:
  status:
    project:
      default:
        target: 80%
        threshold: 2%
    patch:
      default:
        target: 80%

comment:
  layout: "header, diff, files"
  behavior: default
  require_changes: false
```

---

## 12. Performance Optimization

### Caching Strategy

**Python dependencies**:
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'
    cache-dependency-path: backend/requirements.txt
```

**Node dependencies**:
```yaml
- uses: actions/setup-node@v4
  with:
    cache: 'npm'
    cache-dependency-path: frontend/package-lock.json
```

**Docker layers**:
```yaml
cache-from: type=registry,ref=user/image:buildcache
cache-to: type=registry,ref=user/image:buildcache,mode=max
```

### Expected Timings

| Job | Duration | Optimization |
|-----|----------|-------------|
| Lint | ~30s | Parallel with tests |
| Backend Tests | ~2 min | PostgreSQL caching, pip cache |
| Frontend Tests | ~1 min | npm cache |
| Security Scan | ~1 min | Image caching |
| Docker Build | ~3 min | Layer caching |
| **Total** | **~5 min** | Parallel execution |

---

## 13. Troubleshooting

### Common Issues

**Issue**: Tests fail in CI but pass locally
- **Cause**: Environment differences (DB, secrets)
- **Fix**: Ensure test fixtures use CI environment variables

**Issue**: Coverage fails to upload
- **Cause**: Missing CODECOV_TOKEN secret
- **Fix**: Add secret in GitHub repo settings

**Issue**: Docker build times out
- **Cause**: Large image, no caching
- **Fix**: Enable layer caching, use multi-stage builds

**Issue**: npm audit fails with high severity
- **Cause**: Vulnerable dependencies
- **Fix**: Run `npm audit fix` locally, commit updates

---

## 14. Implementation Checklist

### Week 1 Tasks

**Day 1-2**: Setup
- [ ] Create `.github/workflows/ci.yml`
- [ ] Add GitHub secrets (Codecov, Docker Hub)
- [ ] Configure linting tools (flake8, ESLint)

**Day 3**: Backend CI
- [ ] Add backend test job with PostgreSQL
- [ ] Configure coverage reporting
- [ ] Test with real PR

**Day 4**: Frontend CI
- [ ] Add frontend test job
- [ ] Configure build check
- [ ] Add coverage upload

**Day 5**: Security & Docker
- [ ] Add security scanning job
- [ ] Add Docker build/push job
- [ ] Add status badges to README
- [ ] Documentation

---

## 15. Cost Analysis

### GitHub Actions Minutes

**Per Pipeline Run**: ~5 minutes  
**Expected Runs**: 6/day (3 PRs + 3 commits to main)  
**Monthly Usage**: 6 × 5 min × 30 days = **900 minutes**

**Free Tier**: 2,000 minutes/month for private repos  
**Overage Cost**: $0 (well within free tier)

### Third-Party Services

| Service | Cost | Notes |
|---------|------|-------|
| **Codecov** | Free | Public repos unlimited |
| **Docker Hub** | Free | 1 private repo, unlimited public |
| **GitHub Actions** | Free | 2,000 min/mo private |

**Total Monthly Cost**: **$0**

---

## 16. Success Criteria

- ✅ CI pipeline runs on every PR
- ✅ All tests pass before merge allowed
- ✅ Coverage stays above 80% backend, 70% frontend
- ✅ Security scans catch vulnerabilities
- ✅ Docker images auto-published on merge to main
- ✅ Pipeline completes in <5 minutes
- ✅ Zero false positives causing failed builds
- ✅ Team understands how to debug CI failures

---

## 17. Future Enhancements (Phase 4)

- **Deployment automation**: Auto-deploy to staging on merge
- **E2E testing**: Playwright/Cypress integration
- **Performance testing**: Load testing with k6
- **Release automation**: Auto-create GitHub releases
- **Dependency updates**: Dependabot auto-merge
- **Matrix builds**: Test on Python 3.10, 3.11, 3.12

---

**Status**: 📋 Specification Complete | Ready for Implementation
