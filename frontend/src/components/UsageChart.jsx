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
import { Bar, Line } from "react-chartjs-2";
import { getChartDatasetConfig, getTooltipConfig, getSourceLegendLabels } from "../utils/chartConfig";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Tooltip,
  Legend
);

/**
 * UsageChart renders either a grouped-by-day Bar chart (when records lack
 * source information) or a Line chart with per-point source styling.
 *
 * Props:
 *   records  Array of usage history records from /api/usage/history
 *   mode     "bar" (default) | "line"
 */
export default function UsageChart({ records, mode = "bar" }) {
  const sorted = (records || [])
    .filter((r) => r.timestamp)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    .slice(-90); // cap at 90 days of data

  if (!sorted.length) {
    return (
      <p className="muted" style={{ padding: "2rem", textAlign: "center" }}>
        No usage data yet.
      </p>
    );
  }

  if (mode === "line") {
    // Line chart with per-point source styling
    const dataset = getChartDatasetConfig(sorted);
    const chartData = { datasets: [dataset] };

    const options = {
      responsive: true,
      maintainAspectRatio: true,
      parsing: false,
      plugins: {
        tooltip: getTooltipConfig(),
        legend: {
          display: true,
          labels: {
            color: "#e0e0e0",
            generateLabels: getSourceLegendLabels(),
          },
        },
      },
      scales: {
        x: {
          type: "category",
          ticks: { color: "#888", maxRotation: 45 },
          grid: { color: "#2a2a4a" },
        },
        y: {
          beginAtZero: true,
          ticks: { color: "#888", callback: (v) => `$${v.toFixed(2)}` },
          grid: { color: "#2a2a4a" },
        },
      },
    };

    return <Line data={chartData} options={options} />;
  }

  // Default: grouped bar chart (aggregated by day)
  const dailyMap = {};
  sorted.forEach((r) => {
    const day = r.timestamp.slice(0, 10);
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

  return <Bar data={data} options={options} />;
}
