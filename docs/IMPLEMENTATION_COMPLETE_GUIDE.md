# Complete Implementation Guide: Multi-Provider AI Cost Tracking

**Target Audience:** Claude Code, GitHub Copilot, VS Code Copilot, human developers  
**Date:** March 2, 2026  
**Status:** Ready for implementation

---

## Executive Summary

This guide provides step-by-step instructions to implement comprehensive usage tracking for 6 AI providers:

1. **OpenAI** - Start here (easiest)
2. **Anthropic** - Admin key required
3. **Groq** - Fast, simple
4. **Perplexity** - No usage API (manual logging)
5. **Mistral** - OpenAI-compatible
6. **Google Gemini** - Most complex (GCP setup)

**Current Issue:** No data appearing in dashboard, likely due to Anthropic admin key confusion.

---

## Phase 1: Immediate Fixes (Week 1)

### Fix 1: Verify Anthropic Key Type

**Problem:** Using `sk-ant-api-` instead of `sk-ant-admin-`

```bash
# Check current key
echo $ANTHROPIC_API_KEY | head -c 15

# If output is: sk-ant-api-
# YOU NEED TO REGENERATE

# Steps:
# 1. Go to: https://console.anthropic.com/settings/organization
# 2. Click: "Generate Admin Key" (NOT "API Key")
# 3. Copy key starting with: sk-ant-admin-
# 4. Update .env:
ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-...

# 5. Restart app
docker-compose restart backend

# 6. Test connectivity
curl "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=2026-03-01T00:00:00Z&ending_at=2026-03-02T00:00:00Z" \
  -H "x-api-key: $ANTHROPIC_ADMIN_API_KEY" \
  -H "anthropic-version: 2023-06-01" | jq .

# Should return data, not 401/403
```

### Fix 2: Enable DEBUG Logging

**backend/config.py**

```python
import logging

class Config:
    # Change from INFO to DEBUG
    LOG_LEVEL = logging.DEBUG  # was logging.INFO
    
    # Add structured logging
    LOGGING_CONFIG = {
        'version': 1,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'detailed'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/debug.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'level': 'DEBUG',
                'formatter': 'detailed'
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file']
        }
    }
```

**Create logs directory:**

```bash
mkdir -p backend/logs
touch backend/logs/debug.log
chmod 666 backend/logs/debug.log
```

### Fix 3: Test Each Provider

**backend/scripts/test_providers.py**

```python
#!/usr/bin/env python3
"""Test connectivity and credentials for all providers."""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.anthropic_service import AnthropicService
from services.openai_service import OpenAIService
from utils.diagnostic_logger import get_diagnostic_logger

logger = get_diagnostic_logger(__name__)

def test_anthropic():
    """Test Anthropic Admin API."""
    logger.info("Testing Anthropic...")
    api_key = os.getenv('ANTHROPIC_ADMIN_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        logger.error("No Anthropic API key found")
        return False
    
    logger.info(f"Key prefix: {api_key[:15]}")
    
    if not api_key.startswith('sk-ant-admin'):
        logger.error(f"Wrong key type! Need sk-ant-admin-, got {api_key[:12]}")
        return False
    
    try:
        service = AnthropicService(api_key)
        valid = service.validate_credentials()
        logger.info(f"Anthropic: {'✅ VALID' if valid else '❌ INVALID'}")
        return valid
    except Exception as e:
        logger.error(f"Anthropic test failed: {e}", exc_info=True)
        return False

def test_openai():
    """Test OpenAI API."""
    logger.info("Testing OpenAI...")
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("No OpenAI API key found")
        return False
    
    try:
        service = OpenAIService(api_key)
        valid = service.validate_credentials()
        logger.info(f"OpenAI: {'✅ VALID' if valid else '❌ INVALID'}")
        return valid
    except Exception as e:
        logger.error(f"OpenAI test failed: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Provider Connectivity Test")
    logger.info("=" * 60)
    
    results = {
        'Anthropic': test_anthropic(),
        'OpenAI': test_openai(),
    }
    
    logger.info("=" * 60)
    logger.info("Results:")
    for provider, status in results.items():
        logger.info(f"  {provider}: {'✅ PASS' if status else '❌ FAIL'}")
    logger.info("=" * 60)
    
    sys.exit(0 if all(results.values()) else 1)
```

**Run test:**

```bash
python backend/scripts/test_providers.py
```

---

## Phase 2: Enhanced Schema (Week 2)

### Step 1: Backup Database

```bash
# Production
pg_dump -h $DB_HOST -U $DB_USER -d ai_cost_tracker > backup_$(date +%Y%m%d).sql

# Verify
ls -lh backup_*.sql
```

### Step 2: Apply Migration

See `docs/DATABASE_SCHEMA_ENHANCED.md` for full schema.

```bash
# Run migration
flask db upgrade

# Or manually
psql -h $DB_HOST -U $DB_USER -d ai_cost_tracker -f backend/migrations/versions/202603_enhanced_usage_tracking.py
```

### Step 3: Update Service Integrations

**backend/services/anthropic_service.py** (already done)

Already stores:
- input_tokens
- output_tokens  
- cache_creation_tokens
- cache_read_tokens
- service_tier
- workspace_id
- model_name

**backend/services/openai_service.py** (needs update)

Add rate limit extraction:

```python
def _extract_rate_limits(self, response):
    """Extract rate limit headers from OpenAI response."""
    headers = response.headers
    return {
        'rate_limit_tpm': self._parse_int(headers.get('x-ratelimit-limit-tokens')),
        'rate_limit_rpm': self._parse_int(headers.get('x-ratelimit-limit-requests')),
        'remaining_tpm': self._parse_int(headers.get('x-ratelimit-remaining-tokens')),
        'remaining_rpm': self._parse_int(headers.get('x-ratelimit-remaining-requests')),
        'reset_tpm_seconds': self._parse_duration(headers.get('x-ratelimit-reset-tokens')),
        'reset_rpm_seconds': self._parse_duration(headers.get('x-ratelimit-reset-requests')),
    }

def _parse_int(self, value):
    try:
        return int(value) if value else None
    except:
        return None

def _parse_duration(self, value):
    """Parse duration like '6m0s' to seconds."""
    if not value:
        return None
    # Simple parser: 6m0s -> 360
    try:
        if 'm' in value:
            parts = value.split('m')
            minutes = int(parts[0])
            seconds = int(parts[1].replace('s', '')) if len(parts) > 1 else 0
            return minutes * 60 + seconds
        elif 's' in value:
            return int(value.replace('s', ''))
    except:
        return None
```

---

## Phase 3: Add Remaining Providers (Week 3)

### Groq Service

**backend/services/groq_service.py**

```python
from services.base_service import BaseService
from utils.diagnostic_logger import get_diagnostic_logger

logger = get_diagnostic_logger(__name__)

class GroqService(BaseService):
    """Groq API integration with ultra-fast inference tracking."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.groq.com/openai/v1"
    
    def get_usage(self, start_date, end_date, account_id=None):
        """Groq has no usage API - must track per-request."""
        logger.warning("Groq has no usage API - use per-request tracking")
        return {
            'total_tokens': 0,
            'total_cost': 0.0,
            'daily': [],
            'note': 'Track Groq usage via per-request logging'
        }
    
    def call_with_tracking(self, model, messages, db, account_id):
        """Make Groq API call and store usage immediately."""
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={"model": model, "messages": messages}
        )
        
        data = response.json()
        usage = data.get('usage', {})
        headers = response.headers
        
        # Store immediately
        db.usage_records.insert({
            'timestamp': datetime.now(),
            'account_id': account_id,
            'service_id': self.get_service_id('groq'),
            'model_name': model,
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'queue_time_ms': usage.get('queue_time', 0) * 1000,
            'total_time_ms': usage.get('total_time', 0) * 1000,
            'rate_limit_tpm': self._parse_int(headers.get('x-ratelimit-limit-tokens')),
            'rate_limit_rpd': self._parse_int(headers.get('x-ratelimit-limit-requests')),
            'remaining_tpm': self._parse_int(headers.get('x-ratelimit-remaining-tokens')),
            'remaining_rpd': self._parse_int(headers.get('x-ratelimit-remaining-requests')),
        })
        
        return data
```

### Perplexity Service

**backend/services/perplexity_service.py**

```python
from services.base_service import BaseService
from utils.diagnostic_logger import get_diagnostic_logger

logger = get_diagnostic_logger(__name__)

PRICING = {
    'sonar': {'input': 1/1_000_000, 'output': 1/1_000_000, 'request': 0.01},
    'sonar-pro': {'input': 3/1_000_000, 'output': 15/1_000_000, 'request': 0.01},
    'sonar-deep-research': {
        'input': 2/1_000_000,
        'output': 8/1_000_000,
        'citations': 2/1_000_000,
        'reasoning': 3/1_000_000,
        'searches': 5/1000
    }
}

class PerplexityService(BaseService):
    """Perplexity API integration with per-request cost calculation."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.perplexity.ai"
    
    def get_usage(self, start_date, end_date, account_id=None):
        """Perplexity has no usage API - must track per-request."""
        logger.warning("Perplexity has no usage API - use per-request tracking")
        # Query from database instead
        # ... (implement database query)
    
    def call_with_tracking(self, model, messages, db, account_id):
        """Make Perplexity API call and store usage immediately."""
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={"model": model, "messages": messages}
        )
        
        data = response.json()
        usage = data.get('usage', {})
        
        # Calculate cost
        cost = self._calculate_cost(model, usage)
        
        # Store immediately
        db.usage_records.insert({
            'timestamp': datetime.now(),
            'account_id': account_id,
            'service_id': self.get_service_id('perplexity'),
            'model_name': model,
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'search_queries_count': usage.get('search_queries', 0),
            'reasoning_tokens': usage.get('reasoning_tokens', 0),
            'citation_tokens': usage.get('citation_tokens', 0),
            'cost': cost,
        })
        
        return data
    
    def _calculate_cost(self, model, usage):
        pricing = PRICING.get(model, {})
        input_cost = usage.get('prompt_tokens', 0) * pricing.get('input', 0)
        output_cost = usage.get('completion_tokens', 0) * pricing.get('output', 0)
        request_cost = pricing.get('request', 0)
        citation_cost = usage.get('citation_tokens', 0) * pricing.get('citations', 0)
        reasoning_cost = usage.get('reasoning_tokens', 0) * pricing.get('reasoning', 0)
        search_cost = usage.get('search_queries', 0) * pricing.get('searches', 0)
        return sum([input_cost, output_cost, request_cost, citation_cost, reasoning_cost, search_cost])
```

---

## Phase 4: Testing & Verification

### Test Checklist

```bash
# 1. Run provider tests
python backend/scripts/test_providers.py

# 2. Trigger manual sync
curl -X POST http://localhost:5000/api/accounts/1/sync \
  -H "Authorization: Bearer $API_TOKEN"

# 3. Check logs
tail -f backend/logs/debug.log | grep -E "anthropic|openai|groq"

# 4. Verify database
psql -h $DB_HOST -U $DB_USER -d ai_cost_tracker -c "
  SELECT 
    s.name,
    COUNT(*) as records,
    SUM(input_tokens + output_tokens) as total_tokens,
    SUM(cost) as total_cost
  FROM usage_records ur
  JOIN services s ON ur.service_id = s.id
  WHERE ur.timestamp >= NOW() - INTERVAL '24 hours'
  GROUP BY s.name;
"

# 5. Check dashboard
curl http://localhost:3000/api/dashboard | jq .
```

---

## Troubleshooting

### No Data Appearing

1. **Check API keys:**
   ```bash
   env | grep -E "ANTHROPIC|OPENAI|GROQ|PERPLEXITY"
   ```

2. **Check logs:**
   ```bash
   grep -i error backend/logs/debug.log | tail -20
   ```

3. **Test connectivity:**
   ```bash
   python backend/scripts/test_providers.py
   ```

4. **Verify database:**
   ```sql
   SELECT * FROM usage_records ORDER BY created_at DESC LIMIT 5;
   ```

### Anthropic 401/403

- ❌ Using `sk-ant-api-` → Need `sk-ant-admin-`
- ❌ Not organization admin → Grant admin role
- ❌ Key revoked → Regenerate

---

## AI Coding Assistant Instructions

### For Claude Code

```
@docs/providers/*.md - Provider API documentation
@docs/DATABASE_SCHEMA_ENHANCED.md - Database schema
@backend/services/anthropic_service.py - Reference implementation

Implement remaining provider services following the Anthropic pattern.
Use diagnostic_logger for all operations.
Store usage immediately for providers without usage APIs.
```

### For GitHub Copilot

```python
# Context: Implementing Groq service
# Reference: backend/services/anthropic_service.py
# Schema: docs/DATABASE_SCHEMA_ENHANCED.md
# Requirements:
# - Extract rate limits from headers
# - Track timing metrics (queue/prompt/completion)
# - Store immediately (no usage API exists)
```

---

## Success Criteria

- [ ] All provider tests pass
- [ ] Data appears in dashboard within 5 minutes
- [ ] Logs show successful syncs
- [ ] Database has records for each provider
- [ ] No errors in last 24h of logs
- [ ] Rate limits tracked and alerted
- [ ] Cache effectiveness visible (Anthropic)

---

**Next:** Run `python backend/scripts/test_providers.py` to diagnose current state.
