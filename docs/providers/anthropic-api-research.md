# Anthropic Claude API Research & Implementation Guide

**Last Updated:** March 2, 2026  
**Status:** Production Implementation Ready  
**Focus:** Usage & Cost tracking for billing and monitoring

---

## Critical Finding: Admin API Key Required

**⚠️ YOUR CURRENT ISSUE:** Standard API keys (`sk-ant-api-...`) **CANNOT** access usage/cost endpoints.

**✅ SOLUTION:** Use Admin API key (`sk-ant-admin-...`) generated at:
- https://console.anthropic.com/settings/organization
- Requires organization admin role
- Only admin keys have organization-level visibility

---

## Quick Reference

### Authentication
```bash
# Test if you have correct key type
echo $ANTHROPIC_ADMIN_API_KEY | head -c 15
# Must print: sk-ant-admin-

# Test connectivity
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=2026-03-01T00:00:00Z&ending_at=2026-03-02T00:00:00Z" \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: $ANTHROPIC_ADMIN_API_KEY" | jq .
```

### Key Endpoints

1. **Usage Report**: `/v1/organizations/usage_report/messages`
   - Tracks tokens by model, workspace, service tier, speed, geography
   - Bucket widths: 1m, 1h, 1d
   - Data available within 5 minutes

2. **Cost Report**: `/v1/organizations/cost_report`
   - USD costs by service tier (excludes Priority Tier)
   - Workspace-level breakdown

### Available Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| input_tokens | New input tokens | Cost calculation |
| output_tokens | Completion tokens | Cost calculation |
| cache_creation_input_tokens | Tokens written to cache | Cache write cost |
| cache_read_input_tokens | Tokens read from cache | 90% discount tracking |
| service_tier | standard/batch/priority | Tier-based billing |
| speed | standard/fast | Fast mode tracking (2026+) |
| inference_geo | us/global/not_available | Data residency |
| workspace_id | Workspace identifier | Multi-team billing |
| api_key_id | Key identifier | Key-level tracking |

---

## Implementation Priority

### Week 1: Basic Daily Sync
```python
def fetch_anthropic_daily_usage(admin_key, date):
    response = requests.get(
        "https://api.anthropic.com/v1/organizations/usage_report/messages",
        headers={
            "anthropic-version": "2023-06-01",
            "x-api-key": admin_key
        },
        params={
            "starting_at": f"{date}T00:00:00Z",
            "ending_at": f"{date}T23:59:59Z",
            "bucket_width": "1d",
            "group_by[]": ["model", "service_tier"]
        }
    )
    return response.json()
```

### Week 2: Hourly Granularity
```python
params["bucket_width"] = "1h"
params["group_by[]"].append("workspace_id")
```

### Week 3: Cache Tracking
```python
# Calculate cache hit ratio
cache_hit_ratio = (
    cache_read_tokens / 
    (cache_read_tokens + cache_creation_tokens)
)
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Wrong key type | Use sk-ant-admin- not sk-ant-api- |
| 403 Forbidden | Not org admin | Grant admin role in Console |
| Empty data | Too recent | Wait 5 min after API calls |
| 404 Not Found | Invalid workspace ID | Verify via /workspaces endpoint |

---

**Full detailed guide:** See artifacts in previous messages for complete 400+ line implementation guide.
