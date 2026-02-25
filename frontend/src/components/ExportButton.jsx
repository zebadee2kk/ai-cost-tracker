import React, { useState } from "react";

/**
 * ExportButton — lets users download their usage data as CSV or JSON.
 *
 * Props:
 *   filters  - object with optional keys: start_date, end_date, service_id,
 *              account_id, source.  All values are forwarded as query params.
 */
const ExportButton = ({ filters = {} }) => {
  const [format, setFormat] = useState("csv");
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const handleExport = async () => {
    setIsExporting(true);
    setProgress(0);
    setError(null);

    const params = new URLSearchParams({ format });
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== "") {
        params.append(key, value);
      }
    });

    const token = localStorage.getItem("token");
    const url = `/api/usage/export?${params.toString()}`;

    try {
      // Use XMLHttpRequest so we get progress events on chunked responses.
      await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("GET", url);
        xhr.responseType = "blob";
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

        xhr.onprogress = (e) => {
          if (e.lengthComputable && e.total > 0) {
            setProgress(Math.round((e.loaded / e.total) * 100));
          } else {
            // Indeterminate — pulse between 10–90 %
            setProgress((prev) => (prev < 90 ? prev + 5 : prev));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            const blob = xhr.response;
            const objectUrl = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = objectUrl;
            const today = new Date().toISOString().split("T")[0];
            link.setAttribute("download", `usage_export_${today}.${format}`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(objectUrl);
            resolve();
          } else {
            reject(new Error(`Server returned ${xhr.status}`));
          }
        };

        xhr.onerror = () => reject(new Error("Network error during export"));
        xhr.send();
      });
    } catch (err) {
      setError("Export failed. Please try again.");
      console.error("Export error:", err);
    } finally {
      setIsExporting(false);
      setProgress(0);
    }
  };

  return (
    <div className="export-controls" data-testid="export-controls">
      <select
        value={format}
        onChange={(e) => setFormat(e.target.value)}
        disabled={isExporting}
        aria-label="Export format"
        className="export-format-select"
      >
        <option value="csv">CSV (Excel)</option>
        <option value="json">JSON</option>
      </select>

      <button
        onClick={handleExport}
        disabled={isExporting}
        aria-label={isExporting ? `Exporting ${progress}%` : "Export data"}
        className="export-btn"
      >
        {isExporting ? `Exporting… ${progress}%` : "⬇ Export Data"}
      </button>

      {isExporting && (
        <div
          className="export-progress-bar"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Export progress"
        >
          <div
            className="export-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {error && (
        <span className="export-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
};

export default ExportButton;
