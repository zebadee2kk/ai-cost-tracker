import React from "react";

/**
 * SourceFilter — toggle buttons for filtering usage records by data source.
 *
 * Props:
 *   selected   "all" | "api" | "manual"
 *   onChange   (value: string) => void
 */
const SourceFilter = ({ selected, onChange }) => {
  const options = [
    { value: "all",    label: "All",         icon: null },
    { value: "api",    label: "API Only",    icon: "🔄" },
    { value: "manual", label: "Manual Only", icon: "✏️" },
  ];

  return (
    <div className="source-filter" role="group" aria-label="Filter by data source">
      <span className="source-filter__label">Show:</span>
      <div className="source-filter__buttons">
        {options.map((opt) => (
          <button
            key={opt.value}
            className={`source-filter__button${selected === opt.value ? " active" : ""}`}
            onClick={() => onChange(opt.value)}
            aria-pressed={selected === opt.value}
            data-testid={`source-filter-${opt.value}`}
          >
            {opt.icon && (
              <span className="source-filter__icon" aria-hidden="true">
                {opt.icon}
              </span>
            )}
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SourceFilter;
