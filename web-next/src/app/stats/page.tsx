"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import HouseLogo from "@/components/HouseLogo";
import { fetchListings } from "@/lib/api";
import { Listing } from "@/types";

const STATS_NAV: [string, string][] = [["/#listings","LISTINGS"],["/#how","HOW IT WORKS"],["/video","VIDEOS"],["/tours","TOURS"],["/reno","RENO ROI"],["/stats","STATS"],["/faq","FAQ"]];

/* ── Shared nav (same as other pages) ──────────────────────────────── */
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
        {STATS_NAV.map(([href,label]) => (
          <li key={href}>
            <Link href={href} style={{ fontFamily: "var(--mono)", fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.14em", color: href === "/stats" ? "var(--accent)" : "var(--text-mute)", textDecoration: "none" }}>
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
          {[...STATS_NAV, ["/dashboard", "DASHBOARD"]].map(([href, label]) => (
            <Link key={href} href={href} onClick={() => setMenuOpen(false)} style={{ display: "block", padding: "14px 0", borderBottom: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-mute)", textDecoration: "none" }}>
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}

/* ── Stat card ──────────────────────────────────────────────────────── */
function StatCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div style={{ border: "1px solid var(--border)", padding: "24px 28px", background: "var(--bg-elev)" }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 10 }}>{label}</div>
      <div style={{ fontFamily: "var(--mono)", fontSize: "2.2rem", fontWeight: 700, color: accent ? "var(--accent)" : "var(--text)", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-mute)", marginTop: 8 }}>{sub}</div>}
    </div>
  );
}

/* ── Distribution bar ───────────────────────────────────────────────── */
function DistBar({ under, over, fair }: { under: number; over: number; fair: number }) {
  const total = under + over + fair || 1;
  const pUnder = Math.round(under / total * 100);
  const pOver  = Math.round(over  / total * 100);
  const pFair  = 100 - pUnder - pOver;
  return (
    <div>
      <div style={{ display: "flex", height: 10, overflow: "hidden", border: "1px solid var(--border)" }}>
        <div style={{ width: `${pUnder}%`, background: "#2ed573", transition: "width 0.6s" }} />
        <div style={{ width: `${pFair}%`,  background: "var(--border-strong)", transition: "width 0.6s" }} />
        <div style={{ width: `${pOver}%`,  background: "#cf6357", transition: "width 0.6s" }} />
      </div>
      <div style={{ display: "flex", gap: 20, marginTop: 10, fontFamily: "var(--mono)", fontSize: "0.6rem" }}>
        <span style={{ color: "#2ed573" }}>↓ {pUnder}% underpriced</span>
        <span style={{ color: "var(--text-mute)" }}>≈ {pFair}% fair</span>
        <span style={{ color: "#cf6357" }}>↑ {pOver}% overpriced</span>
      </div>
    </div>
  );
}

/* ── Neighbourhood table ────────────────────────────────────────────── */
interface NbhdRow {
  name: string;
  count: number;
  avgPrice: number;
  avgPsf: number;
  under: number;
}

function NbhdTable({ rows }: { rows: NbhdRow[] }) {
  const mono: React.CSSProperties = { fontFamily: "var(--mono)", fontSize: "0.72rem" };
  return (
    <div style={{ border: "1px solid var(--border)", overflow: "hidden" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 120px 80px 80px", padding: "10px 20px", borderBottom: "1px solid var(--border)", background: "var(--bg-elev)" }}>
        {["Area","Listings","Avg Price","$/sqft","Deals"].map(h => (
          <div key={h} style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text-dim)" }}>{h}</div>
        ))}
      </div>
      {rows.map((r, i) => (
        <div key={r.name} style={{ display: "grid", gridTemplateColumns: "1fr 80px 120px 80px 80px", padding: "12px 20px", borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none", background: i % 2 === 0 ? "transparent" : "rgba(255,191,0,0.015)" }}>
          <span style={{ ...mono, color: "var(--text)", fontWeight: 600 }}>{r.name}</span>
          <span style={{ ...mono, color: "var(--text-mute)" }}>{r.count}</span>
          <span style={{ ...mono, color: "var(--accent)" }}>${Math.round(r.avgPrice / 1000)}K</span>
          <span style={{ ...mono, color: "var(--text-mute)" }}>{r.avgPsf > 0 ? `$${Math.round(r.avgPsf).toLocaleString()}` : "—"}</span>
          <span style={{ ...mono, color: r.under > 0 ? "#2ed573" : "var(--text-dim)" }}>{r.under > 0 ? `${r.under} ↓` : "—"}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Main page ──────────────────────────────────────────────────────── */
export default function StatsPage() {
  const [listings, setListings]     = useState<Listing[]>([]);
  const [total, setTotal]           = useState(0);
  const [loading, setLoading]       = useState(true);
  const [scanTime, setScanTime]     = useState<string | null>(null);
  const [fetchError, setFetchError] = useState(false);
  const [retryIn, setRetryIn]       = useState<number | null>(null);

  const loadStats = useCallback(async (attempt = 0) => {
    setFetchError(false);
    setRetryIn(null);
    let willRetry = false;
    try {
      const data = await fetchListings({ limit: 200 });
      setListings(data.listings);
      setTotal(data.total);
      setScanTime(data.scan_time);
    } catch {
      if (attempt < 2) {
        // Auto-retry — backend may be cold-starting (~30s on DO basic tier)
        willRetry = true;
        const delay = attempt === 0 ? 8 : 15;
        setRetryIn(delay);
        const tick = setInterval(() => {
          setRetryIn(prev => {
            if (prev == null || prev <= 1) { clearInterval(tick); return null; }
            return prev - 1;
          });
        }, 1000);
        setTimeout(() => {
          clearInterval(tick);
          void loadStats(attempt + 1);
        }, delay * 1000);
      } else {
        setFetchError(true);
        setRetryIn(null);
      }
    } finally {
      // Only stop the top-level spinner when we won't auto-retry
      if (!willRetry) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStats();
    // Auto-refresh every 5 minutes
    const interval = setInterval(() => { void loadStats(); }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadStats]);

  /* ── Compute stats ── */
  const prices   = listings.filter(l => l.price > 0).map(l => l.price);
  const avgPrice = prices.length ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0;
  const medPrice = prices.length ? [...prices].sort((a, b) => a - b)[Math.floor(prices.length / 2)] : 0;

  const psfArr   = listings.filter(l => l.price > 0 && l.sqft > 0).map(l => l.price / l.sqft);
  const avgPsf   = psfArr.length ? Math.round(psfArr.reduce((a, b) => a + b, 0) / psfArr.length) : 0;

  const domArr   = listings.filter(l => l.dom != null).map(l => l.dom!);
  const avgDom   = domArr.length ? Math.round(domArr.reduce((a, b) => a + b, 0) / domArr.length) : null;

  const withVal  = listings.filter(l => l.fair_value != null);
  const under    = withVal.filter(l => (l.fair_value ?? 0) >= 3).length;
  const over     = withVal.filter(l => (l.fair_value ?? 0) <= -3).length;
  const fair     = withVal.length - under - over;

  /* ── Neighbourhood grouping ── */
  const nbhdMap = new Map<string, { prices: number[]; psfs: number[]; under: number }>();
  for (const l of listings) {
    const key = l.city || "Unknown";
    if (!nbhdMap.has(key)) nbhdMap.set(key, { prices: [], psfs: [], under: 0 });
    const row = nbhdMap.get(key)!;
    if (l.price > 0) row.prices.push(l.price);
    if (l.price > 0 && l.sqft > 0) row.psfs.push(l.price / l.sqft);
    if ((l.fair_value ?? 0) >= 3) row.under++;
  }
  const nbhdRows: NbhdRow[] = Array.from(nbhdMap.entries())
    .map(([name, { prices: p, psfs, under: u }]) => ({
      name,
      count: p.length,
      avgPrice: p.length ? Math.round(p.reduce((a, b) => a + b, 0) / p.length) : 0,
      avgPsf:   psfs.length ? Math.round(psfs.reduce((a, b) => a + b, 0) / psfs.length) : 0,
      under:    u,
    }))
    .filter(r => r.count >= 2)
    .sort((a, b) => b.count - a.count)
    .slice(0, 12);

  /* ── Shared mono style ── */
  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <NavBar />

      {/* ── Page header ── */}
      <header style={{ borderBottom: "1px solid var(--border)", padding: "56px 80px 48px" }} className="sec-wrap">
        <div style={{ maxWidth: 1320, margin: "0 auto" }}>
          <div style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)", marginBottom: 14 }}>
            ◆ GTA Market Intelligence · Live data
          </div>
          <h1 className="page-h1" style={{ ...mono, fontSize: "clamp(2.4rem,4vw,4rem)", fontWeight: 700, margin: 0, letterSpacing: "-0.01em" }}>
            City Stats
          </h1>
          <p style={{ ...mono, fontSize: "0.85rem", color: "var(--text-mute)", marginTop: 16, maxWidth: "60ch" }}>
            Real-time market intelligence derived from {total.toLocaleString()} active GTA listings.
            {scanTime && (
              <span style={{ color: "var(--text-dim)", marginLeft: 8 }}>
                Last scan: {new Date(scanTime).toLocaleString("en-CA", { dateStyle: "medium", timeStyle: "short" })}
              </span>
            )}
          </p>
        </div>
      </header>

      {loading ? (
        <div style={{ padding: "80px 80px", textAlign: "center", ...mono, fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
          {retryIn != null ? (
            <>
              <div style={{ color: "#cf6357", marginBottom: 8 }}>◆ Backend is starting up…</div>
              <div style={{ color: "var(--text-mute)" }}>Retrying in {retryIn}s</div>
            </>
          ) : (
            <>◆ Loading market data…</>
          )}
        </div>
      ) : fetchError ? (
        <div style={{ padding: "80px 80px", textAlign: "center" }}>
          <div style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "#cf6357", marginBottom: 12 }}>◆ Could not reach the listings API</div>
          <div style={{ ...mono, fontSize: "0.78rem", color: "var(--text-mute)", marginBottom: 24 }}>The backend may still be starting up — please try again in a moment.</div>
          <button onClick={() => { setLoading(true); void loadStats(); }} style={{ padding: "12px 28px", background: "var(--accent)", color: "#000", border: "none", fontFamily: "var(--mono)", fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", cursor: "pointer" }}>
            Retry
          </button>
        </div>
      ) : (
        <div style={{ maxWidth: 1320, margin: "0 auto", padding: "0 80px 80px" }} className="sec-wrap">

          {/* ── Stat cards row ── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0, borderTop: "none", marginTop: 48, border: "1px solid var(--border)" }}>
            <div style={{ borderRight: "1px solid var(--border)", padding: "24px 28px" }}>
              <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 10 }}>Total Active Listings</div>
              <div style={{ ...mono, fontSize: "2.2rem", fontWeight: 700, color: "var(--accent)" }}>{total.toLocaleString()}</div>
              <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text-mute)", marginTop: 8 }}>across GTA • {listings.filter(l => l.source).length} with source data</div>
            </div>
            <div style={{ borderRight: "1px solid var(--border)", padding: "24px 28px" }}>
              <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 10 }}>Avg List Price</div>
              <div style={{ ...mono, fontSize: "2.2rem", fontWeight: 700 }}>${(avgPrice / 1000).toFixed(0)}K</div>
              <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text-mute)", marginTop: 8 }}>Median: ${(medPrice / 1000).toFixed(0)}K</div>
            </div>
            <div style={{ borderRight: "1px solid var(--border)", padding: "24px 28px" }}>
              <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 10 }}>Avg $/sqft</div>
              <div style={{ ...mono, fontSize: "2.2rem", fontWeight: 700 }}>${avgPsf > 0 ? avgPsf.toLocaleString() : "—"}</div>
              <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text-mute)", marginTop: 8 }}>{psfArr.length} listings with area data</div>
            </div>
            <div style={{ padding: "24px 28px" }}>
              <div style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 10 }}>Avg Days on Market</div>
              <div style={{ ...mono, fontSize: "2.2rem", fontWeight: 700, color: avgDom != null && avgDom > 30 ? "#cf6357" : "var(--text)" }}>
                {avgDom != null ? `${avgDom}d` : "—"}
              </div>
              <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text-mute)", marginTop: 8 }}>{domArr.length} listings with DOM data</div>
            </div>
          </div>

          {/* ── Market distribution ── */}
          {withVal.length > 0 && (
            <section style={{ marginTop: 56 }}>
              <div style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 18 }}>
                ◆ Valuation Distribution · {withVal.length} listings analysed
              </div>
              <div style={{ border: "1px solid var(--border)", padding: "28px 32px", background: "var(--bg-elev)" }}>
                <DistBar under={under} over={over} fair={fair} />
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 0, marginTop: 28, borderTop: "1px solid var(--border)", paddingTop: 24 }}>
                  {[
                    { label: "Underpriced Listings", value: under, color: "#2ed573", desc: "fair_value ≥ 3% below estimate" },
                    { label: "At Market", value: fair, color: "var(--text-mute)", desc: "within 3% of fair value" },
                    { label: "Overpriced Listings", value: over, color: "#cf6357", desc: "fair_value ≥ 3% above estimate" },
                  ].map(({ label, value, color, desc }) => (
                    <div key={label} style={{ borderRight: "1px solid var(--border)", paddingRight: 28, marginRight: 28 }}>
                      <div style={{ ...mono, fontSize: "1.8rem", fontWeight: 700, color }}>{value}</div>
                      <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text)", marginTop: 4 }}>{label}</div>
                      <div style={{ ...mono, fontSize: "0.58rem", color: "var(--text-dim)", marginTop: 4 }}>{desc}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* ── Neighbourhood breakdown ── */}
          {nbhdRows.length > 0 && (
            <section style={{ marginTop: 56 }}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 20 }}>
                <div style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)" }}>
                  ◆ By Area · Top {nbhdRows.length} Markets
                </div>
                <div style={{ ...mono, fontSize: "0.58rem", color: "var(--text-dim)" }}>Sorted by listing volume</div>
              </div>
              <NbhdTable rows={nbhdRows} />
            </section>
          )}

          {/* ── Model status card ── */}
          <section style={{ marginTop: 56 }}>
            <div style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 20 }}>
              ◆ Valuation Engine Status
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0, border: "1px solid var(--border)", background: "var(--bg-elev)" }} className="how-grid">
              {[
                { label: "Model", value: "LightGBM Regressor", sub: "Trained on GTA sold comps", ok: true },
                { label: "Features", value: "6 inputs", sub: "Beds · Baths · sqft · Type · Neighbourhood · City", ok: true },
                { label: "Target Variable", value: "$/sqft", sub: "Predicts price-per-sqft × area", ok: true },
                { label: "Confidence Range", value: "65 – 92%", sub: "Based on comp density in neighbourhood", ok: true },
              ].map(({ label, value, sub, ok }, i) => (
                <div key={label} style={{ padding: "24px 28px", borderBottom: i < 2 ? "1px solid var(--border)" : "none", borderRight: i % 2 === 0 ? "1px solid var(--border)" : "none" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: ok ? "#2ed573" : "#cf6357", flexShrink: 0 }} />
                    <span style={{ ...mono, fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text-dim)" }}>{label}</span>
                  </div>
                  <div style={{ ...mono, fontSize: "1.1rem", fontWeight: 600, color: "var(--text)" }}>{value}</div>
                  <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text-mute)", marginTop: 4 }}>{sub}</div>
                </div>
              ))}
            </div>
          </section>

          {/* ── CTA to Dashboard ── */}
          <section style={{ marginTop: 56, borderTop: "1px solid var(--border)", paddingTop: 48, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
            <div>
              <div style={{ ...mono, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 10 }}>Ready to find underpriced listings?</div>
              <div style={{ ...mono, fontSize: "1.6rem", fontWeight: 700 }}>Browse the live dashboard →</div>
            </div>
            <Link href="/dashboard" style={{
              padding: "14px 32px", background: "var(--accent)", color: "var(--bg)",
              fontFamily: "var(--mono)", fontSize: "0.78rem", fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none",
            }}>
              Open Dashboard
            </Link>
          </section>

        </div>
      )}

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
