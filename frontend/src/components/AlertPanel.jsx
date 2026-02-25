import React, { useState, useEffect } from "react";
import { getAlerts, acknowledgeAlert } from "../services/api";

const ALERT_LABELS = {
  approaching_limit: "Approaching Limit",
  limit_exceeded: "Limit Exceeded",
  high_cost: "High Cost",
  service_down: "Service Down",
  unusual_activity: "Unusual Activity",
};

export default function AlertPanel() {
  const [alerts, setAlerts] = useState([]);

  const load = async () => {
    try {
      const res = await getAlerts();
      setAlerts(res.data.alerts || []);
    } catch (_) {}
  };

  useEffect(() => { load(); }, []);

  const handleAck = async (id) => {
    await acknowledgeAlert(id);
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  if (!alerts.length) {
    return <p className="muted" style={{ textAlign: "center", padding: "1rem" }}>No active alerts.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="card"
          style={{
            borderLeft: `4px solid ${alert.alert_type === "limit_exceeded" ? "var(--danger)" : "var(--warning)"}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <strong style={{ fontSize: "0.9rem" }}>
              {ALERT_LABELS[alert.alert_type] || alert.alert_type}
            </strong>
            <p style={{ fontSize: "0.8rem" }}>{alert.message}</p>
            {alert.last_triggered && (
              <p className="muted" style={{ fontSize: "0.75rem" }}>
                {new Date(alert.last_triggered).toLocaleString()}
              </p>
            )}
          </div>
          <button
            className="btn-ghost"
            style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}
            onClick={() => handleAck(alert.id)}
          >
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}
