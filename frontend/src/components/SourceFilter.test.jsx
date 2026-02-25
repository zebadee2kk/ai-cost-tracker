import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import SourceFilter from "./SourceFilter";

describe("SourceFilter", () => {
  // --- Rendering ---
  test("renders all three filter buttons", () => {
    render(<SourceFilter selected="all" onChange={() => {}} />);
    expect(screen.getByTestId("source-filter-all")).toBeInTheDocument();
    expect(screen.getByTestId("source-filter-api")).toBeInTheDocument();
    expect(screen.getByTestId("source-filter-manual")).toBeInTheDocument();
  });

  test("renders 'Show:' label", () => {
    render(<SourceFilter selected="all" onChange={() => {}} />);
    expect(screen.getByText("Show:")).toBeInTheDocument();
  });

  // --- Active state ---
  test("'All' button is active when selected='all'", () => {
    render(<SourceFilter selected="all" onChange={() => {}} />);
    expect(screen.getByTestId("source-filter-all")).toHaveClass("active");
  });

  test("'API Only' button is active when selected='api'", () => {
    render(<SourceFilter selected="api" onChange={() => {}} />);
    expect(screen.getByTestId("source-filter-api")).toHaveClass("active");
  });

  test("'Manual Only' button is active when selected='manual'", () => {
    render(<SourceFilter selected="manual" onChange={() => {}} />);
    expect(screen.getByTestId("source-filter-manual")).toHaveClass("active");
  });

  test("non-selected buttons do not have 'active' class", () => {
    render(<SourceFilter selected="api" onChange={() => {}} />);
    expect(screen.getByTestId("source-filter-all")).not.toHaveClass("active");
    expect(screen.getByTestId("source-filter-manual")).not.toHaveClass("active");
  });

  // --- Interactions ---
  test("calls onChange with 'api' when API Only is clicked", () => {
    const handleChange = jest.fn();
    render(<SourceFilter selected="all" onChange={handleChange} />);
    fireEvent.click(screen.getByTestId("source-filter-api"));
    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith("api");
  });

  test("calls onChange with 'manual' when Manual Only is clicked", () => {
    const handleChange = jest.fn();
    render(<SourceFilter selected="all" onChange={handleChange} />);
    fireEvent.click(screen.getByTestId("source-filter-manual"));
    expect(handleChange).toHaveBeenCalledWith("manual");
  });

  test("calls onChange with 'all' when All is clicked", () => {
    const handleChange = jest.fn();
    render(<SourceFilter selected="api" onChange={handleChange} />);
    fireEvent.click(screen.getByTestId("source-filter-all"));
    expect(handleChange).toHaveBeenCalledWith("all");
  });

  // --- Accessibility ---
  test("group has aria-label", () => {
    const { container } = render(<SourceFilter selected="all" onChange={() => {}} />);
    const group = container.querySelector("[role='group']");
    expect(group).toBeInTheDocument();
    expect(group).toHaveAttribute("aria-label");
  });

  test("active button has aria-pressed=true", () => {
    render(<SourceFilter selected="api" onChange={() => {}} />);
    expect(screen.getByTestId("source-filter-api")).toHaveAttribute("aria-pressed", "true");
  });

  test("inactive buttons have aria-pressed=false", () => {
    render(<SourceFilter selected="api" onChange={() => {}} />);
    expect(screen.getByTestId("source-filter-all")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("source-filter-manual")).toHaveAttribute("aria-pressed", "false");
  });
});
