# Handover to Claude Code: AI Cost Tracker Phase 2 Implementation

**From**: Perplexity (Architecture & Research)  
**To**: Claude Code (Implementation)  
**Date**: February 25, 2026, 8:00 PM GMT  
**Phase**: Phase 2 - Multi-Service Support

---

## 🎯 Executive Summary

You're taking over a **fully functional Phase 1 MVP** with Flask backend, React frontend, OpenAI integration, and complete authentication/security. Your mission is to implement **Phase 2: Multi-Service Support** by adding Anthropic Claude, fixing data integrity issues, and creating a manual entry system for providers without APIs.

**Current State**: MVP complete on branch `codex/conduct-project-handover-for-next-steps`  
**Your Task**: Implement Sprint 2.1 from ROADMAP.md (Anthropic + Idempotency)  
**Timeline**: 2 weeks  
**Expected Outcome**: Multi-provider cost tracking with zero duplicate records

---

## 📁 Repository Structure

```
ai-cost-tracker/
├── backend/                    # Flask API (Python 3.10+)
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py            # User authentication
│   │   ├── service.py         # AI service definitions
│   │   ├── account.py         # User accounts per service
│   │   ├── usage_record.py    # Token usage tracking
│   │   ├── alert.py           # Alert configurations
│   │   └── cost_projection.py # Cost forecasting
│   ├── routes/                 # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py            # Register, login, logout
│   │   ├── accounts.py        # Account CRUD + test
│   │   ├── services.py        # Service management
│   │   ├── usage.py           # Usage data endpoints
│   │   └── alerts.py          # Alert management
│   ├── services/               # Provider integrations
│   │   ├── __init__.py
│   │   ├── base_service.py    # Base class (USE AS TEMPLATE)
│   │   ├── openai_service.py  # OpenAI implementation (WORKING)
│   │   └── [ADD ANTHROPIC HERE]
│   ├── utils/                  # Helper functions
│   │   ├── encryption.py      # AES-256 encryption
│   │   ├── cost_calculator.py # Cost computation
│   │   └── alert_generator.py # Alert detection
│   ├── jobs/                   # Background tasks
│   │   └── sync_usage.py      # APScheduler job (NEEDS FIX)
│   ├── migrations/             # Alembic migrations
│   ├── scripts/
│   │   └── seed_services.py   # Database seeding
│   ├── tests/                  # Backend tests
│   ├── app.py                  # Flask app factory
│   ├── config.py               # Configuration
│   └── requirements.txt        # Dependencies
├── frontend/                   # React UI
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── docs/                       # Documentation
│   ├── ai-tool-tracker-plan.md          # Technical spec
│   ├── api-integration-guide.md         # API details
│   ├── provider-api-research-2026.md    # **READ THIS FIRST**
│   ├── handover-to-perplexity.md        # From Codex
│   └── handover-to-claude-code.md       # This file
├── docker-compose.yml          # Container orchestration
├── .env.example                # Environment template
└── PROJECT_STATUS.md           # Current state
```

---

## 📖 Required Reading (Priority Order)

### 1. **MUST READ FIRST** (30 minutes)

**[docs/provider-api-research-2026.md](provider-api-research-2026.md)** - Provider API Research
- Current API capabilities for Anthropic, Groq, Perplexity (Feb 2026)
- **Anthropic has full Usage & Cost API** (this is your primary task)
- Groq and Perplexity require workarounds (Phase 2B)
- Implementation patterns and code examples
- Error handling taxonomy

**[docs/handover-to-perplexity.md](https://github.com/zebadee2kk/ai-cost-tracker/blob/codex/conduct-project-handover-for-next-steps/docs/handover-to-perplexity.md)** - From Codex
- What's already implemented
- Known issues (CRITICAL: scheduler idempotency)
- Testing gaps
- Recommended priorities

### 2. **Reference During Implementation** (as needed)

**[docs/ai-tool-tracker-plan.md](ai-tool-tracker-plan.md)** - Technical Specification
- Database schema (Section 2.1) - field types, constraints
- System architecture (Section 3)
- Security requirements (Section 7) - encryption, JWT, CORS

**[docs/api-integration-guide.md](api-integration-guide.md)** - API Integration Details
- Service-specific patterns
- Request/response examples
- Error handling

**[backend/services/openai_service.py](https://github.com/zebadee2kk/ai-cost-tracker/blob/codex/conduct-project-handover-for-next-steps/backend/services/openai_service.py)** - Working Reference
- Follow this pattern for Anthropic
- See how BaseService is extended
- Study error handling approach

### 3. **Quick Reference**

**[ROADMAP.md](../ROADMAP.md)** - Your sprint breakdown  
**[PROJECT_STATUS.md](../PROJECT_STATUS.md)** - Current detailed status  
**[.cursorrules](../.cursorrules)** - Coding standards and guidelines

---

## 🎯 Your Sprint: Phase 2.1 (Weeks 1-2)

### Sprint Goals
1. ✅ Fix scheduler idempotency (eliminate duplicate records)
2. ✅ Implement Anthropic Claude integration (full API support)
3. ✅ Achieve >80% test coverage
4. ✅ Set up CI pipeline

### Definition of Done
- [ ] Multi-provider sync runs without creating duplicates
- [ ] Anthropic accounts can be added, tested, and synced
- [ ] All backend tests pass in CI
- [ ] Test coverage >80%
- [ ] Documentation updated

---

## 🔧 Task 1: Fix Scheduler Idempotency (Priority: CRITICAL)

### Problem Statement
**Current Issue**: `backend/jobs/sync_usage.py` creates duplicate `usage_records` when run multiple times for the same account/date.

**Impact**: Inflated cost totals, incorrect analytics, unreliable forecasting.

**Root Cause**: No uniqueness constraint on usage records; scheduler blindly inserts on every run.

### Solution: Implement Idempotent UPSERT

#### Step 1: Add Database Constraint

**Create Migration**:
```bash
cd backend
flask db revision -m "Add unique constraint to usage_records for idempotency"
```

**Migration File** (`migrations/versions/XXXX_add_unique_constraint.py`):
```python
"""Add unique constraint to usage_records for idempotency

Revision ID: XXXX
Revises: YYYY
Create Date: 2026-02-XX
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add unique constraint
    op.create_unique_constraint(
        'uq_usage_record_account_date_type',
        'usage_records',
        ['account_id', 'service_id', 'date', 'request_type']
    )
    
    # Add source field to track origin
    op.add_column(
        'usage_records',
        sa.Column('source', sa.String(20), nullable=False, server_default='api')
    )
    
    # Add updated_at timestamp
    op.add_column(
        'usage_records',
        sa.Column('updated_at', sa.DateTime, nullable=True, onupdate=sa.func.now())
    )

def downgrade():
    op.drop_constraint('uq_usage_record_account_date_type', 'usage_records')
    op.drop_column('usage_records', 'source')
    op.drop_column('usage_records', 'updated_at')
```

#### Step 2: Update UsageRecord Model

**File**: `backend/models/usage_record.py`

```python
from sqlalchemy import UniqueConstraint

class UsageRecord(db.Model):
    __tablename__ = 'usage_records'
    
    # ... existing fields ...
    
    source = db.Column(db.String(20), nullable=False, default='api')
    # Options: 'api', 'manual', 'reconciled'
    
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())
    
    __table_args__ = (
        UniqueConstraint(
            'account_id', 'service_id', 'date', 'request_type',
            name='uq_usage_record_account_date_type'
        ),
    )
```

#### Step 3: Update Scheduler with UPSERT Logic

**File**: `backend/jobs/sync_usage.py`

```python
from sqlalchemy.dialects.postgresql import insert
from backend.models import UsageRecord, db
import logging

logger = logging.getLogger(__name__)

def sync_account_usage(account):
    """Sync usage for a single account with idempotent upsert."""
    try:
        service_client = get_service_client(account.service.name)
        
        # Fetch usage from provider API
        usage_data = service_client.get_usage(
            api_key=decrypt_api_key(account.encrypted_api_key)
        )
        
        # Process each daily record
        for daily in usage_data.get('daily', []):
            record_data = {
                'account_id': account.id,
                'service_id': account.service_id,
                'date': daily['date'],
                'request_type': daily.get('request_type', 'standard'),
                'prompt_tokens': daily['prompt_tokens'],
                'completion_tokens': daily['completion_tokens'],
                'total_tokens': daily['total_tokens'],
                'total_cost': daily['cost'],
                'currency': 'USD',
                'model': daily.get('model'),
                'source': 'api',
                'metadata': daily.get('metadata', {})
            }
            
            # PostgreSQL UPSERT using SQLAlchemy
            stmt = insert(UsageRecord).values(**record_data)
            stmt = stmt.on_conflict_do_update(
                constraint='uq_usage_record_account_date_type',
                set_={
                    'prompt_tokens': stmt.excluded.prompt_tokens,
                    'completion_tokens': stmt.excluded.completion_tokens,
                    'total_tokens': stmt.excluded.total_tokens,
                    'total_cost': stmt.excluded.total_cost,
                    'model': stmt.excluded.model,
                    'metadata': stmt.excluded.metadata,
                    'updated_at': db.func.now()
                }
            )
            
            db.session.execute(stmt)
        
        db.session.commit()
        logger.info(f"Successfully synced usage for account {account.id}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to sync account {account.id}: {str(e)}")
        raise
```

#### Step 4: Write Tests

**File**: `backend/tests/test_scheduler_idempotency.py`

```python
import pytest
from datetime import date
from backend.models import UsageRecord, Account, Service, db
from backend.jobs.sync_usage import sync_account_usage

def test_scheduler_idempotency(app, test_account):
    """Test that running sync twice doesn't create duplicates."""
    
    # First sync
    sync_account_usage(test_account)
    first_count = UsageRecord.query.filter_by(account_id=test_account.id).count()
    
    # Second sync (should update, not insert)
    sync_account_usage(test_account)
    second_count = UsageRecord.query.filter_by(account_id=test_account.id).count()
    
    assert first_count == second_count, "Duplicate records created!"
    
    # Verify updated_at changed
    records = UsageRecord.query.filter_by(account_id=test_account.id).all()
    for record in records:
        assert record.updated_at is not None

def test_upsert_updates_existing_record(app, test_account):
    """Test that upsert updates existing records with new data."""
    
    # Create initial record
    record = UsageRecord(
        account_id=test_account.id,
        service_id=test_account.service_id,
        date=date.today(),
        request_type='standard',
        total_tokens=100,
        total_cost=0.01,
        source='api'
    )
    db.session.add(record)
    db.session.commit()
    initial_cost = record.total_cost
    
    # Sync with updated data (different token count)
    sync_account_usage(test_account)  # Mock will return different values
    
    # Verify record was updated, not duplicated
    records = UsageRecord.query.filter_by(
        account_id=test_account.id,
        date=date.today()
    ).all()
    
    assert len(records) == 1, "Should be exactly one record"
    assert records[0].total_cost != initial_cost, "Cost should be updated"
```

---

## 🚀 Task 2: Implement Anthropic Claude Integration

### API Overview

**Status**: ✅ Full API Support Available (launched Aug 2025)

**Key Points**:
- Requires **Admin API Key** (different from regular API key)
- Two endpoints: `/v1/organizations/usage` and `/v1/organizations/cost_report`
- Real-time usage tracking (~instantaneous)
- Supports Priority Tier billing (separate pricing model)
- Includes prompt caching metrics

### Implementation Steps

#### Step 1: Create AnthropicService Class

**File**: `backend/services/anthropic_service.py`

```python
"""
Anthropic Claude API Service Integration

Official API Documentation:
https://platform.claude.com/docs/en/build-with-claude/usage-cost-api

API Version: 2023-06-01
Last Updated: February 2026
"""

import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import logging

from .base_service import BaseService, ServiceError

logger = logging.getLogger(__name__)

class AnthropicService(BaseService):
    """
    Anthropic Claude API client for usage and cost tracking.
    
    Requires Admin API key for usage/cost endpoints.
    Regular API keys will return 403 Forbidden.
    """
    
    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"
    
    # Current pricing (as of Feb 2026)
    PRICING = {
        'claude-opus-4.5': {
            'input': Decimal('5.00'),   # per million tokens
            'output': Decimal('25.00')
        },
        'claude-sonnet-4.5': {
            'input': Decimal('3.00'),
            'output': Decimal('15.00')
        },
        'claude-haiku-4.5': {
            'input': Decimal('1.00'),
            'output': Decimal('5.00')
        }
    }
    
    def __init__(self, api_key: str, admin_api_key: Optional[str] = None):
        """
        Initialize Anthropic service client.
        
        Args:
            api_key: Regular API key (for validation)
            admin_api_key: Admin API key (for usage/cost endpoints)
        """
        super().__init__(api_key)
        self.admin_api_key = admin_api_key or api_key
        self.headers = {
            'anthropic-version': self.API_VERSION,
            'x-api-key': self.admin_api_key,
            'Content-Type': 'application/json'
        }
    
    def validate_credentials(self) -> Dict[str, any]:
        """
        Validate API credentials by testing usage endpoint access.
        
        Returns:
            Dict with 'valid' boolean and optional 'error' message
        """
        try:
            # Test with small date range
            today = datetime.utcnow()
            yesterday = today - timedelta(days=1)
            
            url = f"{self.BASE_URL}/organizations/usage"
            params = {
                'starting_at': yesterday.isoformat() + 'Z',
                'ending_at': today.isoformat() + 'Z'
            }
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return {'valid': True}
            elif response.status_code == 403:
                return {
                    'valid': False,
                    'error': 'Admin API key required for usage tracking. Regular API keys cannot access usage endpoints.'
                }
            else:
                return {
                    'valid': False,
                    'error': f'API error: {response.status_code} - {response.text}'
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'valid': False,
                'error': f'Connection error: {str(e)}'
            }
    
    def get_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Fetch usage data from Anthropic Usage API.
        
        Args:
            start_date: Start of date range (defaults to 30 days ago)
            end_date: End of date range (defaults to now)
        
        Returns:
            Normalized usage data dict with:
            - total_tokens: int
            - total_cost: Decimal
            - daily: List[Dict] with per-day breakdown
        """
        # Default to last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        try:
            # Fetch usage data
            usage_url = f"{self.BASE_URL}/organizations/usage"
            params = {
                'starting_at': start_date.isoformat() + 'Z',
                'ending_at': end_date.isoformat() + 'Z'
            }
            
            response = requests.get(
                usage_url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            usage_data = response.json()
            
            # Fetch cost report
            cost_url = f"{self.BASE_URL}/organizations/cost_report"
            cost_response = requests.get(
                cost_url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            cost_response.raise_for_status()
            cost_data = cost_response.json()
            
            # Normalize to standard format
            return self._normalize_usage(usage_data, cost_data)
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise ServiceError(
                    "Admin API key required",
                    error_type="authentication_error"
                )
            elif e.response.status_code == 429:
                raise ServiceError(
                    "Rate limit exceeded",
                    error_type="rate_limit_error"
                )
            else:
                raise ServiceError(
                    f"API error: {e.response.text}",
                    error_type="api_error"
                )
        
        except requests.exceptions.RequestException as e:
            raise ServiceError(
                f"Connection error: {str(e)}",
                error_type="connection_error"
            )
    
    def _normalize_usage(
        self,
        usage_data: Dict,
        cost_data: Dict
    ) -> Dict[str, any]:
        """
        Normalize Anthropic API response to standard format.
        
        Args:
            usage_data: Response from /usage endpoint
            cost_data: Response from /cost_report endpoint
        
        Returns:
            Standardized usage dict
        """
        daily_records = []
        total_tokens = 0
        total_cost = Decimal('0')
        
        # Group by date
        usage_by_date = {}
        for item in usage_data.get('data', []):
            date = item['date']
            if date not in usage_by_date:
                usage_by_date[date] = {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'models': set()
                }
            
            usage_by_date[date]['prompt_tokens'] += item.get('input_tokens', 0)
            usage_by_date[date]['completion_tokens'] += item.get('output_tokens', 0)
            usage_by_date[date]['models'].add(item.get('model', 'unknown'))
        
        # Calculate costs per day
        for date, usage in usage_by_date.items():
            prompt_tokens = usage['prompt_tokens']
            completion_tokens = usage['completion_tokens']
            total = prompt_tokens + completion_tokens
            
            # Estimate cost (use average pricing if multiple models)
            # In production, use cost_data for accurate costs
            cost = self._calculate_cost(prompt_tokens, completion_tokens, list(usage['models'])[0])
            
            daily_records.append({
                'date': date,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total,
                'cost': cost,
                'model': ','.join(usage['models']) if len(usage['models']) > 1 else list(usage['models'])[0],
                'request_type': 'standard',
                'metadata': {
                    'workspace_id': usage_data.get('workspace_id'),
                    'models_used': list(usage['models'])
                }
            })
            
            total_tokens += total
            total_cost += cost
        
        return {
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'currency': 'USD',
            'daily': daily_records
        }
    
    def _calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str
    ) -> Decimal:
        """
        Calculate cost based on token usage and model pricing.
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model name
        
        Returns:
            Total cost as Decimal
        """
        # Find matching pricing
        pricing = None
        for model_name, prices in self.PRICING.items():
            if model_name in model:
                pricing = prices
                break
        
        if not pricing:
            # Default to Sonnet pricing if unknown
            logger.warning(f"Unknown model {model}, using Sonnet pricing")
            pricing = self.PRICING['claude-sonnet-4.5']
        
        # Calculate cost (pricing is per million tokens)
        input_cost = (Decimal(prompt_tokens) / Decimal('1000000')) * pricing['input']
        output_cost = (Decimal(completion_tokens) / Decimal('1000000')) * pricing['output']
        
        return input_cost + output_cost
```

#### Step 2: Update Service Dispatch

**File**: `backend/services/__init__.py`

```python
from .base_service import BaseService, ServiceError
from .openai_service import OpenAIService
from .anthropic_service import AnthropicService

SERVICE_CLIENTS = {
    'openai': OpenAIService,
    'chatgpt': OpenAIService,
    'anthropic': AnthropicService,
    'claude': AnthropicService
}

def get_service_client(service_name: str, api_key: str) -> BaseService:
    """
    Factory function to get service client by name.
    
    Args:
        service_name: Service identifier (lowercase)
        api_key: API key for authentication
    
    Returns:
        Service client instance
    
    Raises:
        ValueError: If service not supported
    """
    service_name = service_name.lower()
    
    if service_name not in SERVICE_CLIENTS:
        raise ValueError(f"Unsupported service: {service_name}")
    
    return SERVICE_CLIENTS[service_name](api_key)
```

#### Step 3: Update Scheduler

**File**: `backend/jobs/sync_usage.py`

```python
# Add to service dispatch
def get_service_client_for_sync(account):
    """Get appropriate service client for account."""
    from backend.services import get_service_client
    from backend.utils.encryption import decrypt_api_key
    
    decrypted_key = decrypt_api_key(account.encrypted_api_key)
    
    # Special handling for Anthropic (needs admin key)
    if account.service.name.lower() in ['anthropic', 'claude']:
        from backend.services.anthropic_service import AnthropicService
        # TODO: Store admin key separately in account model
        return AnthropicService(api_key=decrypted_key)
    
    return get_service_client(account.service.name, decrypted_key)
```

#### Step 4: Update Account Test Endpoint

**File**: `backend/routes/accounts.py`

```python
@accounts_bp.route('/<int:account_id>/test', methods=['POST'])
@jwt_required()
def test_account_connection(account_id):
    """
    Test API connection for an account.
    
    Supports: OpenAI, Anthropic Claude
    """
    account = Account.query.get_or_404(account_id)
    
    # Verify ownership
    if account.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        service_client = get_service_client_for_sync(account)
        result = service_client.validate_credentials()
        
        if result['valid']:
            return jsonify({
                'success': True,
                'message': 'Connection successful'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Invalid credentials')
            }), 400
    
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

#### Step 5: Write Tests

**File**: `backend/tests/test_anthropic_service.py`

```python
import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from decimal import Decimal

from backend.services.anthropic_service import AnthropicService, ServiceError

MOCK_USAGE_RESPONSE = {
    'data': [
        {
            'date': '2026-02-25',
            'input_tokens': 15000,
            'output_tokens': 5000,
            'model': 'claude-sonnet-4.5',
            'workspace_id': 'ws_test'
        }
    ]
}

MOCK_COST_RESPONSE = {
    'total_cost': '0.12',
    'currency': 'USD'
}

@pytest.fixture
def anthropic_service():
    return AnthropicService(api_key='test-admin-key')

def test_validate_credentials_success(anthropic_service):
    """Test successful credential validation."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = MOCK_USAGE_RESPONSE
        
        result = anthropic_service.validate_credentials()
        
        assert result['valid'] is True
        assert 'error' not in result

def test_validate_credentials_non_admin_key(anthropic_service):
    """Test validation with regular (non-admin) API key."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 403
        
        result = anthropic_service.validate_credentials()
        
        assert result['valid'] is False
        assert 'Admin API key required' in result['error']

def test_get_usage_success(anthropic_service):
    """Test successful usage data retrieval."""
    with patch('requests.get') as mock_get:
        # Mock both usage and cost endpoints
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = [
            MOCK_USAGE_RESPONSE,
            MOCK_COST_RESPONSE
        ]
        
        result = anthropic_service.get_usage()
        
        assert result['total_tokens'] == 20000
        assert result['currency'] == 'USD'
        assert len(result['daily']) == 1
        assert result['daily'][0]['date'] == '2026-02-25'
        assert result['daily'][0]['prompt_tokens'] == 15000
        assert result['daily'][0]['completion_tokens'] == 5000

def test_get_usage_rate_limit(anthropic_service):
    """Test rate limit error handling."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        with pytest.raises(ServiceError) as exc_info:
            anthropic_service.get_usage()
        
        assert exc_info.value.error_type == 'rate_limit_error'

def test_calculate_cost_sonnet(anthropic_service):
    """Test cost calculation for Sonnet model."""
    cost = anthropic_service._calculate_cost(
        prompt_tokens=1000000,  # 1M tokens
        completion_tokens=1000000,  # 1M tokens
        model='claude-sonnet-4.5'
    )
    
    # $3 input + $15 output = $18
    assert cost == Decimal('18.00')

def test_calculate_cost_opus(anthropic_service):
    """Test cost calculation for Opus model."""
    cost = anthropic_service._calculate_cost(
        prompt_tokens=500000,  # 0.5M tokens
        completion_tokens=500000,  # 0.5M tokens
        model='claude-opus-4.5'
    )
    
    # ($5 * 0.5) + ($25 * 0.5) = $15
    assert cost == Decimal('15.00')

def test_normalize_usage_multiple_models(anthropic_service):
    """Test usage normalization with multiple models."""
    usage_data = {
        'data': [
            {
                'date': '2026-02-25',
                'input_tokens': 1000,
                'output_tokens': 500,
                'model': 'claude-sonnet-4.5'
            },
            {
                'date': '2026-02-25',
                'input_tokens': 2000,
                'output_tokens': 1000,
                'model': 'claude-opus-4.5'
            }
        ]
    }
    
    result = anthropic_service._normalize_usage(usage_data, {})
    
    assert result['total_tokens'] == 4500
    assert len(result['daily']) == 1
    assert 'claude-sonnet-4.5,claude-opus-4.5' in result['daily'][0]['model']
```

---

## ✅ Task 3: Update Tests & CI

### Add Integration Tests

**File**: `backend/tests/test_integration_multi_provider.py`

```python
import pytest
from datetime import date, datetime, timedelta
from backend.models import Account, UsageRecord, Service, db
from backend.jobs.sync_usage import sync_all_accounts

@pytest.mark.integration
def test_multi_provider_sync(app, test_user):
    """Test syncing multiple providers doesn't interfere."""
    
    # Create accounts for different services
    openai_service = Service.query.filter_by(name='OpenAI').first()
    anthropic_service = Service.query.filter_by(name='Anthropic').first()
    
    openai_account = Account(
        user_id=test_user.id,
        service_id=openai_service.id,
        encrypted_api_key=encrypt_api_key('sk-test-openai')
    )
    anthropic_account = Account(
        user_id=test_user.id,
        service_id=anthropic_service.id,
        encrypted_api_key=encrypt_api_key('sk-ant-test')
    )
    
    db.session.add_all([openai_account, anthropic_account])
    db.session.commit()
    
    # Sync all (with mocked API calls)
    with patch('backend.services.openai_service.OpenAIService.get_usage'), \
         patch('backend.services.anthropic_service.AnthropicService.get_usage'):
        
        sync_all_accounts()
    
    # Verify records created for both
    openai_records = UsageRecord.query.filter_by(account_id=openai_account.id).count()
    anthropic_records = UsageRecord.query.filter_by(account_id=anthropic_account.id).count()
    
    assert openai_records > 0
    assert anthropic_records > 0

@pytest.mark.integration
def test_usage_endpoint_multi_provider(client, auth_headers, test_user):
    """Test /api/usage endpoints work with multiple providers."""
    
    # Seed usage records for multiple providers
    # ... (create test data)
    
    # Get current month summary
    response = client.get('/api/usage', headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json
    assert 'total_cost' in data
    assert 'services' in data
    assert len(data['services']) >= 2  # OpenAI + Anthropic
```

### Set Up CI Pipeline

**File**: `.github/workflows/backend-tests.yml`

```yaml
name: Backend Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          SECRET_KEY: test-secret-key-for-ci
          ENCRYPTION_KEY: test-encryption-key-for-ci
        run: |
          cd backend
          pytest tests/ -v --cov=. --cov-report=term --cov-report=xml
      
      - name: Check coverage threshold
        run: |
          cd backend
          coverage report --fail-under=80
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          fail_ci_if_error: true
```

---

## 📋 Testing Checklist

Before marking tasks complete:

### Unit Tests
- [ ] Anthropic service credential validation
- [ ] Anthropic service usage parsing
- [ ] Anthropic service cost calculation
- [ ] Anthropic service error handling
- [ ] Scheduler idempotency (duplicate prevention)
- [ ] Scheduler error handling
- [ ] UPSERT logic

### Integration Tests
- [ ] Account creation with Anthropic service
- [ ] Connection test endpoint
- [ ] Usage sync for Anthropic account
- [ ] Multi-provider sync doesn't interfere
- [ ] Usage endpoints return correct data
- [ ] Repeated sync doesn't create duplicates

### Manual Testing
1. [ ] Register user via UI
2. [ ] Add Anthropic account
3. [ ] Test connection (should work with admin key)
4. [ ] Wait for sync or trigger manually
5. [ ] View dashboard - should show Anthropic usage
6. [ ] Check database - no duplicate records
7. [ ] Run sync again - verify no new duplicates
8. [ ] Add OpenAI account - verify both work

---

## 🔍 Code Review Checklist

Before submitting:

### Security
- [ ] API keys encrypted at rest
- [ ] No hardcoded credentials
- [ ] Admin API key stored separately from regular key
- [ ] SQL injection prevention (using SQLAlchemy ORM)
- [ ] Input validation on all endpoints

### Code Quality
- [ ] Follows .cursorrules style guide
- [ ] Docstrings on all public functions
- [ ] Type hints where appropriate
- [ ] Error messages are helpful
- [ ] Logging at appropriate levels

### Data Integrity
- [ ] Unique constraints enforced
- [ ] Transactions used for multi-step operations
- [ ] Rollback on errors
- [ ] DECIMAL used for money (not float)
- [ ] Timestamps in UTC

### Testing
- [ ] >80% code coverage
- [ ] Tests pass in CI
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Mocks used for external APIs

### Documentation
- [ ] README updated if setup changed
- [ ] API integration guide updated
- [ ] Comments explain "why", not "what"
- [ ] Migration instructions clear

---

## 🚨 Common Pitfalls to Avoid

### 1. Admin API Key Confusion
**Problem**: Using regular Anthropic API key for usage endpoints  
**Symptom**: 403 Forbidden errors  
**Solution**: Ensure admin API key is used for `/v1/organizations/*` endpoints

### 2. Float vs Decimal for Costs
**Problem**: Using `float` for money calculations  
**Symptom**: Rounding errors, incorrect totals  
**Solution**: Always use `Decimal` from Python decimal module

### 3. Timezone Issues
**Problem**: Mixing UTC and local times  
**Symptom**: Usage appears on wrong dates  
**Solution**: Store all timestamps in UTC, convert for display only

### 4. Missing Unique Constraint
**Problem**: Forgetting to apply migration  
**Symptom**: Duplicates still created  
**Solution**: Run `flask db upgrade` after creating migration

### 5. Incomplete Error Handling
**Problem**: Not catching all API error codes  
**Symptom**: Scheduler crashes on rate limits  
**Solution**: Handle 429, 403, 500, timeout, connection errors

### 6. Test Data Pollution
**Problem**: Tests not cleaning up after themselves  
**Symptom**: Flaky tests, order-dependent failures  
**Solution**: Use pytest fixtures with teardown, or database rollback

### 7. Hardcoded Pricing
**Problem**: Pricing changes but code doesn't  
**Symptom**: Incorrect cost calculations  
**Solution**: Store pricing in database, update via admin endpoint

---

## 📊 Success Metrics

### Sprint 2.1 Goals

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Test Coverage | >80% | `pytest --cov` |
| Idempotency | 100% | Run sync twice, count records |
| Anthropic Integration | Working | Add account, sync, view dashboard |
| CI Pipeline | Passing | GitHub Actions green |
| Code Quality | Clean | pylint/flake8 score |
| Documentation | Complete | All sections updated |

### Definition of Done

Sprint 2.1 is complete when:
- [x] All tests pass locally
- [x] CI pipeline green
- [x] Test coverage >80%
- [x] No duplicate records created (verified with test)
- [x] Anthropic accounts can be added and synced
- [x] Dashboard shows Anthropic usage correctly
- [x] Code reviewed and refactored
- [x] Documentation updated
- [x] Branch ready for merge

---

## 🆘 Getting Help

### If You're Stuck

1. **Review the references** - All answers are in the docs
2. **Check existing code** - OpenAI service shows the pattern
3. **Look at tests** - They show expected behavior
4. **Check error logs** - Flask logs are detailed

### Questions to Ask Perplexity

- "How do I handle SQLAlchemy UPSERT with unique constraint?"
- "What's the correct way to use Decimal in Python for money?"
- "How do I mock Anthropic API responses in pytest?"
- "What's the best retry strategy for API rate limits?"

### Questions to Ask the Human

- "Where should I store the Anthropic admin API key?"
- "Should Priority Tier billing be tracked separately?"
- "Do you want real-time or daily batch sync?"
- "Should I implement prompt caching cost reduction?"

---

## 🎉 You're Ready!

You have:
- ✅ Complete working MVP to build on
- ✅ Clear implementation tasks
- ✅ Code examples and patterns
- ✅ Comprehensive test strategy
- ✅ Error handling guidance
- ✅ Success criteria

**Start with Task 1 (Idempotency)** - it's critical and foundational. Once that's solid, Task 2 (Anthropic) will be straightforward using the OpenAI service as a template.

**Estimated Time**:
- Task 1 (Idempotency): 4-6 hours
- Task 2 (Anthropic): 6-8 hours
- Task 3 (Tests & CI): 4-6 hours
- **Total Sprint 2.1**: 14-20 hours

Good luck! 🚀

---

**Handover Complete**  
**Your move, Claude Code!** 💪
