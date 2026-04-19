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
  onValuate?: () => void;
}

const SOURCE_COLORS: Record<string, string> = {
  zoocasa:      "#5B3CF5",
  kijiji:       "#E8003D",
  redfin:       "#C82021",
  housesigma:   "#FF6B35",
  "realtor.ca": "#D40511",
};

function getInitials(address: string): string {
  const parts = address.trim().split(/\s+/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : address.slice(0, 2).toUpperCase();
}

/* ── ValueBadge — shows fair-value delta if data available ───────── */
export function ValueBadge({ pct }: { pct: number }) {
  const good = pct >= 3;
  const ok   = pct > 0 && pct < 3;
  const color = good ? "var(--accent)" : ok ? "var(--text-mute)" : "var(--text-dim)";
  const label = good ? "Under market" : ok ? "Fair" : "Over market";
  return (
    <span style={{
      border: `1px solid ${good ? "var(--border-strong)" : "var(--border)"}`,
      padding: "3px 8px",
      fontFamily: "var(--mono)",
      fontSize: "0.58rem",
      letterSpacing: "0.1em",
      textTransform: "uppercase",
      color,
      display: "inline-flex",
      alignItems: "baseline",
      gap: 5,
    }}>
      {good ? "↓" : pct <= 0 ? "↑" : "="} {Math.abs(pct).toFixed(1)}% · {label}
    </span>
  );
}

/* ── TransitChip — shows transit score if data available ─────────── */
export function TransitChip({ score }: { score: number }) {
  const label = score >= 9 ? "Elite" : score >= 7 ? "Excellent" : score >= 5 ? "Good" : "Fair";
  return (
    <span style={{
      fontFamily: "var(--mono)",
      fontSize: "0.58rem",
      letterSpacing: "0.1em",
      textTransform: "uppercase",
      color: "var(--text)",
      background: "var(--bg-elev)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius)",
      padding: "3px 8px",
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
    }}>
      <span style={{ color: "var(--accent)" }}>▸</span>{score}/10 {label}
    </span>
  );
}

/* ── ListRow — compact row for dashboard split-view list ─────────── */
export function ListRow({ listing, active = false, onClick, onValuate }: ListRowProps) {
  const [hov, setHov] = useState(false);
  const photo = listing.photos?.[0];

  const fairValuePct = listing.fair_value && listing.price
    ? ((listing.fair_value - listing.price) / listing.fair_value) * 100
    : null;

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex",
        gap: 12,
        padding: "14px 16px",
        cursor: "pointer",
        borderBottom: "1px solid var(--border)",
        borderLeft: active ? "3px solid var(--accent)" : "3px solid transparent",
        background: active ? "var(--bg-panel)" : hov ? "rgba(212,175,55,0.04)" : "transparent",
        transition: "background 0.15s ease, border-left-color 0.15s ease",
      }}
    >
      {/* Thumbnail */}
      <div style={{
        width: 56, height: 56, flexShrink: 0, overflow: "hidden",
        background: "var(--bg-elev)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {photo ? (
          <img src={photo} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          <span style={{ fontFamily: "var(--serif)", fontSize: "1rem", fontWeight: 700, color: "var(--border-strong)", userSelect: "none" }}>
            {getInitials(listing.address)}
          </span>
        )}
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, marginBottom: 2 }}>
          <span style={{ fontFamily: "var(--serif)", fontSize: "1.05rem", fontWeight: 500, color: "var(--text)" }}>
            {formatPrice(listing.price)}
          </span>
          {fairValuePct !== null && <ValueBadge pct={fairValuePct} />}
        </div>
        <p style={{
          fontFamily: "var(--sans)", fontSize: "0.78rem", color: "var(--text-mute)",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: 2,
        }}>
          {listing.address}
        </p>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            {[listing.beds && `${listing.beds}bd`, listing.baths && `${listing.baths}ba`, listing.sqft && `${listing.sqft.toLocaleString()}sqft`].filter(Boolean).join(" · ")}
          </span>
          {listing.transit_score !== undefined && <TransitChip score={listing.transit_score} />}
        </div>
      </div>

      {/* Valuate btn */}
      {onValuate && (
        <button
          onClick={(e) => { e.stopPropagation(); onValuate(); }}
          style={{
            alignSelf: "center", flexShrink: 0,
            padding: "4px 8px",
            border: "1px solid var(--border)",
            background: "transparent",
            color: "var(--text-mute)",
            fontFamily: "var(--mono)",
            fontSize: "0.55rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            cursor: "pointer",
          }}
        >
          Value
        </button>
      )}
    </div>
  );
}

/* ── ListingCard — photo-first card for grid view ───────────────── */
export function ListingCard({ listing, index = 0, onValuate }: ListingCardProps) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [hovered, setHovered] = useState(false);

  const photo = listing.photos?.[0];
  const showPhoto = !!photo && !imgError;
  const sourceKey = (listing.source || "").toLowerCase();
  const badgeColor = SOURCE_COLORS[sourceKey] ?? "#6b6b60";

  const metaParts: string[] = [];
  if (listing.beds)  metaParts.push(`${listing.beds} bd`);
  if (listing.baths) metaParts.push(`${listing.baths} ba`);
  if (listing.sqft)  metaParts.push(`${listing.sqft.toLocaleString()} sqft`);

  const fairValuePct = listing.fair_value && listing.price
    ? ((listing.fair_value - listing.price) / listing.fair_value) * 100
    : null;

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
      <div style={{ position: "relative", height: 200, overflow: "hidden", background: "linear-gradient(135deg,#1a1a14,#0B0B0B)", flexShrink: 0 }}>
        {/* Initials placeholder */}
        <div style={{
          position: "absolute", inset: 0, display: "flex", alignItems: "center",
          justifyContent: "center",
          opacity: showPhoto && imgLoaded ? 0 : 1,
          transition: "opacity 0.4s",
        }}>
          <span style={{ fontSize: "3rem", fontWeight: 800, color: "var(--border-strong)", fontFamily: "var(--serif)", userSelect: "none" }}>
            {getInitials(listing.address)}
          </span>
        </div>

        {showPhoto && (
          <img
            src={photo}
            alt={listing.address}
            style={{
              position: "absolute", inset: 0, width: "100%", height: "100%",
              objectFit: "cover",
              opacity: imgLoaded ? 1 : 0,
              transition: "opacity 0.5s",
            }}
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
          />
        )}

        {/* Source badge */}
        <span style={{
          position: "absolute", top: 10, right: 10,
          background: `${badgeColor}cc`,
          backdropFilter: "blur(4px)",
          padding: "3px 10px",
          fontSize: "0.55rem",
          fontFamily: "var(--mono)",
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: "#fff",
        }}>
          {(listing.source || "").toUpperCase()}
        </span>
      </div>

      {/* Info panel */}
      <div style={{ padding: "16px 16px 14px" }}>
        {/* Price */}
        <div style={{ marginBottom: 4 }}>
          <span style={{
            fontFamily: "var(--serif)",
            fontSize: "1.5rem",
            fontWeight: 500,
            color: "var(--text)",
            letterSpacing: "0.01em",
          }}>
            {formatPrice(listing.price)}
          </span>
        </div>

        {/* ValueBadge */}
        {fairValuePct !== null && (
          <div style={{ marginBottom: 6 }}>
            <ValueBadge pct={fairValuePct} />
          </div>
        )}

        {/* Beds · Baths · Sqft */}
        {metaParts.length > 0 && (
          <p style={{ fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text-mute)", marginBottom: 4, lineHeight: 1.4, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {metaParts.join(" · ")}
          </p>
        )}

        {/* Transit chip */}
        {listing.transit_score !== undefined && (
          <div style={{ marginBottom: 6 }}>
            <TransitChip score={listing.transit_score} />
          </div>
        )}

        {/* Address */}
        <p style={{
          fontFamily: "var(--sans)",
          fontSize: "0.85rem",
          color: "var(--text-mute)",
          marginBottom: 14,
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          lineHeight: 1.45,
        }}>
          {listing.address}
        </p>

        {/* Divider */}
        <div style={{ height: 1, background: "rgba(255,255,255,0.06)", marginBottom: 12 }} />

        {/* Action buttons */}
        <div style={{ display: "flex", gap: 8 }}>
          <ActionLink href={listing.url} label="View Listing" />
          {onValuate && <ActionButton onClick={onValuate} label="Valuate" />}
        </div>
      </div>
    </div>
  );
}

function ActionLink({ href, label }: { href: string; label: string }) {
  const [hov, setHov] = useState(false);
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        flex: 1, textAlign: "center",
        padding: "8px 4px",
        border: hov ? "1px solid var(--accent)" : "1px solid var(--border-strong)",
        color: hov ? "var(--accent)" : "var(--text)",
        fontFamily: "var(--mono)",
        fontSize: "0.62rem",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        textDecoration: "none",
        transition: "border-color 0.2s, color 0.2s",
        display: "block",
      }}
    >
      {label}
    </a>
  );
}

function ActionButton({ onClick, label }: { onClick: () => void; label: string }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        flex: 1,
        padding: "8px 4px",
        border: hov ? "1px solid var(--accent)" : "1px solid var(--border-strong)",
        color: hov ? "var(--accent)" : "var(--text)",
        background: "transparent",
        fontFamily: "var(--mono)",
        fontSize: "0.62rem",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        cursor: "pointer",
        transition: "border-color 0.2s, color 0.2s",
      }}
    >
      {label}
    </button>
  );
}

/* ── Skeleton loading card ──────────────────────────────────────────── */
export function ListingCardSkeleton() {
  const shimmer: React.CSSProperties = {
    backgroundImage: "linear-gradient(90deg,#1a1a14 25%,#222218 50%,#1a1a14 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.4s infinite",
  };
  return (
    <div style={{ background: "var(--bg-elev)", border: "1px solid var(--border)", overflow: "hidden" }}>
      <div style={{ height: 200, ...shimmer }} />
      <div style={{ padding: 16 }}>
        {[60, 80, 45].map((w, i) => (
          <div
            key={i}
            style={{
              height: i === 0 ? 22 : 14,
              width: `${w}%`,
              ...shimmer,
              marginBottom: i < 2 ? 8 : 0,
              borderRadius: 2,
            }}
          />
        ))}
      </div>
    </div>
  );
}
