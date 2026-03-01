#!/usr/bin/env bash
# AI Cost Tracker - Quick Install Script
# Usage: bash install.sh
# Requires: Docker, Docker Compose plugin, Python 3

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo "================================================"
echo "   AI Cost Tracker — Quick Install"
echo "================================================"
echo ""

# ── Prerequisites check ──────────────────────────────────────────────────────
info "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || error "Docker not found. Install from https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || error "Docker Compose plugin not found. Update Docker Desktop or install the plugin."
command -v python3 >/dev/null 2>&1 || error "python3 not found. Install Python 3.9+."

DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
info "Docker $DOCKER_VERSION found."

# ── .env setup ───────────────────────────────────────────────────────────────
if [ -f ".env" ]; then
    warn ".env already exists — skipping secret generation. Delete .env to regenerate."
else
    info "Generating secrets and creating .env ..."
    cp .env.example .env

    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENC_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
              || python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")

    # Replace placeholder values
    sed -i "s|SECRET_KEY=change-me-in-production|SECRET_KEY=${SECRET_KEY}|g" .env
    sed -i "s|JWT_SECRET_KEY=change-me-in-production|JWT_SECRET_KEY=${JWT_SECRET}|g" .env
    sed -i "s|ENCRYPTION_KEY=change-me-in-production|ENCRYPTION_KEY=${ENC_KEY}|g" .env

    info ".env created with generated secrets."
    warn "Keep .env safe — it contains your encryption keys and is gitignored."
fi

# ── Build & start ─────────────────────────────────────────────────────────────
info "Building and starting containers (this may take a few minutes on first run)..."
docker compose up -d --build

# ── Wait for backend health ───────────────────────────────────────────────────
info "Waiting for backend to be ready..."
MAX_WAIT=60; ELAPSED=0
until curl -sf http://localhost:5000/api/health >/dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        error "Backend did not become healthy within ${MAX_WAIT}s. Check: docker compose logs backend"
    fi
    sleep 2; ELAPSED=$((ELAPSED + 2))
done
info "Backend healthy."

# ── Database migrations & seed ────────────────────────────────────────────────
info "Applying database migrations..."
docker compose exec -T backend flask db upgrade

info "Seeding service catalogue..."
docker compose exec -T backend python scripts/seed_services.py

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo -e "${GREEN}   Installation complete!${NC}"
echo "================================================"
echo ""
echo "  Frontend : http://localhost:3000"
echo "  Backend  : http://localhost:5000/api/health"
echo ""
echo "  Register your account at http://localhost:3000/register"
echo ""
echo "  Logs     : docker compose logs -f"
echo "  Stop     : docker compose down"
echo ""
echo "  For production deployment see: docs/production-deployment.md"
echo ""
