# Phase 3: Enhanced Analytics & Forecasting - Technical Specification

**Feature Priority**: P2 (Nice to Have)  
**Estimated Effort**: 2-3 weeks  
**Dependencies**: Export system (for data processing)  
**Target Sprint**: 3.3 (Weeks 7-9)

---

## 1. Problem Statement

### User Need
Users need predictive insights to:
- **Forecast future costs**: Estimate month-end/quarter-end spending
- **Detect anomalies**: Identify unusual usage patterns early
- **Plan budgets**: Allocate resources based on trends
- **Optimize spending**: Identify cost-saving opportunities

### Current Limitation
- No cost forecasting beyond simple multiplication
- No anomaly detection for usage spikes
- Limited trend analysis (month-over-month)
- No predictive alerts

### Business Value
- **Medium-High**: Differentiates from basic cost trackers
- Enables proactive cost management
- Reduces surprise overages
- Supports data-driven decision-making
- Critical for enterprise adoption

---

## 2. Forecasting Algorithms

### Algorithm Comparison

| Algorithm | Complexity | Accuracy | Speed | Best For |
|-----------|------------|----------|-------|----------|
| **Moving Average** | Low | Low-Medium | Fast | Stable patterns |
| **Linear Regression** | Low | Medium | Fast | Trending data |
| **ARIMA** | High | High | Slow | Seasonal data |
| **Prophet (Facebook)** | Medium | High | Medium | Business data with holidays |
| **LSTM (Deep Learning)** | Very High | Very High | Slow | Large datasets |

### Recommended Approach: **Linear Regression** ✅

**Why?**
- Simple to implement and understand
- Fast computation (<100ms)
- No external dependencies beyond scikit-learn
- Sufficient accuracy for monthly forecasts (<15% MAPE)
- Good baseline for Phase 3 MVP

**Future Enhancement**: Upgrade to ARIMA for seasonality detection in Phase 4

---

## 3. Cost Forecasting Implementation

### Linear Regression Model

```python
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from typing import Dict, List

class CostForecaster:
    """Forecast future costs using linear regression"""
    
    def __init__(self, historical_data: List[Dict]):
        """
        Args:
            historical_data: List of {date: str, cost: float}
        """
        self.data = sorted(historical_data, key=lambda x: x['date'])
        self.model = LinearRegression()
        self._train()
    
    def _train(self):
        """Train model on historical data"""
        if len(self.data) < 7:  # Need at least 7 days
            raise ValueError("Insufficient data for forecasting (minimum 7 days)")
        
        # Convert dates to numeric values (days since first data point)
        start_date = datetime.fromisoformat(self.data[0]['date'])
        X = np.array([
            (datetime.fromisoformat(d['date']) - start_date).days 
            for d in self.data
        ]).reshape(-1, 1)
        
        y = np.array([d['cost'] for d in self.data])
        
        self.model.fit(X, y)
        self.start_date = start_date
    
    def forecast(self, days_ahead: int = 30) -> Dict:
        """
        Predict costs for next N days
        
        Returns:
            {
                'daily_forecast': [{date: str, cost: float, confidence: str}],
                'total_forecast': float,
                'trend': 'increasing'|'decreasing'|'stable',
                'confidence_level': 'high'|'medium'|'low'
            }
        """
        # Get last historical date
        last_date = datetime.fromisoformat(self.data[-1]['date'])
        last_day_num = (last_date - self.start_date).days
        
        # Predict future days
        future_days = np.arange(
            last_day_num + 1, 
            last_day_num + days_ahead + 1
        ).reshape(-1, 1)
        
        predictions = self.model.predict(future_days)
        
        # Build forecast response
        daily_forecast = []
        for i, pred_cost in enumerate(predictions):
            date = last_date + timedelta(days=i+1)
            daily_forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'cost': max(0, pred_cost),  # Ensure non-negative
                'confidence': self._get_confidence(i, days_ahead)
            })
        
        return {
            'daily_forecast': daily_forecast,
            'total_forecast': max(0, sum(predictions)),
            'trend': self._determine_trend(),
            'confidence_level': self._overall_confidence(),
            'model_type': 'linear_regression',
            'r_squared': self.model.score(
                np.array([(datetime.fromisoformat(d['date']) - self.start_date).days 
                         for d in self.data]).reshape(-1, 1),
                np.array([d['cost'] for d in self.data])
            )
        }
    
    def _determine_trend(self) -> str:
        """Determine if costs are increasing, decreasing, or stable"""
        slope = self.model.coef_[0]
        
        if slope > 0.5:  # Increasing by >$0.50/day
            return 'increasing'
        elif slope < -0.5:  # Decreasing by >$0.50/day
            return 'decreasing'
        else:
            return 'stable'
    
    def _get_confidence(self, days_out: int, total_days: int) -> str:
        """Confidence decreases further into future"""
        ratio = days_out / total_days
        if ratio < 0.33:
            return 'high'
        elif ratio < 0.67:
            return 'medium'
        else:
            return 'low'
    
    def _overall_confidence(self) -> str:
        """Overall model confidence based on R-squared"""
        r2 = self.model.score(
            np.array([(datetime.fromisoformat(d['date']) - self.start_date).days 
                     for d in self.data]).reshape(-1, 1),
            np.array([d['cost'] for d in self.data])
        )
        
        if r2 > 0.8:
            return 'high'
        elif r2 > 0.5:
            return 'medium'
        else:
            return 'low'

# Usage example
historical_data = [
    {'date': '2026-02-01', 'cost': 10.50},
    {'date': '2026-02-02', 'cost': 12.30},
    # ... more data
]

forecaster = CostForecaster(historical_data)
forecast = forecaster.forecast(days_ahead=30)
print(f"30-day forecast: ${forecast['total_forecast']:.2f}")
print(f"Trend: {forecast['trend']}")
print(f"Confidence: {forecast['confidence_level']}")
```

### Forecast Accuracy Metric: MAPE

```python
def calculate_mape(actual: List[float], predicted: List[float]) -> float:
    """
    Mean Absolute Percentage Error
    Target: <15% for monthly forecasts
    """
    actual_arr = np.array(actual)
    predicted_arr = np.array(predicted)
    
    # Avoid division by zero
    non_zero_mask = actual_arr != 0
    
    mape = np.mean(
        np.abs((actual_arr[non_zero_mask] - predicted_arr[non_zero_mask]) / actual_arr[non_zero_mask])
    ) * 100
    
    return mape

# Example
actual = [10.5, 11.2, 12.0]
predicted = [10.8, 11.5, 11.8]
mape = calculate_mape(actual, predicted)
print(f"MAPE: {mape:.2f}%")  # Target: <15%
```

---

## 4. Anomaly Detection

### Z-Score Method (Recommended)

**Concept**: Identify data points that deviate significantly from the mean

**Formula**:
```
z_score = (x - μ) / σ

Where:
  x = current value
  μ = mean of historical values
  σ = standard deviation

Anomaly if |z_score| > 3 (99.7% confidence)
```

### Implementation

```python
import numpy as np
from typing import List, Dict
from datetime import datetime

class AnomalyDetector:
    """Detect usage anomalies using statistical methods"""
    
    def __init__(self, historical_data: List[Dict], threshold: float = 3.0):
        """
        Args:
            historical_data: List of {date: str, cost: float, tokens: int}
            threshold: Z-score threshold (default: 3.0 = 99.7% confidence)
        """
        self.data = historical_data
        self.threshold = threshold
        self.mean = np.mean([d['cost'] for d in historical_data])
        self.std = np.std([d['cost'] for d in historical_data])
    
    def detect_anomalies(self) -> List[Dict]:
        """Identify anomalous usage patterns"""
        if self.std == 0:  # No variance in data
            return []
        
        anomalies = []
        
        for record in self.data:
            cost = record['cost']
            z_score = (cost - self.mean) / self.std
            
            if abs(z_score) > self.threshold:
                anomalies.append({
                    'date': record['date'],
                    'cost': cost,
                    'tokens': record.get('tokens', 0),
                    'z_score': round(z_score, 2),
                    'severity': self._classify_severity(z_score),
                    'expected_range': {
                        'min': round(self.mean - (self.threshold * self.std), 2),
                        'max': round(self.mean + (self.threshold * self.std), 2)
                    },
                    'deviation_percentage': round(((cost - self.mean) / self.mean) * 100, 1)
                })
        
        return sorted(anomalies, key=lambda x: abs(x['z_score']), reverse=True)
    
    def _classify_severity(self, z_score: float) -> str:
        """Classify anomaly severity"""
        abs_z = abs(z_score)
        
        if abs_z > 5:
            return 'critical'  # Extremely rare event
        elif abs_z > 4:
            return 'high'
        elif abs_z > 3:
            return 'medium'
        else:
            return 'low'
    
    def check_latest(self, new_record: Dict) -> Dict:
        """Check if latest usage is anomalous"""
        cost = new_record['cost']
        z_score = (cost - self.mean) / self.std if self.std > 0 else 0
        
        is_anomaly = abs(z_score) > self.threshold
        
        return {
            'is_anomaly': is_anomaly,
            'z_score': round(z_score, 2),
            'severity': self._classify_severity(z_score) if is_anomaly else None,
            'message': self._generate_message(cost, z_score, is_anomaly)
        }
    
    def _generate_message(self, cost: float, z_score: float, is_anomaly: bool) -> str:
        """Generate human-readable anomaly message"""
        if not is_anomaly:
            return f"Usage is within normal range (${self.mean:.2f} ± ${3*self.std:.2f})"
        
        if z_score > 0:
            return f"Usage spike detected: ${cost:.2f} is {abs(z_score):.1f}σ above normal (${self.mean:.2f})"
        else:
            return f"Unusual low usage: ${cost:.2f} is {abs(z_score):.1f}σ below normal (${self.mean:.2f})"

# Usage example
historical = [
    {'date': '2026-02-01', 'cost': 10.50, 'tokens': 100000},
    {'date': '2026-02-02', 'cost': 11.20, 'tokens': 110000},
    {'date': '2026-02-03', 'cost': 12.00, 'tokens': 115000},
    {'date': '2026-02-04', 'cost': 50.00, 'tokens': 500000},  # Anomaly!
]

detector = AnomalyDetector(historical)
anomalies = detector.detect_anomalies()

for anomaly in anomalies:
    print(f"Anomaly on {anomaly['date']}: ${anomaly['cost']:.2f}")
    print(f"  Severity: {anomaly['severity']}")
    print(f"  Z-score: {anomaly['z_score']}")
    print(f"  Deviation: {anomaly['deviation_percentage']}%")
```

### Alternative: Rolling Window Z-Score

**For detecting recent changes**:
```python
def rolling_anomaly_detection(data: List[Dict], window_size: int = 7) -> List[Dict]:
    """Detect anomalies using rolling window statistics"""
    anomalies = []
    
    for i in range(window_size, len(data)):
        window = data[i-window_size:i]
        window_costs = [d['cost'] for d in window]
        
        mean = np.mean(window_costs)
        std = np.std(window_costs)
        
        current = data[i]
        z_score = (current['cost'] - mean) / std if std > 0 else 0
        
        if abs(z_score) > 3:
            anomalies.append({
                'date': current['date'],
                'cost': current['cost'],
                'z_score': z_score,
                'window_mean': mean,
                'window_std': std
            })
    
    return anomalies
```

---

## 5. Enhanced Dashboard Visualizations

### Forecast Line Chart (Chart.js)

```javascript
import { Line } from 'react-chartjs-2';

function ForecastChart({ historicalData, forecastData }) {
  const chartData = {
    labels: [
      ...historicalData.map(d => d.date),
      ...forecastData.map(d => d.date)
    ],
    datasets: [
      {
        label: 'Historical Cost',
        data: historicalData.map(d => ({ x: d.date, y: d.cost })),
        borderColor: '#2196F3',
        backgroundColor: 'rgba(33, 150, 243, 0.1)',
        fill: true
      },
      {
        label: 'Forecast',
        data: [
          // Connect to last historical point
          { 
            x: historicalData[historicalData.length - 1].date, 
            y: historicalData[historicalData.length - 1].cost 
          },
          ...forecastData.map(d => ({ x: d.date, y: d.cost }))
        ],
        borderColor: '#FF9800',
        backgroundColor: 'rgba(255, 152, 0, 0.05)',
        borderDash: [5, 5],  // Dashed line
        fill: true,
        pointRadius: 3,
        pointBackgroundColor: (context) => {
          const confidence = forecastData[context.dataIndex - 1]?.confidence;
          return confidence === 'high' ? '#FF9800' : 
                 confidence === 'medium' ? '#FFC107' : '#FFE082';
        }
      }
    ]
  };

  const options = {
    plugins: {
      title: { display: true, text: '30-Day Cost Forecast' },
      tooltip: {
        callbacks: {
          afterLabel: (context) => {
            if (context.datasetIndex === 1 && context.dataIndex > 0) {
              const confidence = forecastData[context.dataIndex - 1]?.confidence;
              return `Confidence: ${confidence || 'N/A'}`;
            }
          }
        }
      },
      annotation: {
        annotations: {
          line1: {
            type: 'line',
            xMin: historicalData[historicalData.length - 1].date,
            xMax: historicalData[historicalData.length - 1].date,
            borderColor: '#9E9E9E',
            borderWidth: 2,
            borderDash: [5, 5],
            label: {
              content: 'Forecast Start',
              enabled: true,
              position: 'top'
            }
          }
        }
      }
    },
    scales: {
      x: { 
        type: 'time',
        time: { unit: 'day' },
        title: { display: true, text: 'Date' }
      },
      y: { 
        title: { display: true, text: 'Cost (USD)' },
        beginAtZero: true
      }
    }
  };

  return <Line data={chartData} options={options} />;
}
```

### Anomaly Markers on Timeline

```javascript
function AnomalyChart({ usageData, anomalies }) {
  const anomalyDates = new Set(anomalies.map(a => a.date));
  
  const chartData = {
    labels: usageData.map(d => d.date),
    datasets: [{
      label: 'Daily Cost',
      data: usageData,
      borderColor: '#2196F3',
      pointRadius: (context) => {
        const date = context.label;
        return anomalyDates.has(date) ? 8 : 4;
      },
      pointBackgroundColor: (context) => {
        const date = context.label;
        if (anomalyDates.has(date)) {
          const anomaly = anomalies.find(a => a.date === date);
          return anomaly.severity === 'critical' ? '#F44336' : '#FF9800';
        }
        return '#2196F3';
      },
      pointStyle: (context) => {
        const date = context.label;
        return anomalyDates.has(date) ? 'triangle' : 'circle';
      }
    }]
  };

  return <Line data={chartData} />;
}
```

### Budget Gauge Component

```jsx
function BudgetGauge({ currentCost, budget }) {
  const percentage = (currentCost / budget) * 100;
  
  const getColor = () => {
    if (percentage < 70) return '#4CAF50';  // Green
    if (percentage < 90) return '#FF9800';  // Orange
    return '#F44336';  // Red
  };

  return (
    <div className="budget-gauge">
      <div className="gauge-container">
        <svg viewBox="0 0 200 100" className="gauge-svg">
          {/* Background arc */}
          <path
            d="M 20 90 A 80 80 0 0 1 180 90"
            fill="none"
            stroke="#E0E0E0"
            strokeWidth="15"
          />
          {/* Progress arc */}
          <path
            d="M 20 90 A 80 80 0 0 1 180 90"
            fill="none"
            stroke={getColor()}
            strokeWidth="15"
            strokeDasharray={`${percentage * 2.51} 251`}
            strokeLinecap="round"
          />
        </svg>
        <div className="gauge-value">
          <div className="percentage">{percentage.toFixed(0)}%</div>
          <div className="label">${currentCost.toFixed(2)} / ${budget.toFixed(2)}</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 6. API Endpoints

### Forecast Endpoint

#### `GET /api/analytics/forecast`
Get cost forecast for next N days

**Query Parameters**:
- `account_id` (optional): Specific account
- `days_ahead` (optional, default: 30): Forecast period

**Response**:
```json
{
  "forecast": {
    "daily_forecast": [
      {"date": "2026-02-26", "cost": 12.50, "confidence": "high"},
      {"date": "2026-02-27", "cost": 12.75, "confidence": "high"}
    ],
    "total_forecast": 375.00,
    "trend": "increasing",
    "confidence_level": "high",
    "model_type": "linear_regression",
    "r_squared": 0.85
  },
  "historical_summary": {
    "days_analyzed": 30,
    "avg_daily_cost": 11.50,
    "total_historical_cost": 345.00
  }
}
```

### Anomaly Detection Endpoint

#### `GET /api/analytics/anomalies`
Get detected anomalies

**Query Parameters**:
- `account_id` (optional): Specific account
- `start_date`, `end_date` (optional): Date range
- `min_severity` (optional): Filter by severity

**Response**:
```json
{
  "anomalies": [
    {
      "date": "2026-02-15",
      "cost": 50.00,
      "tokens": 500000,
      "z_score": 4.5,
      "severity": "high",
      "expected_range": {"min": 8.00, "max": 15.00},
      "deviation_percentage": 333.3
    }
  ],
  "total_anomalies": 1
}
```

### Trend Analysis Endpoint

#### `GET /api/analytics/trends`
Get usage and cost trends

**Response**:
```json
{
  "month_over_month": {
    "current_month": 345.00,
    "previous_month": 280.00,
    "change_percentage": 23.2,
    "trend": "increasing"
  },
  "week_over_week": {
    "current_week": 85.00,
    "previous_week": 78.00,
    "change_percentage": 9.0,
    "trend": "increasing"
  },
  "by_service": [
    {"service": "ChatGPT", "cost": 200.00, "percentage": 58.0},
    {"service": "Claude", "cost": 145.00, "percentage": 42.0}
  ]
}
```

---

## 7. Testing Strategy

### Unit Tests

```python
def test_forecast_linear_regression():
    """Test linear regression forecast"""
    historical = [
        {'date': f'2026-02-{str(i+1).zfill(2)}', 'cost': 10.0 + i}
        for i in range(15)
    ]
    
    forecaster = CostForecaster(historical)
    forecast = forecaster.forecast(days_ahead=7)
    
    assert len(forecast['daily_forecast']) == 7
    assert forecast['total_forecast'] > 0
    assert forecast['trend'] in ['increasing', 'decreasing', 'stable']

def test_anomaly_detection():
    """Test Z-score anomaly detection"""
    data = [
        {'date': f'2026-02-{str(i+1).zfill(2)}', 'cost': 10.0, 'tokens': 100000}
        for i in range(10)
    ]
    data.append({'date': '2026-02-11', 'cost': 50.0, 'tokens': 500000})  # Anomaly
    
    detector = AnomalyDetector(data)
    anomalies = detector.detect_anomalies()
    
    assert len(anomalies) == 1
    assert anomalies[0]['date'] == '2026-02-11'
    assert anomalies[0]['severity'] in ['medium', 'high', 'critical']

def test_forecast_insufficient_data():
    """Test forecast with insufficient data"""
    historical = [{'date': '2026-02-01', 'cost': 10.0}]  # Only 1 day
    
    with pytest.raises(ValueError):
        forecaster = CostForecaster(historical)
```

---

## 8. Implementation Effort

| Task | Effort | Notes |
|------|--------|-------|
| **Forecasting algorithm** | 3 days | Linear regression, API endpoint |
| **Anomaly detection** | 2 days | Z-score method, API endpoint |
| **Frontend charts** | 3 days | Forecast line, anomaly markers, gauge |
| **Trend analysis** | 2 days | Month-over-month, service breakdown |
| **Database optimization** | 1 day | Indexes for analytics queries |
| **Testing** | 2 days | Unit, integration tests |
| **Documentation** | 1 day | User guide, algorithm explanations |

**Total**: 14 days (2-3 weeks)

---

## 9. Acceptance Criteria

- ✅ 30/60/90-day cost forecasts accurate (<15% MAPE)
- ✅ Anomaly detection identifies usage spikes
- ✅ Forecast chart displays with confidence indicators
- ✅ Anomaly markers visible on timeline
- ✅ Budget gauge shows real-time progress
- ✅ Trend analysis (MoM, WoW) functional
- ✅ Performance <2s page load
- ✅ >80% test coverage
- ✅ Documentation complete

---

## 10. Future Enhancements (Phase 4)

- **ARIMA forecasting**: Better accuracy with seasonality
- **Prophet integration**: Facebook's time-series library
- **ML-based anomaly detection**: Isolation Forest, LSTM autoencoders
- **What-if scenarios**: "If usage doubles, cost = ?"
- **Cost optimization suggestions**: "Switch to Model X to save 30%"
- **Comparative benchmarks**: "You're spending 20% more than similar users"

---

**Status**: ✅ Ready for Implementation  
**Assigned To**: TBD  
**Sprint**: 3.3 (Weeks 7-9)
