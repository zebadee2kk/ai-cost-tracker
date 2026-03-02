# Handover to VS Code Copilot: Production Upgrade

**Date:** March 2, 2026  
**Task:** Upgrade local production installation to latest version  
**User:** Richard (richardh@lilyskitchen.co.uk)  
**Estimated Time:** 15-30 minutes

---

## Context

### Current Situation
- User has a working local production installation of AI Cost Tracker
- Previous version has 1-2 providers (Anthropic + possibly OpenAI)
- Current version has 5 providers + new features
- Need to upgrade safely without losing data

### Repository State
- **Latest Commit:** [0dc5565](https://github.com/zebadee2kk/ai-cost-tracker/commit/0dc5565f710ca6ac4d572626958a4cc801c4b416)
- **Branch:** master
- **Recent Changes:**
  - 5 provider implementations (Anthropic, OpenAI, Groq, Perplexity, Mistral)
  - Interactive setup wizard with browser integration
  - Enhanced database schema (rate limits, timing metrics)
  - Manual sync endpoint
  - Diagnostic tools

### What Changed Since Previous Production Version

#### New Files
1. `backend/scripts/setup_wizard.py` - Interactive API key setup
2. `backend/scripts/test_providers.py` - Connectivity testing
3. `backend/services/groq_service.py` - Groq provider (NEW)
4. `backend/services/perplexity_service.py` - Perplexity provider (NEW)
5. `backend/services/mistral_service.py` - Mistral provider (NEW)
6. `docs/SETUP_GUIDE.md` - Setup documentation
7. `docs/UPGRADE_FROM_PROD.md` - Upgrade guide
8. `docs/HANDOVER_TO_PERPLEXITY.md` - Project handover

#### Updated Files
1. `backend/services/openai_service.py` - Enhanced with rate limits + logging
2. `backend/services/__init__.py` - Registered all 5 providers
3. `backend/routes/accounts.py` - Added manual sync endpoint
4. `backend/migrations/` - New migration for enhanced schema

#### Database Changes
- New columns in `usage_records`: rate limit fields, timing fields, cache fields
- New columns in `accounts`: last_sync timestamps
- New indexes for performance

---

## Your Mission

Help Richard upgrade his local production installation safely.

### Primary Goals
1. ✅ Preserve all existing data
2. ✅ Upgrade to latest version successfully
3. ✅ Configure new providers (Groq, Perplexity, Mistral)
4. ✅ Verify everything works
5. ✅ Provide rollback if needed

### Success Criteria
- All containers running healthy
- Database migration applied successfully
- All providers connected and validated
- Dashboard displays data correctly
- No errors in logs
- User can trigger syncs manually

---

## Step-by-Step Tasks

### Phase 1: Assessment (5 minutes)

**Objective:** Understand current installation state

```bash
# 1. Check current running state
docker-compose ps

# 2. Check which version is running
cd <project-directory>
git log --oneline -5
git status

# 3. Check current providers
cat .env | grep -E "(ANTHROPIC|OPENAI|GROQ|PERPLEXITY|MISTRAL)"

# 4. Check database state
docker-compose exec backend flask db current

# 5. Count existing usage records (verify data)
docker-compose exec backend python -c "
from app import create_app, db
from models import UsageRecord
app = create_app()
with app.app_context():
    count = UsageRecord.query.count()
    print(f'Current usage records: {count}')
"
```

**Questions to answer:**
- Are containers running?
- How many commits behind is current version?
- Which providers are currently configured?
- How much data exists in database?
- What's the current migration state?

**Decision:** Based on assessment, recommend:
- **Upgrade** (if data exists and system healthy)
- **Reinstall** (if system problematic or no critical data)

---

### Phase 2: Backup (5 minutes)

**Objective:** Create safety net for rollback

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cd backups/$(date +%Y%m%d_%H%M%S)

# Backup database
echo "Backing up database..."
docker-compose exec -T db pg_dump -U postgres ai_cost_tracker > database_backup.sql

# Verify backup
ls -lh database_backup.sql
head -20 database_backup.sql

# Backup .env
echo "Backing up configuration..."
cp ../../.env env_backup

# Backup volumes (optional but recommended)
echo "Backing up PostgreSQL volume..."
docker-compose exec -T db tar czf - /var/lib/postgresql/data > postgres_volume.tar.gz

# Record current state
echo "Recording system state..."
git log --oneline -1 > git_state.txt
docker-compose ps > docker_state.txt
cat ../../.env > env_state.txt

cd ../..

echo "✅ Backup complete in backups/$(ls -t backups/ | head -1)"
```

---

### Phase 3: Update Code (5 minutes)

**Objective:** Pull latest version

```bash
# Stash any local changes
if [[ -n $(git status -s) ]]; then
    echo "Local changes detected, stashing..."
    git stash save "pre-upgrade-$(date +%Y%m%d_%H%M%S)"
fi

# Pull latest
echo "Fetching latest code..."
git fetch origin
git pull origin master

# Show what changed
echo "\n=== Recent commits ==="
git log --oneline -10

echo "\n=== Files changed ==="
git diff --name-status HEAD~5 HEAD | grep -E "(backend/services|backend/scripts|docs)"
```

---

### Phase 4: Configure New Providers (10 minutes)

**Objective:** Setup API keys for new providers

**Option A: Interactive Wizard (Recommended)**

```bash
echo "Starting interactive setup wizard..."
echo "This will:"
echo "  - Preserve your existing Anthropic & OpenAI keys"
echo "  - Let you add Groq, Perplexity, Mistral"
echo "  - Open browser pages for key creation"
echo "  - Validate all keys"
echo ""

python backend/scripts/setup_wizard.py --update

# The wizard will:
# 1. Show existing keys (masked)
# 2. Ask if you want to keep them
# 3. Ask about new providers (optional)
# 4. Open browser for key creation
# 5. Validate and save
```

**Option B: Manual Configuration**

```bash
# Edit .env
nano .env

# Add these lines (optional providers):
# GROQ_API_KEY=gsk_
# PERPLEXITY_API_KEY=pplx-
# MISTRAL_API_KEY=

# Verify Anthropic key is ADMIN key
if grep -q "ANTHROPIC_ADMIN_API_KEY=sk-ant-api-" .env; then
    echo "⚠️ WARNING: You have a standard API key, not admin key!"
    echo "Admin key required for usage tracking."
    echo "Get admin key from: https://console.anthropic.com/settings/organization"
fi
```

**Critical Check:**
```bash
# Verify Anthropic key type
grep ANTHROPIC_ADMIN_API_KEY .env | head -c 35
# Should show: ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-
# NOT: ANTHROPIC_ADMIN_API_KEY=sk-ant-api-
```

---

### Phase 5: Rebuild Containers (5 minutes)

**Objective:** Apply new code and dependencies

```bash
# Stop current services
echo "Stopping current services..."
docker-compose down

# Pull new base images
echo "Pulling updated base images..."
docker-compose pull

# Rebuild with new code (no cache for clean build)
echo "Rebuilding containers..."
docker-compose build --no-cache

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for startup
echo "Waiting for services to start..."
sleep 10

# Check status
docker-compose ps

# Watch backend logs for startup
echo "\n=== Backend startup logs ==="
docker-compose logs backend | tail -30
```

---

### Phase 6: Database Migration (3 minutes)

**Objective:** Apply schema changes

```bash
# Enter backend container
docker-compose exec backend bash

# Check current migration
echo "Current migration:"
flask db current

# Show migration history
echo "\nMigration history:"
flask db history | head -20

# Check for pending migrations
echo "\nPending migrations:"
flask db heads

# Apply migrations
echo "\nApplying migrations..."
flask db upgrade

# Verify new state
echo "\nNew migration state:"
flask db current

# Check new schema (should show rate limit columns)
echo "\nVerifying new columns:"
psql $DATABASE_URL -c "\d usage_records" | grep -E "(rate_limit|timing|cache)"

# Exit container
exit
```

**Expected new columns:**
- `rate_limit_requests_remaining`
- `rate_limit_tokens_remaining`
- `rate_limit_requests_reset_at`
- `rate_limit_tokens_reset_at`
- `timing_queue_ms`
- `timing_prompt_ms`
- `timing_completion_ms`
- `cache_read_tokens`
- `cache_creation_tokens`

---

### Phase 7: Test Connectivity (5 minutes)

**Objective:** Verify all providers connected

```bash
# Run diagnostic script
echo "Testing provider connectivity..."
docker-compose exec backend python scripts/test_providers.py

# Expected output:
# ✓ Anthropic: VALID
# ✓ OpenAI: VALID
# ✓ Groq: VALID (if configured)
# ✓ Perplexity: VALID (if configured)
# ✓ Mistral: VALID (if configured)
# ✗ Google Gemini: NOT IMPLEMENTED (expected)
```

**If any fail:**
```bash
# Check specific provider
docker-compose exec backend python -c "
from services.anthropic_service import AnthropicService
import os

api_key = os.environ['ANTHROPIC_ADMIN_API_KEY']
service = AnthropicService(api_key=api_key)

try:
    service.validate_credentials()
    print('✓ Anthropic: VALID')
except Exception as e:
    print(f'✗ Anthropic: {e}')
"
```

---

### Phase 8: End-to-End Verification (5 minutes)

**Objective:** Confirm everything works

```bash
# 1. Check all containers healthy
echo "=== Container Status ==="
docker-compose ps

# 2. Check backend health
echo "\n=== Backend Health ==="
curl -s http://localhost:5000/health | jq

# 3. Get accounts
echo "\n=== Accounts ==="
curl -s http://localhost:5000/api/accounts | jq

# 4. Test manual sync (new feature)
echo "\n=== Testing Manual Sync ==="
ACCOUNT_ID=$(curl -s http://localhost:5000/api/accounts | jq -r '.[0].id')
echo "Syncing account: $ACCOUNT_ID"
curl -s -X POST http://localhost:5000/api/accounts/$ACCOUNT_ID/sync | jq

# 5. Check usage records
echo "\n=== Usage Records ==="
curl -s http://localhost:5000/api/usage?limit=5 | jq

# 6. Verify data count matches pre-upgrade
echo "\n=== Data Verification ==="
docker-compose exec backend python -c "
from app import create_app, db
from models import UsageRecord
app = create_app()
with app.app_context():
    count = UsageRecord.query.count()
    print(f'Current usage records: {count}')
    print('Compare to backup count to verify no data loss')
"

# 7. Check for errors in logs
echo "\n=== Error Check ==="
docker-compose logs backend | grep -i error | tail -10
docker-compose logs frontend | grep -i error | tail -10

# 8. Open dashboard
echo "\n=== Opening Dashboard ==="
echo "Opening http://localhost:3000"
open http://localhost:3000 || xdg-open http://localhost:3000
```

**Manual checks in dashboard:**
- [ ] Dashboard loads without errors
- [ ] Usage data displays
- [ ] Costs calculated correctly
- [ ] Date ranges work
- [ ] Provider filter works
- [ ] Charts render

---

### Phase 9: Final Verification (3 minutes)

**Objective:** Complete checklist

```bash
# Run comprehensive check
cat << 'EOF' > /tmp/verify_upgrade.sh
#!/bin/bash

echo "\n=== UPGRADE VERIFICATION CHECKLIST ==="

# System Health
echo "\n[System Health]"
if docker-compose ps | grep -q "Up"; then
    echo "✓ Containers running"
else
    echo "✗ Container issues detected"
fi

if curl -sf http://localhost:5000/health > /dev/null; then
    echo "✓ Backend healthy"
else
    echo "✗ Backend not responding"
fi

if curl -sf http://localhost:3000 > /dev/null; then
    echo "✓ Frontend accessible"
else
    echo "✗ Frontend not responding"
fi

# Database
echo "\n[Database]"
CURRENT_MIGRATION=$(docker-compose exec -T backend flask db current 2>/dev/null | grep "[a-f0-9]" | head -1)
if [ -n "$CURRENT_MIGRATION" ]; then
    echo "✓ Migration applied: $CURRENT_MIGRATION"
else
    echo "✗ Migration status unclear"
fi

# Providers
echo "\n[Providers]"
docker-compose exec -T backend python scripts/test_providers.py 2>/dev/null | grep -E "(Anthropic|OpenAI|Groq|Perplexity|Mistral)"

# Features
echo "\n[Features]"
if curl -sf http://localhost:5000/api/accounts > /dev/null; then
    echo "✓ API accessible"
fi

ACCOUNT_ID=$(curl -s http://localhost:5000/api/accounts | jq -r '.[0].id' 2>/dev/null)
if [ -n "$ACCOUNT_ID" ]; then
    if curl -sf -X POST http://localhost:5000/api/accounts/$ACCOUNT_ID/sync > /dev/null; then
        echo "✓ Manual sync works"
    fi
fi

echo "\n=== VERIFICATION COMPLETE ==="
EOF

chmod +x /tmp/verify_upgrade.sh
/tmp/verify_upgrade.sh
```

---

## Rollback Procedure (If Needed)

If something goes wrong:

```bash
# Quick rollback
echo "Starting rollback..."

# Stop new version
docker-compose down

# Find backup directory
BACKUP_DIR=$(ls -td backups/*/ | head -1)
echo "Using backup: $BACKUP_DIR"

# Restore .env
cp "${BACKUP_DIR}env_backup" .env
echo "✓ Restored .env"

# Reset code to previous commit
PREV_COMMIT=$(cat "${BACKUP_DIR}git_state.txt" | awk '{print $1}')
git reset --hard $PREV_COMMIT
echo "✓ Restored code to $PREV_COMMIT"

# Rebuild and start
docker-compose build
docker-compose up -d
echo "✓ Services restarted"

# Restore database if needed
read -p "Restore database from backup? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose exec -T db psql -U postgres -d ai_cost_tracker < "${BACKUP_DIR}database_backup.sql"
    echo "✓ Database restored"
fi

echo "\nRollback complete. Verify system:"
docker-compose ps
```

---

## Common Issues & Solutions

### Issue: Migration fails with "column already exists"

**Cause:** Migration partially applied

**Solution:**
```bash
docker-compose exec backend bash
flask db stamp head  # Mark as complete
flask db current     # Verify
exit
```

### Issue: Anthropic authentication fails

**Cause:** Using API key instead of Admin key

**Solution:**
```bash
# Check key type
grep ANTHROPIC .env

# If shows sk-ant-api-, regenerate as admin key:
# 1. Go to https://console.anthropic.com/settings/organization
# 2. Click "Generate Admin Key"
# 3. Update .env
# 4. Restart: docker-compose restart backend
```

### Issue: Containers won't start

**Cause:** Port conflicts or build issues

**Solution:**
```bash
# Check ports
lsof -i :5000
lsof -i :3000
lsof -i :5432

# Rebuild clean
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: No data in dashboard

**Cause:** Need to trigger sync

**Solution:**
```bash
# Trigger manual sync
ACCOUNT_ID=$(curl -s http://localhost:5000/api/accounts | jq -r '.[0].id')
curl -X POST http://localhost:5000/api/accounts/$ACCOUNT_ID/sync

# Check if data appeared
curl http://localhost:5000/api/usage?limit=10 | jq
```

---

## Key Files to Reference

### Documentation
1. `docs/UPGRADE_FROM_PROD.md` - Detailed upgrade guide
2. `docs/SETUP_GUIDE.md` - Setup wizard documentation
3. `docs/HANDOVER_TO_PERPLEXITY.md` - Current project state
4. `docs/CURRENT_STATUS.md` - Feature status

### Scripts
1. `backend/scripts/setup_wizard.py` - Interactive API key setup
2. `backend/scripts/test_providers.py` - Connectivity testing

### Services
1. `backend/services/anthropic_service.py` - Anthropic implementation
2. `backend/services/openai_service.py` - OpenAI implementation
3. `backend/services/groq_service.py` - Groq implementation
4. `backend/services/perplexity_service.py` - Perplexity implementation
5. `backend/services/mistral_service.py` - Mistral implementation

### Configuration
1. `.env` - Environment variables
2. `docker-compose.yml` - Service definitions
3. `backend/config.py` - Application config

---

## Success Metrics

Upgrade is successful when:

- ✅ All containers show "Up (healthy)"
- ✅ `flask db current` shows latest migration
- ✅ `scripts/test_providers.py` shows all configured providers valid
- ✅ Dashboard loads at http://localhost:3000
- ✅ Usage data displays correctly
- ✅ Manual sync endpoint works
- ✅ No errors in `docker-compose logs`
- ✅ Usage record count matches pre-upgrade count

---

## Your Approach

1. **Start with assessment** - Understand current state
2. **Always backup first** - Safety net for rollback
3. **Execute upgrade** - Follow phases sequentially
4. **Test thoroughly** - Don't skip verification
5. **Be ready to rollback** - Have procedure ready

### Communication

- Explain what you're doing at each step
- Show command outputs (especially errors)
- Ask for confirmation before destructive operations
- Provide clear success/failure indicators
- Offer rollback if issues occur

### When to Ask for Help

- Migration fails repeatedly
- Data count doesn't match after upgrade
- Multiple providers fail authentication
- Containers crash-loop
- Database connection fails

---

## Estimated Timeline

| Phase | Time | Cumulative |
|-------|------|------------|
| 1. Assessment | 5 min | 5 min |
| 2. Backup | 5 min | 10 min |
| 3. Update Code | 5 min | 15 min |
| 4. Configure | 10 min | 25 min |
| 5. Rebuild | 5 min | 30 min |
| 6. Migration | 3 min | 33 min |
| 7. Test | 5 min | 38 min |
| 8. Verify | 5 min | 43 min |
| 9. Final Check | 3 min | 46 min |

**Total: ~45 minutes** (including configuration of new providers)

If skipping optional providers: **~25 minutes**

---

## Ready to Start?

When Richard says go, begin with **Phase 1: Assessment** to understand the current state of his installation.

Good luck! 🚀
