"use client";

import { useState } from "react";
import { Listing } from "@/types";
import { formatPrice } from "@/lib/utils";

interface ListingCardProps {
  listing: Listing;
  index?: number;
  onValuate?: () => void;
}

interface ListRowProps {
  listing: Listing;
  active?: boolean;
  onClick?: () => void;
  onOpen?: () => void;
  onValuate?: () => void;
}

/* ── ValueBadge ─────────────────────────────────────────────────────── */
export function ValueBadge({ pct }: { pct: number }) {
  const good  = pct >= 3;
  const ok    = pct > 0 && pct < 3;
  const color = good ? "var(--accent)" : ok ? "var(--text-mute)" : "var(--text-dim)";
  const label = good ? "Under market" : ok ? "Fair" : "Over market";
  return (
    <span style={{
      border: `1px solid ${good ? "var(--border-strong)" : "var(--border)"}`,
      padding: "3px 8px",
      fontFamily: "var(--mono)",
      fontSize: "0.58rem",
      letterSpacing: "0.1em",
      textTransform: "uppercase" as const,
      color,
      display: "inline-flex",
      alignItems: "baseline",
      gap: 5,
    }}>
      {good ? "↓" : pct <= 0 ? "↑" : "="} {Math.abs(pct).toFixed(1)}% · {label}
    </span>
  );
}

/* ── TransitChip ────────────────────────────────────────────────────── */
export function TransitChip({ score }: { score: number }) {
  const label = score >= 9 ? "Elite" : score >= 7 ? "Excellent" : score >= 5 ? "Good" : "Fair";
  return (
    <span style={{
      fontFamily: "var(--mono)",
      fontSize: "0.58rem",
      letterSpacing: "0.1em",
      textTransform: "uppercase" as const,
      color: "var(--text)",
      background: "var(--bg-elev)",
      border: "1px solid var(--border)",
      padding: "3px 8px",
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
    }}>
      <span style={{ color: "var(--accent)" }}>▸</span>{score}/10 {label}
    </span>
  );
}

/* ── ListRow — 120px thumbnail grid, matches design spec ────────────── */
export function ListRow({ listing, active = false, onClick, onOpen, onValuate }: ListRowProps) {
  const photo = listing.photos?.[0];
  const fairValuePct = listing.fair_value != null ? listing.fair_value : null;

  return (
    <div
      onClick={onClick}
      style={{
        display: "grid",
        gridTemplateColumns: "120px 1fr",
        gap: 14,
        padding: 16,
        borderBottom: "1px solid var(--border)",
        cursor: "pointer",
        background: active ? "var(--bg-panel)" : "transparent",
        borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
        transition: "all 0.15s",
      }}
    >
      {/* Thumbnail */}
      <div style={{ position: "relative", aspectRatio: "4/3", overflow: "hidden", background: "var(--bg-elev)" }}>
        {photo ? (
          <img src={photo} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
        ) : (
          <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", color: "var(--text-dim)" }}>—</span>
          </div>
        )}
        {listing.floor_plan_url && (
          <span style={{
            position: "absolute", top: 6, left: 6,
            background: "var(--accent)", color: "var(--bg)",
            padding: "2px 6px",
            fontFamily: "var(--mono)", fontSize: "0.52rem",
            letterSpacing: "0.1em", textTransform: "uppercase" as const, fontWeight: 700,
          }}>⬡ 3D</span>
        )}
      </div>

      {/* Info */}
      <div style={{ minWidth: 0 }}>
        {/* Price + badge */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: "1.3rem", fontWeight: 600, lineHeight: 1 }}>
            {formatPrice(listing.price)}
          </div>
          {fairValuePct != null && <ValueBadge pct={fairValuePct} />}
        </div>

        {/* Address */}
        <div style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text)", marginTop: 6, whiteSpace: "nowrap" as const, overflow: "hidden", textOverflow: "ellipsis" }}>
          {listing.address}
        </div>

        {/* Neighbourhood + source */}
        <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", color: "var(--text-mute)", marginTop: 2, letterSpacing: "0.08em" }}>
          {[listing.neighbourhood, listing.source].filter(Boolean).map(s => s!.toUpperCase()).join(" · ")}
        </div>

        {/* Specs */}
        <div style={{ display: "flex", gap: 8, marginTop: 8, fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text-mute)", flexWrap: "wrap" as const }}>
          {listing.beds   != null && <span>{listing.beds}bd</span>}
          {listing.baths  != null && <span>·</span>}
          {listing.baths  != null && <span>{listing.baths}ba</span>}
          {listing.sqft   != null && <span>·</span>}
          {listing.sqft   != null && <span>{listing.sqft.toLocaleString()}sf</span>}
          {listing.dom    != null && <span>·</span>}
          {listing.dom    != null && <span>{listing.dom}d DOM</span>}
        </div>

        {/* Chips */}
        <div style={{ display: "flex", gap: 6, marginTop: 8, alignItems: "center", flexWrap: "wrap" as const }}>
          {listing.transit_score != null && <TransitChip score={listing.transit_score} />}
          {listing.is_assignment && (
            <span style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", letterSpacing: "0.12em", textTransform: "uppercase" as const, color: "var(--accent)", border: "1px solid var(--border)", padding: "3px 7px" }}>
              Assignment
            </span>
          )}
          {(onOpen || onValuate) && (
            <span style={{ flex: 1 }} />
          )}
          {onOpen && (
            <button onClick={e => { e.stopPropagation(); onOpen(); }} style={{ padding: "3px 8px", background: "transparent", border: "1px solid var(--border)", color: "var(--text-mute)", fontFamily: "var(--mono)", fontSize: "0.56rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", cursor: "pointer" }}>
              Open →
            </button>
          )}
          {onValuate && (
            <button onClick={e => { e.stopPropagation(); onValuate(); }} style={{ padding: "3px 8px", background: "transparent", border: "1px solid var(--border)", color: "var(--text-mute)", fontFamily: "var(--mono)", fontSize: "0.56rem", textTransform: "uppercase" as const, letterSpacing: "0.1em", cursor: "pointer" }}>
              Value
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── ListingCard — photo card ────────────────────────────────────────── */
export function ListingCard({ listing, index = 0, onValuate }: ListingCardProps) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError,  setImgError]  = useState(false);
  const [hovered,   setHovered]   = useState(false);

  const photo     = listing.photos?.[0];
  const showPhoto = !!photo && !imgError;
  const metaParts: string[] = [];
  if (listing.beds)  metaParts.push(`${listing.beds} bd`);
  if (listing.baths) metaParts.push(`${listing.baths} ba`);
  if (listing.sqft)  metaParts.push(`${listing.sqft.toLocaleString()} sqft`);

  return (
    <div
      className="card-enter"
      style={{
        animationDelay: `${index * 60}ms`,
        background: "var(--bg-elev)",
        border: hovered ? "1px solid var(--border-strong)" : "1px solid var(--border)",
        overflow: "hidden",
        transform: hovered ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hovered ? "0 12px 40px rgba(0,0,0,0.4)" : "none",
        transition: "transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease",
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Photo */}
      <div style={{ position: "relative", height: 200, overflow: "hidden", background: "var(--bg-elev)" }}>
        {(!showPhoto || !imgLoaded) && (
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", color: "var(--text-dim)" }}>
              {listing.address.slice(0, 2).toUpperCase()}
            </span>
          </div>
        )}
        {showPhoto && (
          <img
            src={photo} alt={listing.address}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: imgLoaded ? 1 : 0, transition: "opacity 0.5s" }}
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
          />
        )}
        <span style={{ position: "absolute", top: 10, right: 10, background: "rgba(5,6,10,0.85)", border: "1px solid var(--border)", padding: "3px 10px", fontSize: "0.55rem", fontFamily: "var(--mono)", textTransform: "uppercase" as const, letterSpacing: "0.12em", color: "var(--text-mute)" }}>
          {(listing.source || "").toUpperCase()}
        </span>
        {listing.floor_plan_url && (
          <span style={{ position: "absolute", top: 10, left: 10, background: "var(--accent)", color: "var(--bg)", padding: "3px 8px", fontSize: "0.55rem", fontFamily: "var(--mono)", textTransform: "uppercase" as const, letterSpacing: "0.1em", fontWeight: 700 }}>⬡ 3D</span>
        )}
      </div>

      {/* Body */}
      <div style={{ padding: "16px 16px 14px" }}>
        <div style={{ marginBottom: 6 }}>
          <span style={{ fontFamily: "var(--mono)", fontSize: "1.4rem", fontWeight: 600 }}>{formatPrice(listing.price)}</span>
        </div>
        {listing.fair_value != null && <div style={{ marginBottom: 6 }}><ValueBadge pct={listing.fair_value} /></div>}
        {metaParts.length > 0 && (
          <p style={{ fontFamily: "var(--mono)", fontSize: "0.7rem", color: "var(--text-mute)", marginBottom: 4, textTransform: "uppercase" as const, letterSpacing: "0.06em" }}>
            {metaParts.join(" · ")}
          </p>
        )}
        {listing.transit_score != null && <div style={{ marginBottom: 6 }}><TransitChip score={listing.transit_score} /></div>}
        <p style={{ fontFamily: "var(--mono)", fontSize: "0.8rem", color: "var(--text-mute)", marginBottom: 14, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const, lineHeight: 1.45 }}>
          {listing.address}
        </p>
        <div style={{ height: 1, background: "var(--border)", marginBottom: 12 }} />
        <div style={{ display: "flex", gap: 8 }}>
          <a href={listing.url} target="_blank" rel="noreferrer" style={{ flex: 1, textAlign: "center", padding: "8px 4px", border: "1px solid var(--border-strong)", color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase" as const, letterSpacing: "0.08em", textDecoration: "none" }}>
            View Listing
          </a>
          {onValuate && (
            <button onClick={onValuate} style={{ flex: 1, padding: "8px 4px", border: "1px solid var(--border-strong)", color: "var(--text-mute)", background: "transparent", fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase" as const, letterSpacing: "0.08em", cursor: "pointer" }}>
              Valuate
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Skeleton ────────────────────────────────────────────────────────── */
export function ListingCardSkeleton() {
  const shimmer: React.CSSProperties = {
    backgroundImage: "linear-gradient(90deg, var(--bg-elev) 25%, #0f1320 50%, var(--bg-elev) 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.4s infinite",
  };
  return (
    <div style={{ background: "var(--bg-elev)", border: "1px solid var(--border)", overflow: "hidden" }}>
      <div style={{ height: 200, ...shimmer }} />
      <div style={{ padding: 16 }}>
        {[60, 80, 45].map((w, i) => (
          <div key={i} style={{ height: i === 0 ? 22 : 14, width: `${w}%`, ...shimmer, marginBottom: i < 2 ? 8 : 0 }} />
        ))}
      </div>
    </div>
  );
}
