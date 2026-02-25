import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../App";
import { logout, getCurrentUsage, getUsageHistory } from "../services/api";
import OverviewCard from "../components/OverviewCard";
import UsageChart from "../components/UsageChart";
import AccountManager from "../components/AccountManager";
import AlertPanel from "../components/AlertPanel";

export default function DashboardPage() {
  const { user, signOut } = useAuth();
  const [usage, setUsage] = useState([]);
  const [history, setHistory] = useState([]);
  const [tab, setTab] = useState("overview");

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
