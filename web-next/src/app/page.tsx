"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchListings } from "@/lib/api";
import HouseLogo from "@/components/HouseLogo";

/* ─── Shared primitives ─────────────────────────────────────────────── */

function Eyebrow({ children, line }: { children: React.ReactNode; line?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)" }}>
      {line && <span style={{ height: 1, width: 28, background: "var(--accent)", flexShrink: 0 }} />}
      {children}
    </div>
  );
}

function PrimaryBtn({ children, onClick, small, href }: { children: React.ReactNode; onClick?: () => void; small?: boolean; href?: string }) {
  const style: React.CSSProperties = {
    display: "inline-block",
    padding: small ? "10px 18px" : "14px 28px",
    background: "var(--accent)",
    border: "none",
    color: "var(--bg)",
    fontFamily: "var(--mono)",
    fontWeight: 700,
    fontSize: small ? "0.68rem" : "0.82rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    cursor: "pointer",
    textDecoration: "none",
    boxShadow: "0 0 22px rgba(255,176,0,0.30), inset 0 1px 0 rgba(255,255,255,0.14)",
    transition: "background 0.2s",
    whiteSpace: "nowrap" as const,
  };
  if (href) return <Link href={href} style={style}>{children}</Link>;
  return <button onClick={onClick} style={style}>{children}</button>;
}

function GhostBtn({ children, onClick, href }: { children: React.ReactNode; onClick?: () => void; href?: string }) {
  const style: React.CSSProperties = {
    display: "inline-block",
    padding: "14px 28px",
    background: "transparent",
    border: "1px solid var(--border-strong)",
    color: "var(--text)",
    fontFamily: "var(--mono)",
    fontSize: "0.72rem",
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    cursor: "pointer",
    textDecoration: "none",
    transition: "border-color 0.2s, color 0.2s",
    whiteSpace: "nowrap" as const,
  };
  if (href) return <Link href={href} style={style}>{children}</Link>;
  return <button onClick={onClick} style={style}>{children}</button>;
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px 14px",
  background: "transparent",
  border: "1px solid var(--border)",
  color: "var(--text)",
  fontFamily: "var(--mono)",
  fontSize: "0.85rem",
  outline: "none",
};

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-mute)", marginBottom: 6 }}>
        {label}
      </label>
      {children}
    </div>
  );
}

/* ─── Data ──────────────────────────────────────────────────────────── */

const FEATURED = {
  neighbourhood: "Yorkville",
  city: "Toronto",
  source: "realtor.ca",
  address: "142 Yorkville Ave, Unit PH2",
  price: 3495000,
  beds: 3,
  baths: 4,
  sqft: 2480,
  photo: "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=1200&q=80",
};

const TICKER_ITEMS = [
  "King West 2BR · $899K · Fair Value +4.2%",
  "Lawrence Park Detached · $2.85M · 3 DOM · 6 comps pulled",
  "Port Credit assignment · $1.1M · Q3 2026 occupancy",
  "Eglinton Crosstown · transit-adjacent tracking +$38K premium",
  "Leslieville semi · $1.35M · +6.1% under comp avg · Agent emailed 4:02 AM",
  "CityPlace 1BR · $749K · 18 comps · score 10/10",
  "Yorkville PH · $3.49M · Sotheby's listing · Valuation pulled",
];

function fmtPriceFull(n: number) {
  return "$" + Math.max(0, n).toLocaleString();
}

/* ─── Nav ───────────────────────────────────────────────────────────── */

const TOP_NAV_LINKS: [string, string][] = [
  ["/dashboard", "Listings"],
  ["/deal", "Deal Analyzer"],
  ["/strategy", "Find My Strategy"],
  ["/#how-it-works", "How It Works"],
  ["/video", "Videos"],
  ["/tours", "Virtual Tours"],
  ["/stats", "Stats"],
  ["/reno", "Reno ROI"],
  ["/faq", "FAQ"],
];

function TopNav({ active }: { active?: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <nav className="nav-bar" style={{
      position: "sticky", top: 0, zIndex: 40,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 56px", height: 64,
      background: "color-mix(in srgb, var(--bg) 82%, transparent)",
      backdropFilter: "blur(20px)",
      borderBottom: "1px solid var(--border)",
    }}>
      <Link href="/" style={{ textDecoration: "none" }}><HouseLogo size={32} sub /></Link>
      <ul className="nav-links" style={{ display: "flex", listStyle: "none", gap: 36, margin: 0, padding: 0, fontFamily: "var(--mono)", fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase" }}>
        {TOP_NAV_LINKS.map(([href, label]) => (
          <li key={href}>
            <Link href={href} style={{ textDecoration: "none", color: active === label ? "var(--accent)" : "var(--text-mute)", transition: "color 0.2s" }}>
              {label}
            </Link>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button
          className="hamburger-btn"
          onClick={() => setMenuOpen(!menuOpen)}
          style={{ background: "transparent", border: "none", color: "var(--text)", fontSize: "1.4rem", cursor: "pointer", padding: "4px 8px", lineHeight: 1 }}
        >
          {menuOpen ? "✕" : "☰"}
        </button>
        <PrimaryBtn href="/#alert" small>Set My Alert</PrimaryBtn>
      </div>
      {menuOpen && (
        <div style={{ position: "fixed", top: 64, left: 0, right: 0, background: "rgba(5,6,10,0.98)", backdropFilter: "blur(20px)", borderBottom: "1px solid var(--border)", padding: "8px 24px 20px", zIndex: 999 }}>
          {[...TOP_NAV_LINKS, ["/#alert", "Set My Alert"]].map(([href, label]) => (
            <Link key={href} href={href} onClick={() => setMenuOpen(false)} style={{ display: "block", padding: "14px 0", borderBottom: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-mute)", textDecoration: "none" }}>
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}

/* ─── Footer ────────────────────────────────────────────────────────── */

function FooterBar() {
  return (
    <footer className="footer-bar" style={{
      maxWidth: 1320, margin: "0 auto",
      padding: "40px 56px",
      borderTop: "1px solid var(--border)",
      display: "flex", justifyContent: "space-between", alignItems: "center",
      fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-mute)",
    }}>
      <HouseLogo size={28} />
      <span>Covering the Greater Toronto Area · Built on real sold data</span>
      <span>© 2026 416Homes · Early Access</span>
    </footer>
  );
}

/* ─── Alert form ────────────────────────────────────────────────────── */

function AlertForm() {
  const [email, setEmail] = useState("");
  const [cities, setCities] = useState({
    Toronto: true, Mississauga: true, Brampton: false, Vaughan: false,
    Markham: false, "Richmond Hill": false, Oakville: false, Burlington: false,
    Ajax: false, Pickering: false, Whitby: false, Oshawa: false,
  });
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!email || submitting) return;
    setSubmitError(null);
    setSubmitting(true);
    const apiBase = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
    if (!apiBase) {
      setSubmitting(false);
      setSubmitError("Alerts service is not configured. Please try again later.");
      return;
    }
    try {
      const res = await fetch(`${apiBase}/api/public-alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          cities: Object.keys(cities).filter(c => cities[c as keyof typeof cities]),
          min_price: minPrice ? Number(minPrice.replace(/\D/g, "")) : null,
          max_price: maxPrice ? Number(maxPrice.replace(/\D/g, "")) : null,
        }),
      });
      if (!res.ok) {
        let msg = `Couldn't save your alert (${res.status}).`;
        try {
          const body = await res.json();
          if (body?.detail && typeof body.detail === "string") msg = body.detail;
        } catch {}
        setSubmitError(msg);
        return;
      }
      setSubmitted(true);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Network error. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div style={{ border: "1px solid var(--border-strong)", padding: 40, background: "var(--bg-elev)", textAlign: "center" }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 16 }}>
          ◆ Alert activated
        </div>
        <div style={{ fontFamily: "var(--mono)", fontSize: "1.6rem", fontWeight: 700, marginBottom: 12 }}>
          You&apos;re set.
        </div>
        <p style={{ fontFamily: "var(--mono)", fontSize: "0.78rem", lineHeight: 1.7, color: "var(--text-mute)" }}>
          We&apos;re watching the GTA every thirty minutes.<br />
          First matches arrive tomorrow morning at {email}.
        </p>
      </div>
    );
  }

  return (
    <div id="alert" style={{ border: "1px solid var(--border)", padding: 40, background: "var(--bg-elev)" }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: "1.3rem", fontWeight: 700, marginBottom: 8 }}>Create your alert</div>
      <p style={{ fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text-mute)", lineHeight: 1.6, marginBottom: 28 }}>
        We&apos;ll watch the entire GTA every thirty minutes and send you matches every morning.
      </p>

      <FormField label="Email address">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" style={inputStyle} />
      </FormField>
      <FormField label="Cities to monitor">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "10px 20px", fontFamily: "var(--mono)", fontSize: "0.76rem", color: "var(--text)" }}>
          {(Object.keys(cities) as Array<keyof typeof cities>).map(c => (
            <label key={c} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={cities[c]} onChange={e => setCities({ ...cities, [c]: e.target.checked })} style={{ accentColor: "var(--accent)" }} />
              {c}
            </label>
          ))}
        </div>
      </FormField>
      <div className="form-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <FormField label="Min price">
          <input value={minPrice} onChange={e => setMinPrice(e.target.value)} placeholder="$500,000" style={inputStyle} />
        </FormField>
        <FormField label="Max price">
          <input value={maxPrice} onChange={e => setMaxPrice(e.target.value)} placeholder="$1,200,000" style={inputStyle} />
        </FormField>
      </div>
      <button
        onClick={handleSubmit}
        disabled={submitting || !email}
        style={{
          width: "100%", marginTop: 16, padding: "16px",
          background: "var(--accent)", border: "none", color: "var(--bg)",
          fontFamily: "var(--mono)", fontSize: "0.88rem", fontWeight: 700,
          letterSpacing: "0.08em", textTransform: "uppercase",
          cursor: submitting || !email ? "not-allowed" : "pointer",
          opacity: submitting || !email ? 0.6 : 1,
          boxShadow: "0 0 22px rgba(255,176,0,0.35), inset 0 1px 0 rgba(255,255,255,0.16)",
        }}>
        {submitting ? "Activating…" : "Activate My Alert →"}
      </button>
      {submitError && (
        <div style={{
          marginTop: 14, padding: "12px 14px",
          border: "1px solid #cf6357", background: "rgba(207,99,87,0.08)",
          color: "#ffb4a8", fontFamily: "var(--mono)", fontSize: "0.74rem", lineHeight: 1.5,
        }}>
          {submitError}
        </div>
      )}
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────── */

export default function HomePage() {
  const ticker = [...TICKER_ITEMS, ...TICKER_ITEMS];
  const router = useRouter();
  const [featured, setFeatured] = useState(FEATURED);
  const [liveCount, setLiveCount] = useState<number | null>(null);
  const [searchCity, setSearchCity] = useState("");
  const [searchType, setSearchType] = useState("");
  const [searchPrice, setSearchPrice] = useState("");
  const [searchBeds, setSearchBeds] = useState("");

  useEffect(() => {
    // Fetch live listing count for the stats strip
    fetchListings({ limit: 1 }).then(({ total }) => {
      if (typeof total === "number" && total > 0) setLiveCount(total);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    fetchListings({ limit: 20 }).then(({ listings }) => {
      if (!listings || listings.length === 0) return;
      const idx = Math.floor(Date.now() / 86_400_000) % listings.length;
      const l = listings[idx];
      setFeatured({
        neighbourhood: l.neighbourhood || l.city || "GTA",
        city: l.city || "Toronto",
        source: l.source || "realtor.ca",
        address: l.address || "Featured Listing",
        price: l.price || 0,
        beds: l.beds || 0,
        baths: l.baths || 0,
        sqft: l.sqft || 0,
        photo: l.photos?.[0] || FEATURED.photo,
      });
    }).catch(() => { /* keep fallback */ });
  }, []);

  function handleSearch() {
    const p = new URLSearchParams();
    if (searchCity.trim()) p.set("city", searchCity.trim());
    if (searchType) p.set("propertyType", searchType);
    if (searchPrice) {
      const [min, max] = searchPrice.split("-");
      if (min) p.set("minPrice", min);
      if (max) p.set("maxPrice", max);
    }
    if (searchBeds) p.set("bedrooms", searchBeds);
    router.push("/dashboard" + (p.toString() ? "?" + p.toString() : ""));
  }

  return (
    <div style={{ minHeight: "100vh", color: "var(--text)", background: "transparent" }}>
      <TopNav active="How It Works" />

      {/* ── Ticker ── */}
      <div style={{
        position: "sticky", top: 64, zIndex: 30,
        borderBottom: "1px solid var(--border)",
        background: "color-mix(in srgb, var(--bg) 92%, transparent)",
        padding: "9px 0", overflow: "hidden",
      }}>
        <div style={{
          display: "flex", gap: 56, whiteSpace: "nowrap",
          animation: "ticker 45s linear infinite",
          fontFamily: "var(--mono)", fontSize: "0.68rem",
          color: "var(--text-mute)", letterSpacing: "0.04em",
        }}>
          {ticker.map((t, i) => (
            <span key={i}><span style={{ color: "var(--accent)", marginRight: 8 }}>◆</span>{t}</span>
          ))}
        </div>
      </div>

      {/* ── Hero ── */}
      <section style={{ position: "relative", width: "100%", minHeight: 580, overflow: "hidden", borderBottom: "1px solid var(--border)" }}>
        {/* Readability overlay: strong left → transparent right */}
        <div style={{ position: "absolute", inset: 0, zIndex: 1, background: "linear-gradient(to right, rgba(5,6,10,0.90) 0%, rgba(5,6,10,0.65) 55%, rgba(5,6,10,0.22) 100%)" }} />

        {/* Hero content */}
        <div className="page-hero-content" style={{ position: "relative", zIndex: 2, maxWidth: 1320, margin: "0 auto", padding: "80px 56px 72px" }}>
          {/* Eyebrow */}
          <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.28em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 24 }}>
            Toronto · Mississauga · Brampton · Vaughan + More
          </div>

          {/* Headline */}
          <h1 style={{ fontFamily: "var(--mono)", fontSize: "clamp(2.6rem, 5vw, 5.4rem)", fontWeight: 700, lineHeight: 0.96, letterSpacing: "-0.02em", margin: "0 0 24px", color: "#fff" }}>
            Find Your Perfect<br />
            <span style={{ background: "var(--accent)", color: "var(--bg)", padding: "4px 14px", display: "inline-block", marginTop: 10, lineHeight: 1.1 }}>Home in the GTA</span>
          </h1>

          {/* Subtext */}
          <p style={{ fontFamily: "var(--mono)", fontSize: "0.88rem", lineHeight: 1.8, color: "rgba(255,255,255,0.65)", maxWidth: "50ch", margin: "0 0 28px" }}>
            Discover verified listings for sale and rent across Toronto, Mississauga,
            Brampton and the entire Greater Toronto Area — with price checks against real sold comps.
          </p>

          {/* Trust badges */}
          <div style={{ display: "flex", gap: 28, marginBottom: 32, flexWrap: "wrap" }}>
            {([["✓", "Verified Listings"], ["↻", "Scanned every 30 min"], ["◎", "Free to start"]] as [string, string][]).map(([icon, label]) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: "var(--mono)", fontSize: "0.68rem", letterSpacing: "0.08em", color: "rgba(255,255,255,0.60)" }}>
                <span style={{ color: "var(--accent)", fontSize: "0.8rem" }}>{icon}</span> {label}
              </div>
            ))}
          </div>

          {/* Search bar */}
          <div className="hero-search-bar" style={{
            display: "grid",
            gridTemplateColumns: "1fr auto auto auto auto",
            gap: 0,
            background: "rgba(5,6,10,0.75)",
            backdropFilter: "blur(16px)",
            border: "1px solid rgba(255,176,0,0.40)",
            maxWidth: 880,
            overflow: "hidden",
          }}>
            <input
              value={searchCity}
              onChange={e => setSearchCity(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="City or neighbourhood (e.g. Yorkville, Mississauga...)"
              style={{
                padding: "16px 18px",
                background: "transparent",
                border: "none",
                color: "#fff",
                fontFamily: "var(--mono)",
                fontSize: "0.82rem",
                outline: "none",
                minWidth: 0,
              }}
            />
            <select
              value={searchType}
              onChange={e => setSearchType(e.target.value)}
              style={{ padding: "16px 14px", background: "rgba(5,6,10,0.90)", border: "none", borderLeft: "1px solid rgba(255,176,0,0.22)", color: "#fff", fontFamily: "var(--mono)", fontSize: "0.76rem", cursor: "pointer", outline: "none", whiteSpace: "nowrap" }}
            >
              <option value="">Type</option>
              <option value="Detached">Detached</option>
              <option value="Semi-Detached">Semi-Detached</option>
              <option value="Condo">Condo</option>
              <option value="Townhouse">Townhouse</option>
            </select>
            <select
              value={searchPrice}
              onChange={e => setSearchPrice(e.target.value)}
              style={{ padding: "16px 14px", background: "rgba(5,6,10,0.90)", border: "none", borderLeft: "1px solid rgba(255,176,0,0.22)", color: "#fff", fontFamily: "var(--mono)", fontSize: "0.76rem", cursor: "pointer", outline: "none", whiteSpace: "nowrap" }}
            >
              <option value="">Price</option>
              <option value="300000-600000">$300K – $600K</option>
              <option value="600000-900000">$600K – $900K</option>
              <option value="900000-1300000">$900K – $1.3M</option>
              <option value="1300000-2000000">$1.3M – $2M</option>
              <option value="2000000-99999999">$2M+</option>
            </select>
            <select
              value={searchBeds}
              onChange={e => setSearchBeds(e.target.value)}
              style={{ padding: "16px 14px", background: "rgba(5,6,10,0.90)", border: "none", borderLeft: "1px solid rgba(255,176,0,0.22)", color: "#fff", fontFamily: "var(--mono)", fontSize: "0.76rem", cursor: "pointer", outline: "none" }}
            >
              <option value="">Beds</option>
              <option value="1">1+</option>
              <option value="2">2+</option>
              <option value="3">3+</option>
              <option value="4">4+</option>
              <option value="5">5+</option>
            </select>
            <button
              onClick={handleSearch}
              style={{ padding: "16px 26px", background: "var(--accent)", border: "none", color: "var(--bg)", fontFamily: "var(--mono)", fontWeight: 700, fontSize: "0.82rem", letterSpacing: "0.06em", textTransform: "uppercase", cursor: "pointer", whiteSpace: "nowrap" }}
            >
              Search →
            </button>
          </div>

          {/* Popular searches */}
          <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginRight: 4 }}>Popular:</span>
            {["Downtown Toronto", "Mississauga", "Vaughan", "Etobicoke", "North York", "Scarborough"].map(city => (
              <Link
                key={city}
                href={`/dashboard?city=${encodeURIComponent(city)}`}
                style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "rgba(255,255,255,0.60)", background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.14)", padding: "5px 12px", textDecoration: "none", borderRadius: 2 }}
              >
                {city}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <div style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-elev)" }}>
        <div style={{ maxWidth: 1320, margin: "0 auto", padding: "0 56px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)" }} className="stats-strip">
          {[
            [liveCount ? `${liveCount.toLocaleString()}` : "2,500+", liveCount ? "Active GTA listings" : "Est. active GTA listings"],
            ["50+", "Neighbourhoods Tracked"],
            ["Every 30 min", "Scan Cadence"],
            ["$0", "To Get Started"],
          ].map(([n, l], i) => (
            <div key={l} style={{ padding: "28px 16px 28px 0", borderRight: i < 3 ? "1px solid var(--border)" : "none" }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "1.8rem", fontWeight: 700, color: "var(--accent)", lineHeight: 1 }}>{n}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-mute)", marginTop: 6 }}>{l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Alert CTA (primary action — above How It Works) ── */}
      <section className="sec-wrap sec-pad-lg alert-cta" id="alert" style={{ maxWidth: 1320, margin: "0 auto", padding: "80px 56px", borderBottom: "1px solid var(--border)", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64 }}>
        <div>
          <Eyebrow line>Free · No credit card</Eyebrow>
          <h2 style={{ fontFamily: "var(--mono)", fontSize: "clamp(2.2rem, 3.4vw, 3.6rem)", fontWeight: 700, lineHeight: 1, letterSpacing: "-0.015em", margin: "20px 0 20px" }}>
            Tell us what you want.<br />
            We watch the GTA <span className="accent-highlight">every 30 minutes.</span>
          </h2>
          <p style={{ fontFamily: "var(--mono)", fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text-mute)", maxWidth: "44ch", marginBottom: 32 }}>
            Set your cities, budget, and beds. We scan every listing source and send you only the properties worth a look — with the price check included.
          </p>
          <div style={{ borderTop: "1px solid var(--border)" }}>
            {[
              ["Listing search", "Realtor.ca · Zoocasa · Condos.ca · Kijiji"],
              ["Price checks", "vs real sold comps from HouseSigma"],
              ["Agent outreach", "Professional email sent on your behalf"],
              ["Morning digest", "New matches in your inbox daily"],
              ["Dashboard", "Listings, alerts, history"],
            ].map(([n, r]) => (
              <div key={n} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.95rem", fontWeight: 600 }}>{n}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text-mute)", marginTop: 3 }}>{r}</div>
                </div>
                <span style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)", border: "1px solid var(--border-strong)", padding: "3px 8px" }}>
                  Free
                </span>
              </div>
            ))}
          </div>
        </div>
        <AlertForm />
      </section>

      {/* ── How It Works ── */}
      <section id="how-it-works" className="sec-wrap sec-pad-lg" style={{ maxWidth: 1320, margin: "0 auto", padding: "96px 56px", borderBottom: "1px solid var(--border)" }}>
        <div className="how-header" style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 64, marginBottom: 56 }}>
          <div>
            <Eyebrow line>The Process</Eyebrow>
            <h2 style={{ fontFamily: "var(--mono)", fontSize: "clamp(2rem, 3.2vw, 3.4rem)", fontWeight: 700, lineHeight: 1.02, letterSpacing: "-0.015em", margin: "20px 0 0" }}>
              Four steps.<br />
              Then you&apos;re <span className="accent-highlight">done.</span>
            </h2>
          </div>
          <p style={{ fontFamily: "var(--mono)", fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text-mute)", alignSelf: "end", maxWidth: "58ch" }}>
            Most property searches make you do the work. 416Homes flips it: we monitor the market,
            price-check every new listing against real comps, and send the first email on your behalf.
            You show up to showings, not inbox triage.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, border: "1px solid var(--border)" }} className="how-grid">
          {[
            ["01", "Define", "Cities, budget, beds, neighbourhoods. Ninety seconds, tops.", "01/04"],
            ["02", "Scan", "Realtor.ca · Zoocasa · Condos.ca · Kijiji, every 30 minutes.", "02/04"],
            ["03", "Value", "Every listing compared to real sold comps in that exact pocket.", "03/04"],
            ["04", "Reach", "When a match appears, a professional email is sent to the listing agent.", "04/04"],
          ].map(([n, t, d, f], i) => (
            <div key={n} className="how-step" style={{
              padding: 36,
              borderRight: i < 3 ? "1px solid var(--border)" : "none",
              minHeight: 260,
              display: "flex", flexDirection: "column", justifyContent: "space-between",
            }}>
              <div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.18em", color: "var(--accent)" }}>{f}</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "3.6rem", fontWeight: 700, color: "var(--accent)", lineHeight: 1, margin: "8px 0 16px" }}>{n}</div>
              </div>
              <div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.2rem", fontWeight: 600, marginBottom: 10 }}>{t}</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.72rem", lineHeight: 1.7, color: "var(--text-mute)" }}>{d}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Why 416 / Intelligence ── */}
      <section className="sec-wrap sec-pad-lg" style={{ maxWidth: 1320, margin: "0 auto", padding: "96px 56px", borderBottom: "1px solid var(--border)" }}>
        <div className="how-header" style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 64, marginBottom: 48 }}>
          <Eyebrow line>Why 416</Eyebrow>
          <h2 style={{ fontFamily: "var(--mono)", fontSize: "clamp(2rem, 3.2vw, 3.4rem)", fontWeight: 700, lineHeight: 1.02, letterSpacing: "-0.015em", margin: 0 }}>
            Built for the way the GTA <span className="accent-highlight">actually works.</span>
          </h2>
        </div>
        <div className="why-grid" style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 0, border: "1px solid var(--border)" }}>
          {[
            ["Sold comps", "What homes actually sold for",
              "We pull real sold-comp prices from HouseSigma across 50+ GTA neighbourhoods — not estimates, not Zestimates. Every listing is compared against actual closes in the exact same pocket."],
            ["Transit premium", "Ontario Line & Eglinton Crosstown",
              "The Crosstown opened late 2024 and premiums are forming along the corridor. Ontario Line lands ~2030. We score every listing's proximity to both — a forward signal most buyers aren't pricing in yet."],
            ["Assignment sales", "Pre-construction, tracked",
              "The GTA has one of North America's largest pre-con markets. 416Homes watches assignment sales — a segment that most search tools don't show at all."],
            ["Autonomous outreach", "The email is already sent",
              "When a new listing crosses your criteria at 3am, a professional note to the listing agent goes out at 3:02. You wake up to replies, not alerts. Fully reviewable."],
          ].map(([label, title, desc], i) => (
            <div key={title as string} style={{
              padding: 48,
              borderRight: i % 2 === 0 ? "1px solid var(--border)" : "none",
              borderBottom: i < 2 ? "1px solid var(--border)" : "none",
            }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--accent)" }}>{label}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: "1.4rem", fontWeight: 600, margin: "10px 0 14px", lineHeight: 1.2 }}>{title}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.78rem", lineHeight: 1.75, color: "var(--text-mute)", maxWidth: "54ch" }}>{desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Products strip ── */}
      <section className="sec-wrap" style={{ maxWidth: 1320, margin: "0 auto", padding: "64px 56px 96px", borderBottom: "1px solid var(--border)" }}>
        <Eyebrow line>Optional add-ons</Eyebrow>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0, marginTop: 32, border: "1px solid var(--border)" }} className="products-grid">
          {[
            { tag: "Listing video", title: "Any listing URL → 30-second MP4", price: "from $99", desc: "Paste a Realtor.ca link. We write the script, record narration, and deliver an MP4 — in under 15 minutes.", cta: "See samples →", href: "/video", right: false },
            { tag: "Virtual tour", title: "Photos → hosted room-by-room tour", price: "$49", desc: "Your listing photos, classified by room and published as a hosted tour. Shareable link and embed code. Delivered in 5 minutes.", cta: "Order a tour →", href: "/tours", right: true },
          ].map(p => (
            <div key={p.tag} className="product-card" style={{ padding: 48, borderRight: p.right ? "none" : "1px solid var(--border)" }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--accent)" }}>{p.tag}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: "1.7rem", fontWeight: 600, margin: "10px 0 12px", lineHeight: 1.15 }}>{p.title}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: "1rem", color: "var(--accent)", marginBottom: 12 }}>{p.price}</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.76rem", lineHeight: 1.7, color: "var(--text-mute)", maxWidth: "48ch", marginBottom: 24 }}>{p.desc}</div>
              <Link href={p.href} style={{
                display: "inline-block",
                background: "transparent", border: "1px solid var(--border-strong)",
                color: "var(--accent)", padding: "10px 20px",
                fontFamily: "var(--mono)", fontSize: "0.7rem",
                letterSpacing: "0.12em", textTransform: "uppercase",
                textDecoration: "none",
              }}>{p.cta}</Link>
            </div>
          ))}
        </div>
      </section>

      <FooterBar />
    </div>
  );
}
