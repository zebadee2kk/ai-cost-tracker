# AI Rules — ai-cost-tracker

These rules apply to ALL AI assistants (Claude, Copilot, Perplexity, Cursor, etc.) working in this repository.

## Non-Negotiable Rules

1. **No secrets in commits** — API keys, tokens, database passwords must NEVER be committed. Use `.env.example` pattern.
2. **Read before write** — always read `README.md` and relevant source files before modifying
3. **Read `.cursorrules`** — this file contains specific AI coding rules for this project
4. **Run tests before committing** — check `README.md` for test commands
5. **Update CHANGELOG.md** for any user-visible change

## Code Style

- **Backend**: Python 3.11+, FastAPI, full type hints, docstrings
- **Frontend**: Follow existing framework/style patterns
- **API responses**: Consistent schema — check existing endpoints for patterns
- **Error handling**: Explicit error responses, never silent failures

## File Ownership

| File/Folder | Rule |
|-------------|------|
| `.env.example` | Update when adding new environment variables |
| `docker-compose.yml` | High caution — read fully before changes |
| `backend/` | Follow existing patterns and type hints |
| `frontend/` | Follow existing component patterns |
| `ai/AI_HANDOVER.md` | Update at end of every session |
| `CHANGELOG.md` | Append only, newest at top |

## Commit Message Format

`feat:`, `fix:`, `docs:`, `chore:`, `test:` — conventional commits

## Before Every Commit

- [ ] No real credentials or API keys in changed files
- [ ] `.env.example` updated if new env vars added
- [ ] Tests pass
- [ ] `ai/AI_HANDOVER.md` updated if significant session
