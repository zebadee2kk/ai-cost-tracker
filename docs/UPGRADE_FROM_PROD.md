# Upgrading from Previous Production Version

**Target Audience:** Users with existing local production installation  
**Estimated Time:** 15-30 minutes  
**Risk Level:** Low (with backup strategy)

---

## Quick Decision Guide

### Should I Upgrade or Reinstall?

| Scenario | Recommendation | Why |
|----------|----------------|-----|
| **Working prod install** | ✅ Upgrade | Preserves data, faster |
| **Have important data** | ✅ Upgrade | Data preserved during upgrade |
| **Clean slate wanted** | ⚠️ Reinstall | Simpler but loses data |
| **Migration issues** | ⚠️ Reinstall | Avoids migration conflicts |
| **Testing/development** | ⚠️ Reinstall | Fastest for non-prod |

---

## Option 1: Safe Upgrade (Recommended)

**Preserves all data and configuration**

### Prerequisites

```bash
# 1. Check current status
docker-compose ps
docker-compose logs backend | tail -20

# 2. Check git status
git status
git branch
```

### Step 1: Backup Everything

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cd backups/$(date +%Y%m%d_%H%M%S)

# Backup database
docker-compose exec -T db pg_dump -U postgres ai_cost_tracker > database_backup.sql
echo "✓ Database backed up"

# Backup .env file
cp ../../.env env_backup
echo "✓ Environment backed up"

# Backup docker volumes (optional but recommended)
docker-compose exec -T db tar czf - /var/lib/postgresql/data > postgres_volume.tar.gz
echo "✓ PostgreSQL volume backed up"

cd ../..
```

### Step 2: Stop Current Services

```bash
# Stop containers (keeps data)
docker-compose down

# Verify stopped
docker-compose ps
```

### Step 3: Pull Latest Code

```bash
# Stash any local changes
git stash save "pre-upgrade-stash-$(date +%Y%m%d_%H%M%S)"

# Pull latest
git fetch origin
git pull origin master

# Check what changed
git log --oneline -10
```

### Step 4: Review Changes

**Major changes in this version:**

1. ✅ **5 Providers** (was 1-2)
   - Anthropic (existing)
   - OpenAI (existing/updated)
   - Groq (NEW)
   - Perplexity (NEW)
   - Mistral (NEW)

2. ✅ **Interactive Setup Wizard** (NEW)
   - Browser-based API key setup
   - Secure key collection
   - Automatic validation

3. ✅ **Enhanced Database Schema** (NEW)
   - Rate limit tracking fields
   - Request metrics fields
   - Timing data fields

4. ✅ **Manual Sync Endpoint** (NEW)
   - `POST /api/accounts/<id>/sync`

5. ✅ **Diagnostic Tools** (NEW)
   - `scripts/test_providers.py`
   - `scripts/setup_wizard.py`

### Step 5: Update Configuration

#### Check for new environment variables:

```bash
# Compare your .env with new requirements
cat .env

# Required variables (check if you have these):
# - ANTHROPIC_ADMIN_API_KEY (note: ADMIN key required now!)
# - OPENAI_API_KEY
# - GROQ_API_KEY (new, optional)
# - PERPLEXITY_API_KEY (new, optional)
# - MISTRAL_API_KEY (new, optional)
```

#### Update .env if needed:

**Option A: Use Setup Wizard (Recommended)**
```bash
# Interactive wizard will preserve existing keys
python backend/scripts/setup_wizard.py --update
```

**Option B: Manual Update**
```bash
# Edit .env
nano .env

# Add new optional providers if desired:
GROQ_API_KEY=gsk_your_key_here
PERPLEXITY_API_KEY=pplx-your_key_here
MISTRAL_API_KEY=your_key_here
```

**⚠️ CRITICAL: Anthropic Key Type**

If you have an Anthropic key, verify it's an ADMIN key:
```bash
# Check your key
echo $ANTHROPIC_ADMIN_API_KEY | head -c 20

# Should see: sk-ant-admin-
# If you see: sk-ant-api-
# Then you need to regenerate as ADMIN key
```

To get admin key:
1. Go to https://console.anthropic.com/settings/organization
2. Click "Generate Admin Key" (NOT "API Key")
3. Update .env with new key

### Step 6: Rebuild Containers

```bash
# Pull new base images
docker-compose pull

# Rebuild with new code
docker-compose build --no-cache

# Start services
docker-compose up -d

# Watch startup
docker-compose logs -f backend
# Press Ctrl+C when you see "Running on http://0.0.0.0:5000"
```

### Step 7: Run Database Migration

```bash
# Enter backend container
docker-compose exec backend bash

# Check current migration state
flask db current

# Show pending migrations
flask db heads
flask db history | head -20

# Apply migrations
flask db upgrade

# Verify new schema
flask db current

# Optional: Inspect new columns
psql $DATABASE_URL -c "\d usage_records"

# Exit container
exit
```

**Expected migration changes:**
- New columns in `usage_records`: rate limit fields, timing fields
- New columns in `accounts`: last_sync timestamps
- Indexes on commonly queried fields

### Step 8: Test Connectivity

```bash
# Run diagnostic script
docker-compose exec backend python scripts/test_providers.py

# Expected output:
# ✓ Anthropic: VALID
# ✓ OpenAI: VALID
# ✓ Groq: VALID (if configured)
# ✓ Perplexity: VALID (if configured)
# ✓ Mistral: VALID (if configured)
```

### Step 9: Verify Services

```bash
# Check all containers running
docker-compose ps

# Should see:
# - backend (healthy)
# - frontend (healthy)
# - db (healthy)

# Check backend health
curl http://localhost:5000/health

# Check frontend
curl http://localhost:3000

# View logs for errors
docker-compose logs backend | grep -i error
docker-compose logs frontend | grep -i error
```

### Step 10: Test End-to-End

```bash
# 1. Get accounts
curl http://localhost:5000/api/accounts | jq

# 2. Test manual sync (new feature)
ACCOUNT_ID=$(curl -s http://localhost:5000/api/accounts | jq -r '.[0].id')
curl -X POST http://localhost:5000/api/accounts/$ACCOUNT_ID/sync | jq

# 3. Check usage records
curl http://localhost:5000/api/usage | jq | head -50

# 4. Open dashboard
open http://localhost:3000

# 5. Verify data appears
# - Check usage charts
# - Verify costs calculated
# - Check rate limits displayed (new feature)
```

### Step 11: Restore Local Changes (if needed)

```bash
# List stashed changes
git stash list

# Review what was stashed
git stash show -p stash@{0}

# Apply if needed
git stash pop

# Or keep stashed
# (changes safely stored)
```

---

## Option 2: Clean Reinstall

**⚠️ WARNING: This will delete all existing data**

### When to use:
- No important data to preserve
- Want completely fresh start
- Migration issues encountered
- Development/testing environment

### Step 1: Backup Critical Data (Optional)

```bash
# Only if you want to preserve data
mkdir -p backups/clean_reinstall_$(date +%Y%m%d)
cd backups/clean_reinstall_$(date +%Y%m%d)

# Backup database
docker-compose exec -T db pg_dump -U postgres ai_cost_tracker > database_backup.sql

# Backup .env
cp ../../.env env_backup

cd ../..
```

### Step 2: Complete Teardown

```bash
# Stop and remove everything
docker-compose down -v

# Remove containers, networks, AND volumes
docker-compose rm -f

# Verify volumes removed
docker volume ls | grep ai-cost-tracker

# If volumes remain, remove manually:
docker volume rm ai-cost-tracker_postgres_data

# Clean up images (optional)
docker images | grep ai-cost-tracker
docker rmi $(docker images -q ai-cost-tracker*)
```

### Step 3: Clean Git State

```bash
# Remove all local changes
git reset --hard HEAD

# Remove untracked files
git clean -fd

# Pull latest
git fetch origin
git pull origin master

# Verify clean state
git status
```

### Step 4: Fresh Setup

```bash
# Run setup wizard
python backend/scripts/setup_wizard.py

# This will:
# - Open browser for each provider
# - Collect API keys securely
# - Validate formats
# - Create new .env file
# - Test connectivity
```

### Step 5: Build and Start

```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f
```

### Step 6: Initialize Database

```bash
# Enter backend container
docker-compose exec backend bash

# Initialize database
flask db upgrade

# Verify
flask db current

exit
```

### Step 7: Verify Everything

```bash
# Test providers
docker-compose exec backend python scripts/test_providers.py

# Check services
docker-compose ps

# Open dashboard
open http://localhost:3000
```

### Step 8: Restore Data (Optional)

If you backed up data and want to restore:

```bash
# Enter db container
docker-compose exec db bash

# Restore database
psql -U postgres -d ai_cost_tracker < /path/to/backup/database_backup.sql

exit
```

---

## Rollback Procedure

If upgrade fails or causes issues:

### Quick Rollback

```bash
# Stop new version
docker-compose down

# Restore previous commit
git reflog  # Find previous HEAD
git reset --hard <previous-commit-sha>

# Restore .env backup
cp backups/<timestamp>/env_backup .env

# Rebuild and start
docker-compose build
docker-compose up -d

# Restore database if needed
docker-compose exec -T db psql -U postgres -d ai_cost_tracker < backups/<timestamp>/database_backup.sql
```

### Full Rollback with Data

```bash
# Stop everything
docker-compose down -v

# Reset code
git reset --hard <previous-commit-sha>

# Restore .env
cp backups/<timestamp>/env_backup .env

# Recreate volumes from backup
docker volume create ai-cost-tracker_postgres_data
docker run --rm -v ai-cost-tracker_postgres_data:/data -v $(pwd)/backups/<timestamp>:/backup alpine sh -c "cd /data && tar xzf /backup/postgres_volume.tar.gz"

# Start services
docker-compose up -d
```

---

## Troubleshooting

### Migration Fails

**Error:** `alembic.util.exc.CommandError: Can't locate revision identified by 'xxxx'`

```bash
# Check migration history
docker-compose exec backend flask db current
docker-compose exec backend flask db history

# Stamp to current head (if needed)
docker-compose exec backend flask db stamp head

# Retry migration
docker-compose exec backend flask db upgrade
```

**Error:** `ERROR: column "rate_limit_requests_remaining" already exists`

```bash
# Migration already partially applied
# Manually verify schema matches expected state
docker-compose exec backend psql $DATABASE_URL -c "\d usage_records"

# If correct, stamp as complete
docker-compose exec backend flask db stamp head
```

### Container Won't Start

**Error:** `Container exited with code 1`

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database not ready - wait 30s and retry
# 2. Invalid .env - check syntax
# 3. Port conflict - check ports 5000/3000/5432 available

# Rebuild clean
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### API Keys Invalid

**Error:** `AuthenticationError: Invalid API key`

```bash
# Re-run setup wizard
python backend/scripts/setup_wizard.py --update

# Or test keys manually
docker-compose exec backend python scripts/test_providers.py

# Check specific provider
docker-compose exec backend python -c "
from services.anthropic_service import AnthropicService
svc = AnthropicService(api_key='$ANTHROPIC_ADMIN_API_KEY')
svc.validate_credentials()
"
```

### Database Connection Issues

**Error:** `psycopg2.OperationalError: could not connect to server`

```bash
# Check database running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec db psql -U postgres -d ai_cost_tracker -c "SELECT 1"

# Restart database
docker-compose restart db
```

### Port Conflicts

**Error:** `Bind for 0.0.0.0:5000 failed: port is already allocated`

```bash
# Find process using port
lsof -i :5000
lsof -i :3000
lsof -i :5432

# Kill if needed
kill -9 <PID>

# Or change ports in docker-compose.yml
nano docker-compose.yml
# Change: "5000:5000" to "5001:5000"
```

---

## Post-Upgrade Verification Checklist

### System Health

- [ ] All containers running (`docker-compose ps`)
- [ ] Backend health check passes (`curl http://localhost:5000/health`)
- [ ] Frontend accessible (`curl http://localhost:3000`)
- [ ] No errors in logs (`docker-compose logs | grep -i error`)

### Database

- [ ] Migration applied (`flask db current` shows latest)
- [ ] New columns exist (`\d usage_records` shows rate limit fields)
- [ ] Existing data intact (`SELECT COUNT(*) FROM usage_records`)
- [ ] No orphaned records

### Providers

- [ ] Anthropic connected (`scripts/test_providers.py`)
- [ ] OpenAI connected
- [ ] Groq connected (if configured)
- [ ] Perplexity connected (if configured)
- [ ] Mistral connected (if configured)

### Features

- [ ] Dashboard loads
- [ ] Usage data displays
- [ ] Costs calculated correctly
- [ ] Rate limits shown (new feature)
- [ ] Manual sync works (`POST /api/accounts/<id>/sync`)
- [ ] Historical data preserved

### Configuration

- [ ] .env file valid
- [ ] API keys correct format
- [ ] Anthropic using ADMIN key
- [ ] Database URL correct
- [ ] All required vars present

---

## What's New in This Version

### 🎉 New Features

1. **5 Provider Support** (was 1-2)
   - Groq with per-request tracking
   - Perplexity with local cost calculation
   - Mistral with 9-model pricing

2. **Interactive Setup Wizard**
   - Browser-based API key setup
   - Secure hidden input
   - Format validation
   - Connectivity testing

3. **Manual Sync Endpoint**
   - `POST /api/accounts/<id>/sync`
   - On-demand sync for pull-based providers
   - Proper error handling for per-request services

4. **Enhanced Tracking**
   - Rate limit monitoring
   - Request timing metrics
   - Cache hit tracking (Anthropic)
   - Queue time tracking (Groq)

5. **Diagnostic Tools**
   - Provider connectivity testing
   - Format validation
   - Troubleshooting hints

### 🔧 Technical Improvements

1. **Database Schema**
   - Rate limit fields (requests, tokens, reset times)
   - Timing fields (queue, prompt, completion)
   - Cache fields (hits, writes)

2. **Service Architecture**
   - Unified BaseService pattern
   - Per-request tracking for providers without usage APIs
   - Local cost calculation with current pricing tables

3. **Error Handling**
   - Exponential backoff retry logic
   - Rate limit detection and warnings
   - Comprehensive logging

4. **Documentation**
   - Setup guide
   - Upgrade guide (this doc)
   - Handover docs
   - Provider-specific research

---

## Getting Help

### Documentation

- **This guide:** Upgrade instructions
- `docs/SETUP_GUIDE.md` - Fresh setup
- `docs/HANDOVER_TO_PERPLEXITY.md` - Current project state
- `docs/CURRENT_STATUS.md` - Features and status
- `docs/providers/*.md` - Provider details

### Diagnostic Commands

```bash
# Test everything
python backend/scripts/test_providers.py

# Check logs
docker-compose logs -f backend

# Check database
docker-compose exec backend flask db current

# Check services
docker-compose ps
```

### Common Commands

```bash
# Restart services
docker-compose restart

# Rebuild
docker-compose build --no-cache

# Fresh start
docker-compose down && docker-compose up -d

# Enter container
docker-compose exec backend bash

# Database shell
docker-compose exec db psql -U postgres -d ai_cost_tracker
```

---

## Timeline

### Upgrade Path (Option 1)

| Step | Time | Description |
|------|------|-------------|
| Backup | 5 min | Database + .env + volumes |
| Stop Services | 1 min | `docker-compose down` |
| Pull Code | 2 min | `git pull` |
| Update Config | 5 min | Run setup wizard or manual |
| Rebuild | 5 min | `docker-compose build` |
| Migrate | 2 min | `flask db upgrade` |
| Test | 5 min | Connectivity + end-to-end |
| **Total** | **~25 min** | Safe upgrade preserving data |

### Reinstall Path (Option 2)

| Step | Time | Description |
|------|------|-------------|
| Teardown | 3 min | Remove everything |
| Fresh Pull | 2 min | Clean git state |
| Setup Wizard | 10 min | Configure all providers |
| Build | 5 min | Fresh containers |
| Verify | 5 min | Test everything |
| **Total** | **~25 min** | Clean slate, no data |

---

## Quick Reference

### Upgrade (Preserves Data)
```bash
# Backup
docker-compose exec -T db pg_dump -U postgres ai_cost_tracker > backup.sql
cp .env .env.backup

# Update
docker-compose down
git pull origin master
python backend/scripts/setup_wizard.py --update
docker-compose build
docker-compose up -d
docker-compose exec backend flask db upgrade
docker-compose exec backend python scripts/test_providers.py
```

### Reinstall (Fresh Start)
```bash
# Remove
docker-compose down -v

# Fresh
git reset --hard HEAD && git pull origin master
python backend/scripts/setup_wizard.py
docker-compose build && docker-compose up -d
docker-compose exec backend flask db upgrade
```

### Rollback
```bash
# Quick rollback
docker-compose down
git reset --hard <previous-commit>
cp .env.backup .env
docker-compose up -d
```

---

**Recommendation:** Use **Option 1 (Upgrade)** unless you have a specific reason for clean reinstall.

**Estimated time:** 15-30 minutes depending on network speed and whether you need to regenerate API keys.

**Risk level:** Low - backups protect data, rollback is straightforward.

---

Good luck with your upgrade! 🚀
