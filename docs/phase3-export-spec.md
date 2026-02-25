# Phase 3: CSV/JSON Export System - Technical Specification

**Feature Priority**: P0 (Must Have)  
**Estimated Effort**: 2 weeks  
**Dependencies**: None  
**Target Sprint**: 3.1 (Weeks 1-2)

---

## 1. Problem Statement

### User Need
Users need to export their AI usage data for:
- External analysis in Excel, Google Sheets, or BI tools
- Compliance and audit requirements
- Integration with accounting/finance systems
- Backup and data portability
- Custom reporting outside the application

### Current Limitation
- No way to extract data from the system
- Users cannot perform offline analysis
- No data portability for users switching tools

### Business Value
- **High**: Most requested feature from Phase 2 feedback
- Enables enterprise adoption (compliance requirements)
- Increases user trust (no vendor lock-in)
- Reduces support burden (users self-serve data needs)

---

## 2. Best Practices & Standards

### CSV Export Standards

**Format Requirements**:
- UTF-8 encoding with BOM for Excel compatibility
- RFC 4180 compliant (proper quoting, escaping)
- Header row with descriptive column names
- ISO 8601 dates (YYYY-MM-DD)
- Decimal costs with 2 decimal places
- Proper line endings (\r\n for Windows compatibility)

**Example CSV Output**:
```csv
Date,Service,Account,Model,Tokens,Cost (USD),Source,Notes
2026-02-01,ChatGPT,Personal API,gpt-4,15000,0.45,api,
2026-02-02,ChatGPT,Personal API,gpt-4,22000,0.66,api,
2026-02-03,Groq,Development,llama-3-70b,50000,0.00,manual,Free tier usage
2026-02-04,Claude,Work Account,claude-opus-4,18000,0.90,api,
```

### JSON Export Standards

**Format Requirements**:
- JSON Lines format for streaming large datasets
- ISO 8601 timestamps with timezone
- Nested structure for metadata
- Proper data types (numbers, not strings)

**Example JSON Output**:
```json
{
  "metadata": {
    "exported_at": "2026-02-25T22:15:00Z",
    "filters": {
      "start_date": "2026-02-01",
      "end_date": "2026-02-25",
      "service_ids": [1, 2],
      "account_ids": [5]
    },
    "total_records": 245,
    "total_cost": 127.45,
    "total_tokens": 8450000
  },
  "records": [
    {
      "date": "2026-02-01",
      "service": "ChatGPT",
      "account": "Personal API",
      "model": "gpt-4",
      "tokens": 15000,
      "cost": 0.45,
      "source": "api",
      "notes": null,
      "created_at": "2026-02-01T08:30:00Z",
      "updated_at": "2026-02-01T08:30:00Z"
    }
  ]
}
```

### Streaming Best Practices

**Why Stream?**
- Avoid loading entire dataset into memory
- Support exports of 100k+ records
- Immediate download start (no waiting)
- Lower server resource usage

**Flask Streaming Pattern**:
```python
from flask import Response, stream_with_context
import csv
import io

def generate_csv():
    """Generator function for streaming CSV"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    
    # Write header
    writer.writerow(['Date', 'Service', 'Account', 'Tokens', 'Cost', 'Source'])
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)
    
    # Stream data rows
    for record in query_usage_records():
        writer.writerow([
            record.timestamp.strftime('%Y-%m-%d'),
            record.service.name,
            record.account.name,
            record.tokens,
            f"{record.cost:.2f}",
            record.source
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

@app.route('/api/usage/export')
@jwt_required()
def export_usage():
    return Response(
        stream_with_context(generate_csv()),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=usage_export.csv',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )
```

---

## 3. Technology Options

### CSV Generation Libraries

| Library | Pros | Cons | Recommendation |
|---------|------|------|----------------|
| **Python csv** | Built-in, RFC 4180 compliant, streaming | Manual encoding handling | ✅ Use this |
| **pandas.to_csv()** | Rich features, handles encoding | Loads all data into memory | ❌ Not for streaming |
| **csvwriter** | Third-party, advanced features | Extra dependency | ❌ Unnecessary |

**Verdict**: Use built-in `csv` module with streaming generator.

### JSON Generation Libraries

| Library | Pros | Cons | Recommendation |
|---------|------|------|----------------|
| **json** (built-in) | Standard, fast, streaming support | Manual serialization | ✅ Use this |
| **ujson** | Faster than json | Extra dependency, minor gains | ❌ Premature optimization |
| **orjson** | Fastest, native types | Extra dependency, Rust-based | ❌ Overkill |

**Verdict**: Use built-in `json` module.

---

## 4. Architecture

### System Design

```
┌─────────────────────────────────────────────────────┐
│          Frontend (React)                          │
│  ┌──────────────┐      ┌──────────────┐           │
│  │ Export Button│      │ Format Toggle│           │
│  │  📥 Download │      │  CSV | JSON  │           │
│  └──────┬───────┘      └──────┬───────┘           │
│         │                     │                    │
│         └──────────┬──────────┘                    │
│                    │ GET /api/usage/export         │
└────────────────────┼───────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────┐
│          Backend API (Flask)                      │
│  ┌──────────────────────────────────────────┐    │
│  │  export_usage() Route                    │    │
│  │  - Authenticate user (JWT)               │    │
│  │  - Validate filters                      │    │
│  │  - Query database (streaming)            │    │
│  │  - Generate CSV/JSON (streaming)         │    │
│  └──────────────┬───────────────────────────┘    │
└─────────────────┼─────────────────────────────────┘
                  │
┌─────────────────▼─────────────────────────────────┐
│          Database (PostgreSQL)                    │
│  SELECT * FROM usage_records                      │
│  WHERE account_id IN (user_accounts)              │
│    AND timestamp BETWEEN ? AND ?                  │
│  ORDER BY timestamp ASC                           │
└───────────────────────────────────────────────────┘
```

### Data Flow

1. **User Action**: Clicks "Export" button, selects format (CSV/JSON)
2. **Frontend**: Constructs URL with filters, initiates download
3. **Backend**: 
   - Authenticates user via JWT
   - Validates date range and filters
   - Queries database with streaming cursor
   - Generates CSV/JSON on-the-fly
   - Streams response chunks to client
4. **Browser**: Receives stream, saves as file

---

## 5. API Design

### Endpoint Specification

#### `GET /api/usage/export`

**Description**: Export usage data in CSV or JSON format

**Authentication**: Required (JWT)

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | string | No | `csv` | Export format: `csv` or `json` |
| `start_date` | date | No | 30 days ago | Start date (YYYY-MM-DD) |
| `end_date` | date | No | Today | End date (YYYY-MM-DD) |
| `service_id` | integer | No | All | Filter by service ID |
| `account_id` | integer | No | All user accounts | Filter by account ID |
| `source` | string | No | All | Filter by source: `api` or `manual` |

**Request Examples**:

```bash
# Export all data as CSV (default)
GET /api/usage/export

# Export specific date range as JSON
GET /api/usage/export?format=json&start_date=2026-01-01&end_date=2026-01-31

# Export only ChatGPT API data
GET /api/usage/export?service_id=1&source=api

# Export specific account
GET /api/usage/export?account_id=5&format=csv
```

**Response Headers**:

```http
Content-Type: text/csv (or application/json)
Content-Disposition: attachment; filename="usage_export_2026-02-25.csv"
X-Accel-Buffering: no
Cache-Control: no-cache
```

**Success Response** (200 OK):
- Streaming CSV or JSON data
- Filename includes export date

**Error Responses**:

```json
// 401 Unauthorized
{
  "error": "Missing or invalid JWT token"
}

// 400 Bad Request
{
  "error": "Invalid date format. Use YYYY-MM-DD"
}

// 403 Forbidden
{
  "error": "Access denied to account ID 10"
}

// 429 Too Many Requests
{
  "error": "Export rate limit exceeded. Try again in 5 minutes"
}
```

---

## 6. UI/UX Considerations

### Frontend Components

#### Export Button Component

**Location**: Dashboard page, Analytics page

**Design**:
```jsx
<div className="export-section">
  <button className="btn-primary" onClick={handleExport}>
    <DownloadIcon /> Export Data
  </button>
  
  <div className="export-options">
    <label>
      <input type="radio" name="format" value="csv" checked /> CSV
    </label>
    <label>
      <input type="radio" name="format" value="json" /> JSON
    </label>
  </div>
  
  <div className="export-filters">
    <DateRangePicker 
      startDate={startDate} 
      endDate={endDate}
      onChange={setDateRange}
    />
    <ServiceFilter 
      services={services}
      selected={selectedService}
      onChange={setSelectedService}
    />
  </div>
</div>
```

#### Export Progress Indicator

**For Large Exports** (>10k records):
- Show loading spinner during download
- Display estimated file size
- Cancel button (abort fetch)

```jsx
{isExporting && (
  <div className="export-progress">
    <Spinner />
    <p>Exporting {recordCount} records...</p>
    <button onClick={cancelExport}>Cancel</button>
  </div>
)}
```

#### Export Success Notification

```jsx
showNotification('success', `Exported ${recordCount} records to ${filename}`);
```

### API Client Implementation

```javascript
// frontend/src/services/api.js

export const exportUsage = async (filters = {}) => {
  const params = new URLSearchParams({
    format: filters.format || 'csv',
    start_date: filters.startDate || '',
    end_date: filters.endDate || '',
    service_id: filters.serviceId || '',
    account_id: filters.accountId || '',
    source: filters.source || ''
  });
  
  // Remove empty params
  for (const [key, value] of params.entries()) {
    if (!value) params.delete(key);
  }
  
  const response = await fetch(
    `${API_BASE_URL}/usage/export?${params.toString()}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Export failed');
  }
  
  // Trigger browser download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = getFilenameFromHeader(response) || 'usage_export.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
};

function getFilenameFromHeader(response) {
  const disposition = response.headers.get('Content-Disposition');
  if (!disposition) return null;
  const match = disposition.match(/filename="(.+)"/);
  return match ? match[1] : null;
}
```

---

## 7. Testing Strategy

### Unit Tests

```python
# backend/tests/test_export.py

import pytest
from io import StringIO
import csv
import json

def test_export_csv_format(client, auth_headers, sample_usage_data):
    """Test CSV export format and structure"""
    response = client.get(
        '/api/usage/export?format=csv',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    
    # Parse CSV
    reader = csv.DictReader(StringIO(response.data.decode('utf-8')))
    rows = list(reader)
    
    assert len(rows) > 0
    assert 'Date' in reader.fieldnames
    assert 'Cost (USD)' in reader.fieldnames

def test_export_json_format(client, auth_headers):
    """Test JSON export format and structure"""
    response = client.get(
        '/api/usage/export?format=json',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    
    data = json.loads(response.data)
    assert 'metadata' in data
    assert 'records' in data
    assert 'total_records' in data['metadata']

def test_export_date_filtering(client, auth_headers):
    """Test date range filtering"""
    response = client.get(
        '/api/usage/export?start_date=2026-02-01&end_date=2026-02-10',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    # Verify all records within date range

def test_export_authentication_required(client):
    """Test authentication requirement"""
    response = client.get('/api/usage/export')
    assert response.status_code == 401

def test_export_rate_limiting(client, auth_headers):
    """Test rate limiting (10 exports/hour)"""
    for i in range(11):
        response = client.get('/api/usage/export', headers=auth_headers)
        if i < 10:
            assert response.status_code == 200
        else:
            assert response.status_code == 429
```

### Integration Tests

```python
def test_export_large_dataset(client, auth_headers):
    """Test streaming with 50k records"""
    # Seed 50k records
    seed_large_dataset(50000)
    
    response = client.get('/api/usage/export', headers=auth_headers)
    assert response.status_code == 200
    
    # Verify complete export
    rows = list(csv.DictReader(StringIO(response.data.decode('utf-8'))))
    assert len(rows) == 50000

def test_export_ownership_isolation(client, auth_headers_user1, auth_headers_user2):
    """Test users only export their own data"""
    response1 = client.get('/api/usage/export', headers=auth_headers_user1)
    response2 = client.get('/api/usage/export', headers=auth_headers_user2)
    
    # Verify different data sets
    assert response1.data != response2.data
```

### Performance Tests

```python
import time

def test_export_streaming_performance(client, auth_headers):
    """Test streaming does not load entire dataset into memory"""
    seed_large_dataset(100000)
    
    start_time = time.time()
    response = client.get('/api/usage/export', headers=auth_headers)
    first_byte_time = time.time() - start_time
    
    # First byte should arrive quickly (streaming working)
    assert first_byte_time < 1.0  # Less than 1 second
```

---

## 8. Implementation Effort

### Time Breakdown

| Task | Effort | Notes |
|------|--------|-------|
| **Backend endpoint** | 2 days | CSV/JSON generation, streaming, filters |
| **Database query optimization** | 1 day | Indexes, query tuning |
| **Frontend UI** | 2 days | Export button, filters, progress indicator |
| **Testing** | 2 days | Unit, integration, performance tests |
| **Documentation** | 1 day | API docs, user guide |
| **Code review & QA** | 2 days | Review, bug fixes |

**Total**: 10 days (2 weeks)

### Acceptance Criteria

- ✅ Users can export data in CSV format
- ✅ Users can export data in JSON format
- ✅ Date range filtering works correctly
- ✅ Service/account filtering works correctly
- ✅ Streaming works for datasets >50k records
- ✅ Export completes in <5 seconds for <10k records
- ✅ Authentication enforced on all exports
- ✅ Rate limiting prevents abuse (10/hour)
- ✅ >80% test coverage maintained
- ✅ Documentation complete

---

## 9. Dependencies

### Python Packages
- `csv` (built-in)
- `json` (built-in)
- `flask` (existing)
- `flask-jwt-extended` (existing)
- `sqlalchemy` (existing)

**No new dependencies required** ✅

### Database Changes

**Add indexes for export performance**:

```sql
-- Optimize export queries
CREATE INDEX IF NOT EXISTS idx_usage_export 
ON usage_records(account_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_usage_service_export 
ON usage_records(service_id, timestamp DESC);
```

---

## 10. Risks & Mitigation

### Risk 1: Large Export Memory Issues
**Impact**: High  
**Probability**: Medium  
**Mitigation**: Use streaming generators, add export size limits (max 100k records per export)

### Risk 2: Export Abuse (Data Scraping)
**Impact**: Medium  
**Probability**: Low  
**Mitigation**: Rate limiting (10 exports/hour), authentication required, audit logging

### Risk 3: CSV Encoding Issues (Excel)
**Impact**: Medium  
**Probability**: Medium  
**Mitigation**: Use UTF-8 BOM, test with Excel on Windows/Mac, provide JSON alternative

### Risk 4: Performance Degradation
**Impact**: High  
**Probability**: Low  
**Mitigation**: Database indexes, query optimization, streaming, load testing

---

## 11. Future Enhancements (Post-Phase 3)

- **Scheduled exports**: Email CSV reports weekly/monthly
- **Export templates**: Save filter presets
- **Additional formats**: Excel (XLSX), PDF reports
- **Bulk exports**: All accounts, all time
- **API pagination**: For programmatic access
- **Export analytics**: Track which exports are most popular

---

**Status**: ✅ Ready for Implementation  
**Assigned To**: TBD  
**Sprint**: 3.1 (Weeks 1-2)
