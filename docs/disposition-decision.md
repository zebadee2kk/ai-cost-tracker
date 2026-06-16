# Disposition Decision: Public Reference vs Archive

**Issue:** [#84](https://github.com/zebadee2kk/ai-cost-tracker/issues/84)
**Date:** 2026-06-16
**Author:** Richard Ham ([@zebadee2kk](https://github.com/zebadee2kk))

---

## Current State

| Property | Value |
|----------|-------|
| Repository | `zebadee2kk/ai-cost-tracker` |
| Visibility | Public |
| Archived | No |
| Default branch | `master` |
| Open issues | 0 (excluding this tracking issue) |
| Open PRs | 0 |
| Canonical internal copy | `zebadee2kk/agent-toolkit/ai-cost-tracker/` (private) |
| Last public commit | `9467abf` — docs: update status |
| Project phase | Phase 3 Sprint 3 (~85% complete per ROADMAP.md) |

### What this repo contains

- Full-stack AI cost tracking application (Flask backend, React frontend)
- Multi-provider API integrations (OpenAI, Anthropic, with manual entry for Groq, Perplexity)
- Phase 1–3 features: sync engine, dashboard, alerts (email/Slack/Discord/Teams), analytics, CI/CD
- Docker Compose deployment configuration
- Comprehensive documentation in `docs/` (handover guides, specs, setup guides)

### What the internal canonical copy contains

The private `zebadee2kk/agent-toolkit` repository holds a sanitized current-tree snapshot of this project at `ai-cost-tracker/`. Source repository history was **not** imported — only the current code state was copied.

---

## Analysis: Keep as Public Reference vs Archive

### Option A — Keep as Legacy Public Reference (current posture)

**Pros:**

1. **External value.** The codebase is a complete, well-documented reference implementation for multi-provider AI cost tracking — a problem many developers face. It demonstrates Flask + React architecture, JWT auth, encrypted key storage, multi-channel notifications, and CI/CD patterns.

2. **No harm in keeping it.** The repo has no open issues or PRs. It requires zero maintenance investment. GitHub hosting costs nothing for a public repo.

3. **Discoverability.** External developers searching for AI cost tracking solutions may find this repo via search engines or GitHub search. Archiving removes discoverability.

4. **No archival approval gate satisfied yet.** Per issue #84 boundary conditions, explicit Richard approval is required before any archive action. This document is a planning artifact, not an approval.

**Cons:**

1. **No active development.** Active development has moved to the private `agent-toolkit` repo. This public repo will increasingly diverge from the canonical version, potentially becoming stale or misleading.

2. **Perceived abandonment.** A public repo with no recent commits and a README stating "development has moved" may confuse visitors expecting an actively maintained project.

3. **README already signals migration.** The README explicitly directs users to the internal canonical copy, reducing the practical value of this public reference.

### Option B — Archive After Approval Gate

**Pros:**

1. **Clean signal.** An archived repo clearly communicates "not actively maintained" and prevents confusion. Visitors can still read and fork, but won't expect new features or responses.

2. **Reduces surface area.** Eliminates a stale public repo from the project estate, simplifying the portfolio.

3. **Still accessible.** Archived repos remain visible and forkable on GitHub — they are not deleted.

**Cons:**

1. **Irreversible signal.** While GitHub allows unarchiving, archiving is a strong signal that may reduce organic discovery.

2. **Requires fulfillment of approval gate conditions:**
   - Explicit Richard approval for this exact repository
   - Backup/snapshot and restorable evidence
   - Final check of no active issues/PRs, external dependencies, or harmed users
   - Public utility/value considered (see Option A pros)
   - Confirmation that internal canonical copy remains available at `zebadee2kk/agent-toolkit/ai-cost-tracker/`

3. **Locked state.** Archived repos cannot accept new issues, PRs, or commits — which is the desired signal but is also a permanent reduction in utility.

### Option C — Keep Public Indefinitely for Standalone Utility

**Pros:**

1. **Maximum utility.** The codebase is a genuinely useful reference for developers building similar tools. The documentation alone (handover guides, specs, setup guides) has standalone educational value.

2. **No action required.** Maintaining the current public posture is zero-effort.

3. **Aligns with open-source ethos.** The project is MIT-licensed and was developed as open source. Keeping it public honors that intent.

**Cons:**

1. **Documentation drift.** Over time, this repo's docs will diverge from the actively maintained internal version, potentially reducing accuracy.

2. **README contradiction.** The README currently says "development has moved" — keeping it public indefinitely without updating this message is confusing.

---

## Recommendation

**Recommendation: Option A — Keep as legacy public reference, with a README update.**

### Rationale

The current posture is the lowest-risk, highest-utility option:

- The repo costs nothing to keep public.
- It has standalone educational and reference value as a full-stack AI cost tracking implementation.
- The README already correctly signals that active development has moved internally.
- Archiving should be deferred until the approval gate conditions are formally satisfied (this document is analysis, not approval).
- If future maintenance of the public README becomes a concern, a single commit updating the status message is sufficient.

### Suggested README Update

The first section of README.md currently reads:

> Active internal development has moved to the private `zebadee2kk/agent-toolkit` repository...

This is correct but could be strengthened with a line like:

> This repository is preserved as a public reference. For the latest development, see the internal canonical copy.

### When to Revisit

Revisit this decision when:

1. Phase 4 development in the private `agent-toolkit` significantly diverges from this snapshot.
2. External links or dependencies on this public repo are identified.
3. Explicit approval for archival is granted by Richard with all gate conditions satisfied.

---

## Approval Gate Checklist (for future archive action)

Before any archive action, all of the following must be confirmed:

- [ ] Explicit Richard approval for `zebadee2kk/ai-cost-tracker`
- [ ] Backup/snapshot taken and restorable
- [ ] No active issues or PRs (current: 0 open, 0 closed PRs pending)
- [ ] No external dependencies or public users identified as harmed
- [ ] Public utility/value considered (documented above in Options A and C)
- [ ] Internal canonical copy confirmed available at `zebadee2kk/agent-toolkit/ai-cost-tracker/`

---

*This document is a planning and analysis artifact. It does not constitute approval for archival.*
