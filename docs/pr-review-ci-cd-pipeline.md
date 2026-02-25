# CI/CD Pipeline PR Review (Sprint 2 Blocker)

## Review Outcome: ❌ REQUEST CHANGES

The CI/CD pipeline implementation is close, but several required checklist items are not satisfied yet.

## Checklist Results

### Code Quality
- ✅ Workflow YAML syntax is valid (`ci.yml`, `security-scan.yml`).
- ✅ Job dependency order is correct for deploy (`docker-build` needs backend/frontend/security).
- ✅ Secrets are referenced via `secrets.*` for Docker Hub and Codecov.
- ⚠️ Hardcoded runtime secrets still exist in CI env (`SECRET_KEY`, `ENCRYPTION_KEY`) and should be moved to generated/runtime values or GH secrets.

### Testing
- ❌ Backend test job does **not** use PostgreSQL service; it currently uses SQLite/testing config only.
- ✅ Frontend test job runs `npm test` with coverage.
- ✅ Coverage thresholds are set (backend `coverage --fail-under=80`, frontend Jest thresholds at 70%).
- ⚠️ Backend uploads coverage artifact, but frontend uploads build artifact only (no frontend test-result/coverage artifact archived via `upload-artifact`).

### Security
- ✅ Bandit scan configured.
- ✅ npm audit configured.
- ✅ Trivy scan configured (filesystem + image scan).
- ❌ Security failures do not consistently block merges because Bandit and npm audit are run with `|| true`, which makes failures non-blocking.

### Performance
- ✅ pip and npm caches configured.
- ✅ Jobs are parallelized where possible.
- ⚠️ Cannot verify runtime <5 min from static review only (no run logs/metrics attached).

### Documentation
- ✅ `docs/phase3-ci-guide.md` updated and includes troubleshooting section.
- ✅ `README.md` includes Codecov badge.

## Required Changes Before Approval

1. Update backend CI job to run tests against PostgreSQL service (or align acceptance criteria/checklist if SQLite is intentional).
2. Remove `|| true` from security commands (or gate with explicit policy) so high/critical findings fail CI.
3. Replace hardcoded CI secret values with secure secret references or generated ephemeral values.
4. Archive frontend coverage/test artifacts (not just production build) for review traceability.
5. Provide at least one successful CI run link demonstrating green pipeline and runtime target.

## Decision

**Status: REQUEST CHANGES**

Please address the five items above and re-request review.
