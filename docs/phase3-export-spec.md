# Phase 3: CSV/JSON Export System Specification

**Created**: February 25, 2026  
**Status**: 📋 Specification Complete  
**Priority**: P1 (High Impact, Medium Effort)

---

## 1. Problem Statement

### Current Limitations
- Users cannot extract usage data for external analysis
- No way to import data into spreadsheets, BI tools, or data warehouses
- Reporting limited to dashboard visualizations
- Compliance/audit requirements may need raw data export

### User Stories
- **As a developer**, I want to export my AI usage data to CSV so I can analyze it in Excel/Google Sheets
- **As a finance manager**, I want to export cost data in JSON so I can integrate it with our internal reporting tools
- **As a compliance officer**, I want to export historical records for audit purposes
- **As a data analyst**, I want to filter exports by date range and service for targeted analysis

---

## 2. Feature Requirements

### Functional Requirements

#### Must Have (MVP)
- [x] Export usage records in CSV format
- [x] Export usage records in JSON format
- [x] Filter by date range (start_date, end_date)
- [x] Filter by service (optional)
- [x] Filter by account (optional)
- [x] Include all usage record fields
- [x] Proper filename with timestamp
- [x] Download button in dashboard UI

#### Should Have
- [x] Streaming response for large datasets
- [x] Progress indicator for large exports
- [x] Export format preview before download
- [x] Remember last export preferences
- [x] Export metadata (generated timestamp, filters applied)

#### Could Have
- [ ] Schedule recurring exports (Phase 4)
- [ ] Export to cloud storage (S3, GCS)
- [ ] Custom field selection
- [ ] Multiple format export (CSV + JSON in ZIP)

---

## 3. API Design

### Endpoint Specification

```http
GET /api/usage/export
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | string | Yes | - | Export format: `csv` or `json` |
| `start_date` | string | No | 30 days ago | ISO 8601 date (YYYY-MM-DD) |
| `end_date` | string | No | today | ISO 8601 date (YYYY-MM-DD) |
| `service_id` | integer | No | - | Filter by specific service |
| `account_id` | integer | No | - | Filter by specific account |
| `include_manual` | boolean | No | true | Include manual entries |
| `include_api` | boolean | No | true | Include API-synced entries |

### Request Examples

```bash
# Export all usage data as CSV
GET /api/usage/export?format=csv

# Export specific date range as JSON
GET /api/usage/export?format=json&start_date=2026-01-01&end_date=2026-01-31

# Export only OpenAI data for specific account
GET /api/usage/export?format=csv&service_id=1&account_id=5

# Export only API-synced data (exclude manual entries)
GET /api/usage/export?format=json&include_manual=false
```

### Response Headers

```http
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="ai-cost-tracker-export-2026-02-25T21-00-00Z.csv"
X-Export-Records: 1523
X-Export-Date-Range: 2026-01-01/2026-02-25
```

### CSV Format Specification

```csv
id,account_id,account_name,service_id,service_name,timestamp,tokens,cost,request_type,source,metadata,created_at,updated_at
1,5,"OpenAI Production",1,"ChatGPT",2026-02-25,150000,0.45,"chat.completions","api","{\"model\":\"gpt-4o\"}",2026-02-25T10:00:00Z,2026-02-25T10:00:00Z
2,5,"OpenAI Production",1,"ChatGPT",2026-02-24,120000,0.36,"chat.completions","api","{\"model\":\"gpt-4o\"}",2026-02-24T10:00:00Z,2026-02-24T10:00:00Z
3,7,"Groq Development",3,"Groq",2026-02-25,0,2.50,"manual","manual","null",2026-02-25T14:30:00Z,2026-02-25T14:30:00Z
```

**CSV Formatting Rules**:
- Header row with column names
- Quote strings containing commas or quotes
- Use UTF-8 encoding
- Line endings: `\r\n` (Windows) or `\n` (Unix)
- Empty/null values: empty string
- JSON metadata: escaped and quoted

### JSON Format Specification

```json
{
  "export_metadata": {
    "generated_at": "2026-02-25T21:00:00Z",
    "filters": {
      "start_date": "2026-01-01",
      "end_date": "2026-02-25",
      "service_id": null,
      "account_id": null,
      "include_manual": true,
      "include_api": true
    },
    "total_records": 1523,
    "format_version": "1.0"
  },
  "data": [
    {
      "id": 1,
      "account": {
        "id": 5,
        "name": "OpenAI Production"
      },
      "service": {
        "id": 1,
        "name": "ChatGPT"
      },
      "timestamp": "2026-02-25T00:00:00Z",
      "tokens": 150000,
      "cost": 0.45,
      "request_type": "chat.completions",
      "source": "api",
      "metadata": {
        "model": "gpt-4o"
      },
      "created_at": "2026-02-25T10:00:00Z",
      "updated_at": "2026-02-25T10:00:00Z"
    }
  ]
}
```

**JSON Structure**:
- Root object with `export_metadata` and `data` array
- Nested objects for account and service details
- ISO 8601 timestamps
- Numeric values as numbers (not strings)
- Null values as `null` (not strings)

---

## 4. Backend Implementation

### File Structure

```
backend/
├── routes/
│   └── usage.py                    # Add export endpoint
├── services/
│   └── export_service.py           # NEW: Export logic
└── tests/
    └── test_export_service.py      # NEW: Export tests
```

### Core Logic (`services/export_service.py`)

```python
import csv
import json
from io import StringIO
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import Response, stream_with_context
from sqlalchemy import and_

from models import UsageRecord, Account, Service
from extensions import db

class ExportService:
    """Service for exporting usage data in various formats."""
    
    CHUNK_SIZE = 1000  # Records per chunk for streaming
    
    @staticmethod
    def export_usage(
        user_id: int,
        format: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        service_id: Optional[int] = None,
        account_id: Optional[int] = None,
        include_manual: bool = True,
        include_api: bool = True
    ) -> Response:
        """Export usage records in specified format.
        
        Args:
            user_id: User ID (for ownership check)
            format: 'csv' or 'json'
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            service_id: Optional service filter
            account_id: Optional account filter
            include_manual: Include manual entries
            include_api: Include API-synced entries
            
        Returns:
            Flask Response with streaming data
        """
        # Build query
        query = db.session.query(
            UsageRecord, Account.name.label('account_name'), 
            Service.name.label('service_name')
        ).join(Account).join(Service).filter(
            Account.user_id == user_id
        )
        
        # Apply filters
        if start_date:
            query = query.filter(UsageRecord.timestamp >= start_date)
        else:
            query = query.filter(
                UsageRecord.timestamp >= datetime.utcnow() - timedelta(days=30)
            )
            
        if end_date:
            query = query.filter(UsageRecord.timestamp <= end_date)
        
        if service_id:
            query = query.filter(UsageRecord.service_id == service_id)
            
        if account_id:
            query = query.filter(UsageRecord.account_id == account_id)
        
        # Source filters
        source_filters = []
        if include_manual:
            source_filters.append(UsageRecord.source == 'manual')
        if include_api:
            source_filters.append(UsageRecord.source == 'api')
        if source_filters:
            query = query.filter(db.or_(*source_filters))
        
        query = query.order_by(UsageRecord.timestamp.desc())
        
        # Generate response based on format
        if format == 'csv':
            return ExportService._export_csv(query, start_date, end_date)
        elif format == 'json':
            return ExportService._export_json(
                query, start_date, end_date, service_id, 
                account_id, include_manual, include_api
            )
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def _export_csv(query, start_date, end_date) -> Response:
        """Stream CSV export."""
        def generate():
            # CSV header
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow([
                'id', 'account_id', 'account_name', 'service_id', 
                'service_name', 'timestamp', 'tokens', 'cost', 
                'request_type', 'source', 'metadata', 
                'created_at', 'updated_at'
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            
            # Stream records in chunks
            offset = 0
            while True:
                chunk = query.offset(offset).limit(
                    ExportService.CHUNK_SIZE
                ).all()
                
                if not chunk:
                    break
                    
                for record, account_name, service_name in chunk:
                    writer.writerow([
                        record.id,
                        record.account_id,
                        account_name,
                        record.service_id,
                        service_name,
                        record.timestamp.isoformat(),
                        record.tokens or 0,
                        float(record.cost) if record.cost else 0.0,
                        record.request_type or '',
                        record.source,
                        json.dumps(record.metadata) if record.metadata else '',
                        record.created_at.isoformat(),
                        record.updated_at.isoformat() if record.updated_at else ''
                    ])
                    
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)
                offset += ExportService.CHUNK_SIZE
        
        filename = ExportService._generate_filename('csv', start_date, end_date)
        return Response(
            stream_with_context(generate()),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    
    @staticmethod
    def _export_json(query, start_date, end_date, service_id, 
                     account_id, include_manual, include_api) -> Response:
        """Stream JSON export."""
        def generate():
            # JSON header with metadata
            total_records = query.count()
            metadata = {
                "export_metadata": {
                    "generated_at": datetime.utcnow().isoformat() + 'Z',
                    "filters": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "service_id": service_id,
                        "account_id": account_id,
                        "include_manual": include_manual,
                        "include_api": include_api
                    },
                    "total_records": total_records,
                    "format_version": "1.0"
                },
                "data": [
            }
            yield json.dumps(metadata)[:-2]  # Remove closing ']'
            
            # Stream records
            offset = 0
            first = True
            while True:
                chunk = query.offset(offset).limit(
                    ExportService.CHUNK_SIZE
                ).all()
                
                if not chunk:
                    break
                    
                for record, account_name, service_name in chunk:
                    if not first:
                        yield ','
                    first = False
                    
                    yield json.dumps({
                        "id": record.id,
                        "account": {
                            "id": record.account_id,
                            "name": account_name
                        },
                        "service": {
                            "id": record.service_id,
                            "name": service_name
                        },
                        "timestamp": record.timestamp.isoformat() + 'Z',
                        "tokens": record.tokens or 0,
                        "cost": float(record.cost) if record.cost else 0.0,
                        "request_type": record.request_type or '',
                        "source": record.source,
                        "metadata": record.metadata,
                        "created_at": record.created_at.isoformat() + 'Z',
                        "updated_at": record.updated_at.isoformat() + 'Z' if record.updated_at else None
                    })
                    
                offset += ExportService.CHUNK_SIZE
            
            yield ']}'  # Close data array and root object
        
        filename = ExportService._generate_filename('json', start_date, end_date)
        return Response(
            stream_with_context(generate()),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    
    @staticmethod
    def _generate_filename(format: str, start_date: str, end_date: str) -> str:
        """Generate export filename with timestamp."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')
        date_range = ''
        if start_date and end_date:
            date_range = f'-{start_date}-to-{end_date}'
        return f'ai-cost-tracker-export{date_range}-{timestamp}.{format}'
```

### Route Handler (`routes/usage.py`)

```python
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.export_service import ExportService

@usage_bp.route('/export', methods=['GET'])
@jwt_required()
def export_usage():
    """Export usage data in CSV or JSON format."""
    user_id = get_jwt_identity()
    
    # Validate format
    format = request.args.get('format', '').lower()
    if format not in ['csv', 'json']:
        return jsonify({
            'error': 'Invalid format. Must be "csv" or "json".'
        }), 400
    
    # Parse filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    service_id = request.args.get('service_id', type=int)
    account_id = request.args.get('account_id', type=int)
    include_manual = request.args.get('include_manual', 'true').lower() == 'true'
    include_api = request.args.get('include_api', 'true').lower() == 'true'
    
    try:
        return ExportService.export_usage(
            user_id=user_id,
            format=format,
            start_date=start_date,
            end_date=end_date,
            service_id=service_id,
            account_id=account_id,
            include_manual=include_manual,
            include_api=include_api
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 5. Frontend Implementation

### Export Modal Component (`frontend/src/components/ExportModal.jsx`)

```jsx
import React, { useState } from 'react';
import api from '../services/api';
import './ExportModal.css';

const ExportModal = ({ onClose }) => {
  const [format, setFormat] = useState('csv');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [includeManual, setIncludeManual] = useState(true);
  const [includeApi, setIncludeApi] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleExport = async () => {
    setLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams({
        format,
        include_manual: includeManual,
        include_api: includeApi
      });
      
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const response = await api.get(`/api/usage/export?${params}`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Get filename from Content-Disposition header
      const contentDisposition = response.headers['content-disposition'];
      const filename = contentDisposition
        ? contentDisposition.split('filename="')[1].split('"')[0]
        : `export-${Date.now()}.${format}`;
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      onClose();
    } catch (err) {
      setError(err.response?.data?.error || 'Export failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Export Usage Data</h2>
        
        <div className="form-group">
          <label>Format</label>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="csv">CSV (Excel, Google Sheets)</option>
            <option value="json">JSON (APIs, databases)</option>
          </select>
        </div>
        
        <div className="form-group">
          <label>Date Range (optional)</label>
          <div className="date-range">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              placeholder="Start date"
            />
            <span>to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              placeholder="End date"
            />
          </div>
          <small>Leave empty to export last 30 days</small>
        </div>
        
        <div className="form-group">
          <label>Data Sources</label>
          <div className="checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={includeApi}
                onChange={(e) => setIncludeApi(e.target.checked)}
              />
              API-synced data
            </label>
            <label>
              <input
                type="checkbox"
                checked={includeManual}
                onChange={(e) => setIncludeManual(e.target.checked)}
              />
              Manual entries
            </label>
          </div>
        </div>
        
        {error && <div className="error-message">{error}</div>}
        
        <div className="modal-actions">
          <button onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button 
            onClick={handleExport} 
            disabled={loading || (!includeApi && !includeManual)}
            className="btn-primary"
          >
            {loading ? 'Exporting...' : `Export ${format.toUpperCase()}`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportModal;
```

### Integration into Dashboard

```jsx
// In DashboardPage.jsx or AnalyticsPage.jsx
import ExportModal from '../components/ExportModal';

const DashboardPage = () => {
  const [showExportModal, setShowExportModal] = useState(false);
  
  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <button 
          className="btn-secondary"
          onClick={() => setShowExportModal(true)}
        >
          ⬇️ Export Data
        </button>
      </div>
      
      {/* Dashboard content */}
      
      {showExportModal && (
        <ExportModal onClose={() => setShowExportModal(false)} />
      )}
    </div>
  );
};
```

---

## 6. Testing Strategy

### Backend Tests (`tests/test_export_service.py`)

```python
import pytest
import json
import csv
from io import StringIO
from datetime import datetime, timedelta

def test_export_csv_basic(client, auth_headers, seed_usage_data):
    """Test basic CSV export."""
    response = client.get(
        '/api/usage/export?format=csv',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.content_type == 'text/csv; charset=utf-8'
    assert 'attachment' in response.headers['Content-Disposition']
    
    # Parse CSV
    content = response.data.decode('utf-8')
    reader = csv.DictReader(StringIO(content))
    rows = list(reader)
    
    assert len(rows) > 0
    assert 'id' in rows[0]
    assert 'account_name' in rows[0]
    assert 'service_name' in rows[0]

def test_export_json_basic(client, auth_headers, seed_usage_data):
    """Test basic JSON export."""
    response = client.get(
        '/api/usage/export?format=json',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    
    data = json.loads(response.data)
    assert 'export_metadata' in data
    assert 'data' in data
    assert data['export_metadata']['total_records'] > 0

def test_export_date_filter(client, auth_headers, seed_usage_data):
    """Test export with date range filter."""
    start = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
    end = datetime.utcnow().strftime('%Y-%m-%d')
    
    response = client.get(
        f'/api/usage/export?format=json&start_date={start}&end_date={end}',
        headers=auth_headers
    )
    
    data = json.loads(response.data)
    assert data['export_metadata']['filters']['start_date'] == start
    assert data['export_metadata']['filters']['end_date'] == end

def test_export_source_filter(client, auth_headers, seed_usage_data):
    """Test filtering by data source."""
    response = client.get(
        '/api/usage/export?format=json&include_manual=false',
        headers=auth_headers
    )
    
    data = json.loads(response.data)
    for record in data['data']:
        assert record['source'] == 'api'

def test_export_invalid_format(client, auth_headers):
    """Test invalid format returns 400."""
    response = client.get(
        '/api/usage/export?format=xml',
        headers=auth_headers
    )
    
    assert response.status_code == 400

def test_export_large_dataset(client, auth_headers, seed_large_dataset):
    """Test streaming with large dataset (10,000 records)."""
    response = client.get(
        '/api/usage/export?format=csv',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    reader = csv.DictReader(StringIO(content))
    rows = list(reader)
    
    assert len(rows) == 10000
```

### Frontend Tests

```javascript
// tests/ExportModal.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExportModal from '../components/ExportModal';
import api from '../services/api';

jest.mock('../services/api');

test('renders export modal', () => {
  render(<ExportModal onClose={() => {}} />);
  expect(screen.getByText('Export Usage Data')).toBeInTheDocument();
});

test('exports CSV on button click', async () => {
  const mockBlob = new Blob(['csv content']);
  api.get.mockResolvedValue({
    data: mockBlob,
    headers: { 'content-disposition': 'attachment; filename="export.csv"' }
  });
  
  render(<ExportModal onClose={() => {}} />);
  
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'csv' } });
  fireEvent.click(screen.getByText('Export CSV'));
  
  await waitFor(() => {
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining('format=csv'),
      expect.any(Object)
    );
  });
});
```

---

## 7. Performance Considerations

### Streaming vs Full Load

| Records | Full Load Memory | Streaming Memory | Recommendation |
|---------|------------------|------------------|----------------|
| 1-1,000 | ~500 KB | ~50 KB | Either |
| 1,000-10,000 | ~5 MB | ~100 KB | Streaming |
| 10,000-100,000 | ~50 MB | ~200 KB | Streaming |
| 100,000+ | >500 MB | ~500 KB | Streaming + Pagination |

### Database Query Optimization

```python
# Add indexes for export queries
from sqlalchemy import Index

Index('idx_usage_timestamp_account', 
      UsageRecord.timestamp, UsageRecord.account_id)

Index('idx_usage_source', UsageRecord.source)
```

### Chunk Size Tuning

- Small chunks (100-500): More DB queries, less memory
- Large chunks (5000-10000): Fewer DB queries, more memory
- **Recommended: 1000 records per chunk** (balanced)

---

## 8. Security Considerations

### Access Control
- ✅ JWT authentication required
- ✅ User can only export their own data
- ✅ Ownership verified via `Account.user_id`

### Rate Limiting
```python
from flask_limiter import Limiter

# Limit exports to 10 per hour per user
@limiter.limit("10 per hour")
@usage_bp.route('/export', methods=['GET'])
def export_usage():
    ...
```

### Data Sanitization
- Escape CSV special characters
- Validate date formats
- Prevent SQL injection via parameterized queries

---

## 9. Implementation Effort

| Task | Effort | Notes |
|------|--------|-------|
| Backend service | 2 days | Core export logic |
| Route endpoint | 0.5 days | Request handling |
| Frontend modal | 1.5 days | UI component |
| Testing | 2 days | Backend + frontend |
| Documentation | 1 day | API docs + user guide |
| **Total** | **7 days** | Single engineer |

---

## 10. Success Criteria

- ✅ Users can export data in CSV and JSON formats
- ✅ Date range filtering works correctly
- ✅ Exports complete in <10 seconds for 50,000 records
- ✅ Memory usage stays <500 MB for largest exports
- ✅ Test coverage >80% for export functionality
- ✅ Export feature used by >60% of users within first month

---

**Next Steps**: 
1. Review this specification with stakeholders
2. Create GitHub issue/epic for tracking
3. Begin backend implementation
4. Add frontend UI in parallel
5. Integration testing and polish
