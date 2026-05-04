import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "416Homes — GTA Real Estate Intelligence";
export const size = { width: 1200, height: 628 };
export const contentType = "image/png";

const BG      = "#05060A";
const AMBER   = "#FFB000";
const TEXT    = "#E8E4D9";
const MUTED   = "#8A8876";
const BORDER  = "rgba(255,176,0,0.22)";
const PANEL   = "rgba(255,176,0,0.04)";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: BG,
          fontFamily: "monospace",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Amber top border */}
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 3, backgroundColor: AMBER }} />

        {/* Subtle grid lines */}
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "space-between", pointerEvents: "none" }}>
          {[...Array(8)].map((_, i) => (
            <div key={i} style={{ height: 1, backgroundColor: "rgba(255,176,0,0.04)" }} />
          ))}
        </div>
        <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "space-between", pointerEvents: "none" }}>
          {[...Array(12)].map((_, i) => (
            <div key={i} style={{ width: 1, backgroundColor: "rgba(255,176,0,0.04)" }} />
          ))}
        </div>

        {/* Main content */}
        <div style={{ display: "flex", flexDirection: "column", flex: 1, padding: "52px 72px 48px", justifyContent: "space-between" }}>

          {/* ── Logo row ── */}
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <svg width="44" height="44" viewBox="0 0 36 36" fill="none">
              <path d="M18 3 L33 16 L3 16 Z" fill={AMBER} />
              <rect x="24" y="6" width="4" height="9" fill={AMBER} opacity="0.75" />
              <rect x="4" y="16" width="28" height="15" fill={AMBER} opacity="0.82" />
              <rect x="14" y="22" width="8" height="9" fill={BG} />
              <rect x="7" y="19" width="5" height="5" fill={BG} opacity="0.65" />
              <rect x="24" y="19" width="5" height="5" fill={BG} opacity="0.65" />
            </svg>
            <div style={{ display: "flex", alignItems: "baseline", gap: 0 }}>
              <span style={{ fontSize: 40, fontWeight: 800, color: AMBER, letterSpacing: "-0.01em" }}>416</span>
              <span style={{ fontSize: 40, fontWeight: 800, color: TEXT, letterSpacing: "-0.01em" }}>&nbsp;HOMES</span>
            </div>
            <div style={{ marginLeft: 16, display: "flex", padding: "4px 12px", border: `1px solid ${BORDER}`, backgroundColor: PANEL }}>
              <span style={{ color: AMBER, fontSize: 12, letterSpacing: "0.2em" }}>TORONTO · GTA</span>
            </div>
          </div>

          {/* ── Hero text ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <div style={{ width: 32, height: 2, backgroundColor: AMBER }} />
              <span style={{ fontSize: 14, color: AMBER, letterSpacing: "0.2em" }}>REAL ESTATE INTELLIGENCE</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 66, fontWeight: 800, color: TEXT, lineHeight: 1.0, letterSpacing: "-0.02em" }}>
                Stop chasing listings.
              </span>
              <span style={{ fontSize: 66, fontWeight: 800, color: AMBER, lineHeight: 1.0, letterSpacing: "-0.02em" }}>
                Let them find you.
              </span>
            </div>
            <div style={{ display: "flex", marginTop: 8 }}>
              <span style={{ fontSize: 18, color: MUTED, letterSpacing: "0.02em", maxWidth: 640 }}>
                Scans Realtor.ca · Zoocasa · Condos.ca · Kijiji every 30 minutes.
                Real sold-comp valuations. Telegram + email alerts. Free to start.
              </span>
            </div>
          </div>

          {/* ── Stats strip ── */}
          <div style={{ display: "flex", border: `1px solid ${BORDER}`, backgroundColor: PANEL }}>
            {[
              ["2,500+",  "Active GTA Listings"],
              ["50+",     "Neighbourhoods"],
              ["30 min",  "Scan Frequency"],
              ["$0",      "To Start"],
            ].map(([val, label], i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  gap: 5,
                  padding: "18px 28px",
                  borderRight: i < 3 ? `1px solid ${BORDER}` : "none",
                }}
              >
                <span style={{ fontSize: 30, fontWeight: 700, color: AMBER, letterSpacing: "-0.01em" }}>{val}</span>
                <span style={{ fontSize: 11, color: MUTED, letterSpacing: "0.14em", textTransform: "uppercase" }}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Amber bottom accent bar */}
        <div style={{ height: 3, backgroundColor: AMBER, opacity: 0.35 }} />
      </div>
    ),
    { ...size }
  );
}
