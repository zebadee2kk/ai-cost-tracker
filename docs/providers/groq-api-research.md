# Groq API Research & Implementation Guide

**Last Updated:** March 2, 2026  
**Status:** Production Implementation Ready  
**Complexity:** ⭐⭐ Easy
**Special Feature:** Ultra-fast inference (fastest LLM API)

---

## Quick Reference

### Authentication
```bash
# Generate at: https://console.groq.com/keys
# Format: gsk-...

# Test connectivity
curl https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Rate Limit Headers (Every Response)

```
x-ratelimit-limit-requests: 14400        # RPD (requests per day)
x-ratelimit-limit-tokens: 18000          # TPM (tokens per minute)
x-ratelimit-remaining-requests: 14370    # RPD remaining
x-ratelimit-remaining-tokens: 17997      # TPM remaining
x-ratelimit-reset-requests: 2m59.56s     # RPD reset
x-ratelimit-reset-tokens: 7.66s          # TPM reset
```

**IMPORTANT:** 
- `limit-requests` / `remaining-requests` = RPD (requests per DAY)
- `limit-tokens` / `remaining-tokens` = TPM (tokens per MINUTE)

### Available Models (March 2026)

| Model | RPM | TPM | TPD |
|-------|-----|-----|-----|
| llama-3.3-70b-versatile | 30 | 12,000 | 100,000 |
| llama-4-scout-17b | 30 | 30,000 | 500,000 |
| groq/compound | 30 | 70,000 | - |
| whisper-large-v3 | 20 | 7,200 ASH | 28,800 ASD |

### Response Format

```json
{
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "total_tokens": 225,
    "queue_time": 0.002,
    "prompt_time": 0.015,
    "completion_time": 0.045,
    "total_time": 0.062
  }
}
```

**Unique to Groq:** Detailed timing metrics for performance analysis

---

## Implementation Strategy

### Week 1: Header Extraction
```python
def call_groq_with_tracking(model, messages, db):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={"model": model, "messages": messages}
    )
    
    data = response.json()
    usage = data.get("usage", {})
    headers = response.headers
    
    # Store usage + rate limits
    db.usage_entries.insert_one({
        "timestamp": datetime.now(),
        "model": model,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "queue_time_sec": usage.get("queue_time", 0),
        "total_time_sec": usage.get("total_time", 0),
        "rate_limit_tpm": headers.get("x-ratelimit-limit-tokens"),
        "remaining_tpm": headers.get("x-ratelimit-remaining-tokens")
    })
    
    # Alert if quota low
    remaining_pct = (
        int(headers.get("x-ratelimit-remaining-tokens", 0)) / 
        int(headers.get("x-ratelimit-limit-tokens", 1))
    ) * 100
    
    if remaining_pct < 20:
        alert(f"Groq TPM at {remaining_pct:.1f}%")
    
    return data
```

### Week 2: Performance Tracking
```python
# Groq is known for speed - track it!
def analyze_groq_speed(db):
    recent = db.usage_entries.find({
        "timestamp": {"$gte": datetime.now() - timedelta(hours=24)}
    })
    
    avg_total_time = sum(r["total_time_sec"] for r in recent) / len(recent)
    avg_queue_time = sum(r["queue_time_sec"] for r in recent) / len(recent)
    
    return {
        "avg_response_time": avg_total_time,
        "avg_queue_time": avg_queue_time
    }
```

---

## Key Features

1. ✅ **Ultra-fast inference** - track via timing fields
2. ✅ **Rate limit headers** - automatic on every response
3. ✅ **Multiple model families** - Llama, Mixtral, Gemma
4. ❌ **No usage API** - must log per request
5. ❌ **No public pricing** - cost estimation unavailable

---

## Limitations

- ❌ No usage API endpoint (must log per-request)
- ❌ No public pricing (track tokens only)
- ⚠️ Free tier has low limits (good for testing only)
- ✅ Rate limits clearly exposed in headers

**Full detailed guide:** See artifacts for complete implementation.
