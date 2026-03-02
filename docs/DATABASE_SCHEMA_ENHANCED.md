# Enhanced Database Schema for Multi-Provider Tracking

**Version:** 2.0  
**Date:** March 2, 2026  
**Purpose:** Support rich metrics from 6 AI providers

---

## Overview

This enhanced schema expands `usage_records` to track:

1. **Token Breakdowns**: Input, output, cache (creation/read)
2. **Rate Limits**: TPM/RPM/RPD quotas and remaining
3. **Service Tiers**: Anthropic's standard/batch/priority
4. **Performance**: Groq timing, Google latency
5. **Geography**: Anthropic's data residency
6. **Provider Fields**: Flexible JSON for unique metrics

---

## Enhanced usage_records Table

### New Columns Added

```sql
ALTER TABLE usage_records ADD COLUMN IF NOT EXISTS:

-- Token breakdowns
input_tokens INTEGER DEFAULT 0,
output_tokens INTEGER DEFAULT 0,
cache_creation_tokens INTEGER DEFAULT 0,
cache_read_tokens INTEGER DEFAULT 0,

-- Rate limits (from headers)
rate_limit_tpm INTEGER,              -- Tokens per minute limit
rate_limit_rpm INTEGER,              -- Requests per minute limit  
rate_limit_rpd INTEGER,              -- Requests per day limit
remaining_tpm INTEGER,               -- TPM remaining
remaining_rpm INTEGER,               -- RPM remaining
remaining_rpd INTEGER,               -- RPD remaining
reset_tpm_seconds INTEGER,           -- Seconds until TPM reset
reset_rpm_seconds INTEGER,           -- Seconds until RPM reset

-- Service/tier information
service_tier VARCHAR(50),            -- Anthropic: standard/batch/priority
speed_tier VARCHAR(50),              -- Anthropic: standard/fast
inference_geo VARCHAR(50),           -- Anthropic: us/global/not_available
workspace_id VARCHAR(255),           -- Anthropic workspace
model_name VARCHAR(255),             -- Specific model used

-- Performance metrics
queue_time_ms DECIMAL(10,3),         -- Groq: time in queue
prompt_time_ms DECIMAL(10,3),       -- Groq: input processing time
completion_time_ms DECIMAL(10,3),   -- Groq: output generation time
total_time_ms DECIMAL(10,3),         -- Total request duration

-- Search-specific (Perplexity)
search_queries_count INTEGER DEFAULT 0,
reasoning_tokens INTEGER DEFAULT 0,
citation_tokens INTEGER DEFAULT 0,

-- Existing metadata field remains for flexibility
-- metadata JSONB    (already exists)
```

### Full Enhanced Schema

```sql
CREATE TABLE IF NOT EXISTS usage_records (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) NOT NULL,
    service_id INTEGER REFERENCES services(id) NOT NULL,
    
    -- Timing
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    
    -- Token usage (ENHANCED)
    tokens_used INTEGER DEFAULT 0,              -- Legacy: total tokens
    input_tokens INTEGER DEFAULT 0,             -- NEW: Input tokens only
    output_tokens INTEGER DEFAULT 0,            -- NEW: Output tokens only
    cache_creation_tokens INTEGER DEFAULT 0,    -- NEW: Cache write
    cache_read_tokens INTEGER DEFAULT 0,        -- NEW: Cache read (discounted)
    tokens_remaining INTEGER,                   -- Legacy: quota remaining
    
    -- Cost
    cost NUMERIC(10,4) DEFAULT 0,
    cost_currency VARCHAR(10) DEFAULT 'USD',
    
    -- Rate limits (NEW)
    rate_limit_tpm INTEGER,
    rate_limit_rpm INTEGER,
    rate_limit_rpd INTEGER,
    remaining_tpm INTEGER,
    remaining_rpm INTEGER,
    remaining_rpd INTEGER,
    reset_tpm_seconds INTEGER,
    reset_rpm_seconds INTEGER,
    
    -- Provider-specific (NEW)
    service_tier VARCHAR(50),        -- Anthropic tiers
    speed_tier VARCHAR(50),          -- Anthropic fast mode
    inference_geo VARCHAR(50),       -- Anthropic geography
    workspace_id VARCHAR(255),       -- Anthropic workspace
    model_name VARCHAR(255),         -- Model used
    
    -- Performance (NEW)
    queue_time_ms DECIMAL(10,3),
    prompt_time_ms DECIMAL(10,3),
    completion_time_ms DECIMAL(10,3),
    total_time_ms DECIMAL(10,3),
    
    -- Search (NEW - Perplexity)
    search_queries_count INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    citation_tokens INTEGER DEFAULT 0,
    
    -- Legacy fields
    sessions_active INTEGER,
    api_calls INTEGER DEFAULT 1,
    request_type VARCHAR(100),
    source VARCHAR(50) NOT NULL DEFAULT 'api',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Indexes for performance
    INDEX idx_usage_account_timestamp (account_id, timestamp DESC),
    INDEX idx_usage_service_timestamp (service_id, timestamp DESC),
    INDEX idx_usage_model (model_name, timestamp DESC),
    INDEX idx_usage_service_tier (service_tier, timestamp DESC)
);
```

---

## Provider-Specific Usage

### OpenAI

```python
usage_record = {
    "input_tokens": 500,
    "output_tokens": 200,
    "rate_limit_tpm": 150000,
    "remaining_tpm": 149300,
    "reset_tpm_seconds": 45,
    "model_name": "gpt-4o",
    "cost": 0.015
}
```

### Anthropic

```python
usage_record = {
    "input_tokens": 1000,
    "output_tokens": 500,
    "cache_creation_tokens": 5000,  # Write to cache
    "cache_read_tokens": 3000,       # Read from cache (90% discount)
    "service_tier": "standard",      # or "batch" or "priority"
    "speed_tier": "standard",        # or "fast"
    "inference_geo": "us",           # or "global"
    "workspace_id": "ws_abc123",
    "model_name": "claude-sonnet-4-5",
    "cost": 0.0225
}
```

### Groq

```python
usage_record = {
    "input_tokens": 150,
    "output_tokens": 75,
    "queue_time_ms": 2.5,
    "prompt_time_ms": 15.3,
    "completion_time_ms": 45.7,
    "total_time_ms": 63.5,
    "rate_limit_tpm": 12000,
    "rate_limit_rpd": 14400,
    "remaining_tpm": 11775,
    "remaining_rpd": 14370,
    "model_name": "llama-3.3-70b-versatile"
}
```

### Perplexity

```python
usage_record = {
    "input_tokens": 33,
    "output_tokens": 7163,
    "search_queries_count": 18,
    "reasoning_tokens": 73997,
    "citation_tokens": 20016,
    "model_name": "sonar-deep-research",
    "cost": 0.409393
}
```

### Google Gemini

```python
usage_record = {
    "input_tokens": 800,
    "output_tokens": 400,
    "cache_read_tokens": 2000,  # 50% discount
    "total_time_ms": 1250.5,
    "model_name": "gemini-3.5-flash"
}
```

---

## Migration Strategy

### 1. Backup First

```bash
# Production backup
pg_dump -h $DB_HOST -U $DB_USER -d ai_cost_tracker > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql
```

### 2. Apply Migration

```bash
# Run migration script
flask db upgrade

# Or manually:
psql -h $DB_HOST -U $DB_USER -d ai_cost_tracker -f migrations/versions/202603_enhanced_usage_tracking.py
```

### 3. Verify Schema

```sql
-- Check new columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'usage_records'
AND column_name IN (
    'input_tokens', 'output_tokens', 'cache_creation_tokens',
    'rate_limit_tpm', 'service_tier', 'queue_time_ms'
);

-- Should return 6 rows
```

### 4. Backfill Existing Data (Optional)

```sql
-- Split existing tokens_used into input/output (estimate 60/40 split)
UPDATE usage_records 
SET 
    input_tokens = CAST(tokens_used * 0.6 AS INTEGER),
    output_tokens = CAST(tokens_used * 0.4 AS INTEGER)
WHERE input_tokens = 0 AND output_tokens = 0 AND tokens_used > 0;

-- Extract model from metadata if present
UPDATE usage_records
SET model_name = metadata->>'model'
WHERE model_name IS NULL AND metadata ? 'model';
```

---

## Query Examples

### Cache Effectiveness (Anthropic)

```sql
SELECT 
    DATE(timestamp) as date,
    SUM(cache_read_tokens) as cache_hits,
    SUM(cache_creation_tokens) as cache_writes,
    ROUND(
        SUM(cache_read_tokens)::numeric / 
        NULLIF(SUM(cache_read_tokens + cache_creation_tokens), 0) * 100,
        2
    ) as cache_hit_rate_pct
FROM usage_records
WHERE service_id = (SELECT id FROM services WHERE name = 'anthropic')
AND timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

### Rate Limit Pressure

```sql
SELECT 
    s.name as provider,
    AVG(
        CASE WHEN rate_limit_tpm > 0 
        THEN (remaining_tpm::numeric / rate_limit_tpm) * 100 
        END
    ) as avg_quota_remaining_pct,
    COUNT(CASE WHEN remaining_tpm::numeric / rate_limit_tpm < 0.2 THEN 1 END) as low_quota_events
FROM usage_records ur
JOIN services s ON ur.service_id = s.id
WHERE timestamp >= NOW() - INTERVAL '24 hours'
AND rate_limit_tpm IS NOT NULL
GROUP BY s.name;
```

### Performance by Provider

```sql
SELECT
    s.name as provider,
    model_name,
    COUNT(*) as requests,
    ROUND(AVG(total_time_ms), 2) as avg_latency_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms), 2) as p95_latency_ms
FROM usage_records ur
JOIN services s ON ur.service_id = s.id
WHERE timestamp >= NOW() - INTERVAL '7 days'
AND total_time_ms IS NOT NULL
GROUP BY s.name, model_name
ORDER BY avg_latency_ms ASC;
```

### Service Tier Analysis (Anthropic)

```sql
SELECT
    service_tier,
    COUNT(*) as requests,
    SUM(input_tokens + output_tokens) as total_tokens,
    SUM(cost) as total_cost_usd,
    ROUND(AVG(cost), 6) as avg_cost_per_request
FROM usage_records
WHERE service_id = (SELECT id FROM services WHERE name = 'anthropic')
AND timestamp >= NOW() - INTERVAL '30 days'
AND service_tier IS NOT NULL
GROUP BY service_tier
ORDER BY total_cost_usd DESC;
```

---

## Dashboard Queries

### Real-Time Provider Health

```sql
WITH recent_usage AS (
    SELECT 
        s.name,
        ur.timestamp,
        ur.remaining_tpm,
        ur.rate_limit_tpm,
        ur.remaining_rpd,
        ur.rate_limit_rpd,
        ur.total_time_ms
    FROM usage_records ur
    JOIN services s ON ur.service_id = s.id
    WHERE ur.timestamp >= NOW() - INTERVAL '5 minutes'
)
SELECT
    name as provider,
    COUNT(*) as requests_last_5min,
    ROUND(AVG(total_time_ms), 1) as avg_latency_ms,
    MIN(remaining_tpm) as min_tpm_remaining,
    MIN(remaining_rpd) as min_rpd_remaining,
    CASE 
        WHEN MIN(remaining_tpm::numeric / NULLIF(rate_limit_tpm, 0)) < 0.1 THEN 'CRITICAL'
        WHEN MIN(remaining_tpm::numeric / NULLIF(rate_limit_tpm, 0)) < 0.3 THEN 'WARNING'
        ELSE 'OK'
    END as quota_status
FROM recent_usage
GROUP BY name;
```

---

## Rollback Plan

If migration causes issues:

```sql
-- 1. Drop new columns (safe if no data written yet)
ALTER TABLE usage_records 
DROP COLUMN IF EXISTS input_tokens,
DROP COLUMN IF EXISTS output_tokens,
DROP COLUMN IF EXISTS cache_creation_tokens,
DROP COLUMN IF EXISTS cache_read_tokens,
DROP COLUMN IF EXISTS rate_limit_tpm,
-- ... (drop all new columns)
;

-- 2. Or restore from backup
psql -h $DB_HOST -U $DB_USER -d ai_cost_tracker < backup_YYYYMMDD_HHMMSS.sql
```

---

## Next Steps

1. ✅ Backup production database
2. ✅ Run migration in staging first
3. ✅ Test with sample data
4. ✅ Update all service integrations to use new fields
5. ✅ Deploy to production
6. ✅ Monitor for 24h
7. ✅ Update dashboards to use rich metrics
