# Local Deployment Log

**Started:** 2026-03-01
**Purpose:** Phase 3A local test deployment for control-tower integration
**Environment:** Linux (local dev)

---

## Rollback / Cleanup Reference

To fully reverse everything done in this session:

```bash
# Stop and remove all containers + volumes (destroys database data)
docker compose down -v

# Remove generated .env file (contains local dev secrets)
rm .env

# Remove this log (optional)
rm docs/local-deployment-log.md
```

---

## Actions Log

### Step 1 — Encryption Keys Generated (2026-03-01)

Generated three secrets using Python 3.12:

| Variable        | Method                                      |
|-----------------|---------------------------------------------|
| `SECRET_KEY`    | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ENCRYPTION_KEY`| `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `JWT_SECRET_KEY`| `python3 -c "import secrets; print(secrets.token_hex(32))"` |

**Rollback:** Delete `.env` file. Keys are not persisted anywhere else.

> ⚠️ Do not commit `.env` to git. It is listed in `.gitignore`.

---

### Step 2 — .env File Created (2026-03-01)

- **File:** `.env`
- **Source:** Generated from `.env.example` with live secrets substituted
- **DB credentials:** Matched to `docker-compose.yml` (`ai_user` / `ai_password` / `ai_tracker`)
- **Discrepancy noted:** Handoff doc specified `postgres`/`ai_cost_tracker` — overridden to match actual Compose config

**Rollback:** `rm .env`

---

### Step 3a — Dockerfile Fix Applied (2026-03-01)

- **File:** `frontend/Dockerfile` line 5
- **Change:** `RUN npm ci` → `RUN npm install`
- **Reason:** No `package-lock.json` exists in repo; `npm ci` requires a lockfile
- **Rollback:** `git checkout frontend/Dockerfile`

---

### Step 3b — Missing dependency fix (2026-03-01)

- **File:** `backend/requirements.txt`
- **Change:** Added `psycopg2-binary==2.9.10` after `flask-sqlalchemy==3.1.1`
- **Reason:** Backend crashed on start with `ModuleNotFoundError: No module named 'psycopg2'`; package was missing from requirements entirely
- **Rollback:** Remove the `psycopg2-binary==2.9.10` line from `backend/requirements.txt`

---

### Step 3 — Docker Compose Services (2026-03-01)

**Actions executed:**
- `sudo docker compose up -d --build` — built and started 3 containers
- Created Docker volumes: `postgres_data`, `backend_logs`
- Created network: `ai-cost-tracker_default`

**Status after first attempt:** `db` healthy, `frontend` up, `backend` crash-looping (psycopg2 missing — fixed in Step 3b)

**Final status (after rebuild):** All 3 containers up and healthy ✅
- `ai-cost-tracker-db-1` → Up (healthy), port 5432
- `ai-cost-tracker-backend-1` → Up, Flask running on port 5000
- `ai-cost-tracker-frontend-1` → Up, nginx serving on port 3000

**Rollback:** `sudo docker compose down -v` (removes containers AND volumes — all DB data lost)

---

### Step 4 — Database Migrations (2026-03-01) ✅

**Actions executed:**
- `sudo docker compose exec backend flask db upgrade`
  - `initial` ✅
  - `Add unique constraint for idempotent usage ingestion` ✅
  - `Add notification_preferences, notification_queue, notification_history tables` ✅
  - `Add anomaly_detection_configs and detected_anomalies tables` ✅
- `sudo docker compose exec backend python scripts/seed_services.py`
  - Seeded 5 services: ChatGPT, Claude, Groq, GitHub Copilot, Perplexity ✅
  - Note: handoff doc expected 4 services; codebase has since added GitHub Copilot

**Rollback:** `sudo docker compose down -v` (drops the entire database)

---

### Step 5 — Health Checks (2026-03-01) ✅

**Results:**

| Check | Endpoint | Result |
|-------|----------|--------|
| Backend health | `GET /api/health` | `{"status":"ok","env":"development"}` ✅ |
| Frontend | `http://localhost:3000` | HTTP 200 ✅ |
| User registration | `POST /api/auth/register` | 201 Created, user id=1 ✅ |
| Login + JWT | `POST /api/auth/login` | Token issued ✅ |
| Services seeded | `GET /api/services` | 5 services returned ✅ |
| Accounts endpoint | `GET /api/accounts` | 200 OK, empty list ✅ |
| Usage endpoint | `GET /api/usage` | 200 OK, empty list ✅ |

**Test user created:** `test@example.com` / `SecurePass123!`

**Note:** curl register/login fails due to bash `!` history expansion in password — use Python or escape the `!` as `\!` in curl commands.

**System status: READY FOR PHASE 3A INTEGRATION** ✅

---

## State Summary

| Component       | Status | Notes                                                    |
|-----------------|--------|----------------------------------------------------------|
| Keys            | Done   | Generated and written to .env (not committed)            |
| .env file       | Done   | Created at project root (gitignored)                     |
| Docker          | Done   | Installed Docker 29.2.1 + Compose v5.1.0                 |
| Containers      | Done   | All 3 up and healthy (db, backend, frontend)             |
| DB migrations   | Done   | 4 migrations applied via `flask db upgrade`              |
| DB seed         | Done   | 5 services seeded                                        |
| Health checks   | Done   | All endpoints verified ✅                                |
| Test user       | Done   | test@example.com created and verified via UI             |
