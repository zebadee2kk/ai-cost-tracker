# Phase 3: Data Source Visual Indicators - Technical Specification

**Feature Priority**: P0 (Critical)  
**Estimated Effort**: 1 week  
**Sprint**: 3.1  
**Dependencies**: None

---

## 1. Problem Statement

### User Need
Users need to:
- Quickly distinguish between API-synced and manually entered data
- Understand the reliability and source of cost information
- Filter views to show only verified (API) or estimated (manual) data
- Build trust in dashboard accuracy through transparent data provenance

### Current Limitation
No visual distinction exists between API-synced and manual entries. Users cannot tell which data points are verified vs. user-estimated, potentially causing confusion about data accuracy.

---

## 2. Best Practices

### UI/UX Patterns

**Badge/Label Design**:
- Use color-coded badges for quick visual scanning
- Include icons for accessibility and faster recognition
- Maintain consistent placement across all views
- Follow existing app color palette

**Data Provenance Indicators**[cite:10]:
- Blue/primary color for automated/verified data
- Orange/warning color for manual/estimated data  
- Gray for unknown/legacy data (if applicable)
- Clear legends explaining meaning

**Chart Annotations**[cite:13][cite:16]:
- Use Chart.js annotation plugin for marking data points
- Different point styles (circle vs. triangle) for sources
- Hover tooltips with full metadata
- Optional overlay lines/boxes for manual entry periods

---

## 3. Technology Options

### Chart.js Plugins

| Plugin | Purpose | Pros | Cons | Recommendation |
|--------|---------|------|------|----------------|
| **chartjs-plugin-annotation** | Add labels, lines, boxes to charts | Mature, well-documented | Requires separate install | ✅ **Recommended** |
| **chartjs-plugin-datalabels** | Labels on data points | Good for value display | Not ideal for badges | ❌ Not needed |
| **Custom point styles** | Built-in Chart.js feature | No dependencies | Limited styling | ✅ **Use for basic indicators** |

### Badge Implementation

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **CSS-only badges** | Lightweight, fast | Manual positioning | ✅ **Recommended for tables** |
| **SVG icons** | Scalable, crisp | More complex | ✅ **Use for charts** |
| **Emoji indicators** | Zero dependencies | Not professional | ❌ Avoid |

---

## 4. Architecture

### Component Structure

```
frontend/src/
├── components/
│   ├── DataSourceBadge.jsx          ← NEW: Reusable badge component
│   ├── UsageChart.jsx               ← MODIFY: Add point styles
│   ├── UsageTable.jsx               ← MODIFY: Add badges to rows
│   └── DataSourceFilter.jsx         ← NEW: Filter toggle
├── styles/
│   └── badges.css                   ← NEW: Badge styles
└── utils/
    └── chartConfig.js               ← MODIFY: Add custom point styles
```

### Data Flow

```
UsageRecord (DB)
  │
  ├─ source: 'api' | 'manual'
  │
  ↓
API Response
  │
  └──> Frontend Component
        │
        ├──> UsageTable
        │     └──> <DataSourceBadge source={record.source} />
        │
        └──> UsageChart
              └──> pointStyle: source === 'api' ? 'circle' : 'triangle'
                  pointBackgroundColor: source === 'api' ? '#0066CC' : '#FF8C00'
```

---

## 5. Design Specification

### Color Palette

```css
/* API Data - Blue (verified, automated) */
--badge-api-bg: #E3F2FD;        /* Light blue background */
--badge-api-text: #0D47A1;      /* Dark blue text */
--badge-api-border: #1976D2;    /* Medium blue border */
--chart-api-color: #0066CC;     /* Chart point color */

/* Manual Data - Orange (user-entered, estimated) */
--badge-manual-bg: #FFF3E0;     /* Light orange background */
--badge-manual-text: #E65100;   /* Dark orange text */
--badge-manual-border: #FB8C00; /* Medium orange border */
--chart-manual-color: #FF8C00;  /* Chart point color */

/* Unknown/Legacy - Gray */
--badge-unknown-bg: #F5F5F5;
--badge-unknown-text: #616161;
--badge-unknown-border: #9E9E9E;
```

### Badge Mockup

```
┌──────────────────────────────────────────┐
│ Date       Cost    Tokens    Source        │
├──────────────────────────────────────────┤
│ 2026-02-20 $1.23  150000    [🔄 API]       │  <- Blue badge
│ 2026-02-21 $5.00  0         [✏️ Manual]    │  <- Orange badge
│ 2026-02-22 $0.89  120000    [🔄 API]       │
└──────────────────────────────────────────┘
```

### Chart Point Styles

```
API Data:      ● (filled circle, blue)
Manual Data:   ▲ (filled triangle, orange)

Hover tooltip:
┌──────────────────────┐
│ 2026-02-20              │
│ Cost: $1.23             │
│ Tokens: 150,000         │
│ Source: API (🔄)        │
│ Last synced: 2 hrs ago  │
└──────────────────────┘
```

---

## 6. Frontend Implementation

### Component: `DataSourceBadge.jsx`

```jsx
import React from 'react';
import './badges.css';

const DataSourceBadge = ({ source, showIcon = true, showLabel = true, size = 'medium' }) => {
  const config = {
    api: {
      icon: '🔄',
      label: 'API',
      className: 'badge-api',
      title: 'Automatically synced from service API'
    },
    manual: {
      icon: '✏️',
      label: 'Manual',
      className: 'badge-manual',
      title: 'Manually entered by user'
    },
    unknown: {
      icon: '❓',
      label: 'Unknown',
      className: 'badge-unknown',
      title: 'Source not specified'
    }
  };

  const { icon, label, className, title } = config[source] || config.unknown;

  return (
    <span 
      className={`data-source-badge ${className} badge-${size}`}
      title={title}
      role="img"
      aria-label={`Data source: ${label}`}
    >
      {showIcon && <span className="badge-icon">{icon}</span>}
      {showLabel && <span className="badge-label">{label}</span>}
    </span>
  );
};

export default DataSourceBadge;
```

### Styles: `badges.css`

```css
/* Base badge styles */
.data-source-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid;
  transition: all 0.2s ease;
}

/* Size variants */
.badge-small {
  padding: 2px 6px;
  font-size: 10px;
  border-radius: 8px;
}

.badge-medium {
  padding: 4px 8px;
  font-size: 12px;
}

.badge-large {
  padding: 6px 12px;
  font-size: 14px;
}

/* API badge - Blue */
.badge-api {
  background-color: #E3F2FD;
  color: #0D47A1;
  border-color: #1976D2;
}

.badge-api:hover {
  background-color: #BBDEFB;
}

/* Manual badge - Orange */
.badge-manual {
  background-color: #FFF3E0;
  color: #E65100;
  border-color: #FB8C00;
}

.badge-manual:hover {
  background-color: #FFE0B2;
}

/* Unknown badge - Gray */
.badge-unknown {
  background-color: #F5F5F5;
  color: #616161;
  border-color: #9E9E9E;
}

/* Badge icon */
.badge-icon {
  font-size: 1.1em;
  line-height: 1;
}

/* Badge label */
.badge-label {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Compact variant (icon only) */
.badge-compact {
  padding: 4px;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  justify-content: center;
}

.badge-compact .badge-label {
  display: none;
}
```

### Modified: `UsageTable.jsx`

```jsx
import DataSourceBadge from './DataSourceBadge';

const UsageTable = ({ usageData }) => {
  return (
    <table className="usage-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Service</th>
          <th>Cost</th>
          <th>Tokens</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        {usageData.map((record) => (
          <tr key={record.id}>
            <td>{new Date(record.timestamp).toLocaleDateString()}</td>
            <td>{record.service_name}</td>
            <td>${record.cost.toFixed(2)}</td>
            <td>{record.tokens?.toLocaleString() || 'N/A'}</td>
            <td>
              <DataSourceBadge 
                source={record.source} 
                size="small"
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

### Modified: `UsageChart.jsx` (Chart.js Config)

```jsx
import { Chart } from 'chart.js';
import DataSourceBadge from './DataSourceBadge';

const UsageChart = ({ usageData }) => {
  // Separate data by source
  const apiData = usageData.filter(d => d.source === 'api');
  const manualData = usageData.filter(d => d.source === 'manual');

  const chartConfig = {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'API Data',
          data: apiData.map(d => ({
            x: d.timestamp,
            y: d.cost
          })),
          borderColor: '#0066CC',
          backgroundColor: 'rgba(0, 102, 204, 0.1)',
          pointStyle: 'circle',
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: '#0066CC'
        },
        {
          label: 'Manual Entries',
          data: manualData.map(d => ({
            x: d.timestamp,
            y: d.cost
          })),
          borderColor: '#FF8C00',
          backgroundColor: 'rgba(255, 140, 0, 0.1)',
          pointStyle: 'triangle',
          pointRadius: 6,
          pointHoverRadius: 8,
          pointBackgroundColor: '#FF8C00',
          borderDash: [5, 5]  // Dashed line for manual
        }
      ]
    },
    options: {
      plugins: {
        tooltip: {
          callbacks: {
            afterLabel: (context) => {
              const dataPoint = context.dataset.data[context.dataIndex];
              const record = usageData.find(r => 
                r.timestamp === dataPoint.x && r.cost === dataPoint.y
              );
              
              return [
                `Source: ${record.source.toUpperCase()}`,
                record.source === 'api' 
                  ? `Synced: ${new Date(record.updated_at).toLocaleString()}`
                  : `Added: ${new Date(record.created_at).toLocaleString()}`,
                record.notes ? `Note: ${record.notes}` : ''
              ].filter(Boolean);
            }
          }
        },
        legend: {
          display: true,
          labels: {
            usePointStyle: true,
            generateLabels: (chart) => [
              {
                text: '🔄 API Data (verified)',
                fillStyle: '#0066CC',
                strokeStyle: '#0066CC',
                pointStyle: 'circle'
              },
              {
                text: '✏️ Manual Entries (estimated)',
                fillStyle: '#FF8C00',
                strokeStyle: '#FF8C00',
                pointStyle: 'triangle'
              }
            ]
          }
        }
      }
    }
  };

  return <Chart {...chartConfig} />;
};
```

### Component: `DataSourceFilter.jsx`

```jsx
import React, { useState } from 'react';

const DataSourceFilter = ({ onChange }) => {
  const [filters, setFilters] = useState({
    showAPI: true,
    showManual: true
  });

  const handleToggle = (source) => {
    const newFilters = {
      ...filters,
      [source]: !filters[source]
    };
    setFilters(newFilters);
    onChange(newFilters);
  };

  return (
    <div className="data-source-filter">
      <label className="filter-label">Show:</label>
      
      <label className="filter-checkbox">
        <input
          type="checkbox"
          checked={filters.showAPI}
          onChange={() => handleToggle('showAPI')}
        />
        <span className="badge-api badge-small">🔄 API Data</span>
      </label>
      
      <label className="filter-checkbox">
        <input
          type="checkbox"
          checked={filters.showManual}
          onChange={() => handleToggle('showManual')}
        />
        <span className="badge-manual badge-small">✏️ Manual</span>
      </label>
    </div>
  );
};

export default DataSourceFilter;
```

---

## 7. Backend Support (Optional Enhancement)

### API Endpoint: Filter by Source

**Modify**: `GET /api/usage?source=api|manual`

```python
# In backend/routes/usage.py

@bp.route('/', methods=['GET'])
@jwt_required()
def get_usage():
    # ... existing code ...
    
    # Add source filter
    source_filter = request.args.get('source')
    if source_filter in ['api', 'manual']:
        query = query.filter(UsageRecord.source == source_filter)
    
    # ... rest of code ...
```

---

## 8. Testing Strategy

### Unit Tests

```jsx
// DataSourceBadge.test.jsx
import { render, screen } from '@testing-library/react';
import DataSourceBadge from './DataSourceBadge';

test('renders API badge with correct styling', () => {
  render(<DataSourceBadge source="api" />);
  
  const badge = screen.getByRole('img', { name: /API/i });
  expect(badge).toHaveClass('badge-api');
  expect(badge).toHaveTextContent('🔄');
  expect(badge).toHaveTextContent('API');
});

test('renders manual badge with correct styling', () => {
  render(<DataSourceBadge source="manual" />);
  
  const badge = screen.getByRole('img', { name: /Manual/i });
  expect(badge).toHaveClass('badge-manual');
  expect(badge).toHaveTextContent('✏️');
});

test('handles unknown source gracefully', () => {
  render(<DataSourceBadge source="invalid" />);
  
  const badge = screen.getByRole('img');
  expect(badge).toHaveClass('badge-unknown');
});

test('supports icon-only mode', () => {
  render(<DataSourceBadge source="api" showLabel={false} />);
  
  const badge = screen.getByRole('img');
  expect(badge).toHaveTextContent('🔄');
  expect(badge).not.toHaveTextContent('API');
});
```

### Visual Regression Tests

```jsx
// Storybook stories for visual testing
export const APIBadge = () => <DataSourceBadge source="api" />;
export const ManualBadge = () => <DataSourceBadge source="manual" />;
export const BadgeSizes = () => (
  <div>
    <DataSourceBadge source="api" size="small" />
    <DataSourceBadge source="api" size="medium" />
    <DataSourceBadge source="api" size="large" />
  </div>
);
```

### Integration Tests

```jsx
test('table displays correct badges for mixed data', () => {
  const mockData = [
    { id: 1, source: 'api', cost: 1.23 },
    { id: 2, source: 'manual', cost: 5.00 }
  ];
  
  render(<UsageTable usageData={mockData} />);
  
  const apiBadges = screen.getAllByText(/API/i);
  const manualBadges = screen.getAllByText(/Manual/i);
  
  expect(apiBadges).toHaveLength(1);
  expect(manualBadges).toHaveLength(1);
});
```

---

## 9. Implementation Effort

### Day 1-2: Core Components
- Create `DataSourceBadge.jsx` component
- Create `badges.css` styles
- Write unit tests

### Day 3: Table Integration
- Modify `UsageTable.jsx` to display badges
- Integrate into existing table views
- Test with real data

### Day 4: Chart Integration
- Modify `UsageChart.jsx` with custom point styles
- Add legend with icons
- Enhance tooltips

### Day 5: Filter & Polish
- Create `DataSourceFilter.jsx` component
- Wire up filtering logic
- Visual QA and refinements
- Documentation

**Total**: 5 days (1 week)

---

## 10. Dependencies

### Required
- None (uses existing Chart.js 4)

### Optional
- `chartjs-plugin-annotation` (if adding box/line annotations)
  ```bash
  npm install chartjs-plugin-annotation
  ```

---

## 11. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Color contrast accessibility** | Medium | Low | Use WCAG AA compliant colors, test with tools |
| **Icon rendering issues** | Low | Medium | Use SVG fallbacks, test across browsers |
| **Chart performance with many points** | Medium | Low | Limit dataset size, add pagination |
| **Inconsistent badge placement** | Low | Low | Create layout guidelines, use flexbox |

---

## 12. Accessibility Considerations

### WCAG Compliance
- ✅ Color contrast ratio >4.5:1 for text
- ✅ Don't rely solely on color (use icons + text)
- ✅ Proper ARIA labels on badges
- ✅ Keyboard accessible filter toggles
- ✅ Screen reader friendly tooltips

### Implementation
```jsx
<span 
  className="badge-api"
  role="img"
  aria-label="Data source: API - automatically synced"
  title="Automatically synced from service API"
>
  🔄 API
</span>
```

---

## 13. Success Criteria

- ✅ All usage data displays source badges consistently
- ✅ Charts use distinct point styles for API vs. manual data
- ✅ Users can filter data by source type
- ✅ Badges are accessible (WCAG AA compliant)
- ✅ No performance degradation with 1000+ data points
- ✅ Visual design approved by product owner
- ✅ >90% user satisfaction in usability testing

---

## 14. Future Enhancements (Post-Phase 3)

### Phase 4 Ideas
- Confidence score indicator (e.g., ⭐⭐⭐⭐⭐ for API, ⭐⭐⭐ for manual)
- Data quality dashboard showing API vs. manual ratio
- Bulk actions: "Mark all as verified" button
- Detailed data lineage view (when synced, by whom)
- Color customization in user settings

---

**Status**: 📋 Specification Complete | Ready for Implementation
