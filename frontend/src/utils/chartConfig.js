/**
 * Chart.js configuration helpers for the AI Cost Tracker.
 *
 * These functions return dataset and tooltip configurations that apply
 * per-point colours and shapes based on each record's `source` field:
 *   - API data   → blue circle
 *   - Manual data → orange rotated-rectangle (diamond)
 */

const COLORS = {
  api: {
    point:  "#2196F3",
    border: "#1976D2",
  },
  manual: {
    point:  "#FF9800",
    border: "#F57C00",
  },
};

/**
 * Build a Chart.js dataset config from an array of usage history records.
 *
 * @param {Array<{timestamp: string, cost: number, source: string, extra_data: object}>} records
 * @returns {object} Chart.js dataset configuration object
 */
export const getChartDatasetConfig = (records) => {
  const data = (records || []).map((r) => ({
    x: r.timestamp ? r.timestamp.slice(0, 10) : "",
    y: r.cost || 0,
    source: r.source || "api",
    notes: (r.extra_data || {}).notes || null,
    created_at: r.created_at || null,
  }));

  return {
    label: "Daily Cost (USD)",
    data,

    pointStyle: (ctx) =>
      ctx.raw?.source === "manual" ? "rectRot" : "circle",

    pointBackgroundColor: (ctx) =>
      COLORS[ctx.raw?.source]?.point || COLORS.api.point,

    pointBorderColor: (ctx) =>
      COLORS[ctx.raw?.source]?.border || COLORS.api.border,

    pointRadius: (ctx) =>
      ctx.raw?.source === "manual" ? 6 : 4,

    pointHoverRadius: (ctx) =>
      ctx.raw?.source === "manual" ? 8 : 6,

    pointBorderWidth: 2,

    // Line
    borderColor: "#2196F3",
    borderWidth: 2,
    tension: 0.3,
    fill: false,
  };
};

/**
 * Tooltip plugin configuration with source-aware colours and extra metadata.
 *
 * @returns {object} Chart.js tooltip plugin options
 */
export const getTooltipConfig = () => ({
  callbacks: {
    title: (items) => items[0]?.label || "",

    label: (ctx) => {
      const r = ctx.raw || {};
      const lines = [
        `Cost: $${(r.y || 0).toFixed(4)}`,
        `Source: ${r.source === "manual" ? "✏️ Manual" : "🔄 API"}`,
      ];
      if (r.notes) lines.push(`Notes: ${r.notes}`);
      if (r.created_at) {
        lines.push(`Recorded: ${new Date(r.created_at).toLocaleDateString()}`);
      }
      return lines;
    },

    labelColor: (ctx) => {
      const src = ctx.raw?.source;
      return {
        borderColor: COLORS[src]?.border || COLORS.api.border,
        backgroundColor: COLORS[src]?.point || COLORS.api.point,
        borderWidth: 2,
      };
    },
  },

  backgroundColor: "rgba(0,0,0,0.85)",
  titleColor: "#fff",
  bodyColor: "#fff",
  borderColor: "#444",
  borderWidth: 1,
  padding: 12,
  displayColors: true,
  boxPadding: 6,
});

/**
 * Custom legend labels that show source-type entries (API vs Manual).
 *
 * @returns {function} generateLabels function for Chart.js legend plugin
 */
export const getSourceLegendLabels = () => (_chart) => [
  {
    text: "🔄 API Data",
    fillStyle: COLORS.api.point,
    strokeStyle: COLORS.api.border,
    pointStyle: "circle",
    hidden: false,
  },
  {
    text: "✏️ Manual Data",
    fillStyle: COLORS.manual.point,
    strokeStyle: COLORS.manual.border,
    pointStyle: "rectRot",
    hidden: false,
  },
];
