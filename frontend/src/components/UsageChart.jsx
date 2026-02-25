import React from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend);

export default function UsageChart({ records }) {
  // Aggregate cost per day from usage history records
  const dailyMap = {};
  (records || []).forEach((r) => {
    const day = r.timestamp?.slice(0, 10);
    if (!day) return;
    dailyMap[day] = (dailyMap[day] || 0) + (r.cost || 0);
  });

  const labels = Object.keys(dailyMap).sort().slice(-30);
  const costs = labels.map((d) => dailyMap[d]);

  const data = {
    labels,
    datasets: [
      {
        label: "Daily Cost (USD)",
        data: costs,
        backgroundColor: "rgba(83, 52, 131, 0.7)",
        borderColor: "rgba(123, 82, 171, 1)",
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { labels: { color: "#e0e0e0" } },
      tooltip: {
        callbacks: {
          label: (ctx) => `$${ctx.parsed.y.toFixed(4)}`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: "#888", maxRotation: 45 },
        grid: { color: "#2a2a4a" },
      },
      y: {
        ticks: {
          color: "#888",
          callback: (v) => `$${v.toFixed(2)}`,
        },
        grid: { color: "#2a2a4a" },
      },
    },
  };

  if (!labels.length) {
    return <p className="muted" style={{ padding: "2rem", textAlign: "center" }}>No usage data yet.</p>;
  }

  return <Bar data={data} options={options} />;
}
