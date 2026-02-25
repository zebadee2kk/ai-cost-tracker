import React from "react";

function statusBadge(cost, limit) {
  if (!limit) return null;
  const pct = (cost / limit) * 100;
  if (pct >= 100) return <span className="badge badge-critical">Critical</span>;
  if (pct >= 80)  return <span className="badge badge-warning">Warning</span>;
  return <span className="badge badge-ok">OK</span>;
}

export default function OverviewCard({ account }) {
  const {
    account_name,
    service_name,
    total_cost,
    total_tokens,
    total_calls,
    monthly_limit,
  } = account;

  const pct = monthly_limit ? Math.min((total_cost / monthly_limit) * 100, 100) : null;

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>{account_name}</h3>
          <p className="muted" style={{ fontSize: "0.8rem" }}>{service_name}</p>
        </div>
        {statusBadge(total_cost, monthly_limit)}
      </div>

      <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>
        ${total_cost?.toFixed(4) ?? "0.0000"}
        {monthly_limit && (
          <span className="muted" style={{ fontSize: "0.85rem", fontWeight: 400 }}>
            {" "}/ ${monthly_limit?.toFixed(2)} limit
          </span>
        )}
      </div>

      {pct !== null && (
        <div>
          <div style={{ background: "var(--surface2)", borderRadius: 4, height: 6, overflow: "hidden" }}>
            <div
              style={{
                width: `${pct}%`,
                height: "100%",
                background: pct >= 100 ? "var(--danger)" : pct >= 80 ? "var(--warning)" : "var(--success)",
                transition: "width 0.4s",
              }}
            />
          </div>
          <p className="muted" style={{ fontSize: "0.75rem", marginTop: "0.2rem" }}>
            {pct.toFixed(1)}% of limit used
          </p>
        </div>
      )}

      <div style={{ display: "flex", gap: "1rem", fontSize: "0.8rem" }}>
        <span className="muted">{total_tokens?.toLocaleString() ?? 0} tokens</span>
        <span className="muted">{total_calls?.toLocaleString() ?? 0} calls</span>
      </div>
    </div>
  );
}
