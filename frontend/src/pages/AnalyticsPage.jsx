import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getUsageByService, getUsageForecast } from "../services/api";
import { Pie } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

const COLORS = ["#533483", "#7b52ab", "#0f3460", "#16213e", "#e94560", "#2ecc71"];

export default function AnalyticsPage() {
  const [byService, setByService] = useState([]);
  const [forecasts, setForecasts] = useState([]);

  useEffect(() => {
    Promise.all([getUsageByService(), getUsageForecast()]).then(([svcRes, fcRes]) => {
      setByService(svcRes.data.by_service || []);
      setForecasts(fcRes.data.forecasts || []);
    });
  }, []);

  const pieData = {
    labels: byService.map((s) => s.service_name),
    datasets: [{
      data: byService.map((s) => s.total_cost),
      backgroundColor: COLORS,
    }],
  };

  return (
    <div style={{ minHeight: "100vh" }}>
      <header style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", padding: "0.75rem 1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontSize: "1.1rem" }}>Analytics</h1>
        <Link to="/"><button className="btn-ghost" style={{ fontSize: "0.8rem" }}>← Dashboard</button></Link>
      </header>

      <main style={{ padding: "1.5rem", maxWidth: 900, margin: "0 auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>

          {/* Cost by service pie */}
          <div className="card">
            <h2 style={{ fontSize: "1rem", marginBottom: "1rem" }}>Cost by Service (This Month)</h2>
            {byService.length > 0
              ? <Pie data={pieData} options={{ plugins: { legend: { labels: { color: "#e0e0e0" } } } }} />
              : <p className="muted" style={{ textAlign: "center" }}>No data yet.</p>}
          </div>

          {/* Forecasts */}
          <div className="card">
            <h2 style={{ fontSize: "1rem", marginBottom: "1rem" }}>Month-end Projections</h2>
            {forecasts.length === 0
              ? <p className="muted" style={{ textAlign: "center" }}>No forecast data yet.</p>
              : forecasts.map((f) => (
                <div key={f.account_id} style={{ marginBottom: "0.75rem", paddingBottom: "0.75rem", borderBottom: "1px solid var(--border)" }}>
                  <strong style={{ fontSize: "0.9rem" }}>{f.account_name}</strong>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginTop: "0.25rem" }}>
                    <span className="muted">So far: ${f.cost_so_far.toFixed(4)}</span>
                    <span>Projected: <strong>${f.projected_total.toFixed(4)}</strong></span>
                  </div>
                  <div style={{ background: "var(--surface2)", borderRadius: 4, height: 4, marginTop: "0.35rem", overflow: "hidden" }}>
                    <div style={{ width: `${f.confidence_score}%`, height: "100%", background: "var(--primary-light)" }} />
                  </div>
                  <p className="muted" style={{ fontSize: "0.7rem", marginTop: "0.15rem" }}>Confidence: {f.confidence_score.toFixed(0)}%</p>
                </div>
              ))}
          </div>

        </div>

        {/* Service breakdown table */}
        {byService.length > 0 && (
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <h2 style={{ fontSize: "1rem", marginBottom: "1rem" }}>Service Breakdown</h2>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                  <th style={{ padding: "0.5rem" }}>Service</th>
                  <th style={{ padding: "0.5rem" }}>Tokens</th>
                  <th style={{ padding: "0.5rem" }}>API Calls</th>
                  <th style={{ padding: "0.5rem" }}>Total Cost</th>
                </tr>
              </thead>
              <tbody>
                {byService.map((s) => (
                  <tr key={s.service_id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.5rem" }}>{s.service_name}</td>
                    <td style={{ padding: "0.5rem" }}>{s.total_tokens?.toLocaleString()}</td>
                    <td style={{ padding: "0.5rem" }}>{s.total_calls?.toLocaleString()}</td>
                    <td style={{ padding: "0.5rem" }}>${s.total_cost?.toFixed(4)}</td>
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
