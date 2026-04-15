"use client";

import type { Listing } from "@/types";

interface Props {
  listing: Listing;
}

export default function FloorPlanViewerInner({ listing }: Props) {
  const tourUrl = listing.floor_plan_url;

  /* ── Virtual tour available → embed it ── */
  if (tourUrl) {
    return (
      <div style={{ width: "100%", height: "100%", position: "relative" }}>
        <iframe
          src={tourUrl}
          title="Virtual Tour"
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

  /* ── No tour URL → clean fallback ── */
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
          No virtual tour available
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
          This listing doesn&apos;t have a virtual tour yet. View it directly on
          the source site, or order a cinematic video.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%", maxWidth: "260px" }}>
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
              transition: "background 0.2s",
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
            background: "#c8a96e",
            color: "#0a0a08",
            fontFamily: "DM Mono, monospace",
            fontSize: "0.62rem",
            fontWeight: 700,
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
