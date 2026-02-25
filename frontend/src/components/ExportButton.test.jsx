import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import ExportButton from "./ExportButton";

describe("ExportButton", () => {
  // --- Rendering ---
  test("renders format selector and export button", () => {
    render(<ExportButton />);
    expect(screen.getByRole("combobox", { name: /export format/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /export data/i })).toBeInTheDocument();
  });

  test("default format is 'csv'", () => {
    render(<ExportButton />);
    const select = screen.getByRole("combobox", { name: /export format/i });
    expect(select.value).toBe("csv");
  });

  test("format can be changed to 'json'", () => {
    render(<ExportButton />);
    const select = screen.getByRole("combobox", { name: /export format/i });
    fireEvent.change(select, { target: { value: "json" } });
    expect(select.value).toBe("json");
  });

  test("has csv and json options", () => {
    render(<ExportButton />);
    expect(screen.getByRole("option", { name: /csv/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /json/i })).toBeInTheDocument();
  });

  test("button is initially enabled", () => {
    render(<ExportButton />);
    const btn = screen.getByRole("button", { name: /export data/i });
    expect(btn).not.toBeDisabled();
  });

  test("progress bar is not visible initially", () => {
    const { container } = render(<ExportButton />);
    expect(container.querySelector(".export-progress-bar")).not.toBeInTheDocument();
  });

  // --- Accessibility ---
  test("format selector has aria-label", () => {
    render(<ExportButton />);
    expect(
      screen.getByRole("combobox", { name: /export format/i })
    ).toHaveAttribute("aria-label");
  });

  test("export button has aria-label", () => {
    render(<ExportButton />);
    const btn = screen.getByRole("button", { name: /export data/i });
    expect(btn).toHaveAttribute("aria-label");
  });

  // --- Container ---
  test("renders within export-controls container", () => {
    const { container } = render(<ExportButton />);
    expect(container.querySelector(".export-controls")).toBeInTheDocument();
  });

  test("has correct data-testid", () => {
    render(<ExportButton />);
    expect(screen.getByTestId("export-controls")).toBeInTheDocument();
  });
});
