import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../App";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div style={{ minHeight: "100vh" }}>
      <header style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", padding: "0.75rem 1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontSize: "1.1rem" }}>Settings</h1>
        <Link to="/"><button className="btn-ghost" style={{ fontSize: "0.8rem" }}>← Dashboard</button></Link>
      </header>
      <main style={{ padding: "1.5rem", maxWidth: 600, margin: "0 auto" }}>
        <div className="card">
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Account</h2>
          <p className="muted" style={{ fontSize: "0.85rem" }}>Signed in as: <strong>{user?.email}</strong></p>
        </div>
        <div className="card" style={{ marginTop: "1rem" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Notifications</h2>
          <p className="muted" style={{ fontSize: "0.85rem", marginBottom: "0.75rem" }}>
            Configure email and Slack alerts for budget thresholds and anomalies.
          </p>
          <Link to="/notifications">
            <button className="btn-ghost" style={{ fontSize: "0.85rem" }}>
              Notification Settings →
            </button>
          </Link>
        </div>
        <div className="card" style={{ marginTop: "1rem" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>About</h2>
          <p style={{ fontSize: "0.85rem" }}>AI Cost Tracker v1.0 — Phase 1 MVP</p>
          <p className="muted" style={{ fontSize: "0.8rem", marginTop: "0.4rem" }}>
            Track and manage usage costs across OpenAI, Anthropic, Groq, and more.
          </p>
        </div>
      </main>
    </div>
  );
}
