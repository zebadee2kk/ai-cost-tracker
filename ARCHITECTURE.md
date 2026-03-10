# Architecture — ai-cost-tracker

> For full setup, API documentation, and feature detail, see `README.md`.

## Overview

ai-cost-tracker is a full-stack web application for tracking AI API costs across multiple providers. It has a Python/FastAPI backend, a web frontend, and is deployed via Docker Compose.

## Directory Structure

```
ai-cost-tracker/
├── backend/                   ← Python FastAPI backend
│   ├── app/
│   │   ├── api/               ← API route handlers
│   │   ├── models/            ← Data models
│   │   ├── services/          ← Business logic
│   │   └── core/              ← Configuration, database
├── frontend/                  ← Web frontend
├── docs/                      ← Additional documentation
├── docker-compose.yml         ← Full stack deployment
└── .env.example               ← Environment variable template
```

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI |
| Frontend | See `frontend/` |
| Database | See `docker-compose.yml` |
| Deployment | Docker Compose |
| CI/CD | GitHub Actions (`.github/workflows/`) |

## Key Design Decisions

- All secrets via environment variables (`.env`, never committed)
- Docker Compose for both development and production
- `install.sh` for one-command setup
