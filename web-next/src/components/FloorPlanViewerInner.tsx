"use client";

import { useState } from "react";
import type { Listing } from "@/types";

interface Props {
  listing: Listing;
}

const DEMO_TOUR_URL = "https://my.matterport.com/show/?m=jm5WwEA3HUN";

export default function FloorPlanViewerInner({ listing }: Props) {
  const tourUrl = listing.floor_plan_url;
  const [demoMode, setDemoMode] = useState(false);

  /* ── Real virtual tour available OR demo mode active → show iframe ── */
  if (tourUrl || demoMode) {
    return (
      <div style={{ width: "100%", height: "100%", position: "relative" }}>
        {/* Back button in demo mode */}
        {demoMode && !tourUrl && (
          <button
            onClick={() => setDemoMode(false)}
            style={{
              position: "absolute",
              top: "12px",
              left: "12px",
              zIndex: 10,
              padding: "6px 12px",
              background: "rgba(10,10,8,0.85)",
              border: "1px solid rgba(200,169,110,0.4)",
              color: "#c8a96e",
              fontFamily: "DM Mono, monospace",
              fontSize: "0.6rem",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              cursor: "pointer",
            }}
          >
            ← Back
          </button>
        )}
        {/* Demo label */}
        {demoMode && !tourUrl && (
          <span
            style={{
              position: "absolute",
              top: "12px",
              right: "12px",
              zIndex: 10,
              padding: "4px 10px",
              background: "rgba(200,169,110,0.15)",
              border: "1px solid rgba(200,169,110,0.3)",
              color: "#c8a96e",
              fontFamily: "DM Mono, monospace",
              fontSize: "0.55rem",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
            }}
          >
            Demo Tour
          </span>
        )}
        <iframe
          src={tourUrl || DEMO_TOUR_URL}
          title={tourUrl ? "Virtual Tour" : "Demo Virtual Tour"}
          allow="fullscreen; vr; xr-spatial-tracking"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            border: "none",
            background: "#0a0a08",
          }}
        />
      </div>
    );
  }

  /* ── No tour URL → fallback with demo CTA ── */
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        gap: "20px",
        background: "#0f0f0b",
        padding: "32px",
        textAlign: "center",
      }}
    >
      {/* Icon */}
      <div
        style={{
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          border: "1px solid rgba(200,169,110,0.25)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.5rem",
        }}
      >
        🏠
      </div>

      <div>
        <p
          style={{
            fontFamily: "DM Mono, monospace",
            fontSize: "0.72rem",
            color: "#c8a96e",
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            marginBottom: "8px",
          }}
        >
          No virtual tour for this listing
        </p>
        <p
          style={{
            fontFamily: "DM Mono, monospace",
            fontSize: "0.65rem",
            color: "#6b6b60",
            lineHeight: "1.6",
            maxWidth: "280px",
          }}
        >
          When a listing has a virtual tour, it embeds right here.
          See what it looks like with a live demo:
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%", maxWidth: "260px" }}>
        {/* Demo tour button */}
        <button
          onClick={() => setDemoMode(true)}
          style={{
            display: "block",
            width: "100%",
            padding: "11px 16px",
            background: "#c8a96e",
            color: "#0a0a08",
            fontFamily: "DM Mono, monospace",
            fontSize: "0.62rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            border: "none",
            cursor: "pointer",
            textAlign: "center",
          }}
        >
          ▶ See a Live Demo Tour
        </button>

        {listing.url && (
          <a
            href={listing.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "block",
              padding: "10px 16px",
              background: "rgba(200,169,110,0.1)",
              border: "1px solid rgba(200,169,110,0.25)",
              color: "#c8a96e",
              fontFamily: "DM Mono, monospace",
              fontSize: "0.62rem",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              textDecoration: "none",
              textAlign: "center",
            }}
          >
            View on {listing.source || "listing site"} →
          </a>
        )}
        <a
          href="/video"
          style={{
            display: "block",
            padding: "10px 16px",
            background: "transparent",
            border: "1px solid rgba(200,169,110,0.2)",
            color: "#6b6b60",
            fontFamily: "DM Mono, monospace",
            fontSize: "0.62rem",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            textDecoration: "none",
            textAlign: "center",
          }}
        >
          Order a cinematic video — from $99
        </a>
      </div>
    </div>
  );
}
