# Handover to Codex (Code Review & Testing)

## Role: Quality Gatekeeper

When Claude Code opens each PR, Codex reviews and validates the work against the checklist below.

## Review Checklist (For Each PR)

### 1) Code Quality
- Follow style guides:
  - **Python**: Black
  - **JavaScript**: ESLint
- Ensure all functions include docstrings/comments.
- Ensure no commented-out code or debug statements are merged.
- Verify variable/function names are meaningful.
- Verify error handling is implemented properly.

### 2) Testing
- Unit tests are written and passing.
- Test coverage thresholds:
  - **Backend**: >80%
  - **Frontend**: >70%
- Integration tests exist for API endpoints.
- Edge cases are covered (empty data, null values, etc.).

### 3) Security
- No hardcoded secrets or API keys.
- SQL injection prevention in place (parameterized queries).
- XSS prevention in place (sanitize user inputs).
- CSRF tokens are implemented.
- Bandit security scan passes.
- `npm audit` passes with no high/critical vulnerabilities.

### 4) Performance
- No N+1 queries.
- Database indexes are used appropriately.
- Large datasets handled efficiently (streaming, pagination).
- Page load time <2 seconds.
- API response time <500ms.

### 5) Documentation
- API endpoints are documented.
- Component usage examples are provided.
- README is updated if needed.
- Inline comments exist for complex logic.

---

## Testing Tasks (Week 1-2)

### Export System Testing
- Test with **1,000 records** → should complete in **<3 seconds**.
- Test with **10,000 records** → should complete in **<10 seconds**.
- Test with **100,000 records** → should complete in **<30 seconds**.
- Test CSV format opens correctly in Excel.
- Test JSON format parses correctly in Python/JS.
- Test date range filtering works.
- Test account filtering works.
- Test progress indicator shows during long exports.

### Visual Indicators Testing
- Verify API data shows blue **🔄 API** badge and circle points.
- Verify manual data shows orange **✍️ MANUAL** badge and square points.
- Test filter toggle: **All / API Only / Manual Only**.
- Test tooltips show correct source info.
- Run WCAG accessibility audit (axe DevTools).
- Test in Chrome, Firefox, Safari.
- Test on mobile (iOS Safari, Chrome Android).

---

## When Issues Are Found

If bugs or issues are found:
1. Comment on the PR with specific line numbers.
2. Explain the issue clearly with examples.
3. Suggest fixes where possible.
4. Mark PR as **Changes Requested**.
5. Notify **@Claude Code** and **@Perplexity**.

If everything passes:
1. Leave an approving review comment.
2. Mark PR as **Approved**.
3. Notify **@Perplexity** that the feature is ready to merge.
