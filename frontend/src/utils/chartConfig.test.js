import { getChartDatasetConfig, getTooltipConfig, getSourceLegendLabels } from "./chartConfig";

describe("getChartDatasetConfig", () => {
  const records = [
    { timestamp: "2026-02-10T00:00:00Z", cost: 1.5, source: "api", extra_data: {} },
    { timestamp: "2026-02-11T00:00:00Z", cost: 2.0, source: "manual", extra_data: { notes: "Test" } },
  ];

  test("maps records to {x, y, source} data points", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.data).toHaveLength(2);
    expect(cfg.data[0]).toMatchObject({ x: "2026-02-10", y: 1.5, source: "api" });
    expect(cfg.data[1]).toMatchObject({ x: "2026-02-11", y: 2.0, source: "manual" });
  });

  test("uses blue (#2196F3) for API points", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.pointBackgroundColor({ raw: { source: "api" } })).toBe("#2196F3");
  });

  test("uses orange (#FF9800) for manual points", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.pointBackgroundColor({ raw: { source: "manual" } })).toBe("#FF9800");
  });

  test("uses blue border (#1976D2) for API points", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.pointBorderColor({ raw: { source: "api" } })).toBe("#1976D2");
  });

  test("uses orange border (#F57C00) for manual points", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.pointBorderColor({ raw: { source: "manual" } })).toBe("#F57C00");
  });

  test("uses 'circle' point style for API", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.pointStyle({ raw: { source: "api" } })).toBe("circle");
  });

  test("uses 'rectRot' point style for manual", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.pointStyle({ raw: { source: "manual" } })).toBe("rectRot");
  });

  test("manual points have larger radius than API", () => {
    const cfg = getChartDatasetConfig(records);
    const manualRadius = cfg.pointRadius({ raw: { source: "manual" } });
    const apiRadius = cfg.pointRadius({ raw: { source: "api" } });
    expect(manualRadius).toBeGreaterThan(apiRadius);
  });

  test("handles empty records array", () => {
    const cfg = getChartDatasetConfig([]);
    expect(cfg.data).toEqual([]);
  });

  test("handles null/undefined records gracefully", () => {
    const cfg = getChartDatasetConfig(null);
    expect(cfg.data).toEqual([]);
  });

  test("falls back to API colours for unknown source", () => {
    const cfg = getChartDatasetConfig(records);
    expect(cfg.pointBackgroundColor({ raw: { source: "unknown" } })).toBe("#2196F3");
  });

  test("notes are mapped from extra_data", () => {
    const cfg = getChartDatasetConfig(records);
    const manualPoint = cfg.data.find((d) => d.source === "manual");
    expect(manualPoint.notes).toBe("Test");
  });
});

describe("getTooltipConfig", () => {
  test("returns an object with callbacks", () => {
    const cfg = getTooltipConfig();
    expect(cfg).toHaveProperty("callbacks");
    expect(typeof cfg.callbacks.label).toBe("function");
    expect(typeof cfg.callbacks.title).toBe("function");
    expect(typeof cfg.callbacks.labelColor).toBe("function");
  });

  test("label includes cost and source for API record", () => {
    const cfg = getTooltipConfig();
    const lines = cfg.callbacks.label({ raw: { y: 1.5, source: "api" } });
    expect(lines.some((l) => l.includes("$1.5000"))).toBe(true);
    expect(lines.some((l) => l.includes("API"))).toBe(true);
  });

  test("label includes notes when present", () => {
    const cfg = getTooltipConfig();
    const lines = cfg.callbacks.label({
      raw: { y: 2.0, source: "manual", notes: "Invoice #42" },
    });
    expect(lines.some((l) => l.includes("Invoice #42"))).toBe(true);
  });

  test("labelColor returns blue for API", () => {
    const cfg = getTooltipConfig();
    const color = cfg.callbacks.labelColor({ raw: { source: "api" } });
    expect(color.backgroundColor).toBe("#2196F3");
  });

  test("labelColor returns orange for manual", () => {
    const cfg = getTooltipConfig();
    const color = cfg.callbacks.labelColor({ raw: { source: "manual" } });
    expect(color.backgroundColor).toBe("#FF9800");
  });
});

describe("getSourceLegendLabels", () => {
  test("returns a function", () => {
    expect(typeof getSourceLegendLabels()).toBe("function");
  });

  test("returns two legend entries", () => {
    const fn = getSourceLegendLabels();
    const labels = fn({});
    expect(labels).toHaveLength(2);
  });

  test("first entry is API (circle, blue)", () => {
    const labels = getSourceLegendLabels()({});
    expect(labels[0].text).toContain("API");
    expect(labels[0].fillStyle).toBe("#2196F3");
    expect(labels[0].pointStyle).toBe("circle");
  });

  test("second entry is Manual (rectRot, orange)", () => {
    const labels = getSourceLegendLabels()({});
    expect(labels[1].text).toContain("Manual");
    expect(labels[1].fillStyle).toBe("#FF9800");
    expect(labels[1].pointStyle).toBe("rectRot");
  });
});
