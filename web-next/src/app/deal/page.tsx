"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import HouseLogo from "@/components/HouseLogo";
import { calcInvestor, getDealVerdict, fmtCashflow } from "@/lib/investor";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

/* ── GTA neighbourhood options for property type hint ── */
const GTA_CITIES = ["Toronto", "Mississauga", "Brampton", "Markham", "Vaughan", "Richmond Hill", "Oakville", "Ajax", "Pickering"];

export default function DealPage() {
  // ── Inputs ─────────────────────────────────────────────────────────────────
  const [address,    setAddress]    = useState("");
  const [price,      setPrice]      = useState(850000);
  const [beds,       setBeds]       = useState(2);
  const [downPct,    setDownPct]    = useState(20);
  const [rate,       setRate]       = useState(6.5);
  const [hoaOn,      setHoaOn]      = useState(false);
  const [hoaAmt,     setHoaAmt]     = useState(300);
  const [rentOverride, setRentOverride] = useState<number | "">("");
  const [neighbourhood, setNeighbourhood] = useState("");
  const [propType,   setPropType]   = useState<"condo"|"semi"|"detached"|"townhouse">("condo");
  const [strategy,   setStrategy]   = useState<"cashflow"|"balanced"|"appreciation">("balanced");

  // ── Address lookup ──────────────────────────────────────────────────────────
  const [searching,  setSearching]  = useState(false);
  const [foundAddr,  setFoundAddr]  = useState<string | null>(null);

  const lookupAddress = useCallback(async () => {
    if (!address.trim()) return;
    setSearching(true);
    setFoundAddr(null);
    try {
      const res = await fetch(`${API_BASE}/api/listings?search=${encodeURIComponent(address)}&limit=1`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      const hit = data.listings?.[0] ?? data[0];
      if (hit) {
        if (hit.price > 0)      setPrice(hit.price);
        if (hit.bedrooms > 0)   setBeds(hit.bedrooms);
        if (hit.neighbourhood)  setNeighbourhood(hit.neighbourhood);
        setFoundAddr(hit.address ?? address);
      }
    } catch {
      /* silent — user can still enter manually */
    } finally {
      setSearching(false);
    }
  }, [address]);

  // ── Computed metrics ────────────────────────────────────────────────────────
  const hoa   = hoaOn ? hoaAmt : 0;
  const rent  = rentOverride !== "" ? Number(rentOverride) : undefined;
  const m     = calcInvestor(price, beds, neighbourhood, downPct / 100, rate / 100, hoa);
  // If user overrode rent, recompute manually
  const effectiveRent = rent ?? m.rent;
  const expenses2     = Math.round(effectiveRent * 0.30) + hoa;
  const noi2          = effectiveRent - expenses2;
  const mortgage2     = m.mortgage;
  const cashflow2     = noi2 - mortgage2;
  const grossYield2   = (effectiveRent * 12) / price * 100;
  const capRate2      = (noi2 * 12) / price * 100;
  const down2         = price * (downPct / 100);
  const cashOnCash2   = down2 > 0 ? (cashflow2 * 12) / down2 * 100 : 0;
  const ptr2          = price / (effectiveRent * 12);

  // Strategy adjusts thresholds slightly (cosmetic / hint)
  const v = getDealVerdict(cashOnCash2, capRate2, ptr2);

  const cfColor = cashflow2 >= 0 ? "#2ed573" : "#cf6357";

  // ── Styles ─────────────────────────────────────────────────────────────────
  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };
  const label: React.CSSProperties = { ...mono, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 4 };
  const inputStyle: React.CSSProperties = {
    ...mono, fontSize: "0.82rem", background: "var(--bg-elev)",
    border: "1px solid var(--border)", color: "var(--text)",
    padding: "8px 12px", width: "100%", outline: "none",
  };
  const chipBtn = (active: boolean, col = "var(--accent)"): React.CSSProperties => ({
    ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em",
    padding: "5px 12px", cursor: "pointer",
    background: active ? `${col}18` : "var(--bg-elev)",
    border: `1px solid ${active ? col : "var(--border)"}`,
    color: active ? col : "var(--text-mute)",
    transition: "all 0.15s",
  });
  const metricBox: React.CSSProperties = {
    background: "var(--bg-elev)", border: "1px solid var(--border)", padding: "14px 16px",
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      {/* Nav */}
      <nav style={{ borderBottom: "1px solid var(--border)", padding: "0 40px", height: 52, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <HouseLogo size={22} />
          <span style={{ ...mono, fontSize: "0.7rem", letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--text)" }}>416Homes</span>
        </Link>
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <Link href="/dashboard" style={{ ...mono, fontSize: "0.62rem", color: "var(--text-mute)", textDecoration: "none", letterSpacing: "0.12em", textTransform: "uppercase" }}>Listings</Link>
          <Link href="/strategy" style={{ ...mono, fontSize: "0.62rem", color: "var(--text-mute)", textDecoration: "none", letterSpacing: "0.12em", textTransform: "uppercase" }}>Find My Strategy</Link>
        </div>
      </nav>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "48px 32px" }}>
        {/* Header */}
        <div style={{ marginBottom: 36 }}>
          <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.2em", color: "var(--accent)", marginBottom: 8 }}>◈ Deal Calculator</div>
          <h1 style={{ fontFamily: "var(--serif, Georgia)", fontSize: "2rem", fontWeight: 400, margin: 0, marginBottom: 8 }}>Deal Analysis</h1>
          <p style={{ ...mono, fontSize: "0.65rem", color: "var(--text-mute)", margin: 0 }}>Enter any GTA address or adjust inputs to see your deal analysis instantly.</p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: 32, alignItems: "start" }}>
          {/* ── LEFT PANEL: Inputs ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

            {/* Address lookup */}
            <div style={{ border: "1px solid var(--border)", padding: 20 }}>
              <div style={{ ...mono, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                Property Lookup
                <span style={{ background: "rgba(200,169,110,0.15)", border: "1px solid var(--border)", padding: "1px 6px", fontSize: "0.44rem", letterSpacing: "0.1em" }}>GTA DATA</span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  value={address}
                  onChange={e => setAddress(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && lookupAddress()}
                  placeholder="123 King St W, Toronto"
                  style={{ ...inputStyle, flex: 1 }}
                />
                <button
                  onClick={lookupAddress}
                  disabled={searching}
                  style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", padding: "8px 16px", background: "var(--accent)", color: "var(--bg)", border: "none", cursor: "pointer", opacity: searching ? 0.6 : 1 }}
                >
                  {searching ? "..." : "Search →"}
                </button>
              </div>
              {foundAddr && (
                <div style={{ ...mono, fontSize: "0.58rem", color: "#2ed573", marginTop: 8 }}>✓ Found: {foundAddr}</div>
              )}
            </div>

            {/* Property type */}
            <div>
              <div style={label}>Property Type</div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {(["condo","semi","detached","townhouse"] as const).map(t => (
                  <button key={t} onClick={() => setPropType(t)} style={chipBtn(propType === t)}>
                    {t === "semi" ? "Semi-Det" : t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Purchase */}
            <div style={{ border: "1px solid var(--border)", padding: 16 }}>
              <div style={{ ...mono, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 14 }}>
                Purchase · {downPct}% down · {rate}%
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div>
                  <div style={label}>Purchase Price</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ ...mono, fontSize: "0.82rem", color: "var(--text-dim)" }}>$</span>
                    <input type="number" value={price} onChange={e => setPrice(Number(e.target.value))}
                      style={{ ...inputStyle, flex: 1 }} />
                  </div>
                </div>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div style={label}>Down Payment</div>
                    <span style={{ ...mono, fontSize: "0.6rem", color: "var(--accent)" }}>{downPct}% · ${Math.round(price * downPct / 100).toLocaleString("en-CA")}</span>
                  </div>
                  <input type="range" min={5} max={40} step={5} value={downPct}
                    onChange={e => setDownPct(Number(e.target.value))}
                    style={{ width: "100%", accentColor: "var(--accent)", marginTop: 4 }} />
                  <div style={{ display: "flex", justifyContent: "space-between", ...mono, fontSize: "0.44rem", color: "var(--text-dim)", marginTop: 2 }}>
                    <span>5%</span><span>40%</span>
                  </div>
                </div>
                <div>
                  <div style={label}>Interest Rate (%)</div>
                  <input type="number" value={rate} step={0.1} min={1} max={12}
                    onChange={e => setRate(Number(e.target.value))} style={inputStyle} />
                </div>
                <div>
                  <div style={label}>HOA / Maintenance</div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button onClick={() => setHoaOn(false)} style={chipBtn(!hoaOn)}>No HOA</button>
                    <button onClick={() => setHoaOn(true)}  style={chipBtn(hoaOn)}>Yes →</button>
                    {hoaOn && (
                      <input type="number" value={hoaAmt} onChange={e => setHoaAmt(Number(e.target.value))}
                        placeholder="$/mo" style={{ ...inputStyle, width: 90, padding: "5px 10px" }} />
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Income & Expenses */}
            <div style={{ border: "1px solid var(--border)", padding: 16 }}>
              <div style={{ ...mono, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 14 }}>
                Income &amp; Expenses · Rent ${effectiveRent.toLocaleString("en-CA")}/mo · Exp ${expenses2.toLocaleString("en-CA")}/mo
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <div style={label}>Expected Monthly Rent</div>
                    {rentOverride === "" && (
                      <span style={{ ...mono, fontSize: "0.5rem", color: "var(--text-dim)" }}>auto-estimated</span>
                    )}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ ...mono, fontSize: "0.82rem", color: "var(--text-dim)" }}>$</span>
                    <input type="number" value={rentOverride === "" ? effectiveRent : rentOverride}
                      onChange={e => setRentOverride(e.target.value === "" ? "" : Number(e.target.value))}
                      style={{ ...inputStyle, flex: 1 }} />
                  </div>
                  {rentOverride !== "" && (
                    <button onClick={() => setRentOverride("")} style={{ ...mono, fontSize: "0.5rem", color: "var(--text-dim)", background: "none", border: "none", cursor: "pointer", marginTop: 4 }}>
                      ↺ Reset to estimate
                    </button>
                  )}
                </div>
                <div>
                  <div style={label}>Monthly Expenses (est. 30% of rent)</div>
                  <div style={{ ...mono, fontSize: "0.72rem", color: "var(--text-mute)", padding: "8px 12px", background: "var(--bg-elev)", border: "1px solid var(--border)" }}>
                    ${expenses2.toLocaleString("en-CA")}
                  </div>
                </div>
              </div>
            </div>

            {/* Strategy */}
            <div>
              <div style={label}>Investor Strategy</div>
              <div style={{ display: "flex", gap: 6 }}>
                {(["cashflow","balanced","appreciation"] as const).map(s => (
                  <button key={s} onClick={() => setStrategy(s)} style={chipBtn(strategy === s)}>
                    {s === "cashflow" ? "Cash Flow" : s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
              </div>
              <div style={{ ...mono, fontSize: "0.5rem", color: "var(--text-dim)", marginTop: 6 }}>
                {strategy === "cashflow"     ? "Weighted toward monthly cash flow. GTA condos typically break even." :
                 strategy === "appreciation" ? "Weighted toward long-term equity growth. High-PTR markets still win." :
                 "Averages cash flow and appreciation scores equally."}
              </div>
            </div>
          </div>

          {/* ── RIGHT PANEL: Output ── */}
          <div style={{ position: "sticky", top: 24, display: "flex", flexDirection: "column", gap: 16 }}>

            {price < 10000 ? (
              <div style={{ ...mono, fontSize: "0.7rem", color: "var(--text-dim)", textAlign: "center", padding: "80px 0" }}>
                Enter an address or adjust any input to see your deal analysis.
              </div>
            ) : (<>

              {/* Deal Verdict card */}
              <div style={{ border: `1px solid ${v.color}40`, background: `${v.color}08`, padding: 24 }}>
                <div style={{ ...mono, fontSize: "0.5rem", textTransform: "uppercase", letterSpacing: "0.18em", color: v.color, marginBottom: 8 }}>Deal Verdict</div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <div style={{ fontFamily: "var(--serif, Georgia)", fontSize: "1.6rem", color: v.color }}>{v.label}</div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ ...mono, fontSize: "0.5rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.12em" }}>Confidence</div>
                    <div style={{ ...mono, fontSize: "1.4rem", color: v.color, fontWeight: 700, lineHeight: 1 }}>{v.score}</div>
                    <div style={{ ...mono, fontSize: "0.46rem", color: "var(--text-dim)" }}>/100</div>
                  </div>
                </div>
                {v.reasons.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    {v.reasons.map((r, i) => (
                      <div key={i} style={{ ...mono, fontSize: "0.58rem", color: "var(--text-mute)" }}>· {r}</div>
                    ))}
                  </div>
                )}
              </div>

              {/* Key metrics grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                <div style={{ ...metricBox, gridColumn: "span 3" }}>
                  <div style={label}>Monthly Cash Flow</div>
                  <div style={{ ...mono, fontSize: "1.8rem", color: cfColor, fontWeight: 700 }}>{fmtCashflow(cashflow2)}</div>
                  <div style={{ ...mono, fontSize: "0.52rem", color: "var(--text-dim)", marginTop: 4 }}>
                    Rent ${effectiveRent.toLocaleString("en-CA")} − Mortgage ${mortgage2.toLocaleString("en-CA")} − Exp ${expenses2.toLocaleString("en-CA")}
                  </div>
                </div>
                {[
                  ["Cap Rate",    `${capRate2.toFixed(2)}%`,    capRate2 >= 4],
                  ["Cash-on-Cash",`${cashOnCash2.toFixed(2)}%`, cashOnCash2 > 0],
                  ["Gross Yield", `${grossYield2.toFixed(2)}%`, grossYield2 >= 4],
                  ["Price-to-Rent",`${ptr2.toFixed(1)}×`,       ptr2 < 35],
                  ["Down Payment", `$${down2.toLocaleString("en-CA")}`,  true],
                  ["Mortgage/mo",  `$${mortgage2.toLocaleString("en-CA")}`, true],
                ].map(([l, val, good]) => (
                  <div key={l as string} style={metricBox}>
                    <div style={label}>{l}</div>
                    <div style={{ ...mono, fontSize: "1rem", color: (good as boolean) ? "var(--text)" : "#cf6357", fontWeight: 500 }}>{val}</div>
                  </div>
                ))}
              </div>

              {/* Assumptions footer */}
              <div style={{ ...mono, fontSize: "0.5rem", color: "var(--text-dim)", lineHeight: 1.8 }}>
                ◈ {downPct}% down · {rate}% rate · 25yr amort · 30% expense ratio · GTA market rents{hoaOn ? ` · $${hoaAmt}/mo HOA` : ""}<br />
                Calculator uses estimated values. Not financial advice.
              </div>

              {/* CTA */}
              <div style={{ display: "flex", gap: 12 }}>
                <Link href="/strategy" style={{
                  ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em",
                  padding: "10px 20px", background: "var(--accent)", color: "var(--bg)",
                  textDecoration: "none", display: "inline-block",
                }}>
                  Find My Strategy →
                </Link>
                <Link href="/dashboard" style={{
                  ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em",
                  padding: "10px 20px", background: "transparent", color: "var(--text-mute)",
                  border: "1px solid var(--border)", textDecoration: "none", display: "inline-block",
                }}>
                  Browse Listings
                </Link>
              </div>
            </>)}
          </div>
        </div>
      </div>
    </div>
  );
}
