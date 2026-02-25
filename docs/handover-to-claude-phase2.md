# Handover to Claude Code: Phase 2 Implementation

**Date**: February 25, 2026  
**From**: Perplexity (Research) + Codex (Phase 1 MVP)  
**To**: Claude Code (Phase 2 Implementation)  
**Branch**: Use `main` as base, create feature branches for PRs

---

## 🎯 Mission: Multi-Service Integration + Data Integrity

Your objective is to expand the AI Cost Tracker from OpenAI-only to multi-service support (Anthropic Claude, Groq, Perplexity) while ensuring data integrity through idempotent ingestion.

---

## 📋 Required Reading (Priority Order)

1. **[docs/research-api-capabilities-2026.md](research-api-capabilities-2026.md)** ← **START HERE**
   - API capabilities for all providers
   - Idempotent patterns with code examples
   - Implementation roadmap

2. **[docs/handover-to-perplexity.md](handover-to-perplexity.md)** (from Codex)
   - Current MVP state
   - Known gaps and risks
   - Original Phase 2 recommendations

3. **[docs/ai-tool-tracker-plan.md](ai-tool-tracker-plan.md)**
   - Original project specification
   - Database schema reference

4. **Backend Code** (existing implementation)
   - `backend/services/openai_service.py` - Reference implementation
   - `backend/jobs/sync_usage.py` - Scheduler to modify
   - `backend/models/` - Database models

---

## 🛠️ Phase 2 Implementation Plan

### Sprint 1: Foundation & Anthropic Integration (Priority)

#### Task 1.1: Database Schema Updates

**File**: Create `backend/migrations/versions/add_idempotency_constraint.py`

**Objective**: Add unique constraint to prevent duplicate usage records

**Implementation**:
```python
"""Add unique constraint for idempotent usage ingestion

Revision ID: xxx
Revises: yyy
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add unique constraint
    op.create_unique_constraint(
        'uq_usage_record_idempotency',
        'usage_records',
        ['account_id', 'service_id', 'timestamp', 'request_type']
    )
    
    # Add source field for manual entries
    op.add_column('usage_records', 
        sa.Column('source', sa.String(50), nullable=False, server_default='api')
    )
    
    # Add updated_at for tracking updates
    op.add_column('usage_records',
        sa.Column('updated_at', sa.DateTime, nullable=True)
    )

def downgrade():
    op.drop_constraint('uq_usage_record_idempotency', 'usage_records')
    op.drop_column('usage_records', 'source')
    op.drop_column('usage_records', 'updated_at')
```

**Verification**:
```bash
flask db upgrade
flask db history  # Should show new migration
```

---

#### Task 1.2: Fix Scheduler Duplicate Runs

**File**: `backend/jobs/scheduler.py` (or wherever scheduler is initialized)

**Problem**: Flask debug mode runs scheduler twice

**Solution** (from research):
```python
import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

def init_scheduler(app):
    """Initialize background scheduler for usage sync.
    
    Only runs in production OR in child process of debug mode
    to prevent duplicate job execution.
    """
    # Prevent duplicate in Flask debug mode
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        app.logger.info("Skipping scheduler init in Flask reloader parent process")
        return
    
    scheduler = BackgroundScheduler()
    
    # Daily sync at 2 AM
    scheduler.add_job(
        func=sync_all_accounts,
        trigger='cron',
        hour=2,
        minute=0,
        id='daily_usage_sync',
        replace_existing=True,
        misfire_grace_time=3600  # Allow 1 hour grace period
    )
    
    scheduler.start()
    app.logger.info("Background scheduler started")
    
    # Graceful shutdown
    atexit.register(lambda: scheduler.shutdown(wait=False))
```

**Update** `backend/app.py` if needed:
```python
from jobs.scheduler import init_scheduler

# After app creation
init_scheduler(app)
```

---

#### Task 1.3: Implement Idempotent Upsert in Scheduler

**File**: `backend/jobs/sync_usage.py`

**Current Issue**: Creates duplicate records on repeated runs

**Solution** (using SQLAlchemy ON CONFLICT):

```python
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from backend.models import UsageRecord, db
from decimal import Decimal

def upsert_usage_record(account_id, service_id, date, tokens, cost, metadata=None):
    """
    Insert or update usage record idempotently.
    
    Uses PostgreSQL ON CONFLICT to handle duplicate date/account/service combinations.
    """
    stmt = insert(UsageRecord).values(
        account_id=account_id,
        service_id=service_id,
        timestamp=date,
        tokens=tokens,
        cost=Decimal(str(cost)),  # Ensure DECIMAL precision
        request_type='api',
        source='api',
        metadata=metadata or {},
        created_at=func.now()
    )
    
    # On conflict, update existing record
    stmt = stmt.on_conflict_do_update(
        index_elements=['account_id', 'service_id', 'timestamp', 'request_type'],
        set_={
            'tokens': stmt.excluded.tokens,
            'cost': stmt.excluded.cost,
            'metadata': stmt.excluded.metadata,
            'updated_at': func.now()
        }
    )
    
    db.session.execute(stmt)
```

**Update `sync_account_usage()` function**:
```python
def sync_account_usage(account):
    """Sync usage for a single account."""
    try:
        service = get_service_client(account.service_id, account.api_key)
        
        # Fetch last 7 days
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        
        usage_data = service.get_usage(start_date, end_date)
        
        # Upsert each daily record
        for daily in usage_data['daily']:
            upsert_usage_record(
                account_id=account.id,
                service_id=account.service_id,
                date=datetime.strptime(daily['date'], '%Y-%m-%d').date(),
                tokens=daily['tokens'],
                cost=daily['cost'],
                metadata=daily.get('metadata', {})
            )
        
        db.session.commit()
        logger.info(f"Synced {len(usage_data['daily'])} records for account {account.id}")
        
    except ServiceError as e:
        logger.error(f"Service error for account {account.id}: {str(e)}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error for account {account.id}: {str(e)}")
        db.session.rollback()
        raise
```

---

#### Task 1.4: Create AnthropicService

**File**: `backend/services/anthropic_service.py`

**Reference**: See `docs/research-api-capabilities-2026.md` Section 1 for full API specs

**Implementation Template**:

```python
import requests
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from .base_service import BaseService, ServiceError, AuthenticationError, RateLimitError

class AnthropicService(BaseService):
    """Anthropic Claude API integration using Admin API.
    
    Requires Admin API key (sk-ant-admin...) not standard API key.
    Only works with organization accounts, not individual accounts.
    """
    
    BASE_URL = "https://api.anthropic.com/v1/organizations"
    ANTHROPIC_VERSION = "2023-06-01"
    
    # Pricing per 1M tokens (Feb 2026)
    PRICING = {
        'claude-opus-4-6': {'input': 5.00, 'output': 25.00},
        'claude-opus-4-5': {'input': 5.00, 'output': 25.00},
        'claude-sonnet-4-5': {'input': 3.00, 'output': 15.00},
        'claude-haiku-4-5': {'input': 1.00, 'output': 5.00},
    }
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        
        if not api_key.startswith('sk-ant-admin'):
            raise AuthenticationError(
                "Anthropic integration requires Admin API key (sk-ant-admin...). "
                "Standard API keys are not supported. "
                "Generate Admin API key in Console → Settings → Organization."
            )
    
    def validate_credentials(self) -> bool:
        """Test if Admin API key is valid."""
        try:
            # Try to fetch last day of usage
            end = datetime.utcnow()
            start = end - timedelta(days=1)
            
            response = self._make_request(
                'GET',
                f"{self.BASE_URL}/usage_report/messages",
                params={
                    'starting_at': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'ending_at': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'bucket_width': '1d'
                }
            )
            return response.status_code == 200
            
        except AuthenticationError:
            return False
        except Exception as e:
            self.logger.error(f"Credential validation error: {str(e)}")
            return False
    
    def get_usage(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch usage data from Anthropic Admin API.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
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
                            'input_tokens': int,
                            'output_tokens': int,
                            'models': List[str]
                        }
                    }
                ]
            }
        """
        # Convert dates to ISO 8601 with time
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        # Fetch usage data
        usage_response = self._make_request(
            'GET',
            f"{self.BASE_URL}/usage_report/messages",
            params={
                'starting_at': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'ending_at': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'bucket_width': '1d',
                'group_by[]': 'model'
            }
        ).json()
        
        # Parse and aggregate by date
        daily_data = self._aggregate_daily_usage(usage_response['data'])
        
        # Calculate totals
        total_tokens = sum(d['tokens'] for d in daily_data)
        total_cost = sum(d['cost'] for d in daily_data)
        
        return {
            'total_tokens': total_tokens,
            'total_cost': Decimal(str(total_cost)),
            'daily': daily_data
        }
    
    def _aggregate_daily_usage(self, data: List[Dict]) -> List[Dict]:
        """Aggregate usage data by date."""
        from collections import defaultdict
        
        daily = defaultdict(lambda: {
            'input_tokens': 0,
            'output_tokens': 0,
            'models': set()
        })
        
        for entry in data:
            date_key = entry['start_time'][:10]  # Extract YYYY-MM-DD
            
            daily[date_key]['input_tokens'] += entry.get('input_tokens', 0)
            daily[date_key]['output_tokens'] += entry.get('output_tokens', 0)
            daily[date_key]['models'].add(entry.get('model', 'unknown'))
        
        # Calculate costs using pricing
        result = []
        for date_str, data in sorted(daily.items()):
            # Estimate cost (simplified - ideally track per-model)
            # Using average pricing for mixed model usage
            input_cost = (data['input_tokens'] / 1_000_000) * 3.00  # Avg input
            output_cost = (data['output_tokens'] / 1_000_000) * 15.00  # Avg output
            total_cost = input_cost + output_cost
            
            result.append({
                'date': date_str,
                'tokens': data['input_tokens'] + data['output_tokens'],
                'cost': Decimal(str(round(total_cost, 4))),
                'metadata': {
                    'input_tokens': data['input_tokens'],
                    'output_tokens': data['output_tokens'],
                    'models': list(data['models'])
                }
            })
        
        return result
    
    def _make_request(self, method: str, url: str, **kwargs):
        """Make authenticated request to Anthropic API."""
        headers = kwargs.pop('headers', {})
        headers.update({
            'anthropic-version': self.ANTHROPIC_VERSION,
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        })
        
        response = requests.request(method, url, headers=headers, **kwargs)
        
        # Handle errors
        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired Admin API key")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 500:
            raise ServiceError(f"Anthropic service error: {response.status_code}")
        elif response.status_code >= 400:
            raise ServiceError(f"Anthropic API error: {response.json().get('error', 'Unknown error')}")
        
        return response
```

**Add to service dispatch** in `backend/services/__init__.py`:
```python
from .anthropic_service import AnthropicService

SERVICE_CLIENTS = {
    'openai': OpenAIService,
    'anthropic': AnthropicService,
    # Add others as implemented
}

def get_service_client(service_id, api_key):
    service = Service.query.get(service_id)
    client_class = SERVICE_CLIENTS.get(service.name.lower())
    
    if not client_class:
        raise ValueError(f"No client implementation for service: {service.name}")
    
    return client_class(api_key)
```

---

#### Task 1.5: Add Anthropic Tests

**File**: `backend/tests/test_anthropic_service.py`

```python
import pytest
from unittest.mock import Mock, patch
from datetime import date
from backend.services.anthropic_service import AnthropicService
from backend.services.base_service import AuthenticationError

def test_requires_admin_api_key():
    """Should reject standard API keys."""
    with pytest.raises(AuthenticationError, match="Admin API key"):
        AnthropicService("sk-ant-api-standard-key")

def test_accepts_admin_api_key():
    """Should accept Admin API keys."""
    service = AnthropicService("sk-ant-admin-test-key")
    assert service.api_key == "sk-ant-admin-test-key"

@patch('backend.services.anthropic_service.requests.request')
def test_get_usage_success(mock_request):
    """Should parse usage data correctly."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'data': [
            {
                'start_time': '2026-02-01T00:00:00Z',
                'end_time': '2026-02-02T00:00:00Z',
                'input_tokens': 100000,
                'output_tokens': 50000,
                'model': 'claude-opus-4-6'
            }
        ],
        'has_more': False
    }
    mock_request.return_value = mock_response
    
    service = AnthropicService("sk-ant-admin-test")
    result = service.get_usage(date(2026, 2, 1), date(2026, 2, 1))
    
    assert result['total_tokens'] == 150000
    assert len(result['daily']) == 1
    assert result['daily'][0]['date'] == '2026-02-01'
    assert result['daily'][0]['metadata']['input_tokens'] == 100000

@patch('backend.services.anthropic_service.requests.request')
def test_handles_401_error(mock_request):
    """Should raise AuthenticationError on 401."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_request.return_value = mock_response
    
    service = AnthropicService("sk-ant-admin-invalid")
    
    with pytest.raises(AuthenticationError):
        service.get_usage(date(2026, 2, 1), date(2026, 2, 1))
```

**Run tests**:
```bash
cd backend
pytest tests/test_anthropic_service.py -v
```

---

### Sprint 2: Manual Entry System (For Groq & Perplexity)

#### Task 2.1: Manual Entry Backend Endpoint

**File**: `backend/routes/usage.py`

**Add new route**:
```python
@bp.route('/manual', methods=['POST'])
@jwt_required()
def create_manual_entry():
    """Create manual usage entry.
    
    Request body:
    {
        "account_id": 1,
        "date": "2026-02-25",
        "tokens": 100000,
        "cost": "5.50",
        "notes": "From invoice #12345"
    }
    """
    data = request.get_json()
    current_user = get_jwt_identity()
    
    # Validate account ownership
    account = Account.query.filter_by(
        id=data['account_id'],
        user_id=current_user
    ).first_or_404()
    
    # Create manual entry
    entry = UsageRecord(
        account_id=account.id,
        service_id=account.service_id,
        timestamp=datetime.strptime(data['date'], '%Y-%m-%d').date(),
        tokens=data['tokens'],
        cost=Decimal(data['cost']),
        request_type='manual',
        source='manual',
        metadata={'notes': data.get('notes', '')},
        created_at=datetime.utcnow()
    )
    
    db.session.add(entry)
    db.session.commit()
    
    return jsonify(entry.to_dict()), 201
```

#### Task 2.2: Manual Entry Frontend UI

**File**: `frontend/src/components/ManualEntryModal.jsx`

```jsx
import React, { useState } from 'react';
import { createManualEntry } from '../services/api';

export default function ManualEntryModal({ account, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    tokens: '',
    cost: '',
    notes: ''
  });
  
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      await createManualEntry(account.id, formData);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Add Manual Usage Entry</h2>
        <p className="text-sm text-gray-600 mb-4">
          For {account.service_name} - {account.account_name}
        </p>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Date</label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({...formData, date: e.target.value})}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Tokens Used</label>
            <input
              type="number"
              value={formData.tokens}
              onChange={(e) => setFormData({...formData, tokens: e.target.value})}
              placeholder="e.g., 100000"
              required
            />
          </div>
          
          <div className="form-group">
            <label>Cost (USD)</label>
            <input
              type="number"
              step="0.01"
              value={formData.cost}
              onChange={(e) => setFormData({...formData, cost: e.target.value})}
              placeholder="e.g., 5.50"
              required
            />
          </div>
          
          <div className="form-group">
            <label>Notes (Optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              placeholder="e.g., Invoice #12345, Dashboard total for February"
              rows="3"
            />
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Adding...' : 'Add Entry'}
            </button>
          </div>
        </form>
        
        <div className="help-text mt-4">
          <strong>Where to find this data:</strong>
          <ul>
            <li><strong>Groq:</strong> Dashboard → Usage</li>
            <li><strong>Perplexity:</strong> Settings → Usage Metrics → Invoices</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
```

---

## 📝 Testing Requirements

### Unit Tests (Required)

- [ ] `test_anthropic_service.py` - API client parsing
- [ ] `test_idempotent_upsert.py` - Duplicate prevention
- [ ] `test_manual_entry.py` - Manual entry validation

### Integration Tests (Required)

- [ ] Scheduler runs multiple times without duplicates
- [ ] Anthropic sync with real/mocked API
- [ ] Manual entry CRUD operations

### Test Command
```bash
cd backend
pytest tests/ -v --cov=backend --cov-report=html
```

---

## ✅ Definition of Done (Phase 2)

### Sprint 1 Complete When:
- [ ] Database migration applied (unique constraint)
- [ ] Scheduler duplicate prevention verified
- [ ] Idempotent upsert working (test with repeated runs)
- [ ] AnthropicService implemented and tested
- [ ] Anthropic added to service dispatch
- [ ] Backend tests passing (>80% coverage)
- [ ] Manual sync test successful with real Anthropic account

### Sprint 2 Complete When:
- [ ] Manual entry endpoint working
- [ ] Manual entry UI implemented
- [ ] Groq and Perplexity marked as "manual entry required"
- [ ] Documentation updated
- [ ] Integration tests passing

---

## 🐛 Known Issues to Address

1. **Scheduler imports cleanup** (from Codex handover)
   - Remove unused imports in `backend/jobs/sync_usage.py`
   - Remove unused variables (`ServiceError`, `tomorrow`)

2. **Frontend connection test** (from Codex handover)
   - Currently only works for OpenAI
   - Extend to support Anthropic after implementation

3. **ROADMAP.md** (from Codex handover)
   - Update to reflect actual Phase 1 completion
   - Add Phase 2 tasks

---

## 📦 Deliverables

### Code
- [ ] Migration file for unique constraint
- [ ] Updated scheduler with duplicate prevention
- [ ] Idempotent upsert function
- [ ] `AnthropicService` class
- [ ] Manual entry endpoint
- [ ] Manual entry UI component
- [ ] Unit and integration tests

### Documentation
- [ ] Update `ROADMAP.md`
- [ ] Update `README.md` with Anthropic setup instructions
- [ ] Add troubleshooting section for Admin API keys

---

## 🚀 Getting Started

### Step 1: Checkout and Setup
```bash
git checkout main
git pull origin main
cd backend
pip install -r requirements.txt
flask db upgrade  # Apply existing migrations
```

### Step 2: Create Feature Branch
```bash
git checkout -b feature/phase2-anthropic-integration
```

### Step 3: Start with Migration
Begin with Task 1.1 (database migration) as all other tasks depend on it.

### Step 4: Implement in Order
Follow the task numbers sequentially for smooth integration.

---

## 📞 Questions?

If anything is unclear:
1. Check `docs/research-api-capabilities-2026.md` for API details
2. Review existing `OpenAIService` implementation as reference
3. Check Codex's handover for context on MVP state

---

**Good luck with Phase 2!** 🚀

**Next Handover**: After Phase 2 completion, document Groq/Perplexity API status for Phase 3 planning.
