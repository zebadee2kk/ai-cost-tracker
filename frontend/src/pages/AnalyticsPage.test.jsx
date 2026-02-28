/**
 * Tests for AnalyticsPage component.
 *
 * Covers:
 * - Page renders without crashing
 * - Header / navigation elements present
 * - "Cost by Service" section renders
 * - "Month-end Projections" section renders
 * - Trend chart section renders
 * - Forecast chart section renders
 * - Anomaly list section renders
 * - Service breakdown table renders when data present
 */

import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { MemoryRouter } from "react-router-dom";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock Chart.js to avoid canvas issues in jsdom
jest.mock("react-chartjs-2", () => ({
  Pie: ({ data }) => (
    <div data-testid="pie-chart">{data.labels?.join(",")}</div>
  ),
  Line: ({ data }) => (
    <div data-testid="line-chart">
      {data.datasets?.map((ds) => ds.label).join("|")}
    </div>
  ),
}));

jest.mock("chart.js", () => ({
  Chart: { register: jest.fn() },
  ArcElement: {},
  Tooltip: {},
  Legend: {},
  LineElement: {},
  PointElement: {},
  CategoryScale: {},
  LinearScale: {},
  Filler: {},
  register: jest.fn(),
}));

// Mock API module
const mockGetUsageByService = jest.fn();
const mockGetUsageForecast = jest.fn();
const mockGetAnalyticsTrends = jest.fn();
const mockGetAnalyticsForecast = jest.fn();
const mockGetAnalyticsAnomalies = jest.fn();
const mockAcknowledgeAnomaly = jest.fn();

jest.mock("../services/api", () => ({
  getUsageByService: (...args) => mockGetUsageByService(...args),
  getUsageForecast: (...args) => mockGetUsageForecast(...args),
  getAnalyticsTrends: (...args) => mockGetAnalyticsTrends(...args),
  getAnalyticsForecast: (...args) => mockGetAnalyticsForecast(...args),
  getAnalyticsAnomalies: (...args) => mockGetAnalyticsAnomalies(...args),
  acknowledgeAnomaly: (...args) => mockAcknowledgeAnomaly(...args),
}));

// ---------------------------------------------------------------------------
// Default mock responses
// ---------------------------------------------------------------------------

const serviceData = {
  data: {
    by_service: [
      { service_id: 1, service_name: "OpenAI", total_cost: 10.5, total_tokens: 5000, total_calls: 20 },
      { service_id: 2, service_name: "Claude", total_cost: 7.25, total_tokens: 3000, total_calls: 15 },
    ],
  },
};

const forecastData = {
  data: {
    forecasts: [
      {
        account_id: 1,
        account_name: "My OpenAI",
        cost_so_far: 10.5,
        projected_total: 35.0,
        confidence_score: 72,
      },
    ],
  },
};

const trendsData = {
  data: {
    account_id: 1,
    account_name: "My OpenAI",
    period: "30d",
    metric: "cost",
    start_date: "2026-02-01",
    end_date: "2026-03-01",
    daily: [
      { date: "2026-02-01", value: 5.0 },
      { date: "2026-02-02", value: 6.0 },
    ],
    moving_avg_7d: [
      { date: "2026-02-01", cost: 5.0, moving_avg: null },
      { date: "2026-02-02", cost: 6.0, moving_avg: null },
    ],
    moving_avg_30d: [],
    growth_rate_pct: 20.0,
    total: 11.0,
  },
};

const analyticsForcastData = {
  data: {
    account_id: 1,
    account_name: "My OpenAI",
    horizon_days: 30,
    forecast: [
      { date: "2026-03-02", predicted_cost: 6.5, lower_bound: 5.0, upper_bound: 8.0 },
    ],
    r_squared: 0.85,
    confidence_pct: 78.5,
    data_points: 30,
  },
};

const anomaliesData = {
  data: {
    account_id: 1,
    account_name: "My OpenAI",
    anomalies: [
      {
        id: 42,
        anomaly_date: "2026-02-15",
        daily_cost: 50.0,
        baseline_mean: 5.0,
        baseline_std: 1.0,
        z_score: 45.0,
        cost_delta: 45.0,
        severity: "critical",
        is_acknowledged: false,
      },
    ],
    total: 1,
  },
};

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderAnalyticsPage() {
  const AnalyticsPage = require("./AnalyticsPage").default;
  return render(
    <MemoryRouter>
      <AnalyticsPage />
    </MemoryRouter>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AnalyticsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetUsageByService.mockResolvedValue(serviceData);
    mockGetUsageForecast.mockResolvedValue(forecastData);
    mockGetAnalyticsTrends.mockResolvedValue(trendsData);
    mockGetAnalyticsForecast.mockResolvedValue(analyticsForcastData);
    mockGetAnalyticsAnomalies.mockResolvedValue(anomaliesData);
    mockAcknowledgeAnomaly.mockResolvedValue({ data: { anomaly: { id: 42, is_acknowledged: true } } });
  });

  test("renders without crashing", () => {
    renderAnalyticsPage();
    expect(screen.getByText("Analytics")).toBeInTheDocument();
  });

  test("shows back-to-dashboard link", () => {
    renderAnalyticsPage();
    expect(screen.getByText(/← Dashboard/i)).toBeInTheDocument();
  });

  test("shows 'Cost by Service' section heading", () => {
    renderAnalyticsPage();
    expect(screen.getByText(/Cost by Service/i)).toBeInTheDocument();
  });

  test("shows 'Month-end Projections' section heading", () => {
    renderAnalyticsPage();
    expect(screen.getByText(/Month-end Projections/i)).toBeInTheDocument();
  });

  test("shows pie chart when service data is loaded", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
    });
    expect(screen.getByTestId("pie-chart")).toHaveTextContent("OpenAI");
  });

  test("shows projection data for account", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText("My OpenAI")).toBeInTheDocument();
    });
  });

  test("shows trend chart after trends loaded", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      const charts = screen.getAllByTestId("line-chart");
      expect(charts.length).toBeGreaterThan(0);
    });
  });

  test("shows 'Spending Anomalies' section heading", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText(/Spending Anomalies/i)).toBeInTheDocument();
    });
  });

  test("renders anomaly entry when anomalies present", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText("2026-02-15")).toBeInTheDocument();
    });
  });

  test("shows unresolved anomaly count badge", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText(/1 unresolved/i)).toBeInTheDocument();
    });
  });

  test("shows service breakdown table when data loaded", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText(/Service Breakdown/i)).toBeInTheDocument();
    });
    expect(screen.getByText("OpenAI")).toBeInTheDocument();
    expect(screen.getByText("Claude")).toBeInTheDocument();
  });

  test("'No data yet' shown when service list is empty", async () => {
    mockGetUsageByService.mockResolvedValue({ data: { by_service: [] } });
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText(/No data yet/i)).toBeInTheDocument();
    });
  });

  test("'No anomalies detected' shown when list is empty", async () => {
    mockGetAnalyticsAnomalies.mockResolvedValue({
      data: { anomalies: [], total: 0 },
    });
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText(/No anomalies detected/i)).toBeInTheDocument();
    });
  });

  test("dismiss button calls acknowledgeAnomaly", async () => {
    renderAnalyticsPage();
    await waitFor(() => {
      expect(screen.getByText("Dismiss")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Dismiss"));
    await waitFor(() => {
      expect(mockAcknowledgeAnomaly).toHaveBeenCalledWith(42);
    });
  });
});
