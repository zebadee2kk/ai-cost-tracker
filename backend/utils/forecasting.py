"""
Forecasting utilities.

Provides linear regression-based cost forecasting and accuracy metrics.

Functions
---------
linear_forecast(data, horizon)
    Predict costs over a future horizon using OLS linear regression on daily data.

calculate_mape(actual, predicted)
    Mean Absolute Percentage Error between two equal-length sequences.

calculate_moving_average(data, window)
    Simple moving averages over a sorted daily-cost series.

calculate_growth_rate(data)
    Compound daily growth rate between first and last observations.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def linear_forecast(
    data: Dict[str, float],
    horizon: int = 30,
) -> Dict:
    """
    Fit a linear regression on historical daily cost data and forecast
    *horizon* days into the future.

    Parameters
    ----------
    data : dict
        Mapping of ISO date string → daily cost, e.g. {"2026-01-01": 3.50, ...}.
        Keys must be sortable ISO-8601 date strings.
    horizon : int
        Number of future days to forecast (default 30, max 90).

    Returns
    -------
    dict with keys:
        "forecast"      – list of {"date": str, "predicted_cost": float,
                                   "lower_bound": float, "upper_bound": float}
        "slope"         – regression slope ($ / day)
        "intercept"     – regression intercept
        "r_squared"     – R² goodness-of-fit
        "data_points"   – number of historical points used
        "confidence_pct"– simple confidence score 0-100 based on R² and data volume
    """
    horizon = min(max(1, horizon), 90)

    if not data:
        return _empty_forecast(horizon)

    sorted_dates = sorted(data.keys())
    if len(sorted_dates) < 2:
        return _empty_forecast(horizon)

    # Convert to numeric x (day index) and y (cost)
    x = np.arange(len(sorted_dates), dtype=float)
    y = np.array([data[d] for d in sorted_dates], dtype=float)

    # Ordinary least squares
    coeffs = np.polyfit(x, y, deg=1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])

    # R² calculation
    y_pred_hist = np.polyval(coeffs, x)
    ss_res = float(np.sum((y - y_pred_hist) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Residual standard error for confidence bands
    residuals = y - y_pred_hist
    residual_std = float(np.std(residuals, ddof=2)) if len(residuals) > 2 else 0.0
    # 1.96 sigma ≈ 95% interval
    confidence_width = 1.96 * residual_std

    # Build forecast
    last_date = date.fromisoformat(sorted_dates[-1])
    n = len(sorted_dates)

    forecast = []
    for i in range(1, horizon + 1):
        future_x = n - 1 + i
        predicted = float(np.polyval(coeffs, future_x))
        predicted = max(0.0, predicted)  # costs can't be negative

        forecast.append(
            {
                "date": (last_date + timedelta(days=i)).isoformat(),
                "predicted_cost": round(predicted, 4),
                "lower_bound": round(max(0.0, predicted - confidence_width), 4),
                "upper_bound": round(predicted + confidence_width, 4),
            }
        )

    # Confidence score: blend R² (weight 0.7) + data_volume factor (weight 0.3)
    data_volume_factor = min(1.0, len(sorted_dates) / 30.0)
    confidence_pct = round((0.7 * max(0.0, r_squared) + 0.3 * data_volume_factor) * 100, 1)

    return {
        "forecast": forecast,
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "r_squared": round(r_squared, 4),
        "data_points": len(sorted_dates),
        "confidence_pct": confidence_pct,
    }


def calculate_mape(
    actual: List[float], predicted: List[float]
) -> float:
    """
    Mean Absolute Percentage Error (MAPE).

    Parameters
    ----------
    actual, predicted : list of float
        Must have the same length.  Zero actual values are skipped to avoid
        division-by-zero.

    Returns
    -------
    float
        MAPE as a percentage (0-100+).  Returns 0.0 if no valid pairs.
    """
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must have the same length.")

    errors = []
    for a, p in zip(actual, predicted):
        if a != 0:
            errors.append(abs((a - p) / a) * 100)

    return float(np.mean(errors)) if errors else 0.0


def calculate_moving_average(
    data: Dict[str, float], window: int = 7
) -> List[Dict]:
    """
    Calculate a simple (trailing) moving average over daily costs.

    Parameters
    ----------
    data : dict  {iso_date: cost}
    window : int  rolling window size in days

    Returns
    -------
    list of {"date": str, "cost": float, "moving_avg": float | None}
    """
    sorted_dates = sorted(data.keys())
    result = []
    for i, d in enumerate(sorted_dates):
        if i < window - 1:
            moving_avg = None
        else:
            window_values = [data[sorted_dates[j]] for j in range(i - window + 1, i + 1)]
            moving_avg = round(float(np.mean(window_values)), 4)
        result.append(
            {
                "date": d,
                "cost": data[d],
                "moving_avg": moving_avg,
            }
        )
    return result


def calculate_growth_rate(data: Dict[str, float]) -> Optional[float]:
    """
    Compound daily growth rate between the first and last observations.

    Returns None if fewer than 2 data points or if first cost is zero.
    """
    sorted_dates = sorted(data.keys())
    if len(sorted_dates) < 2:
        return None

    first_cost = data[sorted_dates[0]]
    last_cost = data[sorted_dates[-1]]
    n_days = len(sorted_dates) - 1

    if first_cost <= 0 or n_days <= 0:
        return None

    cagr = (last_cost / first_cost) ** (1.0 / n_days) - 1.0
    return round(float(cagr) * 100, 4)  # return as percentage


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _empty_forecast(horizon: int) -> Dict:
    """Return a safe empty forecast structure."""
    return {
        "forecast": [],
        "slope": 0.0,
        "intercept": 0.0,
        "r_squared": 0.0,
        "data_points": 0,
        "confidence_pct": 0.0,
    }
