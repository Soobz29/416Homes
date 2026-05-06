"use client";

import { useState, useEffect } from "react";
import { Listing } from "@/types";
import { formatPrice } from "@/lib/utils";

/* ── Investor Panel helpers ──────────────────────────────────────────── */
const GTA_RENT: Record<number, number> = {
  0: 1900, 1: 2200, 2: 2800, 3: 3500, 4: 4200,
};
const NBHD_MULT: Record<string, number> = {
  "king west": 1.15, "yorkville": 1.25, "annex": 1.10,
  "distillery": 1.08, "liberty village": 1.10, "leslieville": 1.05,
  "roncesvalles": 1.05, "beaches": 1.08, "forest hill": 1.20,
  "rosedale": 1.25, "lawrence park": 1.15, "midtown": 1.08,
  "downtown": 1.12, "east york": 0.98, "scarborough": 0.95,
  "north york": 1.02, "etobicoke": 1.00,
};

function calcInvestor(price: number, beds: number, neighbourhood?: string) {
  const down = price * 0.20;
  const principal = price - down;
  const r = 0.065 / 12;
  const n = 300; // 25yr × 12
  const mortgage = Math.round(principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1));
  const nbhdKey = (neighbourhood || "").toLowerCase();
  const nbhdMult = Object.entries(NBHD_MULT).find(([k]) => nbhdKey.includes(k))?.[1] ?? 1.0;
  const bedCapped = Math.min(Math.max(Math.round(beds || 1), 0), 4);
  const rent = Math.round((GTA_RENT[bedCapped] ?? 2200) * nbhdMult);
  const expenses = Math.round(rent * 0.30);
  const noi = rent - expenses;
  const grossYield = (rent * 12) / price * 100;
  const capRate = (noi * 12) / price * 100;
  const cashflow = noi - mortgage;
  const cashOnCash = (cashflow * 12) / down * 100;
  return { down, mortgage, rent, grossYield, capRate, cashflow, cashOnCash };
}

export function InvestorPanel({
  price, beds, neighbourhood,
}: { price: number; beds: number; neighbourhood?: string }) {
  const [open, setOpen] = useState(false);
  if (!price || price < 10000) return null;
  const m = calcInvestor(price, beds, neighbourhood);
  const rows: [string, string, boolean?][] = [
    ["Down (20%)",      `$${m.down.toLocaleString("en-CA")}`],
    ["Monthly mortgage",`$${m.mortgage.toLocaleString("en-CA")}`],
    ["Est. rent / mo",  `$${m.rent.toLocaleString("en-CA")}`],
    ["Gross yield",     `${m.grossYield.toFixed(2)}%`],
    ["Cap rate",        `${m.capRate.toFixed(2)}%`],
    ["Cash-on-cash",    `${m.cashOnCash.toFixed(2)}%`, true],
  ];
  return (
    <div style={{ borderTop: "1px solid var(--border)", marginTop: 10 }} onClick={e => e.stopPropagation()}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: "100%", padding: "7px 0", background: "transparent", border: "none",
          fontFamily: "var(--mono)", fontSize: "0.56rem", letterSpacing: "0.1em",
          textTransform: "uppercase" as const, color: "var(--text-dim)", cursor: "pointer",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}
      >
        <span>◈ Investor View</span>
        <span style={{ fontSize: "0.5rem" }}>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: "var(--border)", marginBottom: 2 }}>
          {rows.map(([label, value, highlight]) => (
            <div key={label} style={{ background: "var(--bg)", padding: "8px 12px" }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.52rem", color: "var(--text-dim)", textTransform: "uppercase" as const, letterSpacing: "0.08em", marginBottom: 2 }}>{label}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.78rem", color: highlight ? (m.cashOnCash > 0 ? "#2ed573" : "#cf6357") : "var(--text)" }}>{value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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

/* ── StatusBadge (Sidestreet-style: Underpriced / Overpriced / Fair / Stale) */
export function StatusBadge({ fairValue, dom }: { fairValue?: number | null; dom?: number | null }) {
  const isUnderpriced = fairValue != null && fairValue >= 3;
  const isOverpriced  = fairValue != null && fairValue <= -3;
  const isStale       = dom != null && dom > 45;

  const label  = isUnderpriced ? "Underpriced" : isOverpriced ? "Overpriced" : isStale ? "Stale" : "Fair value";
  const dot    = isUnderpriced ? "#2ed573" : isOverpriced ? "#cf6357" : isStale ? "#FFB000" : "rgba(255,255,255,0.3)";
  const border = isUnderpriced ? "rgba(46,213,115,0.35)"
               : isOverpriced  ? "rgba(207,99,87,0.35)"
               : isStale       ? "var(--border-strong)"
               : "var(--border)";

  // Always render — "Fair value" is the neutral fallback when no model data exists
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "3px 8px",
      border: `1px solid ${border}`,
      fontFamily: "var(--mono)", fontSize: "0.55rem",
      letterSpacing: "0.12em", textTransform: "uppercase",
      color: isUnderpriced ? "#2ed573" : isOverpriced ? "#cf6357" : isStale ? "var(--accent)" : "var(--text-dim)",
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: dot, flexShrink: 0, display: "inline-block" }} />
      {label}
    </span>
  );
}

/* ── PricePsfChip — price per sqft ──────────────────────────────────── */
export function PricePsfChip({ price, sqft }: { price: number; sqft: number }) {
  if (!sqft || !price) return null;
  const psf = Math.round(price / sqft);
  return (
    <span style={{
      fontFamily: "var(--mono)", fontSize: "0.58rem",
      letterSpacing: "0.08em", color: "var(--text-dim)",
    }}>
      ${psf.toLocaleString()}/sf
    </span>
  );
}

/* ── CommunityPulse — Yes / No / Lower voting (localStorage) ────────── */
type Vote = "yes" | "no" | "lower";

function getStoredVote(id: string): Vote | null {
  try { return (localStorage.getItem(`vote_${id}`) as Vote) || null; } catch { return null; }
}
function setStoredVote(id: string, v: Vote) {
  try { localStorage.setItem(`vote_${id}`, v); } catch { /* noop */ }
}

export function CommunityPulse({ listingId }: { listingId: string }) {
  const [vote, setVote] = useState<Vote | null>(null);
  useEffect(() => { setVote(getStoredVote(listingId)); }, [listingId]);

  function cast(v: Vote, e: React.MouseEvent) {
    e.stopPropagation();
    const next = vote === v ? null : v;
    if (next) { setStoredVote(listingId, next); } else {
      try { localStorage.removeItem(`vote_${listingId}`); } catch { /* noop */ }
    }
    setVote(next);
  }

  const btnBase: React.CSSProperties = {
    padding: "3px 9px", background: "transparent",
    fontFamily: "var(--mono)", fontSize: "0.54rem",
    textTransform: "uppercase", letterSpacing: "0.1em",
    cursor: "pointer", transition: "all 0.15s",
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }} onClick={e => e.stopPropagation()}>
      <span style={{ fontFamily: "var(--mono)", fontSize: "0.52rem", color: "var(--text-dim)", letterSpacing: "0.1em", marginRight: 2 }}>BUY?</span>
      {([["yes","👍","#2ed573"], ["no","👎","#cf6357"], ["lower","↓","#FFB000"]] as [Vote,string,string][]).map(([v, icon, col]) => (
        <button
          key={v}
          onClick={e => cast(v, e)}
          style={{
            ...btnBase,
            border: `1px solid ${vote === v ? col : "var(--border)"}`,
            color: vote === v ? col : "var(--text-dim)",
            background: vote === v ? `${col}18` : "transparent",
          }}
        >
          {icon} {v}
        </button>
      ))}
    </div>
  );
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
      fontFamily: "var(--mono)", fontSize: "0.58rem",
      letterSpacing: "0.1em", textTransform: "uppercase" as const,
      color, display: "inline-flex", alignItems: "baseline", gap: 5,
    }}>
      {good ? "↓" : pct <= 0 ? "↑" : "="} {Math.abs(pct).toFixed(1)}% · {label}
    </span>
  );
}

/* ── TransitChip ────────────────────────────────────────────────────── */
export function TransitChip({ score }: { score: number }) {
  const label = score >= 9 ? "Elite" : score >= 7 ? "Excellent" : score >= 5 ? "Good" : "Fair";
  const color = score >= 9 ? "#2ed573" : score >= 7 ? "#FFB000" : score >= 5 ? "#8A8876" : "#5A5848";
  return (
    <span style={{
      fontFamily: "var(--mono)", fontSize: "0.58rem",
      letterSpacing: "0.1em", textTransform: "uppercase" as const,
      color, background: "var(--bg-elev)",
      border: `1px solid ${color}40`, padding: "3px 8px",
      display: "inline-flex", alignItems: "center", gap: 5,
    }}>
      <span style={{ color }}>▸</span>{score}/10 {label}
    </span>
  );
}

/* ── ListRow ────────────────────────────────────────────────────────── */
export function ListRow({ listing, active = false, onClick, onOpen, onValuate }: ListRowProps) {
  const photo        = listing.photos?.[0];
  const fairValuePct = listing.fair_value != null ? listing.fair_value : null;

  return (
    <div
      onClick={onClick}
      style={{
        display: "grid", gridTemplateColumns: "120px 1fr",
        gap: 14, padding: 16,
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
        {/* Row 1: price + status badge */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" as const }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: "1.3rem", fontWeight: 600, lineHeight: 1 }}>
            {formatPrice(listing.price)}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <StatusBadge fairValue={fairValuePct} dom={listing.dom} />
          </div>
        </div>

        {/* Row 2: ValueBadge (% detail) + $/sf */}
        {(fairValuePct != null || (listing.sqft > 0)) && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 5 }}>
            {fairValuePct != null && <ValueBadge pct={fairValuePct} />}
            {listing.sqft > 0 && <PricePsfChip price={listing.price} sqft={listing.sqft} />}
          </div>
        )}

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
          {listing.beds  > 0 && <span>{listing.beds}bd</span>}
          {listing.baths > 0 && <><span>·</span><span>{listing.baths}ba</span></>}
          {listing.sqft  > 0 && <><span>·</span><span>{listing.sqft.toLocaleString()}sf</span></>}
          {listing.dom   != null && <><span>·</span><span>{listing.dom}d DOM</span></>}
        </div>

        {/* Chips row */}
        <div style={{ display: "flex", gap: 6, marginTop: 8, alignItems: "center", flexWrap: "wrap" as const }}>
          {listing.transit_score != null && <TransitChip score={listing.transit_score} />}
          {listing.is_assignment && (
            <span style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", letterSpacing: "0.12em", textTransform: "uppercase" as const, color: "var(--accent)", border: "1px solid var(--border)", padding: "3px 7px" }}>
              Assignment
            </span>
          )}
        </div>

        {/* Community pulse + action buttons */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10, flexWrap: "wrap" as const, gap: 6 }}>
          <CommunityPulse listingId={listing.id} />
          <div style={{ display: "flex", gap: 6 }}>
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
        {/* Status badge overlay */}
        <div style={{ position: "absolute", top: 10, left: 10 }}>
          <StatusBadge fairValue={listing.fair_value} dom={listing.dom} />
        </div>
        <span style={{ position: "absolute", top: 10, right: 10, background: "rgba(5,6,10,0.85)", border: "1px solid var(--border)", padding: "3px 10px", fontSize: "0.55rem", fontFamily: "var(--mono)", textTransform: "uppercase" as const, letterSpacing: "0.12em", color: "var(--text-mute)" }}>
          {(listing.source || "").toUpperCase()}
        </span>
        {listing.floor_plan_url && (
          <span style={{ position: "absolute", bottom: 10, left: 10, background: "var(--accent)", color: "var(--bg)", padding: "3px 8px", fontSize: "0.55rem", fontFamily: "var(--mono)", textTransform: "uppercase" as const, letterSpacing: "0.1em", fontWeight: 700 }}>⬡ 3D</span>
        )}
      </div>

      {/* Body */}
      <div style={{ padding: "16px 16px 14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
          <span style={{ fontFamily: "var(--mono)", fontSize: "1.4rem", fontWeight: 600 }}>{formatPrice(listing.price)}</span>
          {listing.sqft > 0 && <PricePsfChip price={listing.price} sqft={listing.sqft} />}
        </div>
        {(listing.fair_value != null || (listing.dom != null && listing.dom > 45)) && (
          <div style={{ marginBottom: 6 }}>
            <StatusBadge fairValue={listing.fair_value} dom={listing.dom} />
          </div>
        )}
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
        {/* Community pulse */}
        <div style={{ marginBottom: 10 }}>
          <CommunityPulse listingId={listing.id} />
        </div>
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
        <InvestorPanel price={listing.price} beds={listing.beds} neighbourhood={listing.neighbourhood} />
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
