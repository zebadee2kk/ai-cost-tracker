import React, { useState } from "react";
import { createManualEntry } from "../services/api";

const PROVIDER_HELP = {
  Groq: {
    instructions: "Navigate to console.groq.com → Dashboard → Usage to find your usage data.",
    link: "https://console.groq.com",
    label: "Open Groq Console",
  },
  Perplexity: {
    instructions:
      "Navigate to Settings → Usage Metrics → Invoice history in the Perplexity portal. " +
      "Click on an invoice to see per-key usage.",
    link: "https://www.perplexity.ai/settings/api",
    label: "Open Perplexity Settings",
  },
};

/**
 * ManualEntryModal
 *
 * Props:
 *   account   – Account object { id, account_name, service_name }
 *   onClose   – called when the modal is dismissed
 *   onSuccess – called after a successful submission (use to refresh data)
 */
export default function ManualEntryModal({ account, onClose, onSuccess }) {
  const today = new Date().toISOString().split("T")[0];
  const [form, setForm] = useState({
    date: today,
    tokens: "",
    cost: "",
    notes: "",
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const help = PROVIDER_HELP[account?.service_name] || null;

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await createManualEntry({
        account_id: account.id,
        date: form.date,
        tokens: form.tokens ? parseInt(form.tokens, 10) : 0,
        cost: form.cost,
        notes: form.notes,
      });
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(
        err.response?.data?.error ||
          err.message ||
          "Failed to save entry. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: "480px",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ fontSize: "1.1rem", marginBottom: "0.25rem" }}>
              Add Manual Usage Entry
            </h2>
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              {account?.service_name} — {account?.account_name}
            </p>
          </div>
          <button
            className="btn-ghost"
            onClick={onClose}
            style={{ fontSize: "1.1rem", lineHeight: 1 }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Provider help text */}
        {help && (
          <div
            style={{
              background: "var(--bg-secondary, #f0f4ff)",
              borderRadius: "6px",
              padding: "0.75rem",
              fontSize: "0.8rem",
            }}
          >
            <strong>Where to find this data:</strong>
            <p style={{ marginTop: "0.3rem" }}>{help.instructions}</p>
            <a
              href={help.link}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--color-primary, #5B6EF5)" }}
            >
              {help.label} ↗
            </a>
          </div>
        )}

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <label style={{ fontSize: "0.85rem", fontWeight: 500 }}>Date</label>
            <input
              type="date"
              name="date"
              value={form.date}
              max={today}
              onChange={handleChange}
              required
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <label style={{ fontSize: "0.85rem", fontWeight: 500 }}>
              Cost (USD)
            </label>
            <input
              type="number"
              name="cost"
              value={form.cost}
              onChange={handleChange}
              placeholder="e.g. 5.50"
              step="0.01"
              min="0"
              required
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <label style={{ fontSize: "0.85rem", fontWeight: 500 }}>
              Tokens Used{" "}
              <span className="muted" style={{ fontWeight: 400 }}>
                (optional)
              </span>
            </label>
            <input
              type="number"
              name="tokens"
              value={form.tokens}
              onChange={handleChange}
              placeholder="e.g. 100000"
              min="0"
              step="1"
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <label style={{ fontSize: "0.85rem", fontWeight: 500 }}>
              Notes{" "}
              <span className="muted" style={{ fontWeight: 400 }}>
                (optional)
              </span>
            </label>
            <textarea
              name="notes"
              value={form.notes}
              onChange={handleChange}
              placeholder="e.g. Invoice #12345, dashboard total for February"
              rows={2}
              style={{ resize: "vertical" }}
            />
          </div>

          {error && (
            <p className="error-msg" style={{ marginTop: 0 }}>
              {error}
            </p>
          )}

          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", marginTop: "0.25rem" }}>
            <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Saving…" : "Add Entry"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
