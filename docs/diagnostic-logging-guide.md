# Diagnostic Logging Guide

**Last Updated:** March 2, 2026  
**Purpose:** Comprehensive guide to using diagnostic logging for debugging and monitoring

---

## Overview

The AI Cost Tracker now includes a comprehensive diagnostic logging system that provides:

- **Structured JSON logs** for easy parsing and analysis
- **Request/response correlation** with unique IDs
- **Performance timing metrics** for all API calls
- **Error context preservation** with full stack traces
- **Rate limit tracking** for quota management
- **Provider-specific metadata** for debugging

---

## Quick Start

### Enable Diagnostic Logging

Set the log level to DEBUG in your environment:

```bash
# In .env file
LOG_LEVEL=DEBUG

# Or as environment variable
export LOG_LEVEL=DEBUG
```

### View Real-Time Logs

```bash
# Docker Compose
docker-compose logs -f backend

# Local development
tail -f logs/app.log | jq .
```

---

## Log Structure

All diagnostic logs follow this JSON structure:

```json
{
  "timestamp": "2026-03-02T15:00:00.000000Z",
  "level": "INFO",
  "logger": "diagnostic.services.anthropic_service",
  "message": "API call started: anthropic.usage_report",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "context": {
    "provider": "anthropic",
    "endpoint": "usage_report",
    "account_id": 123,
    "start_date": "2026-03-01",
    "end_date": "2026-03-02"
  }
}
```

### Key Fields

- **timestamp**: UTC timestamp in ISO 8601 format
- **level**: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **logger**: Module that generated the log
- **message**: Human-readable description
- **correlation_id**: Unique ID linking related logs
- **context**: Provider-specific metadata

---

## Log Types

### 1. API Call Tracking

**Start of API Call:**
```json
{
  "message": "API call started: anthropic.usage_report",
  "correlation_id": "abc-123",
  "context": {
    "provider": "anthropic",
    "endpoint": "usage_report/messages",
    "account_id": 123
  }
}
```

**Successful Completion:**
```json
{
  "message": "API call succeeded: anthropic.usage_report",
  "correlation_id": "abc-123",
  "context": {
    "elapsed_seconds": 1.234,
    "provider": "anthropic"
  }
}
```

**Failed Call:**
```json
{
  "level": "ERROR",
  "message": "API call failed: anthropic.usage_report",
  "correlation_id": "abc-123",
  "context": {
    "error_type": "AuthenticationError",
    "error_message": "Invalid API key",
    "elapsed_seconds": 0.543
  },
  "exception": {
    "type": "AuthenticationError",
    "message": "Invalid or expired Anthropic Admin API key",
    "traceback": ["..."]  
  }
}
```

### 2. HTTP Request Logging

```json
{
  "level": "DEBUG",
  "message": "HTTP Request: GET https://api.anthropic.com/v1/organizations/usage_report/messages",
  "context": {
    "provider": "anthropic",
    "method": "GET",
    "url": "https://api.anthropic.com/v1/organizations/usage_report/messages",
    "headers": {
      "anthropic-version": "2023-06-01",
      "x-api-key": "sk-ant-admin-..."
    },
    "params": {
      "starting_at": "2026-03-01T00:00:00Z",
      "ending_at": "2026-03-02T23:59:59Z",
      "bucket_width": "1d"
    }
  }
}
```

### 3. HTTP Response Logging

```json
{
  "level": "INFO",
  "message": "HTTP Response: 200 from anthropic",
  "context": {
    "provider": "anthropic",
    "status_code": 200,
    "response_time_ms": 1234.5,
    "rate_limits": {},
    "body": {"data": [...]}
  }
}
```

### 4. Sync Operations

**Sync Attempt:**
```json
{
  "message": "Starting sync: anthropic account 123",
  "context": {
    "provider": "anthropic",
    "account_id": 123,
    "sync_type": "usage",
    "start_date": "2026-03-01",
    "end_date": "2026-03-02"
  }
}
```

**Sync Result:**
```json
{
  "message": "Sync completed: anthropic account 123",
  "context": {
    "provider": "anthropic",
    "account_id": 123,
    "success": true,
    "records_created": 2,
    "elapsed_seconds": 3.456
  }
}
```

### 5. Rate Limit Tracking

```json
{
  "level": "WARNING",
  "message": "Rate limit status: openai TPM",
  "context": {
    "provider": "openai",
    "limit_type": "TPM",
    "limit_value": 150000,
    "current_usage": 120000,
    "remaining": 30000,
    "usage_percent": 80.0,
    "reset_time": "60s"
  }
}
```

---

## Troubleshooting with Logs

### Problem: No Data Populating

**Step 1: Check sync attempts**

```bash
# Filter for sync logs
docker-compose logs backend | jq 'select(.message | contains("Starting sync"))'
```

**Expected Output:**
```json
{"message": "Starting sync: anthropic account 123", ...}
```

**If not present:** Scheduler isn't running or accounts not configured.

**Step 2: Check for errors**

```bash
# Filter for ERROR level logs
docker-compose logs backend | jq 'select(.level == "ERROR")'
```

**Common Errors:**

#### Authentication Failed
```json
{
  "level": "ERROR",
  "message": "Anthropic authentication failed (401)",
  "context": {
    "api_key_prefix": "sk-ant-api-..."
  }
}
```

**Solution:** Using wrong key type. Need `sk-ant-admin-...` not `sk-ant-api-...`

#### Invalid Key Format
```json
{
  "level": "ERROR",
  "message": "Invalid Anthropic API key format",
  "context": {
    "key_prefix": "sk-ant-api-",
    "required_prefix": "sk-ant-admin",
    "actual_format": "standard"
  }
}
```

**Solution:** Generate admin key at console.anthropic.com/settings/organization

---

### Problem: Rate Limits Hit

**Check rate limit warnings:**

```bash
docker-compose logs backend | jq 'select(.context.usage_percent > 80)'
```

**Example Output:**
```json
{
  "level": "WARNING",
  "message": "Rate limit status: openai TPM",
  "context": {
    "usage_percent": 85.2,
    "remaining": 22200,
    "reset_time": "45s"
  }
}
```

**Solution:** Reduce sync frequency or upgrade API tier

---

### Problem: Slow Performance

**Check timing metrics:**

```bash
# Find slow API calls (>5 seconds)
docker-compose logs backend | jq 'select(.context.elapsed_seconds > 5)'
```

**Example Output:**
```json
{
  "message": "API call succeeded: anthropic.usage_report",
  "context": {
    "elapsed_seconds": 8.234,
    "provider": "anthropic"
  }
}
```

**Common Causes:**
- Large date ranges
- Pagination with many pages
- Network latency
- Provider API slowdowns

---

## Querying Logs with jq

### Find All Errors for a Provider

```bash
docker-compose logs backend | \
  jq 'select(.level == "ERROR" and .context.provider == "anthropic")'
```

### Track a Specific Sync Operation

```bash
# Use correlation_id from first log entry
docker-compose logs backend | \
  jq 'select(.correlation_id == "abc-123")'
```

### Calculate Average Response Time

```bash
docker-compose logs backend | \
  jq -s '[.[] | select(.context.response_time_ms != null) | .context.response_time_ms] | add/length'
```

### Count Sync Successes vs Failures

```bash
# Successes
docker-compose logs backend | \
  jq -s '[.[] | select(.message | contains("Sync completed") and .context.success == true)] | length'

# Failures  
docker-compose logs backend | \
  jq -s '[.[] | select(.message | contains("Sync failed"))] | length'
```

---

## Integration with Log Aggregation Tools

### Grafana Loki

```yaml
# docker-compose.yml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    
  promtail:
    image: grafana/promtail:latest
    volumes:
      - ./logs:/logs
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
```

**Query Examples:**
```
# All errors
{logger=~"diagnostic.*"} |= "ERROR"

# Anthropic sync failures
{logger="diagnostic.services.anthropic_service"} |= "Sync failed"

# Rate limit warnings
{logger=~"diagnostic.*"} |= "rate limit" |= "WARNING"
```

### ELK Stack (Elasticsearch, Logstash, Kibana)

**Logstash Configuration:**

```conf
input {
  file {
    path => "/app/logs/app.log"
    codec => "json"
  }
}

filter {
  json {
    source => "message"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "ai-cost-tracker-%{+YYYY.MM.dd}"
  }
}
```

**Kibana Queries:**
```
# Authentication failures
level:ERROR AND context.error_type:"AuthenticationError"

# Slow API calls
context.elapsed_seconds:>5

# Rate limit warnings by provider
level:WARNING AND context.provider:* AND message:"rate limit"
```

---

## Best Practices

### Development

1. **Always use DEBUG level** during development
2. **Check logs immediately** after configuration changes
3. **Use correlation IDs** to trace issues across multiple services
4. **Test with small date ranges** first

### Production

1. **Use INFO level** to reduce log volume
2. **Set up log rotation** (logrotate or Docker logging drivers)
3. **Monitor ERROR/WARNING counts** via metrics
4. **Use log aggregation tools** for centralized visibility
5. **Set up alerts** for:
   - Authentication failures
   - Rate limit warnings (>80%)
   - Sync failures
   - API errors

### Log Retention

```yaml
# docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

---

## Provider-Specific Diagnostics

### Anthropic

**Common Issues:**

1. **Wrong key type**
   - Look for: `"actual_format": "standard"`
   - Solution: Use `sk-ant-admin-` key

2. **No usage data**
   - Check: `"data_points": 0`
   - Causes: No API calls made, time range too recent

3. **Empty date ranges**
   - Check: `"total_items": 0`
   - Solution: Verify organization has usage in date range

### OpenAI

**Common Issues:**

1. **Rate limits**
   - Look for: `"usage_percent" > 80`
   - Solution: Implement backoff or upgrade tier

2. **Missing usage data**
   - Check: `"current_usage_usd": 0`
   - Causes: New account, no recent usage

### Google Gemini

**Common Issues:**

1. **Missing credentials**
   - Look for: `"UNAUTHENTICATED"`
   - Solution: Set `GOOGLE_APPLICATION_CREDENTIALS`

2. **Permission denied**
   - Look for: `"403 Permission Denied"`
   - Solution: Grant IAM roles to service account

---

## Next Steps

1. **Enable DEBUG logging** in your environment
2. **Trigger a sync** manually and watch logs
3. **Check for authentication errors** first
4. **Verify API keys** are correct type for each provider
5. **Review response times** for performance issues
6. **Set up log monitoring** for production

---

## Support

If you're still experiencing issues after reviewing logs:

1. Export relevant log entries (correlation_id)
2. Check GitHub Issues for similar problems
3. Include log excerpts when creating new issues
4. Redact API keys before sharing logs
