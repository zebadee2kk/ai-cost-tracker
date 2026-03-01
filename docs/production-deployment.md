# Production Deployment Guide

**Audience:** Self-hosted / homelab / VPS deployments
**Prerequisite:** Local deployment verified via `docs/local-deployment-log.md`

---

## Pre-flight Checklist (P0 — must complete before enabling real APIs)

- [ ] Generate and set production secrets (see Step 1)
- [ ] Override DB credentials (see Step 2)
- [ ] HTTPS configured end-to-end (see Step 3)
- [ ] CORS restricted to exact production origin (see Step 4)
- [ ] Verify all provider credentials with `/api/accounts/{id}/test`

---

## Step 1 — Generate Production Secrets

Generate three separate strong secrets. **Never reuse dev secrets.**

```bash
# Flask secret key
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# JWT secret key (set separately from SECRET_KEY)
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"

# Fernet encryption key for API keys at rest
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Set these in your production `.env` (or secret manager). The app will **hard-fail at startup** in production mode if any of these are missing or set to defaults.

> ⚠️ Never commit production secrets to git. `.env` is in `.gitignore`.

---

## Step 2 — Override Database Credentials

`docker-compose.yml` now reads DB credentials from environment variables with
`:-default` fallbacks for local dev. In production, set real values:

```bash
# In your production .env or environment:
POSTGRES_USER=<strong-username>
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=ai_tracker_prod
DATABASE_URL=postgresql://<user>:<password>@db:5432/ai_tracker_prod
```

Then restart the stack:
```bash
docker compose down -v   # ⚠️ destroys existing data — backup first
docker compose up -d --build
docker compose exec backend flask db upgrade
docker compose exec backend python scripts/seed_services.py
```

---

## Step 3 — HTTPS / TLS

The app must be served over HTTPS in production. Use a reverse proxy (nginx or Caddy) in front of the Docker stack.

### Option A: Caddy (easiest — auto TLS via Let's Encrypt)

```caddyfile
# /etc/caddy/Caddyfile
ai-cost-tracker.yourdomain.com {
    reverse_proxy localhost:3000
}

api.ai-cost-tracker.yourdomain.com {
    reverse_proxy localhost:5000
}
```

```bash
sudo systemctl reload caddy
```

### Option B: nginx + Certbot

```nginx
server {
    listen 443 ssl;
    server_name ai-cost-tracker.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/ai-cost-tracker.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai-cost-tracker.yourdomain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo certbot --nginx -d ai-cost-tracker.yourdomain.com
```

---

## Step 4 — Restrict CORS to Production Origin

Set `CORS_ORIGINS` in your production `.env` to your exact frontend domain only:

```bash
# Single origin (most common):
CORS_ORIGINS=https://ai-cost-tracker.yourdomain.com

# Multiple origins (only if needed):
CORS_ORIGINS=https://ai-cost-tracker.yourdomain.com,https://dashboard.yourdomain.com
```

> Do NOT use `*` or localhost values in production.

---

## Step 5 — Anthropic API Key Note

Anthropic usage sync requires an **Admin API key** (`sk-ant-admin...`), not a
standard inference key. Using the wrong key type causes silent sync failures.

- Log in to console.anthropic.com → Settings → API Keys → Create Admin Key
- Use this key when adding an Anthropic account via the dashboard
- Verify it works: `GET /api/accounts/{id}/test` should return `{"success": true}`

---

## Step 6 — Verify Before Go-Live

```bash
# 1. Confirm all containers healthy
sudo docker compose ps

# 2. Backend health check
curl https://api.ai-cost-tracker.yourdomain.com/api/health

# 3. Confirm FLASK_ENV is production
sudo docker compose exec backend env | grep FLASK_ENV

# 4. Run targeted regression tests
sudo docker compose exec backend python -m pytest tests/test_auth.py tests/test_accounts.py tests/test_encryption.py tests/test_webhook_validator.py -q

# 5. Test each provider credential
# (Replace TOKEN and ACCOUNT_ID with real values)
TOKEN=$(curl -s -X POST https://api.ai-cost-tracker.yourdomain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -H "Authorization: Bearer $TOKEN" \
  https://api.ai-cost-tracker.yourdomain.com/api/accounts/1/test
```

---

## Rollback

```bash
# Stop stack (keep data)
sudo docker compose down

# Full reset (destroys all data — use only if needed)
sudo docker compose down -v
```
