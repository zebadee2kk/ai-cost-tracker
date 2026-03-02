# Provider API Comparison Matrix

**Last Updated:** March 2, 2026  
**Purpose:** Quick reference for implementation priorities

---

## Implementation Order (Recommended)

| Priority | Provider | Complexity | Setup Time | Why |
|----------|----------|-----------|-----------|-----|
| **1st** | OpenAI | ⭐⭐ Easy | 5 min | Single key type, rate headers, cost API |
| **2nd** | Anthropic | ⭐⭐⭐ Medium | 15 min | Rich metrics but admin key required |
| **3rd** | Groq | ⭐⭐ Easy | 5 min | Fast, simple, good rate headers |
| **4th** | Perplexity | ⭐⭐⭐ Medium | 10 min | No usage API, manual logging |
| **5th** | Mistral | ⭐⭐ Easy | 5 min | OpenAI-compatible, simple |
| **6th** | Google | ⭐⭐⭐⭐ Hard | 30 min | GCP setup, most complex |

---

## Authentication Comparison

| Provider | Key Format | Tracking Key | Setup Location |
|----------|-----------|--------------|----------------|
| OpenAI | `sk-...` | Same | platform.openai.com/api-keys |
| Anthropic | `sk-ant-admin-...` | **DIFFERENT** | console.anthropic.com/settings/organization |
| Google | JSON file | Service Account | console.cloud.google.com |
| Perplexity | `pplx-...` | Same | perplexity.ai/settings/api |
| Groq | `gsk-...` | Same | console.groq.com/keys |
| Mistral | `...` | Same | console.mistral.ai |

---

## Usage API Availability

| Provider | Usage API | Method | Data Delay |
|----------|-----------|--------|------------|
| OpenAI | ✅ Yes | `/v1/organization/usage/*` | 5-10 min |
| Anthropic | ✅ Yes | `/v1/organizations/usage_report/*` | 5 min |
| Google | ✅ Via Logging | Cloud Logging + BigQuery | Real-time |
| Perplexity | ❌ No | Per-request logging | Immediate |
| Groq | ❌ No | Per-request logging | Immediate |
| Mistral | ❌ No | Per-request logging | Immediate |

---

## Available Metrics

| Metric | OpenAI | Anthropic | Google | Perplexity | Groq | Mistral |
|--------|--------|-----------|--------|-----------|------|--------|
| Input tokens | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Output tokens | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cache tokens | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Cost USD | ✅ | ✅ | ❌ | Calculate | ❌ | Calculate |
| Rate headers | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Service tier | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Timing metrics | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |

---

## Diagnostic Checklist

### Step 1: Authentication
```bash
# OpenAI
curl -I -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Anthropic (check key type!)
echo $ANTHROPIC_ADMIN_API_KEY | head -c 15  # Must be: sk-ant-admin-

# Groq
curl -I -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models

# Perplexity
curl -I -H "Authorization: Bearer $PERPLEXITY_API_KEY" https://api.perplexity.ai/chat/completions
```

### Step 2: Usage API Test
```bash
# OpenAI
curl "https://api.openai.com/v1/organization/usage/completions?start_time=$(date -d '7 days ago' +%s)" \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.current_usage_usd'

# Anthropic
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=2026-03-01T00:00:00Z&ending_at=2026-03-02T00:00:00Z" \
  -H "x-api-key: $ANTHROPIC_ADMIN_API_KEY" \
  -H "anthropic-version: 2023-06-01" | jq '.data | length'
```

### Step 3: Logging Verification
```bash
# Check if any sync attempts are being logged
grep -i "sync" logs/app.log | tail -20
grep -i "anthropic\|openai\|groq" logs/app.log | tail -20
```

---

## Common Issues

### Anthropic: No Data
**Cause:** Using `sk-ant-api-` instead of `sk-ant-admin-`  
**Fix:** Regenerate admin key at console.anthropic.com/settings/organization

### OpenAI: Empty Usage
**Cause:** Time range too recent (< 5 min old)  
**Fix:** Query data from at least 10 minutes ago

### Google: 403 Forbidden
**Cause:** Missing IAM roles  
**Fix:** Grant roles/aiplatform.user, roles/logging.viewer

### Perplexity: Can't Find Usage
**Cause:** No usage API exists  
**Fix:** Implement per-request logging immediately

### Groq: Rate Limit Confusion
**Cause:** Headers show RPD not RPM for requests  
**Fix:** x-ratelimit-limit-requests = requests per DAY

---

## Next Steps

1. ✅ Implement OpenAI first (easiest, best testing)
2. ✅ Add Anthropic with admin key (richest metrics)
3. ✅ Add Groq (fast, simple)
4. ✅ Add Perplexity (manual logging required)
5. ⏳ Add Google last (most complex)

**See individual provider docs for detailed implementation guides.**
