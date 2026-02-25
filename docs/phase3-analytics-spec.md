# Phase 3: Enhanced Analytics & Forecasting - Technical Specification

**Created**: February 25, 2026  
**Priority**: P2  
**Effort**: 2-3 weeks  
**Dependencies**: Export system (optional - for data validation)

---

## 1. Problem Statement

### Business Need
Users need predictive insights to:
- Forecast future costs (30/60/90 days)
- Detect unusual usage patterns (anomalies)
- Plan budgets proactively
- Identify cost optimization opportunities

### Current Limitations
- Only historical data shown
- No cost projections
- No anomaly detection
- Limited trend analysis
- No budget burn rate tracking

### Success Criteria
- <15% MAPE (Mean Absolute Percentage Error) for 30-day forecasts
- <10% false positive rate for anomaly detection
- <2 seconds page load time for analytics dashboard
- 70%+ user adoption of forecasting features

---

## 2. Feature Overview

### Phase 3 Analytics Features

| Feature | Description | Complexity | Priority |
|---------|-------------|------------|----------|
| **Cost Forecasting** | 30/60/90-day cost predictions | Medium | P2 |
| **Anomaly Detection** | Statistical outlier identification | Medium | P2 |
| **Trend Analysis** | Month-over-month, QoQ comparisons | Low | P2 |
| **Budget Tracking** | Visual burn rate and progress | Low | P2 |
| **Model Breakdown** | Cost by model (GPT-4 vs Claude vs Haiku) | Low | P2 |
| **Usage Heatmap** | Day-of-week and hour-of-day patterns | Medium | P3 |

---

## 3. Cost Forecasting

### Algorithm Selection

**Approach Comparison**:

| Method | Pros | Cons | Accuracy | Complexity | Recommendation |
|--------|------|------|----------|------------|----------------|
| **Moving Average** | Simple, fast | No trend capture | Low | Low | Baseline only |
| **Linear Regression** | Fast, interpretable | Assumes linear trend | Medium | Low | ✅ **MVP Choice** |
| **Exponential Smoothing** | Handles trends | Requires tuning | Medium-High | Medium | Phase 4 upgrade |
| **ARIMA** | Handles seasonality | Complex, slow | High | High | Enterprise feature |
| **Prophet (Meta)** | Auto-detects patterns | Requires 1+ year data | High | Medium | Phase 4 option |

**Recommendation**: Start with **Linear Regression** for MVP. Simple, fast, and sufficient for most use cases.

### Implementation (Linear Regression)

```python
# services/analytics/forecaster.py
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

class CostForecaster:
    def __init__(self, historical_data: List[Dict]):
        """
        Args:
            historical_data: List of dicts with 'date' and 'cost' keys
                [{"date": "2026-01-01", "cost": 12.50}, ...]
        """
        self.data = historical_data
        self.model = LinearRegression()
        self.X = None
        self.y = None
    
    def prepare_data(self):
        """Convert dates to numeric features."""
        dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in self.data]
        base_date = min(dates)
        
        # Days since first date
        self.X = np.array([(d - base_date).days for d in dates]).reshape(-1, 1)
        self.y = np.array([d['cost'] for d in self.data])
    
    def train(self):
        """Train the linear regression model."""
        if self.X is None:
            self.prepare_data()
        
        self.model.fit(self.X, self.y)
    
    def predict(self, days_ahead: int = 30) -> Dict:
        """
        Predict future costs.
        
        Args:
            days_ahead: Number of days to forecast (30, 60, or 90)
        
        Returns:
            {
                'predictions': [(date, cost), ...],
                'total_forecasted': float,
                'daily_rate': float,
                'confidence_interval': (lower, upper),
                'mape': float (if validation data available)
            }
        """
        if self.X is None:
            self.prepare_data()
        
        # Get last date from training data
        last_date = datetime.strptime(self.data[-1]['date'], '%Y-%m-%d')
        last_X_value = self.X[-1][0]
        
        # Generate future dates
        future_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') 
                       for i in range(days_ahead)]
        future_X = np.array([last_X_value + i + 1 for i in range(days_ahead)]).reshape(-1, 1)
        
        # Predict
        predictions = self.model.predict(future_X)
        
        # Calculate confidence interval (simplified - assumes normal distribution)
        residuals = self.y - self.model.predict(self.X)
        std_error = np.std(residuals)
        confidence_interval = (
            np.sum(predictions) - 1.96 * std_error * days_ahead,
            np.sum(predictions) + 1.96 * std_error * days_ahead
        )
        
        return {
            'predictions': list(zip(future_dates, predictions.tolist())),
            'total_forecasted': float(np.sum(predictions)),
            'daily_rate': float(self.model.coef_[0]),
            'confidence_interval': {
                'lower': float(confidence_interval[0]),
                'upper': float(confidence_interval[1])
            },
            'slope': float(self.model.coef_[0]),
            'intercept': float(self.model.intercept_)
        }
    
    def calculate_mape(self, test_data: List[Dict]) -> float:
        """
        Calculate Mean Absolute Percentage Error on test data.
        
        Args:
            test_data: List of actual values to compare against
        
        Returns:
            MAPE as percentage (e.g., 12.5 for 12.5% error)
        """
        actual = np.array([d['cost'] for d in test_data])
        
        # Prepare X values for test data
        base_date = datetime.strptime(self.data[0]['date'], '%Y-%m-%d')
        test_dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in test_data]
        test_X = np.array([(d - base_date).days for d in test_dates]).reshape(-1, 1)
        
        predicted = self.model.predict(test_X)
        
        # Avoid division by zero
        mask = actual != 0
        mape = np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
        
        return float(mape)
```

### API Endpoint

```python
# routes/analytics.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import UsageRecord, Account
from services.analytics.forecaster import CostForecaster

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/analytics/forecast', methods=['GET'])
@jwt_required()
def get_forecast():
    """
    Get cost forecast for specified period.
    
    Query params:
        - account_id: int (optional - defaults to all accounts)
        - days_ahead: int (30, 60, or 90 - default 30)
        - include_confidence: bool (default true)
    
    Returns:
        {
            "forecast": {
                "predictions": [["2026-03-01", 12.50], ...],
                "total_forecasted": 375.00,
                "daily_rate": 12.50,
                "confidence_interval": {"lower": 350.00, "upper": 400.00}
            },
            "historical_summary": {
                "total_days": 60,
                "total_cost": 750.00,
                "average_daily": 12.50,
                "trend": "increasing"  # or "decreasing" or "stable"
            }
        }
    """
    user_id = get_jwt_identity()
    account_id = request.args.get('account_id', type=int)
    days_ahead = request.args.get('days_ahead', type=int, default=30)
    
    if days_ahead not in [30, 60, 90]:
        return jsonify({"error": "days_ahead must be 30, 60, or 90"}), 400
    
    # Fetch historical data (last 90 days minimum for good predictions)
    query = UsageRecord.query.join(Account).filter(Account.user_id == user_id)
    
    if account_id:
        query = query.filter(UsageRecord.account_id == account_id)
    
    # Group by date and sum costs
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    
    results = query.filter(UsageRecord.timestamp >= ninety_days_ago) \
                   .with_entities(
                       func.date(UsageRecord.timestamp).label('date'),
                       func.sum(UsageRecord.cost).label('total_cost')
                   ) \
                   .group_by(func.date(UsageRecord.timestamp)) \
                   .order_by('date') \
                   .all()
    
    if len(results) < 14:
        return jsonify({
            "error": "Insufficient data for forecasting. Need at least 14 days of historical data."
        }), 400
    
    # Prepare data for forecaster
    historical_data = [
        {"date": str(r.date), "cost": float(r.total_cost)}
        for r in results
    ]
    
    # Train and predict
    forecaster = CostForecaster(historical_data)
    forecaster.train()
    forecast = forecaster.predict(days_ahead)
    
    # Calculate historical summary
    total_cost = sum(d['cost'] for d in historical_data)
    average_daily = total_cost / len(historical_data)
    
    # Determine trend
    if forecast['slope'] > 0.5:
        trend = "increasing"
    elif forecast['slope'] < -0.5:
        trend = "decreasing"
    else:
        trend = "stable"
    
    return jsonify({
        "forecast": forecast,
        "historical_summary": {
            "total_days": len(historical_data),
            "total_cost": total_cost,
            "average_daily": average_daily,
            "trend": trend
        }
    })
```

---

## 4. Anomaly Detection

### Algorithm (Z-Score Method)

```python
# services/analytics/anomaly_detector.py
import numpy as np
from typing import List, Dict
from datetime import datetime

class AnomalyDetector:
    def __init__(self, threshold: float = 3.0):
        """
        Args:
            threshold: Z-score threshold (default 3 = 99.7% confidence)
        """
        self.threshold = threshold
    
    def detect(self, usage_data: List[Dict]) -> List[Dict]:
        """
        Detect anomalies in usage data using Z-score method.
        
        Args:
            usage_data: List of dicts with 'date' and 'cost' keys
        
        Returns:
            List of anomaly records:
            [
                {
                    "date": "2026-02-15",
                    "cost": 150.00,
                    "z_score": 4.5,
                    "severity": "high",  # "medium" or "high"
                    "deviation": 100.00,  # Dollars above/below mean
                    "percentage_deviation": 200.0  # Percentage above/below mean
                },
                ...
            ]
        """
        if len(usage_data) < 7:
            return []  # Need at least 7 days for meaningful statistics
        
        costs = np.array([d['cost'] for d in usage_data])
        
        # Calculate statistics
        mean = np.mean(costs)
        std = np.std(costs)
        
        if std == 0:
            return []  # No variation, no anomalies
        
        anomalies = []
        
        for i, record in enumerate(usage_data):
            cost = record['cost']
            z_score = (cost - mean) / std
            
            if abs(z_score) > self.threshold:
                severity = "high" if abs(z_score) > 5 else "medium"
                deviation = cost - mean
                percentage_deviation = (deviation / mean) * 100 if mean > 0 else 0
                
                anomalies.append({
                    "date": record['date'],
                    "cost": cost,
                    "z_score": float(z_score),
                    "severity": severity,
                    "deviation": float(deviation),
                    "percentage_deviation": float(percentage_deviation),
                    "mean": float(mean),
                    "std": float(std)
                })
        
        return anomalies
    
    def detect_spike(self, usage_data: List[Dict], window_size: int = 7) -> List[Dict]:
        """
        Detect sudden spikes by comparing each day to rolling average.
        
        Args:
            usage_data: List of dicts with 'date' and 'cost' keys
            window_size: Days to include in rolling average
        
        Returns:
            List of spike events
        """
        if len(usage_data) < window_size + 1:
            return []
        
        costs = np.array([d['cost'] for d in usage_data])
        spikes = []
        
        for i in range(window_size, len(costs)):
            window = costs[i-window_size:i]
            window_mean = np.mean(window)
            window_std = np.std(window)
            
            current = costs[i]
            
            # Spike = current value > mean + 2*std
            if window_std > 0 and current > (window_mean + 2 * window_std):
                spikes.append({
                    "date": usage_data[i]['date'],
                    "cost": float(current),
                    "expected_range": {
                        "lower": float(window_mean - 2 * window_std),
                        "upper": float(window_mean + 2 * window_std)
                    },
                    "spike_magnitude": float(current - window_mean),
                    "spike_percentage": float(((current - window_mean) / window_mean) * 100) if window_mean > 0 else 0
                })
        
        return spikes
```

### API Endpoint

```python
# routes/analytics.py (continued)
@analytics_bp.route('/api/analytics/anomalies', methods=['GET'])
@jwt_required()
def get_anomalies():
    """
    Detect anomalies in usage data.
    
    Query params:
        - account_id: int (optional)
        - days: int (default 90 - lookback period)
        - threshold: float (default 3.0 - Z-score threshold)
    
    Returns:
        {
            "anomalies": [
                {"date": "2026-02-15", "cost": 150.00, "z_score": 4.5, ...},
                ...
            ],
            "spikes": [
                {"date": "2026-02-20", "cost": 120.00, "spike_magnitude": 80.00, ...},
                ...
            ],
            "summary": {
                "total_anomalies": 3,
                "severity_breakdown": {"high": 1, "medium": 2}
            }
        }
    """
    user_id = get_jwt_identity()
    account_id = request.args.get('account_id', type=int)
    days = request.args.get('days', type=int, default=90)
    threshold = request.args.get('threshold', type=float, default=3.0)
    
    # Fetch historical data
    query = UsageRecord.query.join(Account).filter(Account.user_id == user_id)
    
    if account_id:
        query = query.filter(UsageRecord.account_id == account_id)
    
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    lookback_date = datetime.utcnow() - timedelta(days=days)
    
    results = query.filter(UsageRecord.timestamp >= lookback_date) \
                   .with_entities(
                       func.date(UsageRecord.timestamp).label('date'),
                       func.sum(UsageRecord.cost).label('total_cost')
                   ) \
                   .group_by(func.date(UsageRecord.timestamp)) \
                   .order_by('date') \
                   .all()
    
    if len(results) < 7:
        return jsonify({
            "error": "Insufficient data for anomaly detection. Need at least 7 days."
        }), 400
    
    # Prepare data
    usage_data = [
        {"date": str(r.date), "cost": float(r.total_cost)}
        for r in results
    ]
    
    # Detect anomalies and spikes
    detector = AnomalyDetector(threshold=threshold)
    anomalies = detector.detect(usage_data)
    spikes = detector.detect_spike(usage_data)
    
    # Calculate summary
    severity_breakdown = {}
    for anomaly in anomalies:
        severity = anomaly['severity']
        severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
    
    return jsonify({
        "anomalies": anomalies,
        "spikes": spikes,
        "summary": {
            "total_anomalies": len(anomalies),
            "total_spikes": len(spikes),
            "severity_breakdown": severity_breakdown
        }
    })
```

---

## 5. Frontend Dashboard

### Enhanced Analytics Page

```jsx
// pages/EnhancedAnalyticsPage.jsx
import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import api from '../services/api';
import './EnhancedAnalyticsPage.css';

function EnhancedAnalyticsPage() {
  const [forecastData, setForecastData] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [historicalData, setHistoricalData] = useState([]);
  const [forecastDays, setForecastDays] = useState(30);
  
  useEffect(() => {
    loadAnalytics();
  }, [forecastDays]);
  
  const loadAnalytics = async () => {
    // Load historical data
    const usage = await api.get('/api/usage');
    setHistoricalData(usage.data);
    
    // Load forecast
    const forecast = await api.get(`/api/analytics/forecast?days_ahead=${forecastDays}`);
    setForecastData(forecast.data);
    
    // Load anomalies
    const anom = await api.get('/api/analytics/anomalies');
    setAnomalies(anom.data.anomalies);
  };
  
  // Prepare chart data
  const chartData = {
    datasets: [
      {
        label: 'Historical Cost',
        data: historicalData.map(d => ({ x: d.date, y: d.cost })),
        borderColor: '#2196F3',
        backgroundColor: 'rgba(33, 150, 243, 0.1)',
        fill: true
      },
      {
        label: `Forecast (${forecastDays} days)`,
        data: forecastData?.forecast.predictions.map(([date, cost]) => ({ x: date, y: cost })) || [],
        borderColor: '#FF9800',
        borderDash: [5, 5],
        backgroundColor: 'rgba(255, 152, 0, 0.1)',
        fill: true
      },
      {
        label: 'Anomalies',
        data: anomalies.map(a => ({ x: a.date, y: a.cost })),
        pointBackgroundColor: '#F44336',
        pointRadius: 8,
        pointStyle: 'triangle',
        showLine: false
      }
    ]
  };
  
  return (
    <div className="analytics-page">
      <h1>📊 Enhanced Analytics</h1>
      
      {/* Forecast Summary Cards */}
      <div className="summary-cards">
        <div className="card">
          <h3>30-Day Forecast</h3>
          <p className="value">${forecastData?.forecast.total_forecasted.toFixed(2)}</p>
          <p className="subtitle">
            {forecastData?.historical_summary.trend === 'increasing' ? '📈' : '📉'} 
            {forecastData?.historical_summary.trend}
          </p>
        </div>
        
        <div className="card">
          <h3>Daily Burn Rate</h3>
          <p className="value">${forecastData?.forecast.daily_rate.toFixed(2)}/day</p>
          <p className="subtitle">Average projected cost</p>
        </div>
        
        <div className="card">
          <h3>Confidence Range</h3>
          <p className="value">
            ${forecastData?.forecast.confidence_interval.lower.toFixed(2)} - 
            ${forecastData?.forecast.confidence_interval.upper.toFixed(2)}
          </p>
          <p className="subtitle">95% confidence interval</p>
        </div>
        
        <div className="card alert">
          <h3>Anomalies Detected</h3>
          <p className="value">{anomalies.length}</p>
          <p className="subtitle">Unusual usage patterns</p>
        </div>
      </div>
      
      {/* Chart Controls */}
      <div className="chart-controls">
        <label>
          Forecast Period:
          <select value={forecastDays} onChange={(e) => setForecastDays(Number(e.target.value))}>
            <option value={30}>30 Days</option>
            <option value={60}>60 Days</option>
            <option value={90}>90 Days</option>
          </select>
        </label>
      </div>
      
      {/* Main Chart */}
      <div className="chart-container">
        <Line data={chartData} options={chartOptions} />
      </div>
      
      {/* Anomalies Table */}
      {anomalies.length > 0 && (
        <div className="anomalies-section">
          <h2>🚨 Detected Anomalies</h2>
          <table className="anomalies-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Cost</th>
                <th>Severity</th>
                <th>Deviation</th>
                <th>Z-Score</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((anomaly, i) => (
                <tr key={i} className={`severity-${anomaly.severity}`}>
                  <td>{anomaly.date}</td>
                  <td>${anomaly.cost.toFixed(2)}</td>
                  <td>
                    {anomaly.severity === 'high' ? '🔴' : '🟡'} {anomaly.severity}
                  </td>
                  <td>{anomaly.deviation > 0 ? '+' : ''}${anomaly.deviation.toFixed(2)}</td>
                  <td>{anomaly.z_score.toFixed(2)}σ</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default EnhancedAnalyticsPage;
```

---

## 6. Testing Strategy

### Unit Tests

```python
# tests/test_forecaster.py
import pytest
from services.analytics.forecaster import CostForecaster

def test_forecaster_basic():
    # Generate synthetic data (linear trend)
    data = [{"date": f"2026-01-{i+1:02d}", "cost": 10.0 + i * 0.5} for i in range(30)]
    
    forecaster = CostForecaster(data)
    forecaster.train()
    
    forecast = forecaster.predict(30)
    
    assert 'predictions' in forecast
    assert len(forecast['predictions']) == 30
    assert forecast['total_forecasted'] > 0
    assert forecast['daily_rate'] > 0

def test_forecaster_accuracy():
    # Use first 60 days to train, next 30 to test
    all_data = [{"date": f"2026-01-{i+1:02d}", "cost": 10.0 + i * 0.5} for i in range(90)]
    train_data = all_data[:60]
    test_data = all_data[60:]
    
    forecaster = CostForecaster(train_data)
    forecaster.train()
    
    mape = forecaster.calculate_mape(test_data)
    
    assert mape < 15.0  # Less than 15% error
```

### Integration Tests

```python
# tests/test_analytics_endpoints.py
def test_forecast_endpoint(client, auth_headers, seed_usage_data):
    response = client.get('/api/analytics/forecast?days_ahead=30', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json
    
    assert 'forecast' in data
    assert 'historical_summary' in data
    assert len(data['forecast']['predictions']) == 30

def test_anomalies_endpoint(client, auth_headers, seed_usage_data_with_spike):
    response = client.get('/api/analytics/anomalies', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json
    
    assert 'anomalies' in data
    assert data['summary']['total_anomalies'] > 0
```

---

## 7. Implementation Checklist

### Week 1: Forecasting (Days 1-5)
- [ ] Implement CostForecaster class
- [ ] Add `/api/analytics/forecast` endpoint
- [ ] Write unit tests for forecaster
- [ ] Test with real usage data
- [ ] Validate MAPE <15%

### Week 2: Anomaly Detection (Days 6-10)
- [ ] Implement AnomalyDetector class
- [ ] Add `/api/analytics/anomalies` endpoint
- [ ] Write unit tests for detector
- [ ] Test with synthetic spikes
- [ ] Tune Z-score threshold

### Week 3: Frontend & Polish (Days 11-15)
- [ ] Create EnhancedAnalyticsPage component
- [ ] Add forecast chart with confidence bands
- [ ] Add anomaly markers to chart
- [ ] Create summary cards
- [ ] Add anomalies table
- [ ] Test chart performance with 90+ days data
- [ ] Update documentation
- [ ] Deploy to staging

---

## 8. Success Metrics

### Forecast Accuracy (after 30 days)
- **Target**: <15% MAPE
- **Measurement**: Compare forecasts to actual costs monthly

### Anomaly Detection Quality
- **Target**: <10% false positive rate
- **Measurement**: User feedback + manual review

### Performance
- **Target**: <2s page load
- **Measurement**: Chrome DevTools Performance tab

### Adoption
- **Target**: 70% of users view forecast
- **Measurement**: Analytics on `/analytics` page views

---

**Document Status**: ✅ Complete  
**Ready for Implementation**: Yes  
**Estimated Effort**: 2-3 weeks  
**Dependencies**: scikit-learn library  
**Risks**: Requires 14+ days historical data for accuracy
