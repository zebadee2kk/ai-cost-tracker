# API Capabilities Research - February 2026

**Research Date**: February 25, 2026  
**Purpose**: Phase 2 multi-service integration planning  
**Researched By**: Perplexity AI

---

## Executive Summary

### API Availability Status

| Provider | Usage API | Cost API | Historical Data | Status |
|----------|-----------|----------|-----------------|--------|
| **Anthropic Claude** | ✅ Available | ✅ Available | ✅ Yes (5min delay) | **Production Ready** |
| **Groq** | ⚠️ Dashboard Only | ⚠️ Dashboard Only | ❌ No API | **Manual Tracking Required** |
| **Perplexity** | ⚠️ Dashboard Only | ⚠️ Dashboard Only | ❌ No API | **Manual Tracking Required** |
| **OpenAI** | ✅ Available | ✅ Available | ✅ Yes | **Already Implemented** |

### Key Findings

1. **Anthropic Claude**: Full-featured Usage & Cost Admin API available (as of August 2025)
2. **Groq**: No programmatic API - dashboard viewing only, community requesting feature
3. **Perplexity**: No programmatic API - invoice history tracking only via dashboard
4. **Implementation Strategy**: Hybrid approach needed (API + manual entry)

---

## 1. Anthropic Claude API (✅ Production Ready)

### API Capabilities

**Official Documentation**: [Usage and Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api)

**Launch Date**: August 2025[web:31]

**Key Features**:
- ✅ Near real-time usage data (5-minute delay typical)[page:61]
- ✅ Separate usage and cost endpoints
- ✅ Organization-level Admin API (requires `sk-ant-admin...` key)[page:61]
- ✅ Token consumption tracking with model breakdown
- ✅ Cost tracking in USD with granular grouping
- ✅ Historical data support with flexible date ranges
- ✅ Pagination for large datasets

### Authentication

- **Requirement**: Admin API key (different from standard API keys)
- **Key Format**: `sk-ant-admin...`
- **Access**: Only organization admins can provision Admin API keys
- **Note**: Individual accounts cannot use Admin API[page:61]

### API Endpoints

#### Usage Endpoint
```
GET https://api.anthropic.com/v1/organizations/usage_report/messages
```

**Parameters**:
- `starting_at` (required): ISO 8601 timestamp (e.g., `2025-01-01T00:00:00Z`)
- `ending_at` (required): ISO 8601 timestamp
- `bucket_width` (required): Granularity - `1m`, `1h`, or `1d`
- `group_by[]` (optional): Array - `model`, `workspace_id`, `api_key_id`, `service_tier`, `context_window`, `inference_geo`, `speed`
- `models[]` (optional): Filter by specific models
- `service_tiers[]` (optional): `batch`, `priority`
- `context_window[]` (optional): e.g., `0-200k`
- `api_key_ids[]` (optional): Filter by API keys
- `workspace_ids[]` (optional): Filter by workspaces
- `inference_geos[]` (optional): `global`, `us`, `not_available`
- `speeds[]` (optional): `standard`, `fast` (requires beta header)
- `page` (optional): For pagination
- `limit` (optional): Results per page (default 7 for daily, varies by granularity)

**Response Structure**:
```json
{
  "data": [
    {
      "start_time": "2025-01-01T00:00:00Z",
      "end_time": "2025-01-02T00:00:00Z",
      "input_tokens": 150000,
      "output_tokens": 50000,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0,
      "model": "claude-opus-4-6",
      "service_tier": "standard",
      "context_window": "0-200k",
      "inference_geo": "us",
      "speed": "standard"
    }
  ],
  "has_more": false,
  "next_page": null
}
```

#### Cost Endpoint
```
GET https://api.anthropic.com/v1/organizations/cost_report
```

**Parameters**:
- `starting_at` (required): ISO 8601 timestamp
- `ending_at` (required): ISO 8601 timestamp
- `group_by[]` (optional): `workspace_id`, `description`
- `bucket_width` (optional): `1d` (daily)
- `page`, `limit` (optional): For pagination

**Response Structure**:
```json
{
  "data": [
    {
      "start_time": "2025-01-01T00:00:00Z",
      "end_time": "2025-01-02T00:00:00Z",
      "cost_usd": "12.50",
      "description": "claude-opus-4-6 - Standard Tier - Input Tokens",
      "model": "claude-opus-4-6",
      "inference_geo": "us",
      "workspace_id": "wrkspc_01ABC..."
    }
  ],
  "has_more": false,
  "next_page": null
}
```

### Pricing (February 2026)

**Current Models**[web:28][web:37]:

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Notes |
|-------|----------------------|------------------------|-------|
| **Claude Opus 4.5** | $5.00 | $25.00 | Heavy-duty agentic workflows |
| **Claude Sonnet 4.5** | $3.00 | $15.00 | Balanced performance |
| **Claude Haiku 4.5** | $1.00 | $5.00 | Fast, cost-effective |

**Additional Costs**:
- Prompt caching (reduces repeat input costs)
- Code execution (appears in cost endpoint as "Code Execution Usage")
- Priority Tier (different billing model, tracked via usage endpoint only)[page:61]

### Rate Limits & Data Freshness

- **Update Frequency**: Data available within ~5 minutes of API request completion[page:61]
- **Polling Limit**: Once per minute for sustained use[page:61]
- **Burst Polling**: More frequent polling acceptable for short bursts (e.g., pagination)

### Granularity Limits[page:61]

| Granularity | Default Limit | Maximum Limit | Use Case |
|-------------|---------------|---------------|---------|
| `1m` | 60 buckets | 1440 buckets | Real-time monitoring |
| `1h` | 24 buckets | 168 buckets | Daily patterns |
| `1d` | 7 buckets | 31 buckets | Weekly/monthly reports |

### Implementation Recommendations

1. **Admin Key Setup**: User must provide Admin API key (not standard API key)
2. **Organization Required**: Cannot use with individual accounts
3. **Endpoint Selection**: Use usage endpoint for token tracking, cost endpoint for USD amounts
4. **Polling Strategy**: Fetch daily summaries once per day, avoid excessive polling
5. **Pagination**: Implement cursor-based pagination for large datasets
6. **Error Handling**: Handle `null` values for `workspace_id` (default workspace) and `api_key_id` (Workbench usage)[page:61]

---

## 2. Groq API (⚠️ Manual Tracking Required)

### Current Status

**Official Documentation**: [Billing FAQs](https://console.groq.com/docs/billing-faqs)

**API Availability**: ❌ **No programmatic billing/usage API available**[web:32]

### Dashboard-Only Tracking

**Available Via Console**:
- Navigate to **Dashboard → Usage**[page:60][web:35]
- View near real-time usage (~15 min delay)
- Monitor daily/monthly spend
- Track per-model usage
- Set spend limits and alerts

**Features**:
- ✅ Usage visualization (dashboard)
- ✅ Spend limits with alerts
- ✅ Invoice history
- ❌ No REST endpoint for usage data
- ❌ No programmatic access to billing

### Community Requests

**Feature Request Status** (as of August 2024)[web:32]:
- Community actively requesting billing/usage API endpoint
- Requested features:
  - REST endpoint with JSON response
  - Monthly spend, daily spend, per-model usage
  - Date range support
  - ~15 min update frequency
- **Status**: No official response or timeline from Groq

### Billing Model[page:60]

**Progressive Billing Thresholds**:
- New Developer plan users billed at: $1, $10, $100, $500, $1,000
- After $1,000 lifetime usage: Monthly billing only
- **Special for India**: $1, $10, then recurring $100 thresholds

**Payment Methods**:
- Credit cards (Visa, MasterCard, Amex, Discover)
- US bank accounts
- SEPA debit accounts

**Free Tier**:
- 30 requests per minute
- No billing until upgrade to Developer tier

### Implementation Recommendations

**Option 1: Manual Entry Workflow**
1. User manually checks Groq Console dashboard
2. User enters daily/monthly totals into AI Cost Tracker
3. System stores as manual entry with confidence flag

**Option 2: Scraping (Not Recommended)**
- Violates terms of service
- Fragile (breaks with UI changes)
- Authentication complexity

**Option 3: Wait for API**
- Monitor Groq community for API announcement
- Implement when available

**Recommended Approach**: Implement manual entry workflow with clear UI indicating "Manual Entry Required - No API Available"

---

## 3. Perplexity API (⚠️ Manual Tracking Required)

### Current Status

**Official Documentation**: [API Groups & Billing](https://docs.perplexity.ai/docs/getting-started/api-groups)

**API Availability**: ❌ **No programmatic billing/usage API available**[web:33]

### Dashboard-Only Tracking

**Available Via Portal**[web:36][web:39]:
- Navigate to **Settings → Usage Metrics**
- View total API call trends over time
- Breakdown by API model and key
- Optional date range filters
- Invoice history with per-key tracking

**Per-Key Tracking Method**[web:36][web:39]:
1. Navigate to **Settings → Usage Metrics**
2. Select **Invoice history → Invoices**
3. Click on invoice to view details
4. Each line item shows last 4 characters of API key (e.g., `pro (743S)`)

### Community Requests

**Feature Request Status** (as of April 2025)[web:33]:
- GitHub issue #266 requesting comprehensive usage/cost tracking endpoint
- Requested features:
  - Programmatic access to usage statistics
  - Billing information API
  - Budget management and alerts
  - Team/project cost allocation
- **Status**: No official response or timeline

### Challenges

- No real-time usage visibility
- Must rely on invoice history (post-facto)
- Cannot set programmatic alerts
- No breakdown of costs by request type
- Manual intervention required for monitoring

### Implementation Recommendations

**Recommended Approach**: Manual entry workflow

1. **UI Design**: 
   - "Add Manual Usage" button
   - Fields: Date, model, request count, total cost
   - Source indicator: "Manual Entry - Invoice Data"
   - Confidence level: "User Entered"

2. **Data Model**:
   - Flag manual entries vs. API-fetched data
   - Store entry source and timestamp
   - Allow editing/correction of manual entries

3. **User Guidance**:
   - Instructions on finding Perplexity invoice data
   - Link to Perplexity Settings → Usage Metrics
   - Screenshot/tutorial for locating API key charges

**Alternative**: Periodic email reminders to update manual entries

---

## 4. OpenAI API (✅ Already Implemented)

### Current Status

**Implementation**: Already complete in MVP (Codex implementation)

**API Notes**:
- Usage endpoint available
- Standard API endpoints working
- **Deprecation Alert**: `gpt-4o` (chatgpt-4o-latest) deprecated February 17, 2026[web:42][web:46]
- Migration to GPT-5.1 series recommended[web:46]
- Assistants API deprecated August 26, 2026 (migrate to Responses API)[web:45][web:55]

**No Changes Required**: Existing implementation sufficient for Phase 2

---

## 5. Idempotent Data Ingestion Patterns

### Problem Statement

Scheduler runs can create duplicate usage records if not properly guarded. Need idempotent upsert strategy for daily usage sync.

### Solution Options

#### Option 1: Database Unique Constraint + ON CONFLICT (Recommended)

**PostgreSQL Native Approach**[web:47]:

```sql
-- Add unique constraint
ALTER TABLE usage_records 
ADD CONSTRAINT unique_daily_usage 
UNIQUE (account_id, service_id, timestamp, request_type);

-- Upsert query
INSERT INTO usage_records 
  (account_id, service_id, timestamp, tokens, cost, request_type)
VALUES 
  (?, ?, ?, ?, ?, ?)
ON CONFLICT (account_id, service_id, timestamp, request_type)
DO UPDATE SET
  tokens = EXCLUDED.tokens,
  cost = EXCLUDED.cost,
  updated_at = NOW();
```

**SQLAlchemy Implementation**:

```python
from sqlalchemy.dialects.postgresql import insert

stmt = insert(UsageRecord).values(
    account_id=account_id,
    service_id=service_id,
    timestamp=date,
    tokens=tokens,
    cost=cost,
    request_type='api'
)

stmt = stmt.on_conflict_do_update(
    index_elements=['account_id', 'service_id', 'timestamp', 'request_type'],
    set_={
        'tokens': stmt.excluded.tokens,
        'cost': stmt.excluded.cost,
        'updated_at': func.now()
    }
)

db.session.execute(stmt)
db.session.commit()
```

#### Option 2: Pre-Insert Existence Check

**SQLAlchemy ORM Approach**:

```python
existing = UsageRecord.query.filter_by(
    account_id=account_id,
    service_id=service_id,
    timestamp=date,
    request_type='api'
).first()

if existing:
    # Update existing record
    existing.tokens = tokens
    existing.cost = cost
    existing.updated_at = datetime.utcnow()
else:
    # Create new record
    record = UsageRecord(
        account_id=account_id,
        service_id=service_id,
        timestamp=date,
        tokens=tokens,
        cost=cost,
        request_type='api'
    )
    db.session.add(record)

db.session.commit()
```

**Pros**: Simple, ORM-native  
**Cons**: Race condition potential, two DB queries

#### Option 3: Bulk Upsert with Row Comparison[web:47]

**PostgreSQL WHERE Comparison**:

```sql
INSERT INTO usage_records (account_id, service_id, timestamp, tokens, cost)
SELECT account_id, service_id, timestamp, tokens, cost
FROM (VALUES (1, 1, '2025-01-01', 1000, 0.50)) AS data(account_id, service_id, timestamp, tokens, cost)
WHERE NOT EXISTS (
    SELECT 1 FROM usage_records 
    WHERE data = usage_records
);
```

This compares entire rows and only inserts if no exact match exists.

### Recommended Approach

**Use Option 1 (Unique Constraint + ON CONFLICT)**:

1. **Add migration** for unique constraint
2. **Update scheduler** to use `on_conflict_do_update`
3. **Add logging** to track updates vs. inserts
4. **Test thoroughly** with repeated sync runs

**Benefits**:
- ✅ Database-enforced uniqueness
- ✅ Atomic operation (no race conditions)
- ✅ Handles both insert and update in single query
- ✅ PostgreSQL native, efficient

---

## 6. APScheduler Duplicate Prevention

### Problem: Flask Debug Mode Runs Jobs Twice

**Cause**: Flask's reloader creates two processes[web:48][web:51]

### Solutions

#### Solution 1: Disable Reloader in Development

```python
app.run(use_reloader=False)
```

**Pros**: Simple  
**Cons**: Manual app reload during development

#### Solution 2: Environment Check (Recommended)

```python
import os

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=sync_usage, trigger="interval", hours=24)
    scheduler.start()
```

**Explanation**: Only start scheduler in child process, not master[web:48]

#### Solution 3: Before First Request Hook

```python
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

@app.before_first_request
def init_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=sync_usage, trigger="interval", hours=24)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
```

**Pros**: Runs only once per Flask instance[web:51]  
**Cons**: Deprecated in Flask 2.3+ (use `app.before_request` with flag)

### Recommended Approach

**Use Solution 2** with production configuration:

```python
# In app.py or scheduler init
import os
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

def init_scheduler(app):
    # Only run in production OR in the child process of debug mode
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=sync_all_accounts,
            trigger="cron",
            hour=2,  # Run at 2 AM daily
            id='sync_usage',
            replace_existing=True
        )
        scheduler.start()
        
        # Graceful shutdown
        atexit.register(lambda: scheduler.shutdown(wait=False))
        
        app.logger.info("Scheduler initialized")
```

---

## 7. Normalized Service Integration Schema

### Base Service Contract

All service integrations must implement:

```python
class BaseService:
    def get_usage(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Fetch usage data for date range.
        
        Returns:
            {
                'total_tokens': int,
                'total_cost': Decimal,
                'daily': [
                    {
                        'date': 'YYYY-MM-DD',
                        'tokens': int,
                        'cost': Decimal,
                        'metadata': {
                            'model': str (optional),
                            'request_count': int (optional),
                            'input_tokens': int (optional),
                            'output_tokens': int (optional)
                        }
                    }
                ]
            }
        """
        raise NotImplementedError
    
    def validate_credentials(self, api_key: str) -> bool:
        """Test if API key is valid."""
        raise NotImplementedError
```

### Implementation Matrix

| Service | Method | Data Granularity | Special Handling |
|---------|--------|------------------|------------------|
| **OpenAI** | `get_usage()` | Daily | ✅ Existing implementation |
| **Anthropic** | `get_usage()` | Hourly/Daily | Requires Admin API key, parse token types |
| **Groq** | N/A | Manual | Return placeholder, flag as manual entry required |
| **Perplexity** | N/A | Manual | Return placeholder, flag as manual entry required |

### Error Taxonomy

```python
class ServiceError(Exception):
    """Base exception for service errors."""
    pass

class AuthenticationError(ServiceError):
    """Invalid or expired API key."""
    pass

class RateLimitError(ServiceError):
    """Rate limit exceeded."""
    pass

class ServiceUnavailableError(ServiceError):
    """Service temporarily unavailable."""
    pass

class NoDataAvailableError(ServiceError):
    """No usage data for requested period."""
    pass
```

---

## 8. Implementation Roadmap

### Phase 2.1: Anthropic Integration (Week 1-2)

**Prerequisites**:
- ✅ Research complete
- ⏳ User provides Admin API key

**Tasks**:
1. Create `AnthropicService` class
2. Implement usage endpoint client
3. Implement cost endpoint client (optional, can derive from usage)
4. Parse response and normalize to standard format
5. Handle Admin API key storage (separate from standard key)
6. Unit tests with mocked responses
7. Integration test with real API (using test account)

**Deliverables**:
- Functional Anthropic sync
- Test coverage >80%
- Documentation

### Phase 2.2: Manual Entry System (Week 2-3)

**For**: Groq, Perplexity, GitHub Copilot, local LLMs

**Tasks**:
1. Database schema for manual entries (add `source` field)
2. Backend endpoint: `POST /api/usage/manual`
3. Frontend: "Add Manual Entry" modal
4. Validation and error handling
5. Edit/delete manual entries
6. Dashboard indicator for manual vs. API data

**UI Requirements**:
- Clear labeling: "Manual Entry Required"
- Help text with instructions
- Link to provider dashboard
- Date picker, model selector, token/cost inputs

### Phase 2.3: Idempotency & Data Integrity (Week 3-4)

**Tasks**:
1. Add unique constraint migration
2. Update scheduler to use ON CONFLICT
3. Add scheduler duplicate prevention
4. Comprehensive logging
5. Integration tests for idempotency
6. Dry-run mode for testing

**Testing**:
- Run scheduler multiple times, verify no duplicates
- Simulate partial failures
- Verify atomic transactions

---

## 9. References

### Official Documentation

- [Anthropic Usage & Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api)
- [Groq Billing FAQs](https://console.groq.com/docs/billing-faqs)
- [Perplexity API Groups & Billing](https://docs.perplexity.ai/docs/getting-started/api-groups)
- [OpenAI API Deprecations](https://platform.openai.com/docs/deprecations)

### Community Discussions

- [Groq: Feature Request - Billing API](https://community.groq.com/t/add-api-endpoint-to-fetch-billing-and-usage-data/378)
- [Perplexity: Feature Request - Usage Tracking](https://github.com/ppl-ai/api-discussion/issues/266)
- [Reddit: Claude Usage API Launch](https://www.reddit.com/r/Anthropic/comments/1mtsc6q/usage_and_cost_api_now_available/)

### Technical Resources

- [PostgreSQL ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)
- [SQLAlchemy ON CONFLICT](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Flask-APScheduler Duplicate Issue](https://github.com/viniciuschiele/flask-apscheduler/issues/28)

---

## 10. Action Items for Next Engineer

### Immediate (This Week)

- [ ] Review this research document
- [ ] Test Anthropic Admin API with your organization
- [ ] Create Anthropic Admin API key
- [ ] Implement unique constraint migration
- [ ] Fix scheduler duplicate run issue

### Short Term (Next 2 Weeks)

- [ ] Implement `AnthropicService` class
- [ ] Add Anthropic to service dispatch
- [ ] Create manual entry UI and backend
- [ ] Update documentation

### Medium Term (Next Month)

- [ ] Add CSV/JSON export
- [ ] Implement alert system enhancements
- [ ] Add usage anomaly detection
- [ ] Production deployment preparation

---

**Document Version**: 1.0  
**Last Updated**: February 25, 2026  
**Next Review**: After Groq/Perplexity API announcements
