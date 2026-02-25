# Phase 3: GitHub Actions CI/CD Pipeline - Implementation Guide

**Feature Priority**: P1 (High Priority)  
**Estimated Effort**: 1 week  
**Dependencies**: None  
**Target Sprint**: 3.1 (Week 3)

---

## 1. Problem Statement

### Current Limitations
- No automated testing on pull requests
- Manual test execution required
- No coverage tracking over time
- No automated security scanning
- No consistent build validation
- Deployment is manual process

### Business Value
- **High**: Prevents bugs from reaching production
- Increases developer confidence
- Reduces manual QA time by 70%
- Catches security vulnerabilities early
- Enforces code quality standards
- Enables continuous delivery

---

## 2. Best Practices & Industry Standards

### CI/CD Pipeline Principles

1. **Fast Feedback**: Pipeline completes in <5 minutes
2. **Fail Fast**: Run fastest tests first
3. **Parallel Execution**: Run independent jobs concurrently
4. **Reproducible Builds**: Same code = same result
5. **Security First**: Scan before merge
6. **Coverage Thresholds**: Enforce minimum 80% coverage

### GitHub Actions Best Practices

- Use specific action versions (not `@latest`)
- Cache dependencies for speed
- Store secrets in GitHub Secrets
- Use matrix builds for multi-version testing
- Fail builds on warnings (strict mode)
- Upload artifacts for debugging

---

## 3. CI/CD Workflow Design

### Pipeline Architecture

```yaml
Triggers: [push, pull_request] on branches [main, develop]

Jobs:
  1. backend-tests (PostgreSQL service)
     ├─ Setup Python 3.10
     ├─ Install dependencies (cached)
     ├─ Run pytest with coverage
     ├─ Upload coverage to Codecov
     └─ Fail if coverage <80%

  2. frontend-tests
     ├─ Setup Node.js 18
     ├─ Install dependencies (cached)
     ├─ Run Jest tests
     ├─ Check ESLint
     └─ Build frontend

  3. security-scan
     ├─ Bandit (Python)
     ├─ npm audit (JavaScript)
     └─ Trivy (Docker images)

  4. docker-build (only on main branch)
     ├─ Build backend image
     ├─ Build frontend image
     └─ Push to Docker Hub
```

### Workflow Execution Time

| Job | Estimated Time | Can Parallelize |
|-----|----------------|------------------|
| backend-tests | 2-3 min | Yes |
| frontend-tests | 1-2 min | Yes |
| security-scan | 1-2 min | Yes |
| docker-build | 3-5 min | No (depends on tests) |
| **Total** | **4-7 min** | |

---

## 4. Complete Workflow Implementation

### `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.10'
  NODE_VERSION: '18'

jobs:
  backend-tests:
    name: Backend Tests (Python + PostgreSQL)
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: testuser
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
          cache-dependency-path: backend/requirements.txt
      
      - name: Install dependencies
        run: |
          cd backend
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          SECRET_KEY: test-secret-key-for-ci
          ENCRYPTION_KEY: ${{ secrets.CI_ENCRYPTION_KEY }}
        run: |
          cd backend
          pytest tests/ \
            --cov=. \
            --cov-report=xml \
            --cov-report=html \
            --cov-report=term-missing \
            --junitxml=test-results.xml \
            -v
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml
          flags: backend
          fail_ci_if_error: true
          token: ${{ secrets.CODECOV_TOKEN }}
      
      - name: Check coverage threshold
        run: |
          cd backend
          coverage report --fail-under=80
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: backend-test-results
          path: backend/test-results.xml
      
      - name: Upload coverage HTML report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: backend-coverage-html
          path: backend/htmlcov/

  frontend-tests:
    name: Frontend Tests (React + Jest)
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
      
      - name: Run ESLint
        run: |
          cd frontend
          npm run lint
      
      - name: Run tests with coverage
        run: |
          cd frontend
          npm test -- --coverage --watchAll=false
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./frontend/coverage/coverage-final.json
          flags: frontend
          fail_ci_if_error: false
          token: ${{ secrets.CODECOV_TOKEN }}
      
      - name: Build frontend
        run: |
          cd frontend
          npm run build
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: frontend-build
          path: frontend/build/

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Run Bandit (Python security linter)
        run: |
          pip install bandit[toml]
          bandit -r backend/ -ll -f json -o bandit-report.json || true
          bandit -r backend/ -ll
      
      - name: Upload Bandit report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bandit-security-report
          path: bandit-report.json
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Run npm audit
        run: |
          cd frontend
          npm audit --audit-level=high
      
      - name: Run Trivy vulnerability scanner (filesystem)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'HIGH,CRITICAL'
      
      - name: Upload Trivy results to GitHub Security
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  docker-build:
    name: Build and Push Docker Images
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests, security-scan]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Extract metadata (tags, labels)
        id: meta-backend
        uses: docker/metadata-action@v5
        with:
          images: ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-backend
          tags: |
            type=sha,prefix={{branch}}-
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ${{ steps.meta-backend.outputs.tags }}
          labels: ${{ steps.meta-backend.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Extract metadata for frontend
        id: meta-frontend
        uses: docker/metadata-action@v5
        with:
          images: ${{ secrets.DOCKERHUB_USERNAME }}/ai-cost-tracker-frontend
          tags: |
            type=sha,prefix={{branch}}-
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ${{ steps.meta-frontend.outputs.tags }}
          labels: ${{ steps.meta-frontend.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 5. GitHub Secrets Configuration

### Required Secrets

Navigate to **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | How to Generate |
|-------------|-------------|------------------|
| `CODECOV_TOKEN` | Codecov upload token | Get from codecov.io after linking repo |
| `DOCKERHUB_USERNAME` | Docker Hub username | Your Docker Hub account |
| `DOCKERHUB_TOKEN` | Docker Hub access token | Docker Hub → Account Settings → Security |
| `CI_ENCRYPTION_KEY` | Test encryption key | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

### Setting Up Codecov

1. Visit [codecov.io](https://codecov.io) and sign in with GitHub
2. Add your repository
3. Copy the upload token
4. Add to GitHub Secrets as `CODECOV_TOKEN`
5. Add Codecov badge to README:
   ```markdown
   [![codecov](https://codecov.io/gh/zebadee2kk/ai-cost-tracker/branch/main/graph/badge.svg)](https://codecov.io/gh/zebadee2kk/ai-cost-tracker)
   ```

### Setting Up Docker Hub

1. Create Docker Hub account at [hub.docker.com](https://hub.docker.com)
2. Go to **Account Settings → Security → New Access Token**
3. Name: "GitHub Actions CI", Permissions: Read & Write
4. Copy token immediately (won't be shown again)
5. Add username and token to GitHub Secrets

---

## 6. Cost Analysis

### GitHub Actions Free Tier

| Plan | Minutes/Month | Cost |
|------|---------------|------|
| **Public repos** | Unlimited | Free ✅ |
| **Private repos (Free)** | 2,000 minutes | Free |
| **Private repos (Pro)** | 3,000 minutes | Included |

### Estimated Usage (Private Repo)

- Pipeline duration: ~5 minutes
- Runs per day: ~10 (PRs + merges)
- Monthly usage: 5 min × 10 runs × 22 days = **1,100 minutes/month**
- **Verdict**: Well within free tier ✅

### External Service Costs

| Service | Plan | Cost |
|---------|------|------|
| **Codecov** | Open source | Free ✅ |
| **Docker Hub** | Free tier | Free ✅ (1 private repo, unlimited public) |
| **Trivy scanning** | Built into GitHub | Free ✅ |

**Total Monthly Cost**: $0 🎉

---

## 7. Badge Integration

### README.md Badges

Add to top of README after existing badges:

```markdown
[![CI/CD](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/zebadee2kk/ai-cost-tracker/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/zebadee2kk/ai-cost-tracker/branch/main/graph/badge.svg)](https://codecov.io/gh/zebadee2kk/ai-cost-tracker)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/zebadee2kk/ai-cost-tracker/actions)
```

---

## 8. Branch Protection Rules

### Recommended Settings

Navigate to **Settings → Branches → Add branch protection rule**

**Branch name pattern**: `main`

Enable:
- ☑️ Require a pull request before merging
- ☑️ Require approvals: 1
- ☑️ Dismiss stale approvals
- ☑️ Require status checks to pass before merging
  - Required checks:
    - `backend-tests`
    - `frontend-tests`
    - `security-scan`
- ☑️ Require branches to be up to date
- ☑️ Require conversation resolution
- ☑️ Do not allow bypassing the above settings

---

## 9. Testing the Pipeline

### Initial Setup Checklist

1. ☐ Create `.github/workflows/ci.yml` file
2. ☐ Add all required GitHub Secrets
3. ☐ Set up Codecov integration
4. ☐ Set up Docker Hub account
5. ☐ Push to `main` branch
6. ☐ Verify workflow runs successfully
7. ☐ Enable branch protection rules

### Testing Steps

```bash
# 1. Create feature branch
git checkout -b test/ci-pipeline

# 2. Make small change
echo "# CI Test" >> README.md
git add README.md
git commit -m "test: verify CI pipeline"

# 3. Push and create PR
git push origin test/ci-pipeline

# 4. Observe workflow run on GitHub
# Go to: Actions tab → CI/CD Pipeline workflow

# 5. Verify all jobs pass
# backend-tests: ✅
# frontend-tests: ✅
# security-scan: ✅

# 6. Merge PR (docker-build should run)
```

### Troubleshooting Common Issues

**Issue**: `pg_isready: command not found`  
**Fix**: Add `options: --health-cmd pg_isready` to postgres service

**Issue**: `npm ERR! code ELIFECYCLE`  
**Fix**: Check Node.js version matches local development

**Issue**: `Coverage decreased`  
**Fix**: Add tests or adjust threshold temporarily

**Issue**: `Docker build failed`  
**Fix**: Ensure Dockerfile exists in backend/frontend directories

---

## 10. Implementation Roadmap

### Phase 1: Basic CI (Day 1-2)
- ✅ Backend tests job
- ✅ Frontend tests job
- ✅ PostgreSQL service
- ✅ Coverage reporting

### Phase 2: Security (Day 3)
- ✅ Bandit Python scanning
- ✅ npm audit
- ✅ Trivy vulnerability scanning

### Phase 3: Docker Build (Day 4)
- ✅ Docker Hub integration
- ✅ Build and push backend image
- ✅ Build and push frontend image

### Phase 4: Optimization (Day 5)
- ✅ Dependency caching
- ✅ Branch protection rules
- ✅ Badge integration
- ✅ Documentation

---

## 11. Acceptance Criteria

- ✅ CI pipeline runs on every PR
- ✅ All tests execute successfully
- ✅ Coverage threshold enforced (>80% backend)
- ✅ Security scans complete without HIGH/CRITICAL issues
- ✅ Docker images build and push to registry
- ✅ Pipeline completes in <5 minutes
- ✅ Branch protection prevents merging with failing tests
- ✅ Codecov badge shows in README
- ✅ GitHub Actions badge shows in README
- ✅ Documentation complete

---

## 12. Future Enhancements (Post-Phase 3)

- **Deploy to staging**: Automatic deployment on main branch merge
- **Performance tests**: Lighthouse CI for frontend
- **E2E tests**: Playwright or Cypress integration
- **Semantic versioning**: Automatic changelog generation
- **Slack notifications**: Alert on build failures
- **Matrix testing**: Test multiple Python/Node versions
- **Scheduled runs**: Nightly security scans

---

**Status**: ✅ Ready for Implementation  
**Assigned To**: TBD  
**Sprint**: 3.1 (Week 3)
