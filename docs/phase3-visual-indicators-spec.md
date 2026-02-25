# Phase 3: Data Source Visual Indicators - Technical Specification

**Created**: February 25, 2026  
**Priority**: P0 (Highest)  
**Effort**: 1 week  
**Dependencies**: None

---

## 1. Problem Statement

### Business Need
Users cannot distinguish between:
- **API-synced data** - Automatically fetched, high confidence
- **Manual entries** - User-entered, potential for errors

This creates confusion and trust issues with the dashboard data.

### Current Limitations
- All data points look identical in UI
- No visual indication of data provenance
- Users can't filter by source type
- Manual entries blend in with API data

### Success Criteria
- Users can instantly identify manual vs API data
- <2 seconds to find data source for any entry
- Clear visual distinction without cluttering UI
- Filter functionality to show/hide by source

---

## 2. Feature Requirements

### Functional Requirements

#### Must Have (MVP)
- [x] Badge/label for each data entry showing source (API/Manual)
- [x] Color-coded chart points (blue=API, orange=manual)
- [x] Custom point styles in Chart.js (circle vs square)
- [x] Hover tooltips with source metadata
- [x] Filter toggle: [All] [API Only] [Manual Only]
- [x] Legend showing source types
- [x] Consistent color scheme across dashboard

#### Should Have (Phase 3.1)
- [ ] Annotation lines/boxes on charts marking manual periods
- [ ] "Last synced" timestamp for API accounts
- [ ] Warning icon for stale API data (>48 hours)
- [ ] Bulk select by source type
- [ ] Export filtering by source

#### Could Have (Phase 4)
- [ ] Data confidence scores (0-100%)
- [ ] Edit history for manual entries
- [ ] Source attribution in all reports
- [ ] Custom source types (API, Manual, Imported, Estimated)

### Non-Functional Requirements
- **Performance**: No impact on chart rendering (<50ms overhead)
- **Accessibility**: WCAG 2.1 AA compliant colors
- **Consistency**: Same badge style across all pages
- **Mobile**: Badges readable on small screens

---

## 3. Design System

### Color Palette

```css
/* Primary Colors - WCAG AA Compliant */
--color-api-primary: #2196F3;      /* Material Blue 500 */
--color-api-light: #BBDEFB;        /* Material Blue 100 */
--color-api-dark: #1976D2;         /* Material Blue 700 */

--color-manual-primary: #FF9800;   /* Material Orange 500 */
--color-manual-light: #FFE0B2;     /* Material Orange 100 */
--color-manual-dark: #F57C00;      /* Material Orange 700 */

/* Background overlays */
--color-api-bg: rgba(33, 150, 243, 0.1);
--color-manual-bg: rgba(255, 152, 0, 0.1);

/* Text on colored backgrounds */
--color-text-on-api: #FFFFFF;
--color-text-on-manual: #000000;
```

### Typography
- **Badge text**: 11px, bold, uppercase
- **Tooltip text**: 13px, regular
- **Legend text**: 12px, regular

### Spacing
- Badge padding: 4px 8px
- Icon size: 14px × 14px
- Margin between badge and text: 8px

---

## 4. Component Specifications

### Badge Component

#### Visual Design

```
API Badge:     [🔄 API]     - Blue background, white text
Manual Badge:  [✏️ MANUAL]  - Orange background, black text
```

#### React Component

```jsx
// components/SourceBadge.jsx
import React from 'react';
import './SourceBadge.css';

const SourceBadge = ({ source, size = 'medium', showIcon = true }) => {
  const isAPI = source === 'api';
  
  const icons = {
    api: '🔄',
    manual: '✏️'
  };
  
  const labels = {
    api: 'API',
    manual: 'MANUAL'
  };
  
  return (
    <span 
      className={`source-badge source-badge--${source} source-badge--${size}`}
      title={isAPI ? 'Automatically synced from API' : 'Manually entered by user'}
    >
      {showIcon && <span className="source-badge__icon">{icons[source]}</span>}
      <span className="source-badge__label">{labels[source]}</span>
    </span>
  );
};

export default SourceBadge;
```

#### CSS Styling

```css
/* components/SourceBadge.css */
.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.source-badge--api {
  background: var(--color-api-primary);
  color: var(--color-text-on-api);
}

.source-badge--manual {
  background: var(--color-manual-primary);
  color: var(--color-text-on-manual);
}

.source-badge:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}

.source-badge__icon {
  font-size: 12px;
  line-height: 1;
}

.source-badge__label {
  line-height: 1;
}

/* Size variants */
.source-badge--small {
  padding: 2px 6px;
  font-size: 10px;
}

.source-badge--small .source-badge__icon {
  font-size: 10px;
}

.source-badge--large {
  padding: 6px 12px;
  font-size: 12px;
}

.source-badge--large .source-badge__icon {
  font-size: 14px;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .source-badge--api {
    background: var(--color-api-dark);
  }
  
  .source-badge--manual {
    background: var(--color-manual-dark);
  }
}
```

---

## 5. Chart.js Integration

### Custom Point Styles

```javascript
// utils/chartConfig.js
export const getChartDatasetConfig = (usageData) => {
  return {
    label: 'Daily Cost',
    data: usageData.map(record => ({
      x: record.date,
      y: record.cost,
      source: record.source,
      notes: record.notes,
      timestamp: record.created_at
    })),
    
    // Custom point styling based on source
    pointStyle: (context) => {
      const source = context.raw.source;
      return source === 'manual' ? 'rectRot' : 'circle';
    },
    
    pointBackgroundColor: (context) => {
      const source = context.raw.source;
      return source === 'manual' ? '#FF9800' : '#2196F3';
    },
    
    pointBorderColor: (context) => {
      const source = context.raw.source;
      return source === 'manual' ? '#F57C00' : '#1976D2';
    },
    
    pointRadius: (context) => {
      const source = context.raw.source;
      return source === 'manual' ? 6 : 4;
    },
    
    pointHoverRadius: (context) => {
      const source = context.raw.source;
      return source === 'manual' ? 8 : 6;
    },
    
    pointBorderWidth: 2,
    
    // Line styling
    borderColor: '#2196F3',
    borderWidth: 2,
    tension: 0.4,
    fill: false
  };
};
```

### Enhanced Tooltips

```javascript
// utils/chartConfig.js
export const getTooltipConfig = () => {
  return {
    callbacks: {
      title: (tooltipItems) => {
        const item = tooltipItems[0];
        return item.label; // Date
      },
      
      label: (context) => {
        const record = context.raw;
        const lines = [
          `Cost: $${record.y.toFixed(2)}`,
          `Source: ${record.source === 'api' ? '🔄 API' : '✏️ Manual'}`
        ];
        
        if (record.notes) {
          lines.push(`Notes: ${record.notes}`);
        }
        
        if (record.timestamp) {
          const date = new Date(record.timestamp);
          lines.push(`Entered: ${date.toLocaleDateString()}`);
        }
        
        return lines;
      },
      
      labelColor: (context) => {
        const source = context.raw.source;
        return {
          borderColor: source === 'manual' ? '#F57C00' : '#1976D2',
          backgroundColor: source === 'manual' ? '#FF9800' : '#2196F3',
          borderWidth: 2
        };
      }
    },
    
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    titleColor: '#fff',
    bodyColor: '#fff',
    borderColor: '#666',
    borderWidth: 1,
    padding: 12,
    displayColors: true,
    boxPadding: 6
  };
};
```

### Chart.js Plugin for Annotations (Optional)

```javascript
// Install: npm install chartjs-plugin-annotation
import annotationPlugin from 'chartjs-plugin-annotation';

Chart.register(annotationPlugin);

export const getAnnotationsConfig = (manualEntries) => {
  return {
    annotations: manualEntries.map((entry, index) => ({
      type: 'point',
      xValue: entry.date,
      yValue: entry.cost,
      backgroundColor: 'rgba(255, 152, 0, 0.3)',
      borderColor: '#F57C00',
      borderWidth: 2,
      radius: 8,
      label: {
        display: true,
        content: '✏️',
        position: 'top'
      }
    }))
  };
};
```

---

## 6. Filter Component

### UI Design

```
┌─────────────────────────────────────────┐
│ Show: [All] [API Only] [Manual Only]   │
└─────────────────────────────────────────┘
```

### React Component

```jsx
// components/SourceFilter.jsx
import React from 'react';
import './SourceFilter.css';

const SourceFilter = ({ selected, onChange }) => {
  const options = [
    { value: 'all', label: 'All' },
    { value: 'api', label: 'API Only', icon: '🔄' },
    { value: 'manual', label: 'Manual Only', icon: '✏️' }
  ];
  
  return (
    <div className="source-filter">
      <span className="source-filter__label">Show:</span>
      <div className="source-filter__buttons">
        {options.map(option => (
          <button
            key={option.value}
            className={`source-filter__button ${selected === option.value ? 'active' : ''}`}
            onClick={() => onChange(option.value)}
          >
            {option.icon && <span className="source-filter__icon">{option.icon}</span>}
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SourceFilter;
```

### CSS Styling

```css
/* components/SourceFilter.css */
.source-filter {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.source-filter__label {
  font-size: 14px;
  font-weight: 600;
  color: #666;
}

.source-filter__buttons {
  display: flex;
  gap: 8px;
}

.source-filter__button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: white;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  cursor: pointer;
  transition: all 0.2s ease;
}

.source-filter__button:hover {
  border-color: #2196F3;
  background: #E3F2FD;
}

.source-filter__button.active {
  border-color: #2196F3;
  background: #2196F3;
  color: white;
}

.source-filter__icon {
  font-size: 16px;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .source-filter {
    background: #333;
  }
  
  .source-filter__label {
    color: #ccc;
  }
  
  .source-filter__button {
    background: #444;
    border-color: #555;
    color: #eee;
  }
  
  .source-filter__button:hover {
    background: #555;
  }
}
```

---

## 7. Integration Points

### Dashboard Usage History Table

```jsx
// pages/DashboardPage.jsx
import SourceBadge from '../components/SourceBadge';
import SourceFilter from '../components/SourceFilter';

function DashboardPage() {
  const [sourceFilter, setSourceFilter] = useState('all');
  const [usageData, setUsageData] = useState([]);
  
  const filteredData = usageData.filter(record => {
    if (sourceFilter === 'all') return true;
    return record.source === sourceFilter;
  });
  
  return (
    <div className="dashboard">
      <SourceFilter selected={sourceFilter} onChange={setSourceFilter} />
      
      <table className="usage-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Service</th>
            <th>Cost</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {filteredData.map(record => (
            <tr key={record.id}>
              <td>{record.date}</td>
              <td>{record.service}</td>
              <td>${record.cost.toFixed(2)}</td>
              <td>
                <SourceBadge source={record.source} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### Analytics Page Chart

```jsx
// pages/AnalyticsPage.jsx
import { Line } from 'react-chartjs-2';
import { getChartDatasetConfig, getTooltipConfig } from '../utils/chartConfig';

function AnalyticsPage() {
  const [usageData, setUsageData] = useState([]);
  
  const chartData = {
    datasets: [getChartDatasetConfig(usageData)]
  };
  
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: getTooltipConfig(),
      legend: {
        display: true,
        labels: {
          generateLabels: (chart) => {
            return [
              {
                text: '🔄 API Data',
                fillStyle: '#2196F3',
                strokeStyle: '#1976D2',
                pointStyle: 'circle'
              },
              {
                text: '✏️ Manual Data',
                fillStyle: '#FF9800',
                strokeStyle: '#F57C00',
                pointStyle: 'rectRot'
              }
            ];
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'day'
        }
      },
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value) => `$${value.toFixed(2)}`
        }
      }
    }
  };
  
  return (
    <div className="analytics">
      <div className="chart-container">
        <Line data={chartData} options={chartOptions} />
      </div>
    </div>
  );
}
```

### Manual Entry Modal

```jsx
// components/ManualEntryModal.jsx (enhancement)
function ManualEntryModal({ onSave }) {
  return (
    <div className="modal">
      <div className="modal-header">
        <h3>
          <SourceBadge source="manual" size="small" /> Add Manual Entry
        </h3>
      </div>
      
      <div className="modal-info">
        <p>
          Manual entries are marked with the <SourceBadge source="manual" size="small" /> badge 
          to distinguish them from automatically synced API data.
        </p>
      </div>
      
      {/* Form fields */}
    </div>
  );
}
```

---

## 8. Backend Support

### API Response Enhancement

Ensure all usage endpoints return `source` field:

```python
# routes/usage.py
@app.route('/api/usage', methods=['GET'])
@jwt_required()
def get_usage():
    records = UsageRecord.query.all()
    
    return jsonify([{
        'id': r.id,
        'date': r.timestamp.strftime('%Y-%m-%d'),
        'service': r.service.name,
        'account': r.account.name,
        'cost': float(r.cost),
        'tokens': r.total_tokens,
        'source': r.source,  # 'api' or 'manual'
        'notes': r.notes,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'updated_at': r.updated_at.isoformat() if r.updated_at else None
    } for r in records])
```

### Filtering Support

```python
# routes/usage.py
@app.route('/api/usage', methods=['GET'])
@jwt_required()
def get_usage():
    source_filter = request.args.get('source', 'all')
    
    query = UsageRecord.query.join(Account).filter(Account.user_id == get_jwt_identity())
    
    if source_filter != 'all':
        query = query.filter(UsageRecord.source == source_filter)
    
    records = query.all()
    # ... rest of response
```

---

## 9. Testing Strategy

### Visual Regression Tests

```javascript
// tests/SourceBadge.test.jsx
import { render, screen } from '@testing-library/react';
import SourceBadge from '../components/SourceBadge';

describe('SourceBadge', () => {
  test('renders API badge with correct styling', () => {
    render(<SourceBadge source="api" />);
    
    const badge = screen.getByText('API');
    expect(badge).toBeInTheDocument();
    expect(badge.parentElement).toHaveClass('source-badge--api');
  });
  
  test('renders manual badge with correct styling', () => {
    render(<SourceBadge source="manual" />);
    
    const badge = screen.getByText('MANUAL');
    expect(badge).toBeInTheDocument();
    expect(badge.parentElement).toHaveClass('source-badge--manual');
  });
  
  test('shows icon by default', () => {
    const { container } = render(<SourceBadge source="api" />);
    expect(container.querySelector('.source-badge__icon')).toBeInTheDocument();
  });
  
  test('hides icon when showIcon is false', () => {
    const { container } = render(<SourceBadge source="api" showIcon={false} />);
    expect(container.querySelector('.source-badge__icon')).not.toBeInTheDocument();
  });
});
```

### Integration Tests

```javascript
// tests/SourceFilter.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import SourceFilter from '../components/SourceFilter';

describe('SourceFilter', () => {
  test('calls onChange when button clicked', () => {
    const handleChange = jest.fn();
    render(<SourceFilter selected="all" onChange={handleChange} />);
    
    fireEvent.click(screen.getByText('API Only'));
    expect(handleChange).toHaveBeenCalledWith('api');
  });
  
  test('highlights selected option', () => {
    render(<SourceFilter selected="manual" onChange={() => {}} />);
    
    const manualButton = screen.getByText('Manual Only').closest('button');
    expect(manualButton).toHaveClass('active');
  });
});
```

### Chart Tests

```javascript
// tests/chartConfig.test.js
import { getChartDatasetConfig } from '../utils/chartConfig';

describe('Chart Configuration', () => {
  test('assigns correct colors to API data', () => {
    const data = [{ date: '2026-02-25', cost: 1.50, source: 'api' }];
    const config = getChartDatasetConfig(data);
    
    const context = { raw: { source: 'api' } };
    expect(config.pointBackgroundColor(context)).toBe('#2196F3');
  });
  
  test('assigns correct colors to manual data', () => {
    const data = [{ date: '2026-02-25', cost: 1.50, source: 'manual' }];
    const config = getChartDatasetConfig(data);
    
    const context = { raw: { source: 'manual' } };
    expect(config.pointBackgroundColor(context)).toBe('#FF9800');
  });
  
  test('uses different point styles for sources', () => {
    const config = getChartDatasetConfig([]);
    
    expect(config.pointStyle({ raw: { source: 'api' } })).toBe('circle');
    expect(config.pointStyle({ raw: { source: 'manual' } })).toBe('rectRot');
  });
});
```

### Accessibility Tests

```javascript
// tests/accessibility.test.jsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import SourceBadge from '../components/SourceBadge';

expect.extend(toHaveNoViolations);

describe('Accessibility', () => {
  test('SourceBadge has no accessibility violations', async () => {
    const { container } = render(<SourceBadge source="api" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
  
  test('SourceFilter has no accessibility violations', async () => {
    const { container } = render(
      <SourceFilter selected="all" onChange={() => {}} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

---

## 10. Performance Considerations

### Chart Rendering Optimization

```javascript
// Use React.memo to prevent unnecessary re-renders
const SourceBadge = React.memo(({ source, size, showIcon }) => {
  // Component implementation
}, (prevProps, nextProps) => {
  return prevProps.source === nextProps.source &&
         prevProps.size === nextProps.size &&
         prevProps.showIcon === nextProps.showIcon;
});
```

### Dataset Filtering

```javascript
// Memoize filtered data to avoid recalculation
import { useMemo } from 'react';

function DashboardPage() {
  const [sourceFilter, setSourceFilter] = useState('all');
  const [usageData, setUsageData] = useState([]);
  
  const filteredData = useMemo(() => {
    if (sourceFilter === 'all') return usageData;
    return usageData.filter(record => record.source === sourceFilter);
  }, [usageData, sourceFilter]);
  
  // Use filteredData in render
}
```

### Large Datasets

- Virtualize table rows for >1000 records (use `react-window`)
- Paginate chart data beyond 90 days
- Lazy load badges (render only visible rows)

---

## 11. Implementation Checklist

### Week 1: Component Development (Days 1-5)

**Day 1-2: Badge Component**
- [ ] Create `SourceBadge.jsx` component
- [ ] Implement CSS styling with color variants
- [ ] Add size variants (small, medium, large)
- [ ] Add dark mode support
- [ ] Write unit tests (5+ tests)

**Day 3-4: Filter Component**
- [ ] Create `SourceFilter.jsx` component
- [ ] Implement button toggle logic
- [ ] Add CSS styling
- [ ] Integrate with dashboard state
- [ ] Write unit tests (5+ tests)

**Day 5: Chart.js Integration**
- [ ] Create `chartConfig.js` utility
- [ ] Implement custom point styles
- [ ] Enhance tooltip configuration
- [ ] Add legend customization
- [ ] Test chart rendering performance

### Week 2: Integration & Polish (Days 6-10)

**Day 6-7: Dashboard Integration**
- [ ] Add `SourceBadge` to usage table
- [ ] Add `SourceFilter` to dashboard header
- [ ] Update API service to include source in responses
- [ ] Wire up filtering logic
- [ ] Test filtering functionality

**Day 8: Analytics Page**
- [ ] Update chart with custom point styles
- [ ] Add enhanced tooltips
- [ ] Update legend with source indicators
- [ ] Test chart with mixed data sources

**Day 9: Manual Entry Modal**
- [ ] Add badge to modal header
- [ ] Add informational text about manual entries
- [ ] Update confirmation messages
- [ ] Test user flow

**Day 10: Testing & Documentation**
- [ ] Run full test suite
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Cross-browser testing
- [ ] Update user documentation
- [ ] Create screenshot/video demo

---

## 12. Success Metrics

### User Experience (30 days post-launch)
- **Target**: 95% of users correctly identify data sources in usability testing
- **Measurement**: 5-question survey to active users

### Performance
- **Target**: <50ms overhead for badge rendering
- **Measurement**: Chrome DevTools Performance profiling

### Adoption
- **Target**: 40% of users use source filtering feature
- **Measurement**: Track filter button clicks in analytics

### Quality
- **Target**: Zero accessibility violations (WCAG 2.1 AA)
- **Measurement**: Automated axe tests in CI

---

## 13. Future Enhancements

### Phase 4+ Ideas

**Confidence Scoring**
- Assign confidence score to each entry (0-100%)
- API data: 95-99% (high confidence)
- Manual entry: 60-80% (user-dependent)
- Imported data: 70-90% (validation-dependent)

**Edit History**
- Show "Last edited" timestamp on manual entries
- Display edit history in tooltip
- Allow reverting to previous values

**Advanced Filtering**
- Filter by date + source combination
- Saved filter presets
- Multi-criteria filtering (source + service + date range)

**Data Quality Indicators**
- Warning icon for suspicious data (e.g., unusually high cost)
- "Needs review" flag for manual entries >30 days old
- Auto-suggest API sync for services with available APIs

---

**Document Status**: ✅ Complete  
**Ready for Implementation**: Yes  
**Estimated Effort**: 1 week  
**Dependencies**: None  
**Risks**: None identified
