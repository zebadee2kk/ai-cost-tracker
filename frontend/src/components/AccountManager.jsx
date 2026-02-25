import React, { useState, useEffect } from "react";
import {
  getAccounts,
  createAccount,
  deleteAccount,
  testAccount,
  getServices,
} from "../services/api";
import ManualEntryModal from "./ManualEntryModal";

export default function AccountManager({ onAccountsChange }) {
  const [accounts, setAccounts] = useState([]);
  const [services, setServices] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ service_id: "", account_name: "", api_key: "", monthly_limit: "" });
  const [formError, setFormError] = useState("");
  const [testResults, setTestResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [manualEntryAccount, setManualEntryAccount] = useState(null);

  useEffect(() => {
    Promise.all([getAccounts(), getServices()]).then(([accRes, svcRes]) => {
      setAccounts(accRes.data.accounts || []);
      setServices(svcRes.data.services || []);
    });
  }, []);

  const refresh = async () => {
    const res = await getAccounts();
    const updated = res.data.accounts || [];
    setAccounts(updated);
    onAccountsChange?.(updated);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setFormError("");
    setLoading(true);
    try {
      await createAccount({
        service_id: parseInt(form.service_id),
        account_name: form.account_name,
        api_key: form.api_key || undefined,
        monthly_limit: form.monthly_limit ? parseFloat(form.monthly_limit) : undefined,
      });
      setForm({ service_id: "", account_name: "", api_key: "", monthly_limit: "" });
      setShowForm(false);
      await refresh();
    } catch (err) {
      setFormError(err.response?.data?.error || "Failed to create account.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this account and all its data?")) return;
    await deleteAccount(id);
    await refresh();
  };

  const handleTest = async (id) => {
    setTestResults((r) => ({ ...r, [id]: "testing…" }));
    try {
      const res = await testAccount(id);
      setTestResults((r) => ({ ...r, [id]: res.data.message }));
    } catch (err) {
      setTestResults((r) => ({
        ...r,
        [id]: err.response?.data?.message || "Connection failed.",
      }));
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ fontSize: "1.1rem" }}>Accounts</h2>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add Account"}
        </button>
      </div>

      {showForm && (
        <form className="card" onSubmit={handleCreate} style={{ marginBottom: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <h3 style={{ fontSize: "0.95rem" }}>New Account</h3>
          <select value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })} required>
            <option value="">Select service…</option>
            {services.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input placeholder="Account name (e.g. Work)" value={form.account_name} onChange={(e) => setForm({ ...form, account_name: e.target.value })} required />
          <input type="password" placeholder="API Key (encrypted at rest)" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} autoComplete="off" />
          <input type="number" min="0" step="0.01" placeholder="Monthly limit ($) — optional" value={form.monthly_limit} onChange={(e) => setForm({ ...form, monthly_limit: e.target.value })} />
          {formError && <p className="error-msg">{formError}</p>}
          <button type="submit" className="btn-primary" disabled={loading}>{loading ? "Saving…" : "Save Account"}</button>
        </form>
      )}

      {accounts.length === 0 ? (
        <p className="muted" style={{ textAlign: "center", padding: "2rem" }}>No accounts yet. Add one above.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {accounts.map((acc) => (
            <div key={acc.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong>{acc.account_name}</strong>
                <span className="muted" style={{ marginLeft: "0.5rem", fontSize: "0.8rem" }}>{acc.service_name}</span>
                {acc.has_api_key && <span className="badge badge-ok" style={{ marginLeft: "0.5rem" }}>Key set</span>}
                {acc.last_sync && <p className="muted" style={{ fontSize: "0.75rem" }}>Last sync: {new Date(acc.last_sync).toLocaleString()}</p>}
                {testResults[acc.id] && <p style={{ fontSize: "0.75rem", marginTop: "0.2rem" }}>{testResults[acc.id]}</p>}
              </div>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn-ghost" style={{ fontSize: "0.8rem" }} onClick={() => handleTest(acc.id)}>Test</button>
                <button className="btn-ghost" style={{ fontSize: "0.8rem" }} onClick={() => setManualEntryAccount(acc)}>+ Manual Entry</button>
                <button className="btn-danger" style={{ fontSize: "0.8rem" }} onClick={() => handleDelete(acc.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {manualEntryAccount && (
        <ManualEntryModal
          account={manualEntryAccount}
          onClose={() => setManualEntryAccount(null)}
          onSuccess={refresh}
        />
      )}
    </div>
  );
}
