# Phase 3: CSV/JSON Export System - Technical Specification

**Feature Priority**: P0 (Critical)  
**Estimated Effort**: 2 weeks  
**Sprint**: 3.1  
**Dependencies**: None

---

## 1. Problem Statement

### User Need
Users need to:
- Export usage data for external analysis (Excel, BI tools, accounting software)
- Archive historical cost data for compliance and auditing
- Share cost reports with stakeholders who don't have dashboard access
- Perform custom calculations and visualizations outside the platform
- Integrate AI cost data with existing financial reporting systems

### Current Limitation
All usage data is locked in the dashboard with no export functionality.

---

## 2. Best Practices

### Industry Standards

**CSV Format**[cite:6][cite:7]:
- UTF-8 encoding with BOM for Excel compatibility
- RFC 4180 compliant (quoted fields, escaped commas)
- Header row with descriptive column names
- ISO 8601 date format (YYYY-MM-DD)
- Consistent decimal precision (2 places for currency)
- Metadata header (export date, filters, totals)

**JSON Format**[cite:5][cite:7]:
- Structured hierarchy (metadata + data array)
- ISO 8601 timestamps
- Proper number types (not strings for numeric values)
- Pagination support for large datasets
- Clear schema documentation

**Performance**[cite:7]:
- Streaming response for datasets >10,000 records
- Server-side filtering to reduce payload
- Compression (gzip) for large files
- Async export jobs for very large datasets (>100k records)

---

## 3. Technology Options

### Backend Options

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Python `csv` module** | Native, simple, fast | Manual streaming setup | ✅ **Recommended for CSV** |
| **Pandas `to_csv()`** | Rich features, easy | High memory for large data | ❌ Too heavy |
| **Flask streaming response** | Memory efficient | More complex code | ✅ **Required for large datasets** |
| **Celery background jobs** | Handles huge exports | Adds infrastructure complexity | ⏳ Phase 4 if needed |

### Frontend Options

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Direct `<a download>` link** | Simple, browser native | No progress indication | ✅ **Recommended for MVP** |
| **Blob API + saveAs** | Progress tracking, client-side | More complex | ⏳ Phase 3.2 enhancement |
| **Preview modal before download** | User confirmation | Extra click | ✅ **Nice to have** |

---

## 4. Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────┐
│              Frontend (React)                          │
│  ┌──────────────────────────────────────────┐  │
│  │  ExportButton Component                    │  │
│  │  - Format selector (CSV/JSON)              │  │
│  │  - Date range picker                       │  │
│  │  - Service filter (optional)               │  │
│  │  - Download trigger                        │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                     │ HTTP GET
                     │ /api/usage/export?format=csv&start_date=...&end_date=...
                     ↓
┌─────────────────────────────────────────────────┐
│              Backend (Flask)                           │
│  ┌──────────────────────────────────────────┐  │
│  │  routes/usage.py                           │  │
│  │  @app.route('/api/usage/export')           │  │
│  │  - Validate auth & params                  │  │
│  │  - Query usage_records with filters        │  │
│  │  - Stream response via generator           │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  utils/export_generator.py                 │  │
│  │  - generate_csv() → yields rows          │  │
│  │  - generate_json() → yields chunks       │  │
│  │  - add_metadata()                          │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                     │
                     ↓ Query with filters
┌─────────────────────────────────────────────────┐
│              PostgreSQL                                │
│  usage_records table                                   │
│  - Indexed on (timestamp, account_id, service_id)      │
└─────────────────────────────────────────────────┘
```

---

## 5. API Design

### Endpoint: Export Usage Data

**Route**: `GET /api/usage/export`

**Authentication**: Required (JWT)

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | string | Yes | - | Export format: `csv` or `json` |
| `start_date` | date | No | 30 days ago | Start date (YYYY-MM-DD) |
| `end_date` | date | No | Today | End date (YYYY-MM-DD) |
| `service_id` | integer | No | All | Filter by specific service |
| `account_id` | integer | No | All user accounts | Filter by specific account |
| `source` | string | No | All | Filter by source: `api` or `manual` |

**Request Example**:
```http
GET /api/usage/export?format=csv&start_date=2026-01-01&end_date=2026-01-31&service_id=1
Authorization: Bearer <jwt_token>
```

**Response Headers**:
```
Content-Type: text/csv; charset=utf-8  (or application/json)
Content-Disposition: attachment; filename="ai-cost-tracker-export-2026-02-25.csv"
X-Total-Records: 1234
X-Export-Date: 2026-02-25T22:00:00Z
```

**CSV Response Example**:
```csv
# AI Cost Tracker Export
# Generated: 2026-02-25 22:00:00 UTC
# Date Range: 2026-01-01 to 2026-01-31
# Service: ChatGPT
# Total Records: 31
# Total Cost: $45.23

Date,Service,Account,Request Type,Tokens,Cost (USD),Source,Notes
2026-01-01,ChatGPT,My OpenAI Account,chat,150000,0.30,api,
2026-01-02,ChatGPT,My OpenAI Account,chat,180000,0.36,api,
2026-01-03,ChatGPT,My OpenAI Account,manual,0,5.00,manual,"Estimated usage for batch jobs"
```

**JSON Response Example**:
```json
{
  "metadata": {
    "export_date": "2026-02-25T22:00:00Z",
    "start_date": "2026-01-01",
    "end_date": "2026-01-31",
    "filters": {
      "service_id": 1,
      "service_name": "ChatGPT"
    },
    "total_records": 31,
    "total_cost": 45.23,
    "total_tokens": 4650000
  },
  "data": [
    {
      "date": "2026-01-01",
      "service_name": "ChatGPT",
      "account_name": "My OpenAI Account",
      "request_type": "chat",
      "tokens": 150000,
      "cost": 0.30,
      "source": "api",
      "notes": null,
      "created_at": "2026-01-02T03:00:00Z",
      "updated_at": "2026-01-02T03:00:00Z"
    }
  ]
}
```

**Error Responses**:

| Status | Error | Description |
|--------|-------|-------------|
| 400 | `INVALID_FORMAT` | Format must be 'csv' or 'json' |
| 400 | `INVALID_DATE_RANGE` | start_date must be before end_date |
| 400 | `DATE_RANGE_TOO_LARGE` | Max 1 year date range |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |
| 403 | `FORBIDDEN` | User doesn't own specified account |
| 404 | `NO_DATA` | No usage data in specified range |
| 429 | `RATE_LIMIT_EXCEEDED` | Max 10 exports per hour |

---

## 6. Backend Implementation

### File: `backend/utils/export_generator.py`

```python
import csv
import io
import json
from datetime import datetime
from typing import Generator, Dict, Any
from models import UsageRecord

def generate_csv(records: list[UsageRecord], metadata: Dict[str, Any]) -> Generator[str, None, None]:
    """
    Generate CSV export as streaming response.
    Yields rows one at a time for memory efficiency.
    """
    output = io.StringIO()
    
    # Write metadata header
    yield "# AI Cost Tracker Export\n"
    yield f"# Generated: {metadata['export_date']}\n"
    yield f"# Date Range: {metadata['start_date']} to {metadata['end_date']}\n"
    if metadata.get('service_name'):
        yield f"# Service: {metadata['service_name']}\n"
    yield f"# Total Records: {metadata['total_records']}\n"
    yield f"# Total Cost: ${metadata['total_cost']:.2f}\n"
    yield "\n"
    
    # Write CSV header
    writer = csv.writer(output)
    writer.writerow([
        'Date', 'Service', 'Account', 'Request Type', 
        'Tokens', 'Cost (USD)', 'Source', 'Notes'
    ])
    yield output.getvalue()
    output.truncate(0)
    output.seek(0)
    
    # Write data rows
    for record in records:
        writer.writerow([
            record.timestamp.strftime('%Y-%m-%d'),
            record.service.name,
            record.account.name,
            record.request_type,
            record.tokens or 0,
            f"{record.cost:.2f}",
            record.source,
            record.notes or ''
        ])
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

def generate_json(records: list[UsageRecord], metadata: Dict[str, Any]) -> Generator[str, None, None]:
    """
    Generate JSON export as streaming response.
    """
    # Opening brace and metadata
    yield '{'
    yield f'"metadata": {json.dumps(metadata)},'
    yield '"data": ['
    
    # Data records
    for i, record in enumerate(records):
        record_dict = {
            'date': record.timestamp.strftime('%Y-%m-%d'),
            'service_name': record.service.name,
            'account_name': record.account.name,
            'request_type': record.request_type,
            'tokens': record.tokens,
            'cost': float(record.cost),
            'source': record.source,
            'notes': record.notes,
            'created_at': record.created_at.isoformat() if record.created_at else None,
            'updated_at': record.updated_at.isoformat() if record.updated_at else None
        }
        
        if i > 0:
            yield ','
        yield json.dumps(record_dict)
    
    # Closing
    yield ']'
    yield '}'
```

### File: `backend/routes/usage.py` (add endpoint)

```python
from flask import Response, stream_with_context
from utils.export_generator import generate_csv, generate_json
from datetime import datetime, timedelta

@bp.route('/export', methods=['GET'])
@jwt_required()
def export_usage():
    """
    Export usage data in CSV or JSON format.
    Streams response for memory efficiency.
    """
    user_id = get_jwt_identity()
    
    # Parse and validate parameters
    export_format = request.args.get('format', '').lower()
    if export_format not in ['csv', 'json']:
        return jsonify({'error': 'INVALID_FORMAT', 'message': 'Format must be csv or json'}), 400
    
    # Date range (default to last 30 days)
    try:
        end_date = datetime.strptime(request.args.get('end_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
        start_date = datetime.strptime(request.args.get('start_date', (end_date - timedelta(days=30)).strftime('%Y-%m-%d')), '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'INVALID_DATE_RANGE', 'message': 'Dates must be YYYY-MM-DD format'}), 400
    
    if start_date > end_date:
        return jsonify({'error': 'INVALID_DATE_RANGE', 'message': 'start_date must be before end_date'}), 400
    
    if (end_date - start_date).days > 365:
        return jsonify({'error': 'DATE_RANGE_TOO_LARGE', 'message': 'Maximum date range is 1 year'}), 400
    
    # Build query
    query = UsageRecord.query.join(Account).filter(Account.user_id == user_id)
    query = query.filter(UsageRecord.timestamp >= start_date, UsageRecord.timestamp <= end_date)
    
    # Optional filters
    if service_id := request.args.get('service_id'):
        query = query.filter(UsageRecord.service_id == int(service_id))
    
    if account_id := request.args.get('account_id'):
        # Verify ownership
        account = Account.query.filter_by(id=int(account_id), user_id=user_id).first()
        if not account:
            return jsonify({'error': 'FORBIDDEN'}), 403
        query = query.filter(UsageRecord.account_id == int(account_id))
    
    if source := request.args.get('source'):
        if source in ['api', 'manual']:
            query = query.filter(UsageRecord.source == source)
    
    # Execute query
    records = query.order_by(UsageRecord.timestamp).all()
    
    if not records:
        return jsonify({'error': 'NO_DATA', 'message': 'No usage data in specified range'}), 404
    
    # Build metadata
    metadata = {
        'export_date': datetime.utcnow().isoformat() + 'Z',
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_records': len(records),
        'total_cost': float(sum(r.cost for r in records)),
        'total_tokens': sum(r.tokens or 0 for r in records)
    }
    
    # Generate filename
    filename = f"ai-cost-tracker-export-{datetime.now().strftime('%Y-%m-%d')}.{export_format}"
    
    # Stream response
    if export_format == 'csv':
        return Response(
            stream_with_context(generate_csv(records, metadata)),
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'X-Total-Records': str(metadata['total_records']),
                'X-Export-Date': metadata['export_date']
            }
        )
    else:  # json
        return Response(
            stream_with_context(generate_json(records, metadata)),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'X-Total-Records': str(metadata['total_records']),
                'X-Export-Date': metadata['export_date']
            }
        )
```

---

## 7. Frontend Implementation

### Component: `frontend/src/components/ExportButton.jsx`

```jsx
import React, { useState } from 'react';
import api from '../services/api';

const ExportButton = ({ serviceId = null, accountId = null }) => {
  const [isExporting, setIsExporting] = useState(false);
  const [format, setFormat] = useState('csv');
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });
  const [showModal, setShowModal] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const params = new URLSearchParams({
        format,
        start_date: dateRange.start,
        end_date: dateRange.end
      });
      
      if (serviceId) params.append('service_id', serviceId);
      if (accountId) params.append('account_id', accountId);
      
      const response = await fetch(`/api/usage/export?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      // Create download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai-cost-export-${dateRange.start}_${dateRange.end}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      setShowModal(false);
    } catch (error) {
      alert('Export failed: ' + error.message);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      <button 
        className="btn-primary"
        onClick={() => setShowModal(true)}
      >
        📊 Export Data
      </button>
      
      {showModal && (
        <div className="modal">
          <div className="modal-content">
            <h2>Export Usage Data</h2>
            
            <div className="form-group">
              <label>Format</label>
              <select value={format} onChange={(e) => setFormat(e.target.value)}>
                <option value="csv">CSV (Excel compatible)</option>
                <option value="json">JSON (Developer friendly)</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Start Date</label>
              <input 
                type="date" 
                value={dateRange.start}
                onChange={(e) => setDateRange({...dateRange, start: e.target.value})}
              />
            </div>
            
            <div className="form-group">
              <label>End Date</label>
              <input 
                type="date" 
                value={dateRange.end}
                onChange={(e) => setDateRange({...dateRange, end: e.target.value})}
              />
            </div>
            
            <div className="modal-actions">
              <button 
                className="btn-primary"
                onClick={handleExport}
                disabled={isExporting}
              >
                {isExporting ? 'Exporting...' : `Download ${format.toUpperCase()}`}
              </button>
              <button 
                className="btn-secondary"
                onClick={() => setShowModal(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ExportButton;
```

### Integration in Dashboard

**In `DashboardPage.jsx`**:
```jsx
import ExportButton from '../components/ExportButton';

// Add to dashboard header
<div className="dashboard-header">
  <h1>Dashboard</h1>
  <ExportButton />
</div>
```

---

## 8. Testing Strategy

### Unit Tests (`backend/tests/test_export.py`)

```python
def test_export_csv_format():
    """Test CSV export generates valid format"""
    records = [create_usage_record()]
    metadata = {'export_date': '2026-02-25', 'total_records': 1}
    
    csv_data = ''.join(generate_csv(records, metadata))
    
    assert 'Date,Service,Account' in csv_data
    assert records[0].service.name in csv_data
    assert csv_data.count('\n') >= 2  # Header + data

def test_export_requires_auth(client):
    """Test export endpoint requires authentication"""
    response = client.get('/api/usage/export?format=csv')
    assert response.status_code == 401

def test_export_invalid_format(client, auth_headers):
    """Test invalid format returns 400"""
    response = client.get('/api/usage/export?format=xml', headers=auth_headers)
    assert response.status_code == 400
    assert 'INVALID_FORMAT' in response.json['error']

def test_export_date_validation(client, auth_headers):
    """Test date range validation"""
    response = client.get(
        '/api/usage/export?format=csv&start_date=2026-12-31&end_date=2026-01-01',
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'INVALID_DATE_RANGE' in response.json['error']

def test_export_ownership_check(client, auth_headers, other_user_account):
    """Test users can only export their own data"""
    response = client.get(
        f'/api/usage/export?format=csv&account_id={other_user_account.id}',
        headers=auth_headers
    )
    assert response.status_code == 403
```

### Integration Tests

```python
def test_export_full_workflow(client, auth_headers, seed_usage_data):
    """Test complete export workflow"""
    response = client.get(
        '/api/usage/export?format=csv&start_date=2026-01-01&end_date=2026-01-31',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert 'attachment' in response.headers['Content-Disposition']
    
    csv_content = response.data.decode('utf-8')
    assert '# AI Cost Tracker Export' in csv_content
    assert 'Date,Service,Account' in csv_content
```

### Performance Tests

```python
import time

def test_export_large_dataset_performance():
    """Test export handles 50k records efficiently"""
    # Create 50k test records
    records = [create_usage_record() for _ in range(50000)]
    
    start_time = time.time()
    csv_gen = generate_csv(records, {})
    
    # Consume generator
    for _ in csv_gen:
        pass
    
    elapsed = time.time() - start_time
    assert elapsed < 5.0  # Should complete in <5 seconds
```

---

## 9. Implementation Effort

### Week 1: Backend
- Day 1-2: Create export_generator.py with CSV/JSON streaming
- Day 3-4: Add /api/usage/export endpoint with filtering
- Day 5: Unit tests and integration tests

### Week 2: Frontend & Polish
- Day 1-2: Build ExportButton component with modal
- Day 3: Integrate into Dashboard and Analytics pages
- Day 4: End-to-end testing
- Day 5: Documentation and code review

**Total**: 10 days (2 weeks)

---

## 10. Dependencies

### Required
- None (builds on existing infrastructure)

### Optional Enhancements (Phase 3.2+)
- Progress indicators for large exports
- Email delivery of exports for very large datasets
- Scheduled exports (daily/weekly/monthly)
- Export templates/presets

---

## 11. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Memory issues with large datasets** | High | Medium | Use streaming response, test with 100k records |
| **Excel encoding issues** | Medium | Low | Use UTF-8 with BOM, test with special characters |
| **Rate limit abuse** | Medium | Low | Implement rate limiting (10 exports/hour) |
| **Database performance** | Medium | Low | Add indexes on timestamp, optimize queries |
| **Browser download failures** | Low | Low | Add retry logic, fallback to blob API |

---

## 12. Success Criteria

- ✅ Users can export data in CSV and JSON formats
- ✅ Export handles >50,000 records without memory issues
- ✅ CSV files open correctly in Excel without encoding issues
- ✅ Export completes in <5 seconds for typical datasets (<10k records)
- ✅ Date range and service filtering works correctly
- ✅ Ownership validation prevents data leakage
- ✅ >80% code coverage for export functionality

---

**Status**: 📋 Specification Complete | Ready for Implementation
