import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  getUsageByService,
  getUsageForecast,
  getAnalyticsTrends,
  getAnalyticsForecast,
  getAnalyticsAnomalies,
  acknowledgeAnomaly,
} from "../services/api";
import { Pie, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Filler,
} from "chart.js";

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Filler
);

const COLORS = ["#533483", "#7b52ab", "#0f3460", "#16213e", "#e94560", "#2ecc71"];
const SEVERITY_COLORS = {
  low: "#f1c40f",
  medium: "#e67e22",
  high: "#e74c3c",
  critical: "#8e1c1c",
};

const PERIOD_OPTIONS = ["7d", "30d", "90d"];
const HORIZON_OPTIONS = [30, 60, 90];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeader({ title }) {
  return (
    <h2 style={{ fontSize: "1rem", marginBottom: "1rem", color: "var(--text)" }}>
      {title}
    </h2>
  );
}

function LoadingPlaceholder() {
  return (
    <p className="muted" style={{ textAlign: "center", padding: "1rem 0" }}>
      Loading…
    </p>
  );
}

function EmptyState({ message }) {
  return (
    <p className="muted" style={{ textAlign: "center", padding: "1rem 0" }}>
      {message}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Trend Chart
// ---------------------------------------------------------------------------

function TrendChart({ trends, period }) {
  if (!trends || trends.daily?.length === 0) {
    return <EmptyState message="No trend data for this period." />;
  }

  const labels = trends.daily.map((d) => d.date);

  const datasets = [
    {
      label: `Daily ${trends.metric === "tokens" ? "Tokens" : "Cost ($)"}`,
      data: trends.daily.map((d) => d.value),
      borderColor: "#7b52ab",
      backgroundColor: "rgba(123,82,171,0.08)",
      fill: true,
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
    },
    {
      label: "7-day MA",
      data: (trends.moving_avg_7d || []).map((d) => d.moving_avg),
      borderColor: "#e94560",
      borderDash: [4, 4],
      borderWidth: 1.5,
      fill: false,
      tension: 0.3,
      pointRadius: 0,
    },
  ];

  if (period !== "7d" && trends.moving_avg_30d?.length > 0) {
    datasets.push({
      label: "30-day MA",
      data: trends.moving_avg_30d.map((d) => d.moving_avg),
      borderColor: "#2ecc71",
      borderDash: [8, 4],
      borderWidth: 1.5,
      fill: false,
      tension: 0.3,
      pointRadius: 0,
    });
  }

  const options = {
    responsive: true,
    plugins: {
      legend: { labels: { color: "#e0e0e0", font: { size: 11 } } },
      tooltip: { mode: "index", intersect: false },
    },
    scales: {
      x: {
        ticks: { color: "#888", maxTicksLimit: 10, font: { size: 10 } },
        grid: { color: "rgba(255,255,255,0.05)" },
      },
      y: {
        ticks: { color: "#888", font: { size: 10 } },
        grid: { color: "rgba(255,255,255,0.05)" },
        beginAtZero: true,
      },
    },
  };

  return (
    <Line data={{ labels, datasets }} options={options} data-testid="trend-chart" />
  );
}

// ---------------------------------------------------------------------------
// Forecast Chart
// ---------------------------------------------------------------------------

function ForecastChart({ historical, forecast }) {
  if (!forecast || forecast.length === 0) {
    return <EmptyState message="Insufficient data to forecast." />;
  }

  const histLabels = (historical || []).map((d) => d.date);
  const fcLabels = forecast.map((d) => d.date);
  const allLabels = [...histLabels, ...fcLabels];

  const histValues = [
    ...(historical || []).map((d) => d.value),
    ...Array(fcLabels.length).fill(null),
  ];
  const predicted = [
    ...Array(histLabels.length).fill(null),
    ...forecast.map((d) => d.predicted_cost),
  ];
  const lower = [
    ...Array(histLabels.length).fill(null),
    ...forecast.map((d) => d.lower_bound),
  ];
  const upper = [
    ...Array(histLabels.length).fill(null),
    ...forecast.map((d) => d.upper_bound),
  ];

  const datasets = [
    {
      label: "Historical Cost ($)",
      data: histValues,
      borderColor: "#7b52ab",
      backgroundColor: "rgba(123,82,171,0.08)",
      fill: false,
      tension: 0.3,
      pointRadius: 2,
    },
    {
      label: "Forecast ($)",
      data: predicted,
      borderColor: "#e94560",
      borderDash: [6, 3],
      borderWidth: 2,
      fill: false,
      tension: 0.3,
      pointRadius: 0,
    },
    {
      label: "Upper Bound",
      data: upper,
      borderColor: "rgba(233,69,96,0.25)",
      backgroundColor: "rgba(233,69,96,0.1)",
      fill: "+1",
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 1,
    },
    {
      label: "Lower Bound",
      data: lower,
      borderColor: "rgba(233,69,96,0.25)",
      fill: false,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 1,
    },
  ];

  const options = {
    responsive: true,
    plugins: {
      legend: { labels: { color: "#e0e0e0", font: { size: 11 } } },
      tooltip: { mode: "index", intersect: false },
    },
    scales: {
      x: {
        ticks: { color: "#888", maxTicksLimit: 12, font: { size: 10 } },
        grid: { color: "rgba(255,255,255,0.05)" },
      },
      y: {
        ticks: { color: "#888", font: { size: 10 } },
        grid: { color: "rgba(255,255,255,0.05)" },
        beginAtZero: true,
      },
    },
  };

  return (
    <Line
      data={{ labels: allLabels, datasets }}
      options={options}
      data-testid="forecast-chart"
    />
  );
}

// ---------------------------------------------------------------------------
// Anomaly List
// ---------------------------------------------------------------------------

function AnomalyList({ anomalies, onAcknowledge }) {
  if (!anomalies || anomalies.length === 0) {
    return <EmptyState message="No anomalies detected." />;
  }

  return (
    <div data-testid="anomaly-list">
      {anomalies.map((a) => (
        <div
          key={a.id}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            padding: "0.6rem 0",
            borderBottom: "1px solid var(--border)",
            gap: "0.5rem",
          }}
        >
          <div style={{ flex: 1 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
                marginBottom: "0.2rem",
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: SEVERITY_COLORS[a.severity] || "#888",
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>
                {a.anomaly_date}
              </span>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: 3,
                  background: (SEVERITY_COLORS[a.severity] || "#888") + "33",
                  color: SEVERITY_COLORS[a.severity] || "#888",
                  textTransform: "uppercase",
                  letterSpacing: "0.03em",
                }}
              >
                {a.severity}
              </span>
            </div>
            <div style={{ fontSize: "0.78rem", color: "#aaa" }}>
              ${a.daily_cost?.toFixed(4)} vs baseline ${a.baseline_mean?.toFixed(4)}{" "}
              (z={a.z_score?.toFixed(2)})
            </div>
          </div>
          {!a.is_acknowledged && (
            <button
              className="btn-ghost"
              style={{ fontSize: "0.72rem", padding: "0.2rem 0.5rem" }}
              onClick={() => onAcknowledge(a.id)}
            >
              Dismiss
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main AnalyticsPage
// ---------------------------------------------------------------------------

export default function AnalyticsPage() {
  // Legacy data (service pie + simple projections)
  const [byService, setByService] = useState([]);
  const [legacyForecasts, setLegacyForecasts] = useState([]);

  // Account selector
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);

  // Controls
  const [period, setPeriod] = useState("30d");
  const [horizon, setHorizon] = useState(30);

  // Data
  const [trends, setTrends] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [anomalies, setAnomalies] = useState([]);

  // Loading flags
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [loadingAnomalies, setLoadingAnomalies] = useState(false);

  // Load legacy data + build account list on mount
  useEffect(() => {
    Promise.all([getUsageByService(), getUsageForecast()])
      .then(([svcRes, fcRes]) => {
        setByService(svcRes.data.by_service || []);
        const fcList = fcRes.data.forecasts || [];
        setLegacyForecasts(fcList);
        if (fcList.length > 0) {
          setSelectedAccount(fcList[0].account_id);
          setAccounts(fcList.map((f) => ({ id: f.account_id, name: f.account_name })));
        }
      })
      .catch(() => {});
  }, []);

  // Trends
  const fetchTrends = useCallback(() => {
    if (!selectedAccount) return;
    setLoadingTrends(true);
    getAnalyticsTrends(selectedAccount, { period })
      .then((res) => setTrends(res.data))
      .catch(() => setTrends(null))
      .finally(() => setLoadingTrends(false));
  }, [selectedAccount, period]);

  // Forecast
  const fetchForecast = useCallback(() => {
    if (!selectedAccount) return;
    setLoadingForecast(true);
    getAnalyticsForecast(selectedAccount, { horizon })
      .then((res) => setForecastData(res.data))
      .catch(() => setForecastData(null))
      .finally(() => setLoadingForecast(false));
  }, [selectedAccount, horizon]);

  // Anomalies
  const fetchAnomalies = useCallback(() => {
    if (!selectedAccount) return;
    setLoadingAnomalies(true);
    getAnalyticsAnomalies(selectedAccount, { acknowledged: false })
      .then((res) => setAnomalies(res.data.anomalies || []))
      .catch(() => setAnomalies([]))
      .finally(() => setLoadingAnomalies(false));
  }, [selectedAccount]);

  useEffect(() => { fetchTrends(); }, [fetchTrends]);
  useEffect(() => { fetchForecast(); }, [fetchForecast]);
  useEffect(() => { fetchAnomalies(); }, [fetchAnomalies]);

  const handleAcknowledge = (anomalyId) => {
    acknowledgeAnomaly(anomalyId)
      .then(() => setAnomalies((prev) => prev.filter((a) => a.id !== anomalyId)))
      .catch(() => {});
  };

  const pieData = {
    labels: byService.map((s) => s.service_name),
    datasets: [
      { data: byService.map((s) => s.total_cost), backgroundColor: COLORS },
    ],
  };

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Header */}
      <header
        style={{
          background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          padding: "0.75rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1 style={{ fontSize: "1.1rem" }}>Analytics</h1>
        <Link to="/">
          <button className="btn-ghost" style={{ fontSize: "0.8rem" }}>
            ← Dashboard
          </button>
        </Link>
      </header>

      <main style={{ padding: "1.5rem", maxWidth: 1100, margin: "0 auto" }}>

        {/* Row 1: pie + legacy forecasts */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
          <div className="card">
            <SectionHeader title="Cost by Service (This Month)" />
            {byService.length > 0 ? (
              <Pie
                data={pieData}
                options={{ plugins: { legend: { labels: { color: "#e0e0e0" } } } }}
              />
            ) : (
              <EmptyState message="No data yet." />
            )}
          </div>

          <div className="card">
            <SectionHeader title="Month-end Projections" />
            {legacyForecasts.length === 0 ? (
              <EmptyState message="No forecast data yet." />
            ) : (
              legacyForecasts.map((f) => (
                <div
                  key={f.account_id}
                  style={{
                    marginBottom: "0.75rem",
                    paddingBottom: "0.75rem",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  <strong style={{ fontSize: "0.9rem" }}>{f.account_name}</strong>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "0.8rem",
                      marginTop: "0.25rem",
                    }}
                  >
                    <span className="muted">So far: ${f.cost_so_far?.toFixed(4)}</span>
                    <span>
                      Projected: <strong>${f.projected_total?.toFixed(4)}</strong>
                    </span>
                  </div>
                  <div
                    style={{
                      background: "var(--surface2)",
                      borderRadius: 4,
                      height: 4,
                      marginTop: "0.35rem",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${f.confidence_score}%`,
                        height: "100%",
                        background: "var(--primary-light)",
                      }}
                    />
                  </div>
                  <p className="muted" style={{ fontSize: "0.7rem", marginTop: "0.15rem" }}>
                    Confidence: {f.confidence_score?.toFixed(0)}%
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Controls (only when accounts are available) */}
        {accounts.length > 0 && (
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <div
              style={{
                display: "flex",
                gap: "1rem",
                alignItems: "flex-end",
                flexWrap: "wrap",
              }}
            >
              <div>
                <label
                  style={{
                    fontSize: "0.78rem",
                    color: "#aaa",
                    display: "block",
                    marginBottom: "0.2rem",
                  }}
                >
                  Account
                </label>
                <select
                  value={selectedAccount || ""}
                  onChange={(e) => setSelectedAccount(Number(e.target.value))}
                  style={{
                    background: "var(--surface2)",
                    color: "var(--text)",
                    border: "1px solid var(--border)",
                    borderRadius: 4,
                    padding: "0.3rem 0.6rem",
                    fontSize: "0.85rem",
                  }}
                >
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  style={{
                    fontSize: "0.78rem",
                    color: "#aaa",
                    display: "block",
                    marginBottom: "0.2rem",
                  }}
                >
                  Trend Period
                </label>
                <div style={{ display: "flex", gap: "0.3rem" }}>
                  {PERIOD_OPTIONS.map((p) => (
                    <button
                      key={p}
                      className={period === p ? "btn-primary" : "btn-ghost"}
                      style={{ fontSize: "0.78rem", padding: "0.25rem 0.6rem" }}
                      onClick={() => setPeriod(p)}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label
                  style={{
                    fontSize: "0.78rem",
                    color: "#aaa",
                    display: "block",
                    marginBottom: "0.2rem",
                  }}
                >
                  Forecast Horizon
                </label>
                <div style={{ display: "flex", gap: "0.3rem" }}>
                  {HORIZON_OPTIONS.map((h) => (
                    <button
                      key={h}
                      className={horizon === h ? "btn-primary" : "btn-ghost"}
                      style={{ fontSize: "0.78rem", padding: "0.25rem 0.6rem" }}
                      onClick={() => setHorizon(h)}
                    >
                      {h}d
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Trend chart */}
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}
          >
            <SectionHeader title={`Cost Trend — ${period}`} />
            {trends?.growth_rate_pct != null && (
              <span
                style={{
                  fontSize: "0.78rem",
                  color: trends.growth_rate_pct >= 0 ? "#e74c3c" : "#2ecc71",
                }}
              >
                {trends.growth_rate_pct >= 0 ? "▲" : "▼"}{" "}
                {Math.abs(trends.growth_rate_pct).toFixed(2)}%/day
              </span>
            )}
          </div>
          {loadingTrends ? (
            <LoadingPlaceholder />
          ) : (
            <TrendChart trends={trends} period={period} />
          )}
        </div>

        {/* Forecast chart */}
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}
          >
            <SectionHeader title={`${horizon}-Day Cost Forecast`} />
            {forecastData?.confidence_pct != null && (
              <span className="muted" style={{ fontSize: "0.78rem" }}>
                Confidence: {forecastData.confidence_pct}% · R²={forecastData.r_squared}
              </span>
            )}
          </div>
          {loadingForecast ? (
            <LoadingPlaceholder />
          ) : (
            <ForecastChart
              historical={trends?.daily}
              forecast={forecastData?.forecast}
            />
          )}
        </div>

        {/* Anomaly list */}
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "0.75rem",
            }}
          >
            <SectionHeader title="Spending Anomalies" />
            {anomalies.length > 0 && (
              <span style={{ fontSize: "0.78rem", color: "#e74c3c" }}>
                {anomalies.length} unresolved
              </span>
            )}
          </div>
          {loadingAnomalies ? (
            <LoadingPlaceholder />
          ) : (
            <AnomalyList anomalies={anomalies} onAcknowledge={handleAcknowledge} />
          )}
        </div>

        {/* Service breakdown table */}
        {byService.length > 0 && (
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <SectionHeader title="Service Breakdown" />
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.85rem",
              }}
            >
              <thead>
                <tr
                  style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}
                >
                  <th style={{ padding: "0.5rem" }}>Service</th>
                  <th style={{ padding: "0.5rem" }}>Tokens</th>
                  <th style={{ padding: "0.5rem" }}>API Calls</th>
                  <th style={{ padding: "0.5rem" }}>Total Cost</th>
                </tr>
              </thead>
              <tbody>
                {byService.map((s) => (
                  <tr
                    key={s.service_id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                  >
                    <td style={{ padding: "0.5rem" }}>{s.service_name}</td>
                    <td style={{ padding: "0.5rem" }}>
                      {s.total_tokens?.toLocaleString()}
                    </td>
                    <td style={{ padding: "0.5rem" }}>
                      {s.total_calls?.toLocaleString()}
                    </td>
                    <td style={{ padding: "0.5rem" }}>
                      ${s.total_cost?.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
