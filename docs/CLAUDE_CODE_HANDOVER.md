# Claude Code Handover: Enhanced Database Schema Migration

**Date:** March 2, 2026  
**Status:** Ready for Implementation  
**Objective:** Upgrade database schema to support rich provider metrics beyond just cost tracking

---

## Executive Summary

### Current State
- ✅ Diagnostic logging implemented ([commit ba728f8](https://github.com/zebadee2kk/ai-cost-tracker/commit/ba728f8733c422fadb0d4c70a6a0edcc4a180e3e))
- ✅ Anthropic service using diagnostic logging
- ✅ Provider research completed (6 providers documented)
- ❌ Database schema limited to basic cost tracking
- ❌ No token breakdown (input/output/cache)
- ❌ No rate limit tracking
- ❌ No service tier/model metadata

### Goal State
- ✅ Rich metrics: tokens, cache hits, rate limits
- ✅ Per-model tracking
- ✅ Service tier breakdown (Anthropic)
- ✅ Rate limit consumption tracking (OpenAI, Groq)
- ✅ Request-level granularity
- ✅ Historical data preserved

---

## Research Completed

### Provider API Capabilities Documented

All provider research documents are in `/docs/` directory:

1. **anthropic-api-research.md** - Admin API, usage/cost endpoints
2. **openai-api-research.md** - Usage API, rate limit headers
3. **google-gemini-api-research.md** - Vertex AI, BigQuery exports
4. **perplexity-api-research.md** - Per-request logging, no usage API
5. **groq-api-research.md** - Rate limit headers, timing metrics
6. **provider-comparison-matrix.md** - Quick reference

### Key Findings Summary

| Provider | Tracking Method | Available Metrics |
|----------|----------------|------------------|
| **Anthropic** | Admin API | Tokens (in/out/cache), models, service tiers, workspaces |
| **OpenAI** | Usage API | Tokens (in/out), cost, rate limits via headers |
| **Google** | Cloud Logging | Tokens (in/out/cache), requests, latency |
| **Perplexity** | Per-request logging | Tokens (in/out), search queries, reasoning tokens |
| **Groq** | Header extraction | Tokens (in/out), rate limits, timing metrics |
| **Mistral** | Per-request logging | Tokens (in/out) |

---

## Enhanced Database Schema Design

### Current `usage_records` Table (Limited)

```python
class UsageRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"))
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"))
    timestamp = db.Column(db.DateTime(timezone=True))
    
    # Current fields (LIMITED):
    tokens_used = db.Column(db.Integer, default=0)  # Total only
    tokens_remaining = db.Column(db.Integer)  # Not populated
    cost = db.Column(db.Numeric(10, 4), default=0)
    cost_currency = db.Column(db.String(10), default="USD")
    sessions_active = db.Column(db.Integer)  # Not used
    api_calls = db.Column(db.Integer, default=1)
    request_type = db.Column(db.String(100))  # Not populated
    extra_data = db.Column("metadata", db.JSON)  # Unstructured
    source = db.Column(db.String(50), default='api')
```

**Problems:**
- No input/output token breakdown
- No cache token tracking
- No rate limit data
- No model information
- No service tier tracking
- Unstructured JSON metadata

### Enhanced `usage_records` Schema (NEW)

```python
class UsageRecord(db.Model):
    """Enhanced usage tracking with rich provider metrics."""
    
    __tablename__ = "usage_records"

    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    
    # Token tracking (NEW - detailed breakdown)
    input_tokens = db.Column(db.Integer, default=0, nullable=False)
    output_tokens = db.Column(db.Integer, default=0, nullable=False)
    total_tokens = db.Column(db.Integer, default=0, nullable=False)  # Computed: input + output
    
    # Cache tracking (NEW - Anthropic, Google)
    cache_creation_tokens = db.Column(db.Integer, default=0)  # Cache writes
    cache_read_tokens = db.Column(db.Integer, default=0)  # Cache hits (90% cheaper)
    
    # Cost tracking (ENHANCED)
    cost = db.Column(db.Numeric(10, 6), default=0, nullable=False)  # Increased precision
    cost_currency = db.Column(db.String(10), default="USD")
    cost_breakdown = db.Column(db.JSON)  # {"input_cost": 0.05, "output_cost": 0.15, "cache_cost": 0.01}
    
    # Model & configuration (NEW)
    model_name = db.Column(db.String(100), index=True)  # claude-opus-4-6, gpt-4o, etc.
    model_version = db.Column(db.String(50))  # Version/snapshot
    service_tier = db.Column(db.String(50))  # standard, batch, priority (Anthropic)
    
    # Request metadata (NEW)
    request_id = db.Column(db.String(100))  # Provider request ID
    api_calls = db.Column(db.Integer, default=1)
    request_type = db.Column(db.String(100))  # completion, embedding, audio
    
    # Rate limit tracking (NEW - OpenAI, Groq)
    rate_limit_rpm = db.Column(db.Integer)  # Requests per minute limit
    rate_limit_tpm = db.Column(db.Integer)  # Tokens per minute limit
    rate_limit_remaining_requests = db.Column(db.Integer)  # Requests remaining
    rate_limit_remaining_tokens = db.Column(db.Integer)  # Tokens remaining
    
    # Performance metrics (NEW - Groq)
    response_time_ms = db.Column(db.Float)  # Response time in milliseconds
    queue_time_ms = db.Column(db.Float)  # Time spent in queue
    
    # Provider-specific extras (NEW - structured)
    workspace_id = db.Column(db.String(100))  # Anthropic workspaces
    api_key_id = db.Column(db.String(100))  # Anthropic key tracking
    inference_geo = db.Column(db.String(50))  # us, global (Anthropic)
    search_queries = db.Column(db.Integer, default=0)  # Perplexity Deep Research
    reasoning_tokens = db.Column(db.Integer, default=0)  # Perplexity Reasoning
    citation_tokens = db.Column(db.Integer, default=0)  # Perplexity citations
    
    # Metadata (KEPT for flexibility)
    extra_data = db.Column("metadata", db.JSON, default=dict)
    source = db.Column(db.String(50), default='api')  # api, manual, webhook
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True))

    # Relationships
    account = db.relationship("Account", back_populates="usage_records")
    service = db.relationship("Service", back_populates="usage_records")

    def to_dict(self):
        """Enhanced serialization with all new fields."""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "service_id": self.service_id,
            "service_name": self.service.name if self.service else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            
            # Token metrics
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            
            # Cost
            "cost": float(self.cost) if self.cost else 0.0,
            "cost_currency": self.cost_currency,
            "cost_breakdown": self.cost_breakdown,
            
            # Model
            "model_name": self.model_name,
            "model_version": self.model_version,
            "service_tier": self.service_tier,
            
            # Request
            "request_id": self.request_id,
            "api_calls": self.api_calls,
            "request_type": self.request_type,
            
            # Rate limits
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_tpm": self.rate_limit_tpm,
            "rate_limit_remaining_requests": self.rate_limit_remaining_requests,
            "rate_limit_remaining_tokens": self.rate_limit_remaining_tokens,
            
            # Performance
            "response_time_ms": self.response_time_ms,
            "queue_time_ms": self.queue_time_ms,
            
            # Provider-specific
            "workspace_id": self.workspace_id,
            "api_key_id": self.api_key_id,
            "inference_geo": self.inference_geo,
            "search_queries": self.search_queries,
            "reasoning_tokens": self.reasoning_tokens,
            "citation_tokens": self.citation_tokens,
            
            # Meta
            "metadata": self.extra_data,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

---

## Migration Strategy

### Approach: Additive Migration (Zero Downtime)

**Philosophy:** Add new columns without dropping old ones, allowing gradual transition.

### Step 1: Create Migration Script

**File:** `backend/migrations/versions/YYYYMMDD_enhance_usage_records.py`

```python
"""Enhance usage_records with rich provider metrics.

Revision ID: enhance_usage_v2
Revises: [previous_revision]
Create Date: 2026-03-02 15:20:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add new columns to usage_records table."""
    
    # Token breakdown columns
    op.add_column('usage_records', sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('usage_records', sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('usage_records', sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'))
    
    # Cache tracking
    op.add_column('usage_records', sa.Column('cache_creation_tokens', sa.Integer(), server_default='0'))
    op.add_column('usage_records', sa.Column('cache_read_tokens', sa.Integer(), server_default='0'))
    
    # Cost breakdown
    op.add_column('usage_records', sa.Column('cost_breakdown', sa.JSON(), nullable=True))
    
    # Model & configuration
    op.add_column('usage_records', sa.Column('model_name', sa.String(100), nullable=True))
    op.add_column('usage_records', sa.Column('model_version', sa.String(50), nullable=True))
    op.add_column('usage_records', sa.Column('service_tier', sa.String(50), nullable=True))
    op.create_index('ix_usage_records_model_name', 'usage_records', ['model_name'])
    
    # Request metadata
    op.add_column('usage_records', sa.Column('request_id', sa.String(100), nullable=True))
    
    # Rate limit tracking
    op.add_column('usage_records', sa.Column('rate_limit_rpm', sa.Integer(), nullable=True))
    op.add_column('usage_records', sa.Column('rate_limit_tpm', sa.Integer(), nullable=True))
    op.add_column('usage_records', sa.Column('rate_limit_remaining_requests', sa.Integer(), nullable=True))
    op.add_column('usage_records', sa.Column('rate_limit_remaining_tokens', sa.Integer(), nullable=True))
    
    # Performance metrics
    op.add_column('usage_records', sa.Column('response_time_ms', sa.Float(), nullable=True))
    op.add_column('usage_records', sa.Column('queue_time_ms', sa.Float(), nullable=True))
    
    # Provider-specific
    op.add_column('usage_records', sa.Column('workspace_id', sa.String(100), nullable=True))
    op.add_column('usage_records', sa.Column('api_key_id', sa.String(100), nullable=True))
    op.add_column('usage_records', sa.Column('inference_geo', sa.String(50), nullable=True))
    op.add_column('usage_records', sa.Column('search_queries', sa.Integer(), server_default='0'))
    op.add_column('usage_records', sa.Column('reasoning_tokens', sa.Integer(), server_default='0'))
    op.add_column('usage_records', sa.Column('citation_tokens', sa.Integer(), server_default='0'))
    
    # Backfill existing data (optional)
    # Migrate tokens_used -> total_tokens for existing records
    op.execute("""
        UPDATE usage_records 
        SET total_tokens = tokens_used 
        WHERE total_tokens = 0 AND tokens_used > 0
    """)
    
    print("✅ Migration upgrade complete")

def downgrade():
    """Remove added columns (rollback)."""
    
    # Drop indexes first
    op.drop_index('ix_usage_records_model_name', table_name='usage_records')
    
    # Drop all new columns
    columns_to_drop = [
        'input_tokens', 'output_tokens', 'total_tokens',
        'cache_creation_tokens', 'cache_read_tokens',
        'cost_breakdown',
        'model_name', 'model_version', 'service_tier',
        'request_id',
        'rate_limit_rpm', 'rate_limit_tpm', 
        'rate_limit_remaining_requests', 'rate_limit_remaining_tokens',
        'response_time_ms', 'queue_time_ms',
        'workspace_id', 'api_key_id', 'inference_geo',
        'search_queries', 'reasoning_tokens', 'citation_tokens',
    ]
    
    for col in columns_to_drop:
        op.drop_column('usage_records', col)
    
    print("✅ Migration downgrade complete")
```

### Step 2: Update Models

**File:** `backend/models/usage_record.py`

Replace existing model with enhanced version above.

### Step 3: Update Service Implementations

Update each service to populate new fields:

**Anthropic Service:**
```python
# In _aggregate_daily_usage, update record creation:
UsageRecord(
    account_id=account_id,
    service_id=service_id,
    timestamp=datetime.fromisoformat(day_str),
    
    # NEW: Token breakdown
    input_tokens=agg['input_tokens'],
    output_tokens=agg['output_tokens'],
    total_tokens=agg['input_tokens'] + agg['output_tokens'],
    cache_creation_tokens=agg['cache_creation_tokens'],
    cache_read_tokens=agg['cache_read_tokens'],
    
    # NEW: Model info
    model_name=agg['models'][0] if len(agg['models']) == 1 else 'mixed',
    service_tier=agg.get('service_tier', 'standard'),
    
    # Cost
    cost=cost,
    cost_breakdown={
        'input_cost': input_cost,
        'output_cost': output_cost,
        'cache_cost': cache_cost,
    },
    
    # Provider-specific
    workspace_id=agg.get('workspace_id'),
    api_key_id=agg.get('api_key_id'),
    inference_geo=agg.get('inference_geo'),
    
    source='api',
)
```

**OpenAI Service:**
```python
# Extract rate limits from headers
UsageRecord(
    account_id=account_id,
    service_id=service_id,
    timestamp=datetime.now(timezone.utc),
    
    # Token breakdown
    input_tokens=usage.get('prompt_tokens', 0),
    output_tokens=usage.get('completion_tokens', 0),
    total_tokens=usage.get('total_tokens', 0),
    
    # Model
    model_name=response.get('model'),
    request_type='completion',
    
    # Rate limits from headers
    rate_limit_rpm=int(headers.get('x-ratelimit-limit-requests', 0)),
    rate_limit_tpm=int(headers.get('x-ratelimit-limit-tokens', 0)),
    rate_limit_remaining_requests=int(headers.get('x-ratelimit-remaining-requests', 0)),
    rate_limit_remaining_tokens=int(headers.get('x-ratelimit-remaining-tokens', 0)),
    
    cost=calculated_cost,
    source='api',
)
```

---

## Implementation Steps for Claude Code

### Pre-Implementation Checklist

- [ ] Review all provider research documents in `/docs/`
- [ ] Understand current `usage_records` model structure
- [ ] Review diagnostic logging implementation
- [ ] Backup production database
- [ ] Test migration on dev/staging first

### Step-by-Step Implementation

#### Step 1: Create Migration File

```bash
# Generate migration
cd backend
flask db revision -m "enhance_usage_records_with_rich_metrics"

# Edit generated file in migrations/versions/
# Copy migration script from above
```

#### Step 2: Update Model Definition

```bash
# Edit: backend/models/usage_record.py
# Replace with enhanced schema from above
```

#### Step 3: Run Migration (Dev First)

```bash
# Apply migration
flask db upgrade

# Verify columns added
psql $DATABASE_URL -c "\d usage_records"
```

#### Step 4: Update Service Implementations

**Priority Order:**
1. ✅ **Anthropic** (already has diagnostic logging)
2. **OpenAI** (simplest, good for testing)
3. **Groq** (rate limit headers)
4. **Perplexity** (per-request logging)
5. **Google** (most complex)
6. **Mistral** (basic tracking)

**For each service:**
1. Update `get_usage()` method to populate new fields
2. Add rate limit extraction (if applicable)
3. Add model/tier tracking
4. Test with real API calls

#### Step 5: Update Frontend (if needed)

```typescript
// Update UsageRecord interface in frontend/src/types/
interface UsageRecord {
  id: number;
  account_id: number;
  timestamp: string;
  
  // Token metrics
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cache_creation_tokens?: number;
  cache_read_tokens?: number;
  
  // Model
  model_name?: string;
  service_tier?: string;
  
  // Rate limits
  rate_limit_remaining_tokens?: number;
  rate_limit_tpm?: number;
  
  // Cost
  cost: number;
  cost_breakdown?: {
    input_cost: number;
    output_cost: number;
    cache_cost?: number;
  };
}
```

#### Step 6: Testing

**Unit Tests:**
```python
# tests/test_enhanced_usage_records.py
def test_anthropic_creates_enhanced_record():
    """Test Anthropic service populates new fields."""
    service = AnthropicService(api_key="sk-ant-admin-test")
    usage = service.get_usage(start_date="2026-03-01", end_date="2026-03-01")
    
    # Verify new fields populated
    record = UsageRecord.query.first()
    assert record.input_tokens > 0
    assert record.output_tokens > 0
    assert record.model_name is not None
    assert record.cache_read_tokens >= 0

def test_openai_rate_limits_tracked():
    """Test OpenAI service tracks rate limits."""
    service = OpenAIService(api_key="sk-test")
    # ... make API call ...
    
    record = UsageRecord.query.first()
    assert record.rate_limit_tpm is not None
    assert record.rate_limit_remaining_tokens is not None
```

**Integration Tests:**
```bash
# Test full sync cycle
FLASK_ENV=development python -m pytest tests/test_services.py -v

# Verify database state
psql $DATABASE_URL -c "SELECT input_tokens, output_tokens, model_name FROM usage_records LIMIT 5;"
```

#### Step 7: Production Deployment

```bash
# 1. Backup production DB
pg_dump $PRODUCTION_DB_URL > backup_pre_migration_$(date +%Y%m%d).sql

# 2. Run migration
FLASK_ENV=production flask db upgrade

# 3. Restart services
docker-compose restart backend

# 4. Monitor logs
docker-compose logs -f backend | grep -E "(ERROR|Sync)"

# 5. Verify data population
curl http://localhost:5000/api/usage?account_id=1 | jq '.data[0].input_tokens'
```

---

## Verification Checklist

### Post-Migration Verification

- [ ] All new columns exist in database schema
- [ ] Existing records preserved (no data loss)
- [ ] New syncs populate `input_tokens` and `output_tokens`
- [ ] Cache tokens tracked for Anthropic
- [ ] Rate limits captured for OpenAI/Groq
- [ ] Model names populated
- [ ] Cost breakdown JSON valid
- [ ] API responses include new fields
- [ ] Frontend displays new metrics (if implemented)
- [ ] No errors in application logs
- [ ] Performance acceptable (query times < 100ms)

### Data Quality Checks

```sql
-- Check token consistency
SELECT 
  COUNT(*) as records,
  SUM(CASE WHEN input_tokens > 0 OR output_tokens > 0 THEN 1 ELSE 0 END) as with_tokens,
  AVG(input_tokens) as avg_input,
  AVG(output_tokens) as avg_output
FROM usage_records
WHERE created_at > NOW() - INTERVAL '24 hours';

-- Check model name population
SELECT model_name, COUNT(*) 
FROM usage_records 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY model_name;

-- Check rate limit tracking
SELECT 
  service_id,
  AVG(rate_limit_tpm) as avg_tpm_limit,
  AVG(rate_limit_remaining_tokens) as avg_remaining
FROM usage_records
WHERE rate_limit_tpm IS NOT NULL
GROUP BY service_id;
```

---

## Rollback Procedure

### If Migration Fails

```bash
# 1. Rollback migration
flask db downgrade -1

# 2. Restore from backup if needed
psql $PRODUCTION_DB_URL < backup_pre_migration_YYYYMMDD.sql

# 3. Restart services with old code
git checkout HEAD~1
docker-compose restart
```

### If Data Issues Found

```sql
-- Reset new columns to defaults
UPDATE usage_records SET
  input_tokens = 0,
  output_tokens = 0,
  total_tokens = tokens_used,
  model_name = NULL,
  rate_limit_tpm = NULL
WHERE created_at > 'YYYY-MM-DD HH:MM:SS';
```

---

## Performance Considerations

### Indexing Strategy

```sql
-- Create composite indexes for common queries
CREATE INDEX idx_usage_timestamp_account ON usage_records(timestamp DESC, account_id);
CREATE INDEX idx_usage_model_timestamp ON usage_records(model_name, timestamp DESC);
CREATE INDEX idx_usage_service_timestamp ON usage_records(service_id, timestamp DESC);
```

### Query Optimization

```python
# Use select_related to avoid N+1 queries
usage_records = (
    UsageRecord.query
    .filter(UsageRecord.account_id == account_id)
    .filter(UsageRecord.timestamp >= start_date)
    .order_by(UsageRecord.timestamp.desc())
    .options(db.joinedload(UsageRecord.service))
    .limit(100)
    .all()
)
```

---

## Next Steps After Migration

1. **Dashboard Updates:**
   - Add token usage charts (input vs output)
   - Show cache hit rates
   - Display rate limit consumption
   - Model-level cost breakdowns

2. **Alerts & Monitoring:**
   - Alert when rate limits > 80%
   - Notify on unusual token spikes
   - Track cache effectiveness

3. **Cost Optimization:**
   - Identify high-cost models
   - Recommend batch API for eligible requests
   - Suggest cache usage for repetitive prompts

4. **Additional Providers:**
   - Implement remaining providers (Groq, Perplexity, Mistral)
   - Add new providers as needed

---

## Support & References

### Documentation
- Provider research: `/docs/*-api-research.md`
- Diagnostic logging: `backend/utils/diagnostic_logger.py`
- Current model: `backend/models/usage_record.py`

### Debugging

```bash
# Enable DEBUG logging
export LOG_LEVEL=DEBUG
export FLASK_ENV=development

# Watch logs
tail -f logs/app.log | grep -E "(Sync|API call|Provider)"

# Check recent syncs
psql $DATABASE_URL -c "SELECT provider, success, records_created, elapsed_seconds FROM sync_log ORDER BY timestamp DESC LIMIT 10;"
```

### Contact
For questions or issues during implementation, check:
- Diagnostic logs in `logs/app.log`
- Provider research documents
- Existing Anthropic service implementation (reference)

---

**Ready to implement!** 🚀

This handover provides everything needed to:
1. ✅ Understand the enhanced schema
2. ✅ Create and run migrations safely
3. ✅ Update service implementations
4. ✅ Test thoroughly
5. ✅ Deploy to production
6. ✅ Verify and monitor

Good luck with the implementation!
