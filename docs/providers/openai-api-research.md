# OpenAI API Research & Implementation Guide

**Last Updated:** March 2, 2026  
**Status:** Production Implementation Ready  
**Complexity:** ⭐⭐ EASIEST - Start here

---

## Quick Reference

### Authentication
```bash
# Generate at: https://platform.openai.com/api-keys
# Format: sk-...

# Test connectivity
curl "https://api.openai.com/v1/organization/usage/completions?start_time=$(date -d '7 days ago' +%s)&bucket_width=1d" \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq .
```

### Key Endpoints

1. **Usage API**: `/v1/organization/usage/*`
   - `/completions` - LLM inference
   - `/embeddings` - Text embeddings
   - `/images` - DALL-E generation
   - `/audio` - Whisper transcription

2. **Rate Limit Headers** (on EVERY response):
```
x-ratelimit-limit-requests: 60
x-ratelimit-limit-tokens: 150000
x-ratelimit-remaining-requests: 59
x-ratelimit-remaining-tokens: 149984
x-ratelimit-reset-requests: 1s
x-ratelimit-reset-tokens: 6m0s
```

### Available Metrics

| Metric | Source | Use Case |
|--------|--------|----------|
| Input tokens | usage.n_context_tokens_total | Cost calculation |
| Output tokens | usage.n_generated_tokens_total | Cost calculation |
| Current cost USD | usage.current_usage_usd | Billing period tracking |
| Projected cost USD | usage.projected_usage_usd | Monthly forecast |
| Rate limits | Response headers | Real-time quota monitoring |

---

## Implementation Priority

### Week 1: Basic Usage Tracking
```python
import time

def fetch_openai_usage(api_key):
    end_time = int(time.time())
    start_time = end_time - (24 * 3600)  # Last 24h
    
    response = requests.get(
        "https://api.openai.com/v1/organization/usage/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        params={
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": "1h"
        }
    )
    
    data = response.json()
    return {
        "tokens": data.get("data", []),
        "current_cost": data.get("current_usage_usd"),
        "projected_cost": data.get("projected_usage_usd")
    }
```

### Week 2: Rate Limit Extraction
```python
def extract_rate_limits(response):
    return {
        "limit_tpm": response.headers.get("x-ratelimit-limit-tokens"),
        "remaining_tpm": response.headers.get("x-ratelimit-remaining-tokens"),
        "reset_tokens": response.headers.get("x-ratelimit-reset-tokens"),
        "timestamp": datetime.now().isoformat()
    }
```

---

## Why Start With OpenAI

1. ✅ **Single key type** - no admin vs standard confusion
2. ✅ **Rate limit headers** - automatic on every call
3. ✅ **Cost API** - direct USD reporting
4. ✅ **5 min setup** - fastest to implement
5. ✅ **Well documented** - extensive examples

---

**Full detailed guide:** See artifacts for complete implementation.
