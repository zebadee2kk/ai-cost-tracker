# Phase 3: CSV/JSON Export System - Technical Specification

**Created**: February 25, 2026  
**Priority**: P0 (Highest)  
**Effort**: 2 weeks  
**Dependencies**: None

---

## 1. Problem Statement

### Business Need
Users need to export their usage data for:
- External analysis in Excel, Python, R
- Backup and archival purposes
- Integration with billing/accounting systems
- Compliance and audit trails
- Custom reporting in BI tools

### Current Limitations
- No way to extract data from the system
- Users locked into web dashboard only
- Cannot perform offline analysis
- No data portability

### Success Criteria
- 60%+ user adoption of export feature
- Support datasets up to 100,000+ records
- Export completes in <30 seconds for typical datasets
- Zero data corruption or encoding issues

---

## 2. Feature Requirements

### Functional Requirements

#### Must Have (MVP)
- [x] Export all usage records to CSV format
- [x] Export all usage records to JSON format
- [x] Filter by date range (start_date, end_date)
- [x] Filter by service (e.g., only OpenAI data)
- [x] Filter by account (for multi-account users)
- [x] Include metadata (export timestamp, filters applied, totals)
- [x] Streaming for large datasets (>10,000 records)
- [x] Frontend download button with format selection
- [x] Progress indicator for large exports

#### Should Have (Phase 3.1)
- [ ] Filter by data source (API vs manual entries)
- [ ] Export with cost summaries at bottom
- [ ] Batch export (all accounts in one file)
- [ ] Email export link for very large datasets
- [ ] Export templates (daily/weekly/monthly presets)

#### Could Have (Phase 4)
- [ ] Scheduled automatic exports
- [ ] Export to Google Sheets/Excel Online
- [ ] Custom column selection
- [ ] Export in additional formats (XML, Parquet)

### Non-Functional Requirements
- **Performance**: <5 seconds for 10k records, <30s for 100k records
- **Memory**: <100MB RAM usage regardless of dataset size
- **Compatibility**: UTF-8 with BOM for Excel compatibility
- **Security**: Authentication required, rate limiting (10 exports/hour)
- **Reliability**: Graceful error handling, resumable downloads

---

## 3. Data Format Specifications

### CSV Format

#### Structure
```csv
Date,Service,Account,Request Type,Tokens,Cost (USD),Data Source,Notes
2026-02-01,ChatGPT,My OpenAI Account,completion,125000,0.25,api,
2026-02-01,Claude,My Anthropic Account,completion,80000,0.24,api,
2026-02-02,Groq,Groq Production,completion,50000,0.05,manual,"Entered from dashboard"
```

#### Field Specifications
| Field | Type | Format | Required | Description |
|-------|------|--------|----------|-------------|
| Date | Date | YYYY-MM-DD | Yes | Usage date (normalized to midnight UTC) |
| Service | String | Plain text | Yes | Service name (e.g., "ChatGPT", "Claude") |
| Account | String | Plain text | Yes | User-defined account name |
| Request Type | String | Enum | Yes | "completion", "embedding", "manual", etc. |
| Tokens | Integer | Numeric | No | Total tokens (input + output), null if unavailable |
| Cost (USD) | Decimal | 0.00 format | Yes | Cost in US dollars |
| Data Source | String | "api" or "manual" | Yes | How data was collected |
| Notes | String | Quoted text | No | User notes (manual entries only) |

#### Encoding
- **Character set**: UTF-8 with BOM (`\ufeff`) for Excel compatibility
- **Line endings**: CRLF (`\r\n`) for Windows compatibility
- **Quote character**: Double quotes (`"`)
- **Escape method**: Double-double quotes (`""`)
- **Delimiter**: Comma (`,`)

#### Metadata Footer (Optional)
```csv
# Export Metadata
# Generated: 2026-02-25T22:23:45Z
# Date Range: 2026-02-01 to 2026-02-25
# Total Records: 1,234
# Total Cost: $456.78
# Filters: service_id=1, account_id=3
```

---

### JSON Format

#### Structure
```json
{
  "export_metadata": {
    "generated_at": "2026-02-25T22:23:45Z",
    "date_range": {
      "start": "2026-02-01",
      "end": "2026-02-25"
    },
    "filters": {
      "service_id": 1,
      "account_id": 3
    },
    "total_records": 1234,
    "total_cost_usd": 456.78
  },
  "records": [
    {
      "date": "2026-02-01",
      "service": "ChatGPT",
      "account": "My OpenAI Account",
      "request_type": "completion",
      "tokens": 125000,
      "cost_usd": 0.25,
      "data_source": "api",
      "notes": null,
      "metadata": {
        "model": "gpt-4o",
        "created_at": "2026-02-01T12:34:56Z"
      }
    },
    {
      "date": "2026-02-02",
      "service": "Groq",
      "account": "Groq Production",
      "request_type": "manual",
      "tokens": 50000,
      "cost_usd": 0.05,
      "data_source": "manual",
      "notes": "Entered from dashboard",
      "metadata": {}
    }
  ]
}
```

#### Field Types
- Dates: ISO 8601 strings (`YYYY-MM-DD`)
- Timestamps: ISO 8601 with timezone (`YYYY-MM-DDTHH:MM:SSZ`)
- Numbers: Native JSON numbers (no quotes)
- Nulls: JSON `null` (not empty strings)

---

## 4. API Specification

### Endpoint

```
GET /api/usage/export
```

### Authentication
- Requires JWT token in `Authorization: Bearer <token>` header
- Only exports data for authenticated user's accounts

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | Enum | No | `csv` | Export format: `csv` or `json` |
| `start_date` | Date | No | 30 days ago | Start of date range (YYYY-MM-DD) |
| `end_date` | Date | No | Today | End of date range (YYYY-MM-DD) |
| `service_id` | Integer | No | All | Filter by specific service |
| `account_id` | Integer | No | All | Filter by specific account |
| `source` | Enum | No | All | Filter by data source: `api`, `manual`, or `all` |

### Request Examples

```bash
# Export all data as CSV (default)
GET /api/usage/export

# Export specific date range as JSON
GET /api/usage/export?format=json&start_date=2026-02-01&end_date=2026-02-25

# Export only OpenAI data
GET /api/usage/export?service_id=1&format=csv

# Export only manual entries
GET /api/usage/export?source=manual
```

### Response Headers

```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="usage_export_2026-02-25.csv"
X-Accel-Buffering: no
Transfer-Encoding: chunked
```

### Response Codes

| Code | Description |
|------|-------------|
| 200 | Success - streaming export |
| 400 | Invalid parameters (bad date format, invalid service_id) |
| 401 | Unauthorized (missing or invalid JWT) |
| 403 | Forbidden (account_id belongs to another user) |
| 429 | Too many requests (rate limit exceeded) |
| 500 | Server error |

### Error Response (JSON)

```json
{
  "error": "Invalid date format",
  "message": "start_date must be in YYYY-MM-DD format",
  "code": "INVALID_DATE_FORMAT"
}
```

---

## 5. Backend Implementation

### Technology Stack
- **Language**: Python 3.10+
- **Framework**: Flask 3.0
- **Database**: PostgreSQL (production), SQLite (dev)
- **Libraries**: 
  - `csv` (stdlib) for CSV generation
  - `json` (stdlib) for JSON generation
  - `io.StringIO` for in-memory buffering

### Streaming Architecture

#### Why Streaming?
- Prevents memory exhaustion with large datasets
- Enables progressive download (user sees progress)
- Reduces time-to-first-byte
- Handles 100k+ records efficiently

#### Implementation Pattern

```python
from flask import Response, stream_with_context, jsonify
from io import StringIO
import csv
from datetime import datetime

@app.route('/api/usage/export', methods=['GET'])
@jwt_required()
def export_usage():
    # Validate parameters
    format_type = request.args.get('format', 'csv').lower()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    service_id = request.args.get('service_id', type=int)
    account_id = request.args.get('account_id', type=int)
    source = request.args.get('source', 'all')
    
    # Validate date format
    try:
        if start_date:
            datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400
    
    # Check ownership of account_id
    current_user_id = get_jwt_identity()
    if account_id:
        account = Account.query.get(account_id)
        if not account or account.user_id != current_user_id:
            return jsonify({"error": "Forbidden"}), 403
    
    # Generate filename
    timestamp = datetime.utcnow().strftime('%Y-%m-%d')
    filename = f"usage_export_{timestamp}.{format_type}"
    
    # Route to appropriate generator
    if format_type == 'csv':
        return Response(
            stream_with_context(generate_csv(current_user_id, start_date, end_date, service_id, account_id, source)),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'X-Accel-Buffering': 'no'
            }
        )
    elif format_type == 'json':
        return Response(
            stream_with_context(generate_json(current_user_id, start_date, end_date, service_id, account_id, source)),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'X-Accel-Buffering': 'no'
            }
        )
    else:
        return jsonify({"error": "Invalid format"}), 400


def generate_csv(user_id, start_date, end_date, service_id, account_id, source):
    """Stream CSV export with minimal memory footprint."""
    buf = StringIO()
    writer = csv.writer(buf)
    
    # UTF-8 BOM for Excel compatibility
    yield '\ufeff'
    
    # Header row
    writer.writerow(['Date', 'Service', 'Account', 'Request Type', 'Tokens', 'Cost (USD)', 'Data Source', 'Notes'])
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)
    
    # Query and stream data
    query = build_export_query(user_id, start_date, end_date, service_id, account_id, source)
    
    total_cost = 0
    record_count = 0
    
    for record in query.yield_per(1000):  # Batch size for DB cursor
        writer.writerow([
            record.timestamp.strftime('%Y-%m-%d'),
            record.service.name,
            record.account.name,
            record.request_type,
            record.total_tokens or '',
            f"{record.cost:.2f}",
            record.source,
            record.notes or ''
        ])
        
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        
        total_cost += float(record.cost)
        record_count += 1
    
    # Metadata footer
    writer.writerow([])
    writer.writerow(['# Export Metadata'])
    writer.writerow(['# Generated', datetime.utcnow().isoformat() + 'Z'])
    writer.writerow(['# Total Records', record_count])
    writer.writerow(['# Total Cost (USD)', f"{total_cost:.2f}"])
    
    yield buf.getvalue()


def generate_json(user_id, start_date, end_date, service_id, account_id, source):
    """Stream JSON export."""
    import json
    
    # Opening structure
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + 'Z',
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "filters": {
            "service_id": service_id,
            "account_id": account_id,
            "source": source
        }
    }
    
    yield '{\n  "export_metadata": '
    yield json.dumps(metadata, indent=2)
    yield ',\n  "records": [\n'
    
    # Stream records
    query = build_export_query(user_id, start_date, end_date, service_id, account_id, source)
    
    first = True
    for record in query.yield_per(1000):
        if not first:
            yield ',\n'
        first = False
        
        record_dict = {
            "date": record.timestamp.strftime('%Y-%m-%d'),
            "service": record.service.name,
            "account": record.account.name,
            "request_type": record.request_type,
            "tokens": record.total_tokens,
            "cost_usd": float(record.cost),
            "data_source": record.source,
            "notes": record.notes,
            "metadata": {}
        }
        
        yield '    ' + json.dumps(record_dict)
    
    # Closing structure
    yield '\n  ]\n}'


def build_export_query(user_id, start_date, end_date, service_id, account_id, source):
    """Build SQLAlchemy query with filters."""
    query = UsageRecord.query.join(Account).join(Service).filter(Account.user_id == user_id)
    
    if start_date:
        query = query.filter(UsageRecord.timestamp >= start_date)
    if end_date:
        query = query.filter(UsageRecord.timestamp <= end_date)
    if service_id:
        query = query.filter(UsageRecord.service_id == service_id)
    if account_id:
        query = query.filter(UsageRecord.account_id == account_id)
    if source != 'all':
        query = query.filter(UsageRecord.source == source)
    
    return query.order_by(UsageRecord.timestamp.asc())
```

### Database Optimization

#### Index Creation
```sql
-- Speed up export queries
CREATE INDEX idx_usage_records_export 
ON usage_records(account_id, timestamp, service_id, source);

-- Cover query for common exports
CREATE INDEX idx_usage_records_covering 
ON usage_records(account_id, timestamp, service_id, source) 
INCLUDE (total_tokens, cost, request_type, notes);
```

#### Query Performance
- Use `yield_per(1000)` for cursor-based fetching
- Avoid loading all records into memory
- Eager load relationships (`joinedload(Service, Account)`)

---

## 6. Frontend Implementation

### UI Design

#### Download Button Component

```jsx
// ExportButton.jsx
import React, { useState } from 'react';
import axios from 'axios';

const ExportButton = ({ filters }) => {
  const [format, setFormat] = useState('csv');
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const handleExport = async () => {
    setIsExporting(true);
    setProgress(0);
    
    const params = new URLSearchParams({
      format,
      ...filters
    });
    
    try {
      const response = await axios.get(`/api/usage/export?${params}`, {
        responseType: 'blob',
        onDownloadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(percentCompleted);
          }
        }
      });
      
      // Trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `usage_export_${new Date().toISOString().split('T')[0]}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      setIsExporting(false);
      setProgress(0);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
      setIsExporting(false);
      setProgress(0);
    }
  };
  
  return (
    <div className="export-controls">
      <select value={format} onChange={(e) => setFormat(e.target.value)} disabled={isExporting}>
        <option value="csv">CSV (Excel)</option>
        <option value="json">JSON</option>
      </select>
      
      <button onClick={handleExport} disabled={isExporting}>
        {isExporting ? `Exporting... ${progress}%` : '⬇️ Export Data'}
      </button>
      
      {isExporting && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }}></div>
        </div>
      )}
    </div>
  );
};

export default ExportButton;
```

#### Integration into Dashboard

```jsx
// DashboardPage.jsx
import ExportButton from '../components/ExportButton';

function DashboardPage() {
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    service_id: null,
    account_id: null
  });
  
  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Usage Dashboard</h1>
        <ExportButton filters={filters} />
      </div>
      
      {/* Rest of dashboard */}
    </div>
  );
}
```

### CSS Styling

```css
.export-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.export-controls select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.export-controls button {
  padding: 8px 16px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.export-controls button:hover:not(:disabled) {
  background: #1976D2;
}

.export-controls button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.progress-bar {
  width: 200px;
  height: 4px;
  background: #eee;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #2196F3;
  transition: width 0.3s ease;
}
```

---

## 7. Testing Strategy

### Unit Tests

```python
# tests/test_export.py
import pytest
from io import StringIO
import csv
import json

def test_csv_export_formatting(client, auth_headers):
    """Test CSV export has correct format."""
    response = client.get('/api/usage/export?format=csv', headers=auth_headers)
    
    assert response.status_code == 200
    assert response.content_type == 'text/csv; charset=utf-8'
    assert 'attachment' in response.headers['Content-Disposition']
    
    # Parse CSV
    content = response.data.decode('utf-8-sig')  # Remove BOM
    reader = csv.DictReader(StringIO(content))
    
    rows = list(reader)
    assert len(rows) > 0
    assert 'Date' in rows[0]
    assert 'Cost (USD)' in rows[0]

def test_json_export_structure(client, auth_headers):
    """Test JSON export has correct structure."""
    response = client.get('/api/usage/export?format=json', headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert 'export_metadata' in data
    assert 'records' in data
    assert 'generated_at' in data['export_metadata']
    assert isinstance(data['records'], list)

def test_date_range_filtering(client, auth_headers):
    """Test date range filter works."""
    response = client.get(
        '/api/usage/export?start_date=2026-02-01&end_date=2026-02-15',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    # Verify all records are within range

def test_invalid_date_format(client, auth_headers):
    """Test invalid date format returns 400."""
    response = client.get('/api/usage/export?start_date=02/01/2026', headers=auth_headers)
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_unauthorized_export(client):
    """Test export requires authentication."""
    response = client.get('/api/usage/export')
    assert response.status_code == 401

def test_forbidden_account_access(client, auth_headers, other_user_account_id):
    """Test cannot export another user's account data."""
    response = client.get(
        f'/api/usage/export?account_id={other_user_account_id}',
        headers=auth_headers
    )
    assert response.status_code == 403
```

### Integration Tests

```python
def test_large_dataset_export(client, auth_headers):
    """Test exporting 50,000 records completes successfully."""
    # Seed 50k records
    seed_usage_records(count=50000)
    
    response = client.get('/api/usage/export?format=csv', headers=auth_headers)
    
    assert response.status_code == 200
    
    # Verify record count
    content = response.data.decode('utf-8-sig')
    row_count = content.count('\n') - 1  # Exclude header
    assert row_count == 50000
```

### Performance Tests

```python
def test_export_performance(client, auth_headers):
    """Test export completes within time limits."""
    import time
    
    seed_usage_records(count=10000)
    
    start = time.time()
    response = client.get('/api/usage/export', headers=auth_headers)
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 5.0  # Must complete in <5 seconds for 10k records
```

---

## 8. Security Considerations

### Authentication & Authorization
- JWT token required for all export requests
- Verify user owns the account_id being exported
- Log all export actions with user_id, timestamp, filters

### Rate Limiting
```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=get_jwt_identity,
    default_limits=["10 per hour"]  # Max 10 exports per hour
)

@app.route('/api/usage/export')
@limiter.limit("10 per hour")
def export_usage():
    # ...
```

### Data Redaction (Optional)
- Optionally redact API keys (show last 4 chars only)
- Redact user email addresses in exports
- Flag sensitive fields in JSON metadata

### Input Validation
- Sanitize all query parameters
- Validate date formats strictly
- Check service_id/account_id exist and are accessible
- Prevent SQL injection via parameterized queries

---

## 9. Monitoring & Logging

### Metrics to Track
- Export requests per day
- Export format distribution (CSV vs JSON)
- Average export size (record count)
- Export duration (p50, p95, p99)
- Error rate by error type
- Rate limit hits

### Logging

```python
import logging

logger = logging.getLogger(__name__)

@app.route('/api/usage/export')
def export_usage():
    user_id = get_jwt_identity()
    
    logger.info(f"Export started", extra={
        "user_id": user_id,
        "format": request.args.get('format'),
        "filters": dict(request.args)
    })
    
    try:
        # Generate export
        result = generate_export()
        
        logger.info(f"Export completed", extra={
            "user_id": user_id,
            "record_count": result.record_count,
            "duration_ms": result.duration
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Export failed", extra={
            "user_id": user_id,
            "error": str(e)
        }, exc_info=True)
        raise
```

---

## 10. Implementation Checklist

### Week 1: Backend Implementation
- [ ] Create `/api/usage/export` endpoint
- [ ] Implement CSV streaming generator
- [ ] Implement JSON streaming generator
- [ ] Add query parameter validation
- [ ] Add rate limiting
- [ ] Create database indexes for export queries
- [ ] Write unit tests (15+ tests)
- [ ] Write integration tests (5+ tests)
- [ ] Performance test with 50k records

### Week 2: Frontend & Polish
- [ ] Create `ExportButton` component
- [ ] Integrate into DashboardPage
- [ ] Add progress indicator UI
- [ ] Add error handling and user feedback
- [ ] Test in all browsers (Chrome, Firefox, Safari, Edge)
- [ ] Test large file downloads (>50MB)
- [ ] Write frontend tests (Jest/React Testing Library)
- [ ] Update documentation
- [ ] Create user guide with screenshots
- [ ] Deploy to staging for QA testing

---

## 11. Success Metrics

### Adoption Metrics (30 days post-launch)
- **Target**: 60% of active users export data at least once
- **Measurement**: Track unique users calling `/api/usage/export`

### Performance Metrics
- **Target**: 95th percentile export time <30s for typical datasets
- **Measurement**: Log export durations, calculate p95

### Quality Metrics
- **Target**: <1% error rate on export requests
- **Measurement**: Track 4xx and 5xx responses

### User Satisfaction
- **Target**: <5 support tickets related to export feature per month
- **Measurement**: Tag support tickets in help desk

---

## 12. Future Enhancements (Phase 4+)

### Scheduled Exports
- Cron-like scheduling (daily/weekly/monthly)
- Email delivery of exports
- Export to cloud storage (S3, Google Drive)

### Advanced Filtering
- Export by model (e.g., only GPT-4 usage)
- Export by cost threshold (records > $1.00)
- Custom column selection

### Additional Formats
- Excel (.xlsx) with formatting and formulas
- Parquet for data science workflows
- SQL dump for database migration

### Export Templates
- Predefined "recipes" (e.g., "Monthly Finance Report")
- Save custom filter combinations
- Share templates with team members

---

**Document Status**: ✅ Complete  
**Ready for Implementation**: Yes  
**Estimated Effort**: 2 weeks (1 backend, 1 frontend)  
**Dependencies**: None  
**Risks**: None identified
