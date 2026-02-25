# Phase 3: GitHub Actions CI/CD Pipeline - Implementation Guide

**Created**: February 25, 2026  
**Priority**: P1  
**Effort**: 1 week  
**Dependencies**: None

---

## 1. Overview

### Purpose
Establish automated testing, security scanning, and deployment pipeline for the AI Cost Tracker using GitHub Actions.

### Goals
- **Quality**: Catch bugs before merge with automated testing
- **Security**: Identify vulnerabilities early
- **Confidence**: >80% test coverage enforced
- **Speed**: <5 minute CI pipeline runtime
- **Cost**: Stay within GitHub Actions free tier (2,000 min/month)

### Success Criteria
- All PRs must pass CI before merge
- Test coverage maintained >80% backend, >70% frontend
- Zero high-severity vulnerabilities in production
- <3 false positive security alerts per month

---

## 2. Pipeline Architecture

### Workflow Stages

```
┌───────────────────┐
│   Code Push/PR      │
└─────────┬──────────┘
           │
     ┌─────┼─────┐
     │           │
┌────┴────┐   ┌─┴──────────┐
│ Backend   │   │  Frontend     │
│ Tests     │   │  Tests        │
└────┬────┘   └─┬─────────┘
     │           │
     └───┬───────┴───┐
         │               │
    ┌────┴─────┐     ┌───┴──────────┐
    │  Security  │     │  Docker Build  │
    │  Scan      │     │  (main only)   │
    └──────────┘     └───────────────┘
```

### Job Parallelization
- Backend tests and frontend tests run in parallel
- Security scan runs in parallel with tests
- Docker build only on main branch after all checks pass

---

## 3. Workflow Configuration

### Main CI/CD Workflow

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.10'
  NODE_VERSION: '18'
  POSTGRES_VERSION: '15'

jobs:
  backend-tests:
    name: Backend Tests (Python)
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      
      - name: Run migrations
        run: |
          cd backend
          flask db upgrade
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/testdb
          FLASK_APP: app.py
          SECRET_KEY: test-secret-key-for-ci-only
          ENCRYPTION_KEY: test-encryption-key-32-chars!!
      
      - name: Run tests with coverage
        run: |
          cd backend
          pytest tests/ -v \
            --cov=. \
            --cov-report=xml \
            --cov-report=html \
            --cov-report=term-missing
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/testdb
          FLASK_APP: app.py
          SECRET_KEY: test-secret-key-for-ci-only
          ENCRYPTION_KEY: test-encryption-key-32-chars!!
      
      - name: Check coverage threshold
        run: |
          cd backend
          coverage report --fail-under=80
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml
          flags: backend
          name: backend-coverage
          fail_ci_if_error: false
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
      
      - name: Archive coverage report
        uses: actions/upload-artifact@v4
        with:
          name: backend-coverage-report
          path: backend/htmlcov/
          retention-days: 30

  frontend-tests:
    name: Frontend Tests (React)
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Node.js ${{ env.NODE_VERSION }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run linter
        run: |
          cd frontend
          npm run lint
      
      - name: Run tests with coverage
        run: |
          cd frontend
          npm test -- --coverage --watchAll=false
      
      - name: Check coverage threshold
        run: |
          cd frontend
          # Jest will fail if coverage below thresholds in package.json
      
      - name: Build production bundle
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
      
      - name: Archive build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: frontend-build
          path: frontend/build/
          retention-days: 7

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Run Bandit (Python security)
        run: |
          pip install bandit[toml]
          bandit -r backend/ -ll -f json -o bandit-report.json || true
          bandit -r backend/ -ll
      
      - name: Upload Bandit report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: bandit-security-report
          path: bandit-report.json
          retention-days: 30
      
      - name: Run npm audit (JavaScript)
        run: |
          cd frontend
          npm audit --audit-level=high --json > ../npm-audit.json || true
          npm audit --audit-level=high
      
      - name: Upload npm audit report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: npm-audit-report
          path: npm-audit.json
          retention-days: 30
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  docker-build:
    name: Docker Build & Push
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests, security-scan]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Extract version from commit
        id: version
        run: |
          echo "sha_short=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT
          echo "date=$(date +'%Y%m%d')" >> $GITHUB_OUTPUT
      
      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: |
            ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-backend:latest
            ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-backend:${{ steps.version.outputs.date }}-${{ steps.version.outputs.sha_short }}
          cache-from: type=registry,ref=${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-backend:latest
          cache-to: type=inline
      
      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: |
            ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-frontend:latest
            ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-frontend:${{ steps.version.outputs.date }}-${{ steps.version.outputs.sha_short }}
          cache-from: type=registry,ref=${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-frontend:latest
          cache-to: type=inline
      
      - name: Scan backend image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-backend:latest
          format: 'table'
          severity: 'CRITICAL,HIGH'
      
      - name: Scan frontend image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-frontend:latest
          format: 'table'
          severity: 'CRITICAL,HIGH'
```

---

## 4. Coverage Configuration

### Backend Coverage (.coveragerc)

```ini
# backend/.coveragerc
[run]
source = .
omit =
    */tests/*
    */test_*.py
    */__pycache__/*
    */venv/*
    */env/*
    */migrations/*
    setup.py
    */config.py

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

### Frontend Coverage (package.json)

```json
{
  "jest": {
    "collectCoverageFrom": [
      "src/**/*.{js,jsx}",
      "!src/index.js",
      "!src/reportWebVitals.js",
      "!src/**/*.test.{js,jsx}"
    ],
    "coverageThreshold": {
      "global": {
        "branches": 70,
        "functions": 70,
        "lines": 70,
        "statements": 70
      }
    },
    "coverageReporters": [
      "text",
      "lcov",
      "html",
      "json"
    ]
  }
}
```

---

## 5. Security Scanning Configuration

### Bandit Configuration

```toml
# backend/pyproject.toml or .bandit
[tool.bandit]
exclude_dirs = [
    "/tests",
    "/venv",
    "/env"
]
skips = [
    "B404",  # Import subprocess (needed for scheduler)
    "B603"   # Subprocess without shell (safe usage)
]
```

### Trivy Configuration

```yaml
# .trivyignore (optional - use sparingly)
# Ignore specific CVEs if false positives
# CVE-2024-XXXXX
```

---

## 6. Repository Secrets Setup

### Required Secrets

In GitHub repo: **Settings → Secrets and variables → Actions**

| Secret Name | Description | How to Generate |
|-------------|-------------|------------------|
| `DOCKERHUB_USERNAME` | Docker Hub username | Your Docker Hub account |
| `DOCKERHUB_TOKEN` | Docker Hub access token | Docker Hub → Account Settings → Security → New Access Token |
| `CODECOV_TOKEN` | Codecov upload token | Codecov.io → Repository Settings → Copy token |

### Optional Secrets (Phase 4)

| Secret Name | Description |
|-------------|-------------|
| `DEPLOY_SSH_KEY` | SSH key for deployment server |
| `SLACK_WEBHOOK` | Slack webhook for CI notifications |
| `AWS_ACCESS_KEY_ID` | AWS credentials for deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |

---

## 7. Branch Protection Rules

### Configuration

GitHub repo: **Settings → Branches → Add rule**

**Branch name pattern**: `main`

**Protection rules**:
- ✅ Require a pull request before merging
  - ✅ Require approvals: 1
  - ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging
  - ✅ Require branches to be up to date before merging
  - **Required checks**:
    - Backend Tests (Python)
    - Frontend Tests (React)
    - Security Scanning
- ✅ Require conversation resolution before merging
- ❌ Require signed commits (optional)
- ❌ Require linear history (optional)
- ✅ Include administrators

---

## 8. Badge Configuration

### Add to README.md

```markdown
[![CI/CD](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/zebadee2kk/ai-cost-tracker/branch/main/graph/badge.svg)](https://codecov.io/gh/zebadee2kk/ai-cost-tracker)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
```

---

## 9. Local Development Workflow

### Run Tests Locally Before Push

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=. --cov-report=term-missing
coverage report --fail-under=80

# Frontend tests
cd frontend
npm test -- --coverage --watchAll=false

# Security scans
pip install bandit
bandit -r backend/ -ll

cd frontend
npm audit --audit-level=high
```

### Pre-commit Hooks (Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        files: ^backend/
  
  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        files: ^backend/
        args: ['--max-line-length=120']
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        files: ^backend/
        args: ['-ll']
EOF

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 10. Monitoring & Notifications

### GitHub Actions Notifications

```yaml
# Add to end of ci.yml
  notify-on-failure:
    name: Notify on Failure
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests, security-scan]
    if: failure() && github.ref == 'refs/heads/main'
    
    steps:
      - name: Send Slack notification
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'CI Pipeline Failed on main branch!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        if: always()
```

### Codecov Dashboard

- View coverage trends: https://codecov.io/gh/zebadee2kk/ai-cost-tracker
- Set coverage targets per file/directory
- Track coverage over time
- Comment coverage changes on PRs

---

## 11. Cost Optimization

### GitHub Actions Free Tier

- **Public repos**: Unlimited minutes
- **Private repos**: 2,000 minutes/month free

### Estimated Usage

| Job | Duration | Runs/Month | Total |
|-----|----------|------------|-------|
| Backend Tests | 3 min | 40 | 120 min |
| Frontend Tests | 2 min | 40 | 80 min |
| Security Scan | 2 min | 40 | 80 min |
| Docker Build | 5 min | 20 | 100 min |
| **Total** | | | **380 min/month** |

**Verdict**: Well within free tier limits

### Optimization Tips

1. **Cache dependencies**: Use `cache: 'pip'` and `cache: 'npm'`
2. **Parallel jobs**: Run tests in parallel
3. **Selective triggers**: Don't run Docker build on every PR
4. **Matrix strategy**: Test multiple Python/Node versions only on main
5. **Artifact retention**: Keep artifacts for 7-30 days, not forever

---

## 12. Troubleshooting

### Common Issues

**Issue**: Backend tests fail with database connection error  
**Solution**: Ensure PostgreSQL service health check passes before running tests

**Issue**: Frontend build fails with memory error  
**Solution**: Add `NODE_OPTIONS=--max_old_space_size=4096` to build step

**Issue**: Codecov upload fails  
**Solution**: Check `CODECOV_TOKEN` secret is set correctly

**Issue**: Docker Hub push fails with authentication error  
**Solution**: Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets

**Issue**: Security scan reports false positives  
**Solution**: Add exceptions to `.trivyignore` or `bandit` config (document why)

---

## 13. Implementation Checklist

### Day 1-2: Workflow Setup
- [x] Create `.github/workflows/ci.yml`
- [x] Backend uses SQLite in-memory (TestingConfig) — no external service required
- [x] Add Python setup with pip caching
- [x] Add Node.js setup with npm caching
- [x] Test backend job runs successfully
- [x] Test frontend job runs successfully

### Day 3: Security Scanning
- [x] Add Bandit security scan (`backend/pyproject.toml` configures skip rules)
- [x] Add npm audit scan (non-blocking at high severity)
- [x] Add Trivy vulnerability scanner (filesystem scan + SARIF output)
- [x] Configure Trivy SARIF upload to GitHub Security
- [x] Test security scan jobs

### Day 4: Coverage Reporting
- [x] Create `backend/.coveragerc` with omit rules and 80% threshold
- [x] Add Jest coverage thresholds (70%) to `frontend/package.json`
- [x] Configure Codecov upload for backend (`coverage.xml`)
- [x] Configure Codecov upload for frontend (`coverage-final.json`)
- [x] Add CI/CD and Codecov badges to README.md
- [ ] **Action needed**: Add `CODECOV_TOKEN` secret in GitHub repo settings
- [ ] **Action needed**: Verify coverage reports on Codecov dashboard after first run

### Day 5: Docker Build
- [x] Docker build job configured in `ci.yml` (runs on main branch pushes only)
- [x] Backend and frontend images with versioned tags
- [x] Post-push Trivy image scan configured
- [ ] **Action needed**: Add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets

### Day 6-7: Polish & Documentation
- [ ] **Action needed**: Configure branch protection rules (see Section 7)
- [x] CI/CD badge added to README.md
- [x] Codecov badge added to README.md
- [x] Troubleshooting guide updated (see Section 12)
- [x] Secrets setup documented (see Section 6)
- [x] Local CI commands documented (see Section 9)

---

## 14. Future Enhancements

### Phase 4+ Ideas

**Deployment Automation**
- Auto-deploy to staging on develop branch
- Auto-deploy to production on main branch (with approval)
- Rollback mechanism for failed deployments

**Performance Testing**
- Load testing with Locust or Artillery
- Frontend performance budget (Lighthouse CI)
- API response time monitoring

**Advanced Security**
- SAST with Semgrep or CodeQL
- Dependency review action
- Secret scanning
- Container signing with Cosign

**Notifications**
- Slack notifications for CI status
- Email notifications for security vulnerabilities
- GitHub Discussions posts for releases

---

**Document Status**: ✅ Implemented (Feb 25, 2026)
**Implementation Branch**: `claude/phase-3-implementation-hLBRj`
**Workflow File**: `.github/workflows/ci.yml`
**Coverage Config**: `backend/.coveragerc`, `frontend/package.json` (jest section)
**Security Config**: `backend/pyproject.toml` (bandit)
**Cost**: $0 (GitHub Actions free tier)
**Remaining Actions**: Add `CODECOV_TOKEN`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` secrets; configure branch protection rules

### Implementation Notes

- Backend tests use SQLite in-memory (`TestingConfig`) rather than PostgreSQL — this matches the existing test setup in `conftest.py` and keeps CI fast without external services.
- Frontend linting uses `--if-present` flag so CI doesn't fail if no lint script is defined; linting also runs implicitly during `npm run build`.
- The `notify-on-failure` Slack job is conditional on `SLACK_WEBHOOK` secret being set; it silently skips if not configured.
- Docker build only runs on `push` to `main` (not on PRs) to conserve Docker Hub rate limits.
