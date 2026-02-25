import React from "react";

/**
 * SourceBadge — displays a coloured badge indicating data provenance.
 *
 * Props:
 *   source    "api" | "manual"
 *   size      "small" | "medium" (default) | "large"
 *   showIcon  boolean (default true)
 */
const SourceBadge = React.memo(({ source, size = "medium", showIcon = true }) => {
  const icons = { api: "🔄", manual: "✏️" };
  const labels = { api: "API", manual: "MANUAL" };
  const titles = {
    api: "Automatically synced from API",
    manual: "Manually entered by user",
  };

  const sizeClass = size === "medium" ? "" : `source-badge--${size}`;

  return (
    <span
      className={`source-badge source-badge--${source} ${sizeClass}`.trim()}
      title={titles[source] || source}
      data-testid={`source-badge-${source}`}
    >
      {showIcon && (
        <span className="source-badge__icon" aria-hidden="true">
          {icons[source]}
        </span>
      )}
      <span className="source-badge__label">{labels[source] || source}</span>
    </span>
  );
});

SourceBadge.displayName = "SourceBadge";

export default SourceBadge;
