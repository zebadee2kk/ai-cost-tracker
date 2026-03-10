# AI Context — ai-cost-tracker

> **Read this first.** This file orients any AI assistant to this repository.

## Repository Purpose

**ai-cost-tracker** is a full-stack web application for tracking, visualising, and managing AI API costs across multiple providers (OpenAI, Anthropic, Google, etc.). It provides a dashboard for monitoring spend by model, provider, project, and user; budget alerting; and cost optimisation recommendations.

## Start Here

| Document | Contents |
|----------|----------|
| [`README.md`](../README.md) | Full setup, features, API docs (23KB — read this) |
| [`ROADMAP.md`](../ROADMAP.md) | Feature roadmap and planned milestones |
| [`PROJECT_STATUS.md`](../PROJECT_STATUS.md) | Current status and priorities |
| [`ARCHITECTURE.md`](../ARCHITECTURE.md) | System architecture |

## Repository Structure

```
ai-cost-tracker/
├── ai/                        ← AI context files (YOU ARE HERE)
├── backend/                   ← Python/FastAPI backend
├── frontend/                  ← Web frontend (React/Next.js)
├── docs/                      ← Documentation
├── archive/                   ← Historical/deprecated files
├── docker-compose.yml         ← Docker Compose stack
├── install.sh                 ← One-command installer
├── .env.example               ← Environment variable template
├── .cursorrules               ← Cursor AI assistant rules
└── ROADMAP.md                 ← Feature roadmap
```

## Key Relationships

| Repo | Relationship |
|------|--------------|
| `portfolio-management` | Governance hub — tracks this repo's status |
| `derek-ai` | Derek AI may use this to report its own AI costs |
| `hamnet` | Infrastructure context — this app may be hosted on hamnet |

## Critical Rules for This Repo

1. **No secrets in commits** — all API keys and credentials in `.env` (never committed); use `.env.example` as template
2. **Read before write** — read `README.md` and relevant source files before making changes
3. **Read `ai/AI_RULES.md`** before any code changes
4. **Check `.cursorrules`** — it contains AI-specific guidance for this codebase
