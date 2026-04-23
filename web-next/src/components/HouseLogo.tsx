"use client";

/**
 * HouseLogo — SVG house icon + "416 HOMES" word mark.
 * Used across all pages in the nav bar.
 */

interface Props {
  size?: number;
  /** Show "Greater Toronto Area" sub-label below word mark */
  sub?: boolean;
}

export default function HouseLogo({ size = 36, sub = false }: Props) {
  const iconW = size;
  const iconH = size;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, lineHeight: 1, userSelect: "none" }}>
      {/* House SVG */}
      <svg
        width={iconW}
        height={iconH}
        viewBox="0 0 36 36"
        fill="none"
        aria-hidden="true"
        style={{ flexShrink: 0 }}
      >
        {/* Roof triangle */}
        <path d="M18 3 L33 16 L3 16 Z" fill="var(--accent)" />
        {/* Chimney */}
        <rect x="24" y="6" width="4" height="9" fill="var(--accent)" opacity="0.75" />
        {/* Walls */}
        <rect x="4" y="16" width="28" height="15" fill="var(--accent)" opacity="0.82" />
        {/* Door */}
        <rect x="14" y="22" width="8" height="9" fill="var(--bg)" />
        {/* Left window */}
        <rect x="7" y="19" width="5" height="5" fill="var(--bg)" opacity="0.65" />
        {/* Right window */}
        <rect x="24" y="19" width="5" height="5" fill="var(--bg)" opacity="0.65" />
      </svg>

      {/* Text */}
      <div>
        <div
          style={{
            fontFamily: "var(--mono)",
            fontWeight: 800,
            fontSize: Math.round(size * 0.56) + "px",
            letterSpacing: "0.03em",
            lineHeight: 1,
          }}
        >
          <span style={{ color: "var(--accent)" }}>416</span>
          <span style={{ color: "var(--text)" }}> HOMES</span>
        </div>
        {sub && (
          <div
            style={{
              fontFamily: "var(--mono)",
              fontSize: Math.round(size * 0.27) + "px",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--text-dim)",
              marginTop: 3,
            }}
          >
            Greater Toronto Area
          </div>
        )}
      </div>
    </div>
  );
}
