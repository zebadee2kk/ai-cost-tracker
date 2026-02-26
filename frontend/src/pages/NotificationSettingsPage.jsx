import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../App";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  sendTestNotification,
} from "../services/api";

const ALERT_TYPE_OPTIONS = [
  { value: "budget", label: "Budget Threshold Alerts" },
  { value: "anomaly", label: "Usage Anomaly Alerts" },
  { value: "system", label: "System & Sync Alerts" },
];

const DEFAULT_CHANNEL = { enabled: false, config: {}, alert_types: [] };

function ChannelCard({ title, icon, channel, settings, onChange, onTest, testing }) {
  const updateConfig = (key, value) =>
    onChange({ ...settings, config: { ...settings.config, [key]: value } });

  const toggleAlertType = (type) => {
    const types = settings.alert_types.includes(type)
      ? settings.alert_types.filter((t) => t !== type)
      : [...settings.alert_types, type];
    onChange({ ...settings, alert_types: types });
  };

  return (
    <div
      className="card"
      style={{ marginBottom: "1rem", opacity: settings.enabled ? 1 : 0.75 }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.75rem",
        }}
      >
        <label
          style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}
        >
          <input
            type="checkbox"
            checked={settings.enabled}
            onChange={() => onChange({ ...settings, enabled: !settings.enabled })}
            style={{ width: "auto" }}
          />
          <span style={{ fontSize: "1rem" }}>
            {icon} {title}
          </span>
        </label>

        {settings.enabled && (
          <button
            className="btn-ghost"
            style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
            onClick={onTest}
            disabled={testing}
          >
            {testing ? "Sending…" : "Send Test"}
          </button>
        )}
      </div>

      {settings.enabled && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
          {channel === "email" && (
            <div>
              <label style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                Email address
              </label>
              <input
                type="email"
                placeholder="you@example.com"
                value={settings.config.address || ""}
                onChange={(e) => updateConfig("address", e.target.value)}
                style={{ marginTop: "0.25rem" }}
              />
            </div>
          )}

          {(channel === "slack" || channel === "discord") && (
            <div>
              <label style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                Webhook URL
              </label>
              <input
                type="url"
                placeholder={
                  channel === "slack"
                    ? "https://hooks.slack.com/services/…"
                    : "https://discord.com/api/webhooks/…"
                }
                value={settings.config.webhook_url || ""}
                onChange={(e) => updateConfig("webhook_url", e.target.value)}
                style={{ marginTop: "0.25rem" }}
              />
            </div>
          )}

          <div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.4rem" }}>
              Alert types
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
              {ALERT_TYPE_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer" }}
                >
                  <input
                    type="checkbox"
                    style={{ width: "auto" }}
                    checked={settings.alert_types.includes(opt.value)}
                    onChange={() => toggleAlertType(opt.value)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function NotificationSettingsPage() {
  const { user } = useAuth();
  const [prefs, setPrefs] = useState({
    email: { ...DEFAULT_CHANNEL },
    slack: { ...DEFAULT_CHANNEL },
    discord: { ...DEFAULT_CHANNEL },
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState({});
  const [flash, setFlash] = useState(null);

  const showFlash = (msg, type = "success") => {
    setFlash({ msg, type });
    setTimeout(() => setFlash(null), 4000);
  };

  const loadPrefs = useCallback(async () => {
    if (!user?.id) return;
    try {
      const res = await getNotificationPreferences(user.id);
      const fetched = res.data.preferences || {};
      setPrefs((prev) => {
        const merged = { ...prev };
        for (const ch of Object.keys(merged)) {
          if (fetched[ch]) {
            merged[ch] = {
              enabled: fetched[ch].enabled ?? false,
              config: fetched[ch].config ?? {},
              alert_types: fetched[ch].alert_types ?? [],
            };
          }
        }
        return merged;
      });
    } catch {
      showFlash("Failed to load notification preferences.", "error");
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    loadPrefs();
  }, [loadPrefs]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateNotificationPreferences(user.id, prefs);
      showFlash("Notification preferences saved.");
    } catch {
      showFlash("Failed to save preferences.", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (channel) => {
    setTesting((t) => ({ ...t, [channel]: true }));
    try {
      await sendTestNotification(channel);
      showFlash(`Test ${channel} notification sent!`);
    } catch (err) {
      const msg = err.response?.data?.error || `Failed to send test ${channel} notification.`;
      showFlash(msg, "error");
    } finally {
      setTesting((t) => ({ ...t, [channel]: false }));
    }
  };

  const updateChannel = (channel, settings) =>
    setPrefs((p) => ({ ...p, [channel]: settings }));

  const flashStyle = {
    padding: "0.6rem 1rem",
    borderRadius: "var(--radius)",
    marginBottom: "1rem",
    fontSize: "0.85rem",
    background: flash?.type === "error" ? "var(--danger)" : "var(--success)",
    color: "#fff",
  };

  return (
    <div style={{ minHeight: "100vh" }}>
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
        <h1 style={{ fontSize: "1.1rem" }}>Notification Settings</h1>
        <Link to="/settings">
          <button className="btn-ghost" style={{ fontSize: "0.8rem" }}>
            ← Settings
          </button>
        </Link>
      </header>

      <main style={{ padding: "1.5rem", maxWidth: 640, margin: "0 auto" }}>
        {flash && <div style={flashStyle}>{flash.msg}</div>}

        {loading ? (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Loading preferences…
          </p>
        ) : (
          <>
            <p
              className="muted"
              style={{ fontSize: "0.85rem", marginBottom: "1rem" }}
            >
              Configure how and when you receive alerts about your AI spend.
              Rate limits: 10 emails/hour, 20 Slack messages/hour.
            </p>

            <ChannelCard
              title="Email Notifications"
              icon="📧"
              channel="email"
              settings={prefs.email}
              onChange={(s) => updateChannel("email", s)}
              onTest={() => handleTest("email")}
              testing={testing.email}
            />

            <ChannelCard
              title="Slack Notifications"
              icon="💬"
              channel="slack"
              settings={prefs.slack}
              onChange={(s) => updateChannel("slack", s)}
              onTest={() => handleTest("slack")}
              testing={testing.slack}
            />

            <ChannelCard
              title="Discord Notifications"
              icon="🎮"
              channel="discord"
              settings={prefs.discord}
              onChange={(s) => updateChannel("discord", s)}
              onTest={() => handleTest("discord")}
              testing={testing.discord}
            />

            <button
              className="btn-primary"
              style={{ width: "100%", marginTop: "0.5rem" }}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving…" : "Save Notification Preferences"}
            </button>
          </>
        )}
      </main>
    </div>
  );
}
