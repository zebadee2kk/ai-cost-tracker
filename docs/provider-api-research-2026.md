# Provider API Research - February 2026

## Executive Summary

Research conducted on February 25, 2026 to assess current API capabilities for Anthropic Claude, Groq, and Perplexity billing/usage tracking.

**Key Findings**:
- ✅ **Anthropic Claude**: Full Usage & Cost API available (launched Aug 2025)
- ⚠️ **Groq**: No official billing API - dashboard only (feature requested by community)
- ⚠️ **Perplexity**: No official usage API - manual tracking required (feature requested)

---

## 1. Anthropic Claude API

### Status: ✅ FULLY SUPPORTED

### Official Usage & Cost API
Anthropic launched a comprehensive Usage and Cost API in August 2025, providing near-instantaneous insights into Claude usage.

### API Endpoints

#### Usage Endpoint
```bash
curl "https://api.anthropic.com/v1/organizations/usage?\  
starting_at=2026-02-01T00:00:00Z&\
ending_at=2026-02-28T23:59:59Z" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

#### Cost Report Endpoint
```bash
curl "https://api.anthropic.com/v1/organizations/cost_report?\  
starting_at=2026-02-01T00:00:00Z&\
ending_at=2026-02-28T23:59:59Z&\
group_by[]=workspace_id&\
group_by[]=description" \
  --header "anthropic-version: 2023-06-01" \
  --header "x-api-key: $ADMIN_API_KEY"
```

### Capabilities
- **Real-time usage tracking** (~instantaneous updates)
- **Token consumption metrics** by model and request
- **Cost reporting** with grouping by workspace/description
- **Date range queries** with flexible time windows
- **Priority Tier tracking** (separate billing model)

### Important Notes
- Requires **Admin API Key** (different from regular API key)
- Priority Tier costs use different billing model and must be tracked via usage endpoint
- Supports grouping by workspace_id and description for multi-team tracking

### Pricing (Feb 2026)
- **Claude Opus 4.5**: $5 input / $25 output per million tokens
- **Claude Sonnet 4.5**: $3 input / $15 output per million tokens
- **Claude Haiku 4.5**: $1 input / $5 output per million tokens
- Batch API discounts available
- Prompt caching reduces costs for repeated contexts

### Documentation
- Official Docs: https://platform.claude.com/docs/en/build-with-claude/usage-cost-api
- API Version: 2023-06-01 (current as of Feb 2026)

---

## 2. Groq API

### Status: ⚠️ NO OFFICIAL API (Dashboard Only)

### Current Limitations
- **No programmatic access** to billing/usage data
- Usage data only available through **Groq Console UI**
- Manual checks required under Dashboard → Usage → Cost
- ~15 minute delay in usage reporting

### Community Feature Requests
Multiple community requests filed (Aug 2025, Jan 2026) requesting:
- REST endpoint returning JSON with monthly/daily spend
- Per-model usage breakdown
- Date range support
- Real-time spend tracking
- Alert threshold capabilities

**Status**: Feature requests acknowledged but not yet implemented as of Feb 2026

### Current Billing Model
- **Free tier**: 30 requests per minute limit
- **Enterprise plans**: Available with custom pricing
- **Individual paid plans**: Not yet enabled (as of Feb 2026)
- Rate limiting: Requests bounce when exceeding RPM limits

### Workaround Options

#### Option 1: Per-Request Tracking (Recommended)
```python
# Track usage client-side from API responses
response = groq_client.chat.completions.create(...)
usage = {
    'prompt_tokens': response.usage.prompt_tokens,
    'completion_tokens': response.usage.completion_tokens,
    'total_tokens': response.usage.total_tokens,
    'model': response.model
}
# Store in local database immediately
```

#### Option 2: UI Scraping (Not Recommended)
- Scrape Groq Console UI (brittle, against ToS)
- Unreliable for automation
- No API stability guarantees

#### Option 3: Manual Entry
- Periodic manual input from dashboard
- Lower accuracy, higher maintenance

### Recommendation for Implementation
**Use per-request tracking pattern** until official API available:
1. Capture usage data from every API response
2. Store immediately in local database
3. Calculate costs based on published pricing
4. Implement reconciliation check against UI periodically

---

## 3. Perplexity API

### Status: ⚠️ NO OFFICIAL API (Dashboard Only)

### Current Limitations
- **No programmatic usage endpoint** available
- Usage statistics only viewable through **dashboard interface**
- Billing tracked via invoice history in Settings → Usage Metrics
- API key-specific tracking available in invoice details (last 4 chars identifier)

### Community Feature Requests
- GitHub issue #266 filed April 2025 requesting usage/cost tracking endpoint
- Request for alignment with OpenAI's usage API pattern
- Enterprise customers specifically requesting cost allocation features

**Status**: Feature acknowledged but not implemented as of Feb 2026

### Billing Structure
- **Credit-based system**: Credits purchased in advance
- **Pay-as-you-go**: Usage charged based on tokens + search queries
- **Auto top-up**: Optional to avoid service interruptions
- **Enterprise pricing**: ~$40/month per seat or custom volume agreements

### Available Tracking Methods

#### Invoice History (Manual)
1. Navigate to API Settings → Usage Metrics
2. Select Invoice history → Invoices
3. Click invoice to view details
4. Identify API key charges by 4-char code suffix

#### Limitations
- Manual process only
- Historical data only (not real-time)
- No programmatic access
- No per-request granularity

### Workaround Options

#### Option 1: Per-Request Tracking (Recommended)
```python
# Track from API responses
response = perplexity_client.chat.completions.create(...)
usage = {
    'prompt_tokens': response.usage.prompt_tokens,
    'completion_tokens': response.usage.completion_tokens,
    'total_tokens': response.usage.total_tokens,
    'model': response.model
}
# Store locally with timestamp
```

#### Option 2: Email Notifications
- Enable billing threshold alerts
- Parse notification emails (unreliable)

#### Option 3: Manual Logging
- Maintain separate request log
- Approximate usage tracking

### Recommendation for Implementation
**Implement hybrid approach**:
1. Per-request client-side tracking for real-time data
2. Periodic manual reconciliation against invoice history
3. Display confidence level ("estimated" vs "reconciled")
4. Alert users to check dashboard for official totals

---

## 4. Recommended Implementation Strategy

### Phase 2A: Anthropic Claude (Priority 1)
- ✅ Full API support available
- Implement complete integration with Usage & Cost API
- Use as reference implementation for other providers
- Test admin API key handling separately from user API keys

### Phase 2B: Groq + Perplexity (Priority 2)
- ⚠️ Use per-request tracking pattern
- Store usage from API response objects immediately
- Calculate costs based on published pricing tables
- Add "Estimated" badge in UI for these providers
- Implement manual reconciliation workflow
- Monitor for official API releases

### Phase 2C: GitHub Copilot (Priority 3)
- No usage API available
- Manual entry only
- Simple form: date, estimated tokens, cost
- Mark as "Manual Entry" in UI

---

## 5. Normalized Schema Design

### Common Fields Across All Providers
```python
class UsageRecord:
    account_id: int
    service_id: int
    timestamp: datetime
    date: date  # For daily aggregation
    
    # Core metrics
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    # Cost tracking
    total_cost: Decimal
    currency: str = "USD"
    
    # Metadata
    model: str
    request_type: str  # 'api', 'manual', 'reconciled'
    confidence: str  # 'official', 'estimated', 'manual'
    
    # Provider-specific JSON
    metadata: dict  # Store provider-specific fields
```

### Provider-Specific Metadata Examples

#### Anthropic Claude
```json
{
  "workspace_id": "ws_xxx",
  "description": "production-api",
  "priority_tier": false,
  "cache_creation_tokens": 1200,
  "cache_read_tokens": 5000
}
```

#### Groq
```json
{
  "queue_time": 0.002,
  "prompt_time": 0.015,
  "completion_time": 0.125,
  "total_time": 0.142
}
```

#### Perplexity
```json
{
  "search_queries": 3,
  "citations_count": 12,
  "api_key_suffix": "743S"
}
```

---

## 6. Error Handling Taxonomy

### Authentication Errors
- Invalid API key
- Expired credentials
- Insufficient permissions (e.g., admin API key required)

### Rate Limit Errors
- RPM limit exceeded
- Daily quota exceeded
- Concurrent request limit

### Billing Errors
- Insufficient credits (Perplexity)
- Prepaid balance depleted (Claude)
- Payment method failure

### Transient API Failures
- Timeout errors
- 5xx server errors
- Network connectivity issues

### Recommended Retry Strategy
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Timeout, ConnectionError))
)
def fetch_usage_with_retry(account):
    return service_client.get_usage(account.api_key)
```

---

## 7. Testing Strategy

### Unit Tests
- Mock API responses for each provider
- Test response parsing and normalization
- Test error handling for each error type
- Test cost calculation accuracy

### Integration Tests
- Test with real API keys (sandbox/test accounts)
- Verify idempotent behavior on repeated fetches
- Test date range queries
- Test rate limit handling

### Fixtures
```python
# Mock Anthropic response
ANTHROPIC_USAGE_RESPONSE = {
    "data": [
        {
            "date": "2026-02-25",
            "input_tokens": 15000,
            "output_tokens": 5000,
            "model": "claude-sonnet-4.5",
            "workspace_id": "ws_test"
        }
    ]
}

# Mock Groq response (from completion)
GROQ_COMPLETION_RESPONSE = {
    "usage": {
        "prompt_tokens": 120,
        "completion_tokens": 450,
        "total_tokens": 570
    },
    "model": "llama-3.1-70b"
}
```

---

## 8. Implementation Checklist

### Anthropic Claude
- [ ] Create `AnthropicService` class
- [ ] Implement admin API key configuration (separate from user key)
- [ ] Implement `get_usage(start_date, end_date)` method
- [ ] Implement `get_cost_report(start_date, end_date)` method
- [ ] Handle Priority Tier separately
- [ ] Parse and normalize response to common schema
- [ ] Add error handling for auth/rate limits
- [ ] Write unit tests with mocked responses
- [ ] Write integration test with real API
- [ ] Update scheduler to call Claude sync

### Groq
- [ ] Create `GroqService` class
- [ ] Implement per-request tracking pattern
- [ ] Store usage from completion responses
- [ ] Calculate costs based on pricing table
- [ ] Add "Estimated" confidence flag
- [ ] Implement reconciliation workflow UI
- [ ] Write unit tests
- [ ] Document workaround approach
- [ ] Monitor for official API release

### Perplexity
- [ ] Create `PerplexityService` class
- [ ] Implement per-request tracking pattern
- [ ] Handle credit-based billing model
- [ ] Track search queries separately
- [ ] Add "Estimated" confidence flag
- [ ] Implement manual reconciliation UI
- [ ] Write unit tests
- [ ] Document invoice history check process

### Cross-Provider
- [ ] Define normalized `UsageData` schema
- [ ] Implement confidence scoring system
- [ ] Add provider-specific metadata support
- [ ] Create base class for per-request tracking
- [ ] Update UI to show confidence levels
- [ ] Add reconciliation workflow
- [ ] Update documentation

---

## 9. References

### Official Documentation
- Anthropic Usage & Cost API: https://platform.claude.com/docs/en/build-with-claude/usage-cost-api
- Groq Community: https://community.groq.com/
- Perplexity API Portal: https://perplexity.mintlify.app/

### Community Feature Requests
- Groq Usage API Request: https://community.groq.com/t/endpoint-for-usage-cost-data/940
- Perplexity Usage API Request: https://github.com/ppl-ai/api-discussion/issues/266

### Pricing Resources
- Anthropic Pricing 2026: https://platform.claude.com/docs/en/about-claude/pricing
- MetaCTO Claude Cost Breakdown: https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration

---

**Last Updated**: February 25, 2026
**Next Review**: Check for Groq/Perplexity API updates in Q2 2026
