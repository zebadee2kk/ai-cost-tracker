import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import SourceBadge from "./SourceBadge";

describe("SourceBadge", () => {
  // --- Rendering ---
  test("renders API badge with label 'API'", () => {
    render(<SourceBadge source="api" />);
    expect(screen.getByText("API")).toBeInTheDocument();
  });

  test("renders MANUAL badge with label 'MANUAL'", () => {
    render(<SourceBadge source="manual" />);
    expect(screen.getByText("MANUAL")).toBeInTheDocument();
  });

  // --- CSS classes ---
  test("API badge has source-badge--api class", () => {
    const { container } = render(<SourceBadge source="api" />);
    expect(container.firstChild).toHaveClass("source-badge--api");
  });

  test("MANUAL badge has source-badge--manual class", () => {
    const { container } = render(<SourceBadge source="manual" />);
    expect(container.firstChild).toHaveClass("source-badge--manual");
  });

  test("badge has base source-badge class", () => {
    const { container } = render(<SourceBadge source="api" />);
    expect(container.firstChild).toHaveClass("source-badge");
  });

  // --- Icon ---
  test("shows icon by default", () => {
    const { container } = render(<SourceBadge source="api" />);
    expect(container.querySelector(".source-badge__icon")).toBeInTheDocument();
  });

  test("hides icon when showIcon=false", () => {
    const { container } = render(<SourceBadge source="api" showIcon={false} />);
    expect(container.querySelector(".source-badge__icon")).not.toBeInTheDocument();
  });

  // --- Size variants ---
  test("medium size has no extra size class", () => {
    const { container } = render(<SourceBadge source="api" size="medium" />);
    expect(container.firstChild.className).not.toContain("source-badge--medium");
  });

  test("small size has source-badge--small class", () => {
    const { container } = render(<SourceBadge source="api" size="small" />);
    expect(container.firstChild).toHaveClass("source-badge--small");
  });

  test("large size has source-badge--large class", () => {
    const { container } = render(<SourceBadge source="api" size="large" />);
    expect(container.firstChild).toHaveClass("source-badge--large");
  });

  // --- Accessibility ---
  test("API badge has descriptive title attribute", () => {
    const { container } = render(<SourceBadge source="api" />);
    expect(container.firstChild).toHaveAttribute("title");
    expect(container.firstChild.getAttribute("title")).toContain("API");
  });

  test("MANUAL badge has descriptive title attribute", () => {
    const { container } = render(<SourceBadge source="manual" />);
    expect(container.firstChild).toHaveAttribute("title");
    expect(container.firstChild.getAttribute("title")).toContain("Manually");
  });

  test("icon span has aria-hidden", () => {
    const { container } = render(<SourceBadge source="api" />);
    const icon = container.querySelector(".source-badge__icon");
    expect(icon).toHaveAttribute("aria-hidden", "true");
  });

  // --- data-testid ---
  test("renders with correct data-testid for api", () => {
    render(<SourceBadge source="api" />);
    expect(screen.getByTestId("source-badge-api")).toBeInTheDocument();
  });

  test("renders with correct data-testid for manual", () => {
    render(<SourceBadge source="manual" />);
    expect(screen.getByTestId("source-badge-manual")).toBeInTheDocument();
  });
});
