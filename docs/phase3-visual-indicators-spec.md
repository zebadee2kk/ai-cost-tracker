# Phase 3: Data Source Visual Indicators - Technical Specification

**Feature Priority**: P0 (Must Have)  
**Estimated Effort**: 1 week  
**Dependencies**: None  
**Target Sprint**: 3.1 (Week 2)

---

## 1. Problem Statement

### User Need
Users need to quickly distinguish between:
- **API-synced data**: Automatically fetched from provider APIs (high confidence)
- **Manual entries**: User-entered data (variable confidence, requires verification)

Without visual indicators, users cannot:
- Trust the accuracy of data sources
- Identify which entries need verification
- Understand data provenance for auditing
- Filter views by data source

### Current Limitation
- All usage data looks identical in the UI
- No way to distinguish manual vs. API data visually
- Users cannot filter by source type
- Charts don't indicate data quality/source

### Business Value
- **High**: Improves data transparency and trust
- Essential for audit/compliance scenarios
- Reduces user confusion about data accuracy
- Enables informed decision-making

---

## 2. Best Practices & Standards

### Visual Indicator Design Principles

**Accessibility (WCAG 2.1 AA)**:
- Don't rely on color alone (use icons + color)
- Maintain 4.5:1 contrast ratio for text
- Provide descriptive tooltips
- Support keyboard navigation

**Consistency**:
- Use same badge design across all views
- Consistent color palette (Material Design recommended)
- Icon usage follows common patterns (🔄 for sync, ✏️ for manual)

**Performance**:
- Badges render client-side (no extra API calls)
- CSS-based badges (avoid images)
- Chart.js point styling (no external plugins for basic styling)

### Chart.js Point Styling Patterns

**Custom Point Styles**:
```javascript
{
  datasets: [{
    data: usageData,
    pointStyle: (context) => {
      const record = context.raw;
      return record.source === 'manual' ? 'rectRot' : 'circle';
    },
    pointBackgroundColor: (context) => {
      const record = context.raw;
      return record.source === 'manual' ? '#FF9800' : '#2196F3';
    },
    pointRadius: (context) => {
      return context.raw.source === 'manual' ? 6 : 4;
    },
    pointBorderColor: '#FFFFFF',
    pointBorderWidth: 2
  }]
}
```

**Chart.js Annotation Plugin** (Optional Enhancement):
- Adds text labels or boxes to chart areas
- Can highlight manual entry periods
- Requires `chartjs-plugin-annotation` dependency

---

## 3. Technology Options

### Badge Implementation

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **CSS + HTML** | No dependencies, customizable, fast | Manual styling | ✅ Use this |
| **Material-UI Chip** | Pre-styled, consistent | Large dependency | ❌ Overkill |
| **Custom Icon Library** | Professional icons | Extra dependency | ❌ Unnecessary |

**Verdict**: Use CSS-based badges with emoji/Unicode icons.

### Chart Styling

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Chart.js Scriptable Options** | Built-in, flexible, no deps | Requires data format changes | ✅ Use this |
| **chartjs-plugin-annotation** | Powerful, feature-rich | Extra dependency (25kb) | ⚠️ Optional enhancement |
| **Custom Canvas Overlay** | Ultimate control | High complexity | ❌ Too complex |

**Verdict**: Use Chart.js scriptable options (built-in). Add annotation plugin only if advanced features needed.

---

## 4. Architecture

### Component Hierarchy

```
┌───────────────────────────────────────────────┐
│        DashboardPage / AnalyticsPage         │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │      UsageChart Component           │    │
│  │  - Chart.js with point styling     │    │
│  │  - Legend shows badge colors       │    │
│  │  - Tooltips show source info       │    │
│  └─────────────────────────────────────┘    │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │    UsageTable Component             │    │
│  │  - Rows with SourceBadge component │    │
│  │  - Filter by source toggle         │    │
│  └─────────────────────────────────────┘    │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │      SourceBadge Component          │    │
│  │  Props: source ('api' | 'manual')  │    │
│  │  Renders: Badge with icon + label  │    │
│  └─────────────────────────────────────┘    │
└───────────────────────────────────────────────┘
```

### Data Flow

1. **Backend**: Already provides `source` field in usage records (Phase 2)
2. **API Response**: Includes `source: 'api'` or `source: 'manual'`
3. **Frontend State**: Stores records with source info
4. **Rendering**: 
   - Table rows show `<SourceBadge source={record.source} />`
   - Chart points styled based on `record.source`
5. **Filtering**: User toggles filter, state updates, view re-renders

---

## 5. UI Design Specification

### Badge Component Design

#### Visual Design

**API Badge**:
```
┌─────────────┐
│ 🔄 API      │  ← Blue background (#2196F3)
└─────────────┘     White text (#FFFFFF)
                    12px padding, 4px border-radius
```

**Manual Badge**:
```
┌─────────────┐
│ ✏️ Manual   │  ← Orange background (#FF9800)
└─────────────┘     White text (#FFFFFF)
                    12px padding, 4px border-radius
```

#### CSS Implementation

```css
/* frontend/src/components/SourceBadge.css */

.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #FFFFFF;
  white-space: nowrap;
}

.source-badge.api {
  background-color: #2196F3; /* Material Blue */
}

.source-badge.manual {
  background-color: #FF9800; /* Material Orange */
}

.source-badge-icon {
  font-size: 14px;
  line-height: 1;
}
```

#### React Component

```jsx
// frontend/src/components/SourceBadge.jsx

import React from 'react';
import './SourceBadge.css';

const SourceBadge = ({ source, tooltip = true }) => {
  const config = {
    api: {
      icon: '🔄',
      label: 'API',
      className: 'api',
      tooltip: 'Automatically synced from provider API'
    },
    manual: {
      icon: '✏️',
      label: 'Manual',
      className: 'manual',
      tooltip: 'Manually entered by user'
    }
  };

  const { icon, label, className, tooltip: tooltipText } = config[source] || config.manual;

  return (
    <span 
      className={`source-badge ${className}`}
      title={tooltip ? tooltipText : ''}
      aria-label={`Data source: ${label}`}
    >
      <span className="source-badge-icon" aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </span>
  );
};

export default SourceBadge;
```

### Usage Table Integration

```jsx
// frontend/src/components/UsageTable.jsx

import SourceBadge from './SourceBadge';

function UsageTable({ records }) {
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
        {records.map(record => (
          <tr key={record.id}>
            <td>{record.date}</td>
            <td>{record.service}</td>
            <td>${record.cost.toFixed(2)}</td>
            <td>{record.tokens.toLocaleString()}</td>
            <td>
              <SourceBadge source={record.source} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### Chart.js Integration

```javascript
// frontend/src/components/UsageChart.jsx

import { Line } from 'react-chartjs-2';

function UsageChart({ usageData }) {
  const chartData = {
    labels: usageData.map(d => d.date),
    datasets: [{
      label: 'Daily Cost',
      data: usageData.map(d => ({
        x: d.date,
        y: d.cost,
        source: d.source // Include source in data point
      })),
      borderColor: '#2196F3',
      backgroundColor: 'rgba(33, 150, 243, 0.1)',
      pointStyle: (context) => {
        const source = context.raw?.source;
        return source === 'manual' ? 'rectRot' : 'circle';
      },
      pointBackgroundColor: (context) => {
        const source = context.raw?.source;
        return source === 'manual' ? '#FF9800' : '#2196F3';
      },
      pointRadius: (context) => {
        return context.raw?.source === 'manual' ? 6 : 4;
      },
      pointHoverRadius: 8,
      pointBorderColor: '#FFFFFF',
      pointBorderWidth: 2
    }]
  };

  const options = {
    plugins: {
      legend: {
        display: true,
        labels: {
          generateLabels: (chart) => {
            return [
              {
                text: '🔄 API Data',
                fillStyle: '#2196F3',
                strokeStyle: '#2196F3'
              },
              {
                text: '✏️ Manual Data',
                fillStyle: '#FF9800',
                strokeStyle: '#FF9800',
                pointStyle: 'rectRot'
              }
            ];
          }
        }
      },
      tooltip: {
        callbacks: {
          afterLabel: (context) => {
            const source = context.raw?.source;
            return source === 'manual' 
              ? 'Source: Manual Entry' 
              : 'Source: API Sync';
          }
        }
      }
    },
    scales: {
      x: { title: { display: true, text: 'Date' } },
      y: { title: { display: true, text: 'Cost (USD)' } }
    }
  };

  return <Line data={chartData} options={options} />;
}
```

### Filter Toggle Component

```jsx
// frontend/src/components/SourceFilter.jsx

import React, { useState } from 'react';

function SourceFilter({ onFilterChange }) {
  const [filter, setFilter] = useState('all');

  const handleChange = (newFilter) => {
    setFilter(newFilter);
    onFilterChange(newFilter);
  };

  return (
    <div className="source-filter">
      <label>Show:</label>
      <div className="filter-buttons">
        <button 
          className={filter === 'all' ? 'active' : ''}
          onClick={() => handleChange('all')}
        >
          All Data
        </button>
        <button 
          className={filter === 'api' ? 'active' : ''}
          onClick={() => handleChange('api')}
        >
          🔄 API Only
        </button>
        <button 
          className={filter === 'manual' ? 'active' : ''}
          onClick={() => handleChange('manual')}
        >
          ✏️ Manual Only
        </button>
      </div>
    </div>
  );
}

export default SourceFilter;
```

---

## 6. Testing Strategy

### Unit Tests

```javascript
// frontend/src/components/SourceBadge.test.jsx

import { render, screen } from '@testing-library/react';
import SourceBadge from './SourceBadge';

test('renders API badge correctly', () => {
  render(<SourceBadge source="api" />);
  expect(screen.getByText('API')).toBeInTheDocument();
  expect(screen.getByText('🔄')).toBeInTheDocument();
});

test('renders manual badge correctly', () => {
  render(<SourceBadge source="manual" />);
  expect(screen.getByText('Manual')).toBeInTheDocument();
  expect(screen.getByText('✏️')).toBeInTheDocument();
});

test('applies correct CSS class', () => {
  const { container } = render(<SourceBadge source="api" />);
  expect(container.querySelector('.source-badge.api')).toBeInTheDocument();
});

test('shows tooltip on hover', () => {
  render(<SourceBadge source="api" tooltip={true} />);
  const badge = screen.getByLabelText('Data source: API');
  expect(badge).toHaveAttribute('title', 'Automatically synced from provider API');
});
```

### Integration Tests

```javascript
// frontend/src/components/UsageChart.test.jsx

import { render } from '@testing-library/react';
import UsageChart from './UsageChart';

test('chart renders with mixed data sources', () => {
  const mockData = [
    { date: '2026-02-01', cost: 10.50, source: 'api' },
    { date: '2026-02-02', cost: 5.25, source: 'manual' },
    { date: '2026-02-03', cost: 15.00, source: 'api' }
  ];

  const { container } = render(<UsageChart usageData={mockData} />);
  expect(container.querySelector('canvas')).toBeInTheDocument();
});
```

### Visual Regression Tests

```javascript
// Using Percy or Chromatic
import { percySnapshot } from '@percy/puppeteer';

test('visual: source badges', async () => {
  await page.goto('http://localhost:3000/dashboard');
  await percySnapshot(page, 'Dashboard with Source Badges');
});
```

---

## 7. Implementation Effort

### Time Breakdown

| Task | Effort | Notes |
|------|--------|-------|
| **SourceBadge component** | 0.5 days | React component + CSS |
| **UsageChart point styling** | 1 day | Chart.js scriptable options |
| **Filter toggle component** | 0.5 days | React component + state management |
| **Integration into dashboard** | 1 day | Wire components into existing views |
| **Testing** | 1 day | Unit + integration tests |
| **Documentation** | 0.5 days | Component docs |
| **Code review & QA** | 0.5 days | Review, bug fixes |

**Total**: 5 days (1 week)

### Acceptance Criteria

- ✅ SourceBadge component renders correctly for both sources
- ✅ Badges appear in usage table
- ✅ Chart points styled differently for manual vs. API
- ✅ Chart legend shows both source types
- ✅ Tooltips display source information
- ✅ Filter toggle works correctly
- ✅ Accessible (keyboard nav, screen readers)
- ✅ >80% test coverage for new components
- ✅ Cross-browser tested (Chrome, Firefox, Safari)

---

## 8. Dependencies

### Frontend Packages
- `react` (existing)
- `react-chartjs-2` (existing)
- `chart.js` (existing)

**No new dependencies required** ✅

### Backend Changes
**None required** - `source` field already exists (Phase 2) ✅

---

## 9. Risks & Mitigation

### Risk 1: Chart Performance with Large Datasets
**Impact**: Medium  
**Probability**: Low  
**Mitigation**: Chart.js efficiently handles scriptable options. Test with 10k+ points.

### Risk 2: Color Blindness Accessibility
**Impact**: Medium  
**Probability**: Medium  
**Mitigation**: Use icons + color (not color alone). Test with color blindness simulator.

### Risk 3: Icon Rendering Issues (Emoji)
**Impact**: Low  
**Probability**: Low  
**Mitigation**: Use Unicode emojis with fallback text. Test on Windows/Mac/Linux.

---

## 10. Future Enhancements (Post-Phase 3)

- **Confidence scores**: Show data quality metrics (e.g., "95% confident")
- **Edit history**: Link badge to show when/who last modified
- **Batch editing**: Bulk convert manual → API after provider API launches
- **Custom badges**: User-defined labels for data sources
- **Chart annotations**: Highlight date ranges with all-manual data

---

**Status**: ✅ Ready for Implementation  
**Assigned To**: TBD  
**Sprint**: 3.1 (Week 2)
