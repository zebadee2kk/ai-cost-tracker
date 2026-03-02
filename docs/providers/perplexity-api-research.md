# Perplexity API Research & Implementation Guide

**Last Updated:** March 2, 2026  
**Status:** Production Implementation Ready  
**Complexity:** ⭐⭐⭐ Medium

---

## Critical Limitation

**❌ NO USAGE API ENDPOINT** (as of March 2026)

**Feature Request:** GitHub issue #266 - community requesting OpenAI-style usage API

**Current Tracking:** Manual per-request logging + monthly invoice reconciliation

---

## Quick Reference

### Authentication
```bash
# Generate at: https://www.perplexity.ai/settings/api
# Format: pplx-...
# Requires: Credits purchased OR payment method added

# Test connectivity
curl https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sonar",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Available APIs

1. **Sonar API** - Web-enhanced chat
   - `sonar`: $1/$1 per 1M tokens + $0.01 request
   - `sonar-pro`: $3/$15 per 1M tokens + $0.01 request
   - `sonar-deep-research`: Complex pricing (tokens + searches + reasoning)

2. **Agent API** - Third-party models at provider rates
   - OpenAI, Anthropic, Google, xAI
   - Transparent pass-through pricing
   - Tool costs: web_search ($0.005), fetch_url ($0.0005)

3. **Search API** - Raw search
   - $5.00 per 1,000 requests (no tokens)

4. **Embeddings API**
   - $0.004-$0.05 per 1M tokens depending on model

### Response Format

```json
{
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "total_tokens": 225,
    "search_queries": 0,
    "reasoning_tokens": 0,
    "citation_tokens": 0
  }
}
```

---

## Implementation Strategy

### Week 1: Per-Request Logging (REQUIRED)
```python
def call_perplexity_with_tracking(model, messages, db):
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
        json={"model": model, "messages": messages}
    )
    
    data = response.json()
    usage = data.get("usage", {})
    
    # Calculate cost based on model
    cost = calculate_perplexity_cost(model, usage)
    
    # MUST store immediately - no usage API to query later
    db.usage_entries.insert_one({
        "timestamp": datetime.now(),
        "model": model,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "search_queries": usage.get("search_queries", 0),
        "cost_usd": cost
    })
    
    return data
```

### Week 2: Invoice Reconciliation
```bash
# Manual process:
# 1. Download invoice from Settings → API → Invoices
# 2. Match 4-char API key suffix (e.g., "743S")
# 3. Compare with internal logs
# 4. Flag discrepancies
```

---

## Pricing Calculation

```python
def calculate_perplexity_cost(model, usage):
    pricing = {
        "sonar": {
            "input": 1/1_000_000,
            "output": 1/1_000_000,
            "request": 0.01
        },
        "sonar-deep-research": {
            "input": 2/1_000_000,
            "output": 8/1_000_000,
            "citations": 2/1_000_000,
            "reasoning": 3/1_000_000,
            "searches": 5/1000
        }
    }
    
    rates = pricing.get(model, {})
    
    input_cost = usage.get("prompt_tokens", 0) * rates.get("input", 0)
    output_cost = usage.get("completion_tokens", 0) * rates.get("output", 0)
    request_cost = rates.get("request", 0)
    citation_cost = usage.get("citation_tokens", 0) * rates.get("citations", 0)
    reasoning_cost = usage.get("reasoning_tokens", 0) * rates.get("reasoning", 0)
    search_cost = usage.get("search_queries", 0) * rates.get("searches", 0)
    
    return sum([input_cost, output_cost, request_cost, citation_cost, reasoning_cost, search_cost])
```

---

**Limitation Summary:**
- ❌ No usage API - must log every request
- ❌ Invoice shows only 4-char key suffix
- ❌ No rate limit headers
- ✅ Response includes detailed usage breakdown

**Full detailed guide:** See artifacts for complete implementation.
