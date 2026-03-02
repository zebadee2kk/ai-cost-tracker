# Google Gemini/Vertex AI API Research & Implementation Guide

**Last Updated:** March 2, 2026  
**Status:** Production Implementation Ready  
**Complexity:** ⭐⭐⭐⭐ HARDEST - Do this last

---

## Quick Reference

### Authentication (Production)
```bash
# Create service account
gcloud iam service-accounts create ai-tracker-sa

# Grant roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:ai-tracker-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Download credentials
gcloud iam service-accounts keys create key.json \
  --iam-account=ai-tracker-sa@PROJECT_ID.iam.gserviceaccount.com

# Set environment
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/key.json
```

### Tracking Methods

1. **Per-Request** (Immediate):
```python
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=prompt
)
usage = response.usage_metadata
# usage.prompt_token_count, usage.candidates_token_count
```

2. **Cloud Logging** (Aggregated):
```bash
gcloud logging read 'resource.type="aiplatform.googleapis.com/Endpoint"' \
  --limit=100 --format=json
```

3. **BigQuery** (Historical):
```sql
SELECT 
  DATE(timestamp) as date,
  SUM(response.input_token_count) as input_tokens,
  SUM(response.output_token_count) as output_tokens
FROM `PROJECT.dataset.predictions_*`
WHERE DATE(timestamp) = CURRENT_DATE()
GROUP BY date
```

### Available Metrics

| Metric | Source | Use Case |
|--------|--------|----------|
| Input tokens | response.usage_metadata.prompt_token_count | Cost calc |
| Output tokens | response.usage_metadata.candidates_token_count | Cost calc |
| Cached tokens | response.usage_metadata.cached_content_token_count | 50% discount |
| Request count | Cloud Logging | API frequency |
| Latency | Response metadata | Performance |

---

## Why Do This Last

1. ❌ **GCP project required** - infrastructure setup
2. ❌ **Service account** - IAM complexity
3. ❌ **Multiple APIs** - Vertex AI, Logging, Monitoring
4. ❌ **30+ min setup** - longest configuration
5. ⚠️ **No cost API** - must calculate manually

---

**Recommendation:** Implement OpenAI and Anthropic first, then tackle Google.

**Full detailed guide:** See artifacts for complete implementation.
