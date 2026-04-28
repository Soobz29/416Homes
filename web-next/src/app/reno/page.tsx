"use client";

import { useState } from "react";
import Link from "next/link";
import HouseLogo from "@/components/HouseLogo";

/* ── Reno ROI data (GTA market averages) ───────────────────────────── */
const RENO_TYPES = [
  { id: "kitchen_full",  label: "Kitchen — Full Renovation",   roi: 0.90, roiRange: "85–95%",  timeMonths: 18, risk: "Low",    typical: "$40,000–$80,000" },
  { id: "kitchen_minor", label: "Kitchen — Minor Refresh",      roi: 1.05, roiRange: "95–115%", timeMonths: 6,  risk: "Low",    typical: "$10,000–$25,000" },
  { id: "bathroom_prim", label: "Primary Bathroom",             roi: 0.75, roiRange: "70–82%",  timeMonths: 14, risk: "Medium", typical: "$20,000–$45,000" },
  { id: "bathroom_add",  label: "Add a Bathroom",               roi: 0.70, roiRange: "65–78%",  timeMonths: 24, risk: "Medium", typical: "$15,000–$35,000" },
  { id: "basement",      label: "Basement — Finish & Suite",    roi: 0.65, roiRange: "60–72%",  timeMonths: 30, risk: "Medium", typical: "$50,000–$100,000" },
  { id: "paint_cosmetic",label: "Paint + Cosmetic Updates",     roi: 1.25, roiRange: "100–150%",timeMonths: 4,  risk: "Very Low","typical": "$5,000–$15,000" },
  { id: "windows",       label: "New Windows & Doors",          roi: 0.67, roiRange: "60–75%",  timeMonths: 24, risk: "Low",    typical: "$15,000–$40,000" },
  { id: "deck_outdoor",  label: "Deck / Outdoor Living",        roi: 0.62, roiRange: "55–70%",  timeMonths: 18, risk: "Low",    typical: "$20,000–$60,000" },
  { id: "addition",      label: "Room Addition / Extension",    roi: 0.60, roiRange: "50–70%",  timeMonths: 48, risk: "High",   typical: "$80,000–$200,000" },
] as const;

const RISK_COLORS: Record<string, string> = {
  "Very Low": "#2ed573",
  "Low":      "#7bed9f",
  "Medium":   "#ffa502",
  "High":     "#cf6357",
};

const RENO_NAV: [string, string][] = [["/#listings","LISTINGS"],["/#how","HOW IT WORKS"],["/video","VIDEOS"],["/tours","TOURS"],["/stats","STATS"],["/reno","RENO ROI"],["/faq","FAQ"]];

/* ── Nav ────────────────────────────────────────────────────────────── */
function NavBar() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <nav className="nav-bar" style={{
      position: "sticky", top: 0, zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      height: 64, padding: "0 56px",
      background: "rgba(5,6,10,0.92)", backdropFilter: "blur(16px)",
      borderBottom: "1px solid var(--border)",
    }}>
      <Link href="/" style={{ textDecoration: "none" }}>
        <HouseLogo size={28} />
      </Link>
      <ul className="nav-links" style={{ display: "flex", gap: 32, listStyle: "none", margin: 0, padding: 0 }}>
        {RENO_NAV.map(([href,label]) => (
          <li key={href}>
            <Link href={href} style={{ fontFamily: "var(--mono)", fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.14em", color: href === "/reno" ? "var(--accent)" : "var(--text-mute)", textDecoration: "none" }}>
              {label}
            </Link>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button className="hamburger-btn" onClick={() => setMenuOpen(!menuOpen)}
          style={{ background: "transparent", border: "none", color: "var(--text)", fontSize: "1.4rem", cursor: "pointer", padding: "4px 8px", lineHeight: 1 }}>
          {menuOpen ? "✕" : "☰"}
        </button>
        <Link className="nav-cta" href="/dashboard" style={{
          padding: "10px 20px", background: "var(--accent)", color: "var(--bg)",
          fontFamily: "var(--mono)", fontSize: "0.68rem", fontWeight: 700,
          textTransform: "uppercase", letterSpacing: "0.08em", textDecoration: "none",
        }}>
          Dashboard →
        </Link>
      </div>
      {menuOpen && (
        <div style={{ position: "fixed", top: 64, left: 0, right: 0, background: "rgba(5,6,10,0.98)", backdropFilter: "blur(20px)", borderBottom: "1px solid var(--border)", padding: "8px 24px 20px", zIndex: 999 }}>
          {[...RENO_NAV, ["/dashboard", "DASHBOARD"]].map(([href, label]) => (
            <Link key={href} href={href} onClick={() => setMenuOpen(false)} style={{ display: "block", padding: "14px 0", borderBottom: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-mute)", textDecoration: "none" }}>
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}

/* ── Result panel ────────────────────────────────────────────────────── */
interface RenoResult {
  renoType: typeof RENO_TYPES[number];
  budget: number;
  homeValue: number;
  addedValue: number;
  newValue: number;
  roiDollars: number;
  roiPct: number;
  breakEvenMonths: number;
}

function ResultPanel({ result }: { result: RenoResult }) {
  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };
  const isPositive = result.roiDollars >= 0;

  return (
    <div style={{ border: "1px solid var(--border-strong)", background: "var(--bg-elev)", overflow: "hidden" }}>
      {/* Header band */}
      <div style={{ padding: "20px 28px", borderBottom: "1px solid var(--border)", background: "rgba(255,191,0,0.04)" }}>
        <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 6 }}>
          ROI Analysis · {result.renoType.label}
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <span style={{ ...mono, fontSize: "2.8rem", fontWeight: 700, color: isPositive ? "var(--accent)" : "#cf6357", lineHeight: 1 }}>
            {result.roiPct >= 0 ? "+" : ""}{result.roiPct.toFixed(1)}%
          </span>
          <span style={{ ...mono, fontSize: "0.72rem", color: "var(--text-mute)" }}>return on renovation spend</span>
        </div>
      </div>

      {/* Metrics grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", border: "none" }}>
        {[
          { label: "Renovation Budget",   value: `$${result.budget.toLocaleString()}`,          color: "var(--text)" },
          { label: "Value Added",          value: `$${result.addedValue.toLocaleString()}`,       color: isPositive ? "#2ed573" : "#cf6357" },
          { label: "Current Home Value",   value: `$${result.homeValue.toLocaleString()}`,        color: "var(--text)" },
          { label: "Est. Post-Reno Value", value: `$${result.newValue.toLocaleString()}`,         color: "var(--accent)" },
          { label: "Net Gain / Loss",      value: `${isPositive ? "+" : ""}$${result.roiDollars.toLocaleString()}`, color: isPositive ? "#2ed573" : "#cf6357" },
          { label: "Break-even at Sale",   value: result.breakEvenMonths > 0 ? `~${result.breakEvenMonths}mo avg DOM` : "At listing", color: "var(--text-mute)" },
        ].map(({ label, value, color }, i) => (
          <div key={label} style={{
            padding: "18px 24px",
            borderBottom: i < 4 ? "1px solid var(--border)" : "none",
            borderRight: i % 2 === 0 ? "1px solid var(--border)" : "none",
          }}>
            <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 6 }}>{label}</div>
            <div style={{ ...mono, fontSize: "1.1rem", fontWeight: 600, color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Risk + range */}
      <div style={{ padding: "18px 28px", borderTop: "1px solid var(--border)", display: "flex", gap: 28, alignItems: "center", flexWrap: "wrap" }}>
        <div>
          <span style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginRight: 8 }}>Risk</span>
          <span style={{ ...mono, fontSize: "0.72rem", color: RISK_COLORS[result.renoType.risk] ?? "var(--text)" }}>{result.renoType.risk}</span>
        </div>
        <div>
          <span style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginRight: 8 }}>GTA ROI Range</span>
          <span style={{ ...mono, fontSize: "0.72rem", color: "var(--text-mute)" }}>{result.renoType.roiRange}</span>
        </div>
        <div>
          <span style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginRight: 8 }}>Typical Budget</span>
          <span style={{ ...mono, fontSize: "0.72rem", color: "var(--text-mute)" }}>{result.renoType.typical}</span>
        </div>
      </div>

      {/* Disclaimer */}
      <div style={{ padding: "12px 28px", borderTop: "1px solid var(--border)", ...mono, fontSize: "0.56rem", color: "var(--text-dim)", lineHeight: 1.6 }}>
        Estimates based on GTA market averages. Actual returns vary by neighbourhood, contractor, and market conditions.
        Upgrade to 416Homes Pro for comp-backed analysis with sold data.
      </div>
    </div>
  );
}

/* ── Main page ──────────────────────────────────────────────────────── */
export default function RenoPage() {
  const [homeValue, setHomeValue]     = useState("");
  const [budget, setBudget]           = useState("");
  const [renoType, setRenoType]       = useState<typeof RENO_TYPES[number]["id"]>("kitchen_full");
  const [result, setResult]           = useState<RenoResult | null>(null);
  const [showPremium, setShowPremium] = useState(false);

  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };

  function compute() {
    const hv = Number(homeValue.replace(/,/g, ""));
    const b  = Number(budget.replace(/,/g, ""));
    if (!hv || !b) return;
    const rt = RENO_TYPES.find(r => r.id === renoType)!;
    const addedValue      = Math.round(b * rt.roi);
    const roiDollars      = addedValue - b;
    const roiPct          = ((addedValue - b) / b) * 100;
    const newValue        = hv + addedValue;
    const breakEvenMonths = rt.timeMonths;
    setResult({ renoType: rt, budget: b, homeValue: hv, addedValue, newValue, roiDollars, roiPct, breakEvenMonths });
  }

  return (
    <div style={{ minHeight: "100vh", background: "transparent", color: "var(--text)" }}>
      <NavBar />

      {/* ── Hero ── */}
      <header style={{ borderBottom: "1px solid var(--border)", padding: "56px 80px 48px" }} className="sec-wrap">
        <div style={{ maxWidth: 1320, margin: "0 auto" }}>
          <div style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)", marginBottom: 14 }}>
            ◆ Reno ROI Engine · GTA Market Data
          </div>
          <h1 className="page-h1" style={{ ...mono, fontSize: "clamp(2rem,4vw,3.6rem)", fontWeight: 700, margin: "0 0 16px", letterSpacing: "-0.01em" }}>
            What&apos;s your renovation worth?
          </h1>
          <p style={{ ...mono, fontSize: "0.85rem", color: "var(--text-mute)", maxWidth: "52ch", lineHeight: 1.7 }}>
            Enter your home value and planned renovation. We&apos;ll calculate expected ROI based on
            GTA-specific market averages across thousands of comparable sales.
          </p>
        </div>
      </header>

      {/* ── Calculator + results ── */}
      <div style={{ maxWidth: 1320, margin: "0 auto", padding: "48px 80px" }} className="sec-wrap">
        <div className="tours-2col" style={{ display: "grid", gridTemplateColumns: "440px 1fr", gap: 0, alignItems: "start" }}>

          {/* Form */}
          <div style={{ border: "1px solid var(--border)", padding: "32px", background: "var(--bg-elev)", borderRight: "none" }} className="tours-order">
            <div style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 24 }}>
              ◆ Calculate ROI
            </div>

            {/* Current home value */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 8 }}>
                Current Home Value ($)
              </label>
              <input
                type="number"
                placeholder="e.g. 850000"
                value={homeValue}
                onChange={e => setHomeValue(e.target.value)}
                style={{ width: "100%", border: "1px solid var(--border)", background: "transparent", padding: "11px 14px", ...mono, fontSize: "0.9rem", color: "var(--text)", outline: "none", boxSizing: "border-box" }}
              />
            </div>

            {/* Reno type */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 8 }}>
                Renovation Type
              </label>
              <div style={{ border: "1px solid var(--border)", overflow: "hidden" }}>
                {RENO_TYPES.map((rt, i) => (
                  <button
                    key={rt.id}
                    onClick={() => setRenoType(rt.id)}
                    style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      width: "100%", padding: "10px 14px", textAlign: "left",
                      background: renoType === rt.id ? "rgba(255,191,0,0.08)" : "transparent",
                      borderBottom: i < RENO_TYPES.length - 1 ? "1px solid var(--border)" : "none",
                      border: "none", cursor: "pointer",
                    }}
                  >
                    <span style={{ ...mono, fontSize: "0.7rem", color: renoType === rt.id ? "var(--accent)" : "var(--text-mute)" }}>
                      {renoType === rt.id ? "▶ " : ""}{rt.label}
                    </span>
                    <span style={{ ...mono, fontSize: "0.58rem", color: RISK_COLORS[rt.risk] ?? "var(--text-dim)" }}>
                      {rt.roiRange}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Budget */}
            <div style={{ marginBottom: 28 }}>
              <label style={{ display: "block", ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 8 }}>
                Renovation Budget ($)
              </label>
              <input
                type="number"
                placeholder={RENO_TYPES.find(r => r.id === renoType)?.typical ?? "e.g. 50000"}
                value={budget}
                onChange={e => setBudget(e.target.value)}
                style={{ width: "100%", border: "1px solid var(--border)", background: "transparent", padding: "11px 14px", ...mono, fontSize: "0.9rem", color: "var(--text)", outline: "none", boxSizing: "border-box" }}
              />
              <div style={{ ...mono, fontSize: "0.58rem", color: "var(--text-dim)", marginTop: 6 }}>
                Typical for this type: {RENO_TYPES.find(r => r.id === renoType)?.typical}
              </div>
            </div>

            <button
              onClick={compute}
              disabled={!homeValue || !budget}
              style={{
                width: "100%", padding: "14px", background: "var(--accent)", color: "var(--bg)",
                ...mono, fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase",
                letterSpacing: "0.1em", border: "none", cursor: !homeValue || !budget ? "not-allowed" : "pointer",
                opacity: !homeValue || !budget ? 0.5 : 1,
                boxShadow: "0 0 22px rgba(255,176,0,0.25)",
              }}
            >
              Calculate ROI →
            </button>
          </div>

          {/* Results */}
          <div style={{ borderTop: "1px solid var(--border)" }}>
            {result ? (
              <ResultPanel result={result} />
            ) : (
              <div style={{ border: "1px solid var(--border)", padding: "60px 40px", textAlign: "center" }}>
                <div style={{ fontSize: "2.5rem", color: "var(--border)", marginBottom: 20 }}>◎</div>
                <div style={{ ...mono, fontSize: "1rem", color: "var(--text-mute)", marginBottom: 8 }}>
                  Enter your details to see ROI
                </div>
                <div style={{ ...mono, fontSize: "0.72rem", color: "var(--text-dim)" }}>
                  GTA-calibrated estimates based on thousands of sold comps
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── GTA ROI reference table ── */}
        <section style={{ marginTop: 64, borderTop: "1px solid var(--border)", paddingTop: 48 }}>
          <div style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 20 }}>
            ◆ GTA Renovation ROI Reference · 2024–2026 Market Data
          </div>
          <div style={{ border: "1px solid var(--border)", overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 100px 120px 100px", padding: "10px 20px", background: "var(--bg-elev)", borderBottom: "1px solid var(--border)" }}>
              {["Renovation","ROI Range","Risk","Typical Cost","Break-even"].map(h => (
                <div key={h} style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>{h}</div>
              ))}
            </div>
            {RENO_TYPES.map((rt, i) => (
              <div key={rt.id} style={{ display: "grid", gridTemplateColumns: "1fr 100px 100px 120px 100px", padding: "12px 20px", borderBottom: i < RENO_TYPES.length - 1 ? "1px solid var(--border)" : "none", background: i % 2 ? "rgba(255,191,0,0.01)" : "transparent", cursor: "pointer" }}
                onClick={() => setRenoType(rt.id)}>
                <span style={{ ...mono, fontSize: "0.72rem", color: rt.id === renoType ? "var(--accent)" : "var(--text)", fontWeight: rt.id === renoType ? 600 : 400 }}>{rt.label}</span>
                <span style={{ ...mono, fontSize: "0.68rem", color: "var(--text-mute)" }}>{rt.roiRange}</span>
                <span style={{ ...mono, fontSize: "0.68rem", color: RISK_COLORS[rt.risk] }}>{rt.risk}</span>
                <span style={{ ...mono, fontSize: "0.62rem", color: "var(--text-dim)" }}>{rt.typical}</span>
                <span style={{ ...mono, fontSize: "0.68rem", color: "var(--text-mute)" }}>~{rt.timeMonths}mo</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── Premium CTA (Tier 3) ── */}
        <section style={{ marginTop: 64 }}>
          <div style={{ border: "1px solid var(--border-strong)", background: "rgba(255,191,0,0.03)", padding: "40px 48px", display: "flex", gap: 48, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 320px" }}>
              <div style={{ ...mono, fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 12 }}>
                416Homes Pro · $99 / month
              </div>
              <div style={{ ...mono, fontSize: "1.6rem", fontWeight: 700, marginBottom: 16 }}>
                Comp-backed reno analysis
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  "Sold comps within 500m matching your reno type",
                  "Before/after price data from HouseSigma",
                  "Contractor cost benchmarks by postal code",
                  "Optimal listing timing post-renovation",
                  "Neighbourhood ROI heat map",
                ].map(f => (
                  <div key={f} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <span style={{ color: "var(--accent)", flexShrink: 0, marginTop: 1 }}>◆</span>
                    <span style={{ ...mono, fontSize: "0.72rem", color: "var(--text-mute)" }}>{f}</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ flex: "0 0 auto" }}>
              {showPremium ? (
                <div style={{ border: "1px solid var(--border)", padding: "24px 28px", ...mono }}>
                  <div style={{ fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 12 }}>
                    Join the waitlist
                  </div>
                  <input
                    type="email"
                    placeholder="you@example.com"
                    style={{ width: "100%", border: "1px solid var(--border)", background: "transparent", padding: "10px 12px", ...mono, fontSize: "0.78rem", color: "var(--text)", outline: "none", marginBottom: 10, boxSizing: "border-box" }}
                  />
                  <button
                    style={{ width: "100%", padding: "10px", background: "var(--accent)", color: "var(--bg)", ...mono, fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", border: "none", cursor: "pointer" }}
                    onClick={() => alert("We'll be in touch!")}
                  >
                    Join waitlist →
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowPremium(true)}
                  style={{
                    padding: "14px 36px", background: "var(--accent)", color: "var(--bg)",
                    ...mono, fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase",
                    letterSpacing: "0.1em", border: "none", cursor: "pointer",
                    boxShadow: "0 0 30px rgba(255,176,0,0.3)",
                  }}
                >
                  Get Pro Access — $99/mo →
                </button>
              )}
            </div>
          </div>
        </section>

      </div>

      {/* ── Footer ── */}
      <footer className="footer-bar" style={{ borderTop: "1px solid var(--border)", padding: "20px 80px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <HouseLogo size={22} />
        <div style={{ ...mono, fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
          © 2026 416Homes · GTA Real Estate Intelligence
        </div>
      </footer>
    </div>
  );
}
