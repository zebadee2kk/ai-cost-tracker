import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../App";
import { logout, getCurrentUsage, getUsageHistory } from "../services/api";
import OverviewCard from "../components/OverviewCard";
import UsageChart from "../components/UsageChart";
import AccountManager from "../components/AccountManager";
import AlertPanel from "../components/AlertPanel";
import ExportButton from "../components/ExportButton";
import SourceBadge from "../components/SourceBadge";
import SourceFilter from "../components/SourceFilter";

export default function DashboardPage() {
  const { user, signOut } = useAuth();
  const [usage, setUsage] = useState([]);
  const [history, setHistory] = useState([]);
  const [tab, setTab] = useState("overview");
  const [sourceFilter, setSourceFilter] = useState("all");

  const loadData = async () => {
    try {
      const [usageRes, histRes] = await Promise.all([
        getCurrentUsage(),
        getUsageHistory({ per_page: 200 }),
      ]);
      setUsage(usageRes.data.usage || []);
      setHistory(histRes.data.records || []);
    } catch (_) {}
  };

  useEffect(() => { loadData(); }, []);

  const handleLogout = async () => {
    try { await logout(); } catch (_) {}
    signOut();
  };

  const totalCost = usage.reduce((s, u) => s + (u.total_cost || 0), 0);

  // Filter history records by selected source
  const filteredHistory = useMemo(() => {
    if (sourceFilter === "all") return history;
    return history.filter((r) => r.source === sourceFilter);
  }, [history, sourceFilter]);

  // Build export filters from current source selection
  const exportFilters = useMemo(() => {
    const f = {};
    if (sourceFilter !== "all") f.source = sourceFilter;
    return f;
  }, [sourceFilter]);

  const navBtn = (id, label) => (
    <button
      onClick={() => setTab(id)}
      style={{
        background: tab === id ? "var(--primary)" : "transparent",
        color: "var(--text)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "0.4rem 1rem",
        cursor: "pointer",
        fontSize: "0.85rem",
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <header style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", padding: "0.75rem 1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.1rem", fontWeight: 700 }}>AI Cost Tracker</h1>
          <p className="muted" style={{ fontSize: "0.75rem" }}>{user?.email}</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <span style={{ fontSize: "0.85rem" }}>
            This month: <strong>${totalCost.toFixed(4)}</strong>
          </span>
          <Link to="/analytics"><button className="btn-ghost" style={{ fontSize: "0.8rem" }}>Analytics</button></Link>
          <Link to="/settings"><button className="btn-ghost" style={{ fontSize: "0.8rem" }}>Settings</button></Link>
          <button className="btn-ghost" style={{ fontSize: "0.8rem" }} onClick={handleLogout}>Sign Out</button>
        </div>
      </header>

      {/* Main */}
      <main style={{ flex: 1, padding: "1.5rem", maxWidth: 1100, margin: "0 auto", width: "100%" }}>

        {/* Tab nav */}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
          {navBtn("overview", "Overview")}
          {navBtn("chart", "Usage Chart")}
          {navBtn("history", "History")}
          {navBtn("accounts", "Accounts")}
          {navBtn("alerts", "Alerts")}
        </div>

        {/* Overview tab */}
        {tab === "overview" && (
          usage.length === 0
            ? <p className="muted" style={{ textAlign: "center", padding: "3rem" }}>No usage data yet. Add an account and sync.</p>
            : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
                {usage.map((u) => <OverviewCard key={u.account_id} account={u} />)}
              </div>
        )}

        {/* Chart tab */}
        {tab === "chart" && (
          <div className="card">
            <h2 style={{ marginBottom: "1rem", fontSize: "1rem" }}>Daily Cost — Last 30 Days</h2>
            <UsageChart records={history} />
          </div>
        )}

        {/* History tab — with source filter, badges, and export */}
        {tab === "history" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
              <SourceFilter selected={sourceFilter} onChange={setSourceFilter} />
              <ExportButton filters={exportFilters} />
            </div>

            {filteredHistory.length === 0 ? (
              <p className="muted" style={{ textAlign: "center", padding: "2rem" }}>
                No records match the current filter.
              </p>
            ) : (
              <div className="card" style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                      <th style={{ padding: "0.5rem 0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Date</th>
                      <th style={{ padding: "0.5rem 0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Service</th>
                      <th style={{ padding: "0.5rem 0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Tokens</th>
                      <th style={{ padding: "0.5rem 0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Cost (USD)</th>
                      <th style={{ padding: "0.5rem 0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHistory.map((r) => (
                      <tr
                        key={r.id}
                        style={{ borderBottom: "1px solid var(--border)" }}
                      >
                        <td style={{ padding: "0.5rem 0.75rem" }}>
                          {r.timestamp ? r.timestamp.slice(0, 10) : "—"}
                        </td>
                        <td style={{ padding: "0.5rem 0.75rem" }}>
                          {r.service_name || "—"}
                        </td>
                        <td style={{ padding: "0.5rem 0.75rem" }}>
                          {r.tokens_used != null ? r.tokens_used.toLocaleString() : "—"}
                        </td>
                        <td style={{ padding: "0.5rem 0.75rem" }}>
                          ${(r.cost || 0).toFixed(4)}
                        </td>
                        <td style={{ padding: "0.5rem 0.75rem" }}>
                          <SourceBadge source={r.source || "api"} size="small" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Accounts tab */}
        {tab === "accounts" && (
          <AccountManager onAccountsChange={loadData} />
        )}

        {/* Alerts tab */}
        {tab === "alerts" && (
          <div>
            <h2 style={{ marginBottom: "1rem", fontSize: "1rem" }}>Active Alerts</h2>
            <AlertPanel />
          </div>
        )}
      </main>
    </div>
  );
}
