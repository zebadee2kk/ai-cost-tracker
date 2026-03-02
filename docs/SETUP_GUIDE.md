# AI Cost Tracker - Setup Guide

**Quick Start:** Run the interactive setup wizard

```bash
python backend/scripts/setup_wizard.py
```

---

## Interactive Setup Wizard

The setup wizard provides a guided experience for configuring your AI Cost Tracker:

### Features

✅ **Browser Integration**
- Automatically opens provider console pages
- Direct links to API key creation
- Step-by-step instructions for each provider

✅ **Secure Key Collection**
- Hidden input for API keys (like password fields)
- No keys displayed in terminal history
- Keys never logged or printed

✅ **Validation**
- Checks key format before saving
- Warns about common mistakes (e.g., wrong Anthropic key type)
- Validates key prefixes and length

✅ **Smart Defaults**
- Preserves existing configuration
- Updates only what you want to change
- Backs up existing .env file

✅ **Connectivity Testing**
- Tests each provider after configuration
- Shows real-time connection status
- Provides troubleshooting hints

---

## Usage

### First Time Setup

```bash
# Run the wizard
python backend/scripts/setup_wizard.py

# The wizard will:
# 1. Ask which providers to configure
# 2. Open browser pages for key creation
# 3. Securely collect API keys
# 4. Validate key formats
# 5. Save to .env file
# 6. Test connectivity
```

### Update Existing Configuration

```bash
# Update mode - add/change keys
python backend/scripts/setup_wizard.py --update

# This will:
# - Load existing .env
# - Let you keep or replace each key
# - Preserve other configuration
# - Backup original .env
```

---

## Provider-Specific Instructions

### Anthropic Claude (Required)

**Important:** You need an **Admin API key**, not a standard API key.

```bash
# The wizard will open:
https://console.anthropic.com/settings/organization

# Steps:
1. Go to "Organization" settings (not "API Keys")
2. Click "Generate Admin Key"
3. Admin keys start with: sk-ant-admin-
4. Standard keys (sk-ant-api-) will NOT work
```

**Why Admin Keys?**
- Required for usage/cost tracking APIs
- Standard API keys can't access billing data
- Admin access needed for organization-level stats

### OpenAI (Required)

```bash
# The wizard will open:
https://platform.openai.com/api-keys

# Steps:
1. Click "Create new secret key"
2. Name it (e.g., "AI Cost Tracker")
3. Copy the key (starts with sk-)
4. You can only see it once!
```

### Groq (Optional)

```bash
# The wizard will open:
https://console.groq.com/keys

# Steps:
1. Click "Create API Key"
2. Give it a name
3. Copy key (starts with gsk_)
```

**Note:** Groq has no usage history API - uses per-request tracking

### Perplexity (Optional)

```bash
# The wizard will open:
https://www.perplexity.ai/settings/api

# Steps:
1. Click "Generate API Key"
2. Copy key (starts with pplx-)
3. Note last 4 chars (appear on invoices)
```

**Note:** Perplexity has no usage API - uses per-request tracking with local cost calculation

### Mistral AI (Optional)

```bash
# The wizard will open:
https://console.mistral.ai/api-keys/

# Steps:
1. Click "Create new key"
2. Give it a name
3. Copy the API key
```

**Note:** Mistral has no usage API - uses per-request tracking

---

## Manual Configuration (Alternative)

If you prefer not to use the wizard:

### 1. Create .env File

```bash
cp .env.example .env
```

### 2. Add API Keys

```bash
# Required
ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-YOUR-KEY-HERE
OPENAI_API_KEY=sk-YOUR-KEY-HERE

# Optional
GROQ_API_KEY=gsk_YOUR-KEY-HERE
PERPLEXITY_API_KEY=pplx-YOUR-KEY-HERE
MISTRAL_API_KEY=YOUR-KEY-HERE

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/ai_cost_tracker

# Flask
FLASK_ENV=development
SECRET_KEY=$(openssl rand -hex 32)
```

### 3. Test Configuration

```bash
python backend/scripts/test_providers.py
```

---

## After Setup

### 1. Start Services

```bash
# Start Docker containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 2. Apply Database Migration

```bash
# Enter backend container
docker-compose exec backend bash

# Apply migration
flask db upgrade

# Verify
flask db current

# Exit
exit
```

### 3. Verify Everything Works

```bash
# Test provider connectivity
docker-compose exec backend python scripts/test_providers.py

# Check dashboard
open http://localhost:3000

# Trigger manual sync
curl -X POST http://localhost:5000/api/accounts/<ID>/sync
```

---

## Troubleshooting

### "Invalid key format" Error

**Anthropic:**
- Make sure key starts with `sk-ant-admin-` not `sk-ant-api-`
- Use Organization settings, not API Keys page

**OpenAI:**
- Key should start with `sk-`
- Make sure you copied the full key

**Groq:**
- Key should start with `gsk_`

**Perplexity:**
- Key should start with `pplx-`

### "Key seems too short" Error

- Make sure you copied the entire key
- Check for trailing spaces or newlines
- Don't include quotes or brackets

### Connectivity Test Fails

**Check API key:**
```bash
# Print first 15 chars of key (safe)
echo $ANTHROPIC_ADMIN_API_KEY | head -c 15
```

**Test manually:**
```bash
# Anthropic
curl -H "x-api-key: $ANTHROPIC_ADMIN_API_KEY" \
     https://api.anthropic.com/v1/messages

# OpenAI
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

**Check network:**
```bash
# Inside Docker container
docker-compose exec backend bash
ping -c 3 api.anthropic.com
exit
```

### .env File Issues

**Backup corrupted:**
```bash
# Restore from backup
cp .env.backup .env
```

**Permission denied:**
```bash
# Fix permissions
chmod 600 .env
```

**Not loading:**
```bash
# Make sure .env is in project root
ls -la .env

# Check Docker Compose loads it
docker-compose config
```

---

## Security Best Practices

### API Key Safety

✅ **Do:**
- Use the wizard's hidden input (getpass)
- Store keys only in .env file
- Add .env to .gitignore
- Use environment-specific keys
- Rotate keys periodically
- Restrict key permissions in provider consoles

❌ **Don't:**
- Commit .env to git
- Share keys in chat/email
- Use production keys in development
- Store keys in code
- Log API keys

### File Permissions

```bash
# Secure .env file (owner read/write only)
chmod 600 .env

# Verify
ls -l .env
# Should show: -rw------- (600)
```

### Key Rotation

```bash
# 1. Generate new keys in provider consoles
# 2. Run wizard in update mode
python backend/scripts/setup_wizard.py --update

# 3. Test new keys
python backend/scripts/test_providers.py

# 4. Revoke old keys in consoles
```

---

## Advanced Configuration

### Custom Database URL

The wizard asks for database configuration. Default:
```
postgresql://postgres:postgres@db:5432/ai_cost_tracker
```

For custom setup:
```
postgresql://user:password@host:port/database
```

### Environment-Specific Setup

```bash
# Development
cp .env .env.development
python backend/scripts/setup_wizard.py
# Edit .env for development keys

# Production
cp .env .env.production
python backend/scripts/setup_wizard.py
# Edit .env.production for production keys

# Use
docker-compose --env-file .env.production up -d
```

### CI/CD Integration

```bash
# Set keys as GitHub Secrets or environment variables
# Skip interactive wizard in CI

# Create .env programmatically
cat > .env << EOF
ANTHROPIC_ADMIN_API_KEY=$ANTHROPIC_KEY
OPENAI_API_KEY=$OPENAI_KEY
EOF
```

---

## Getting Help

### Documentation
- **This guide:** Setup instructions
- `docs/HANDOVER_TO_PERPLEXITY.md` - Next steps after setup
- `docs/CURRENT_STATUS.md` - Project status
- `docs/providers/*.md` - Provider-specific details

### Test Scripts
```bash
# Test connectivity
python backend/scripts/test_providers.py

# Run setup wizard
python backend/scripts/setup_wizard.py

# Update configuration
python backend/scripts/setup_wizard.py --update
```

### Support
- Check logs: `docker-compose logs -f backend`
- Review docs: `docs/`
- Test manually: `curl` commands above

---

## Quick Reference

### Setup Wizard
```bash
python backend/scripts/setup_wizard.py         # First time
python backend/scripts/setup_wizard.py --update # Update keys
```

### Provider Consoles
- **Anthropic:** https://console.anthropic.com/settings/organization
- **OpenAI:** https://platform.openai.com/api-keys
- **Groq:** https://console.groq.com/keys
- **Perplexity:** https://www.perplexity.ai/settings/api
- **Mistral:** https://console.mistral.ai/api-keys/

### Key Prefixes
- **Anthropic:** `sk-ant-admin-` (ADMIN key required!)
- **OpenAI:** `sk-`
- **Groq:** `gsk_`
- **Perplexity:** `pplx-`
- **Mistral:** (varies)

### After Setup
```bash
docker-compose up -d                              # Start
docker-compose exec backend flask db upgrade      # Migrate
docker-compose exec backend python scripts/test_providers.py  # Test
open http://localhost:3000                        # Dashboard
```

---

**Happy tracking! 🚀**
