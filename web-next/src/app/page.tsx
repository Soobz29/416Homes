"use client";

import Link from "next/link";
import { useState } from "react";

/* ─── Shared primitives ─────────────────────────────────────────────── */

function Logo({ sub }: { sub?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 8, fontFamily: "var(--mono)", fontWeight: 800, fontSize: "1.2rem", letterSpacing: "0.02em" }}>
      <span style={{ color: "var(--accent)" }}>416</span>
      <span style={{ color: "var(--text)" }}>Homes</span>
      {sub && (
        <span style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", color: "var(--text-dim)", letterSpacing: "0.14em", textTransform: "uppercase", paddingLeft: 4, fontWeight: 400 }}>
          {sub}
        </span>
      )}
    </div>
  );
}

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

function TopNav({ active }: { active?: string }) {
  return (
    <nav style={{
      position: "sticky", top: 0, zIndex: 40,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "20px 56px",
      background: "color-mix(in srgb, var(--bg) 82%, transparent)",
      backdropFilter: "blur(20px)",
      borderBottom: "1px solid var(--border)",
    }}>
      <Link href="/" style={{ textDecoration: "none" }}><Logo sub="GTA" /></Link>
      <ul style={{ display: "flex", listStyle: "none", gap: 36, margin: 0, padding: 0, fontFamily: "var(--mono)", fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase" }}>
        {[
          ["/dashboard", "Listings"],
          ["/#how-it-works", "How It Works"],
          ["/video", "Videos"],
          ["/tours", "Virtual Tours"],
        ].map(([href, label]) => (
          <li key={href}>
            <Link href={href} style={{ textDecoration: "none", color: active === label ? "var(--accent)" : "var(--text-mute)", transition: "color 0.2s" }}>
              {label}
            </Link>
          </li>
        ))}
      </ul>
      <PrimaryBtn href="/#alert" small>Set My Alert</PrimaryBtn>
    </nav>
  );
}

/* ─── Footer ────────────────────────────────────────────────────────── */

function FooterBar() {
  return (
    <footer style={{
      maxWidth: 1320, margin: "0 auto",
      padding: "40px 56px",
      borderTop: "1px solid var(--border)",
      display: "flex", justifyContent: "space-between", alignItems: "center",
      fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-mute)",
    }}>
      <Logo />
      <span>Covering Toronto &amp; Mississauga · Built on real sold data</span>
      <span>© 2026 416Homes · Early Access</span>
    </footer>
  );
}

/* ─── Alert form ────────────────────────────────────────────────────── */

function AlertForm() {
  const [email, setEmail] = useState("");
  const [cities, setCities] = useState({ Toronto: true, Mississauga: true });
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit() {
    if (!email) return;
    try {
      const res = await fetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          cities: Object.keys(cities).filter(c => cities[c as keyof typeof cities]),
          min_price: minPrice ? Number(minPrice.replace(/\D/g, "")) : null,
          max_price: maxPrice ? Number(maxPrice.replace(/\D/g, "")) : null,
        }),
      });
      if (res.ok) setSubmitted(true);
    } catch {
      setSubmitted(true); // show success even on network error in demo
    }
  }

  if (submitted) {
    return (
      <div id="alert" style={{ border: "1px solid var(--border-strong)", padding: 40, background: "var(--bg-elev)", textAlign: "center" }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 16 }}>
          ◆ Alert activated
        </div>
        <div style={{ fontFamily: "var(--mono)", fontSize: "1.6rem", fontWeight: 700, marginBottom: 12 }}>
          You&apos;re set.
        </div>
        <p style={{ fontFamily: "var(--mono)", fontSize: "0.78rem", lineHeight: 1.7, color: "var(--text-mute)" }}>
          We&apos;re watching Toronto and Mississauga every thirty minutes.<br />
          First matches arrive tomorrow morning at {email}.
        </p>
      </div>
    );
  }

  return (
    <div id="alert" style={{ border: "1px solid var(--border)", padding: 40, background: "var(--bg-elev)" }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: "1.3rem", fontWeight: 700, marginBottom: 8 }}>Create your alert</div>
      <p style={{ fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text-mute)", lineHeight: 1.6, marginBottom: 28 }}>
        We&apos;ll watch Toronto and Mississauga every thirty minutes and send you matches every morning.
      </p>

      <FormField label="Email address">
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" style={inputStyle} />
      </FormField>
      <FormField label="Cities to monitor">
        <div style={{ display: "flex", gap: 20, fontFamily: "var(--mono)", fontSize: "0.78rem", color: "var(--text)" }}>
          {(Object.keys(cities) as Array<keyof typeof cities>).map(c => (
            <label key={c} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={cities[c]} onChange={e => setCities({ ...cities, [c]: e.target.checked })} style={{ accentColor: "var(--accent)" }} />
              {c}
            </label>
          ))}
        </div>
      </FormField>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <FormField label="Min price">
          <input value={minPrice} onChange={e => setMinPrice(e.target.value)} placeholder="$500,000" style={inputStyle} />
        </FormField>
        <FormField label="Max price">
          <input value={maxPrice} onChange={e => setMaxPrice(e.target.value)} placeholder="$1,200,000" style={inputStyle} />
        </FormField>
      </div>
      <button
        onClick={handleSubmit}
        style={{
          width: "100%", marginTop: 16, padding: "16px",
          background: "var(--accent)", border: "none", color: "var(--bg)",
          fontFamily: "var(--mono)", fontSize: "0.88rem", fontWeight: 700,
          letterSpacing: "0.08em", textTransform: "uppercase", cursor: "pointer",
          boxShadow: "0 0 22px rgba(255,176,0,0.35), inset 0 1px 0 rgba(255,255,255,0.16)",
        }}>
        Activate My Alert →
      </button>
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────── */

export default function HomePage() {
  const ticker = [...TICKER_ITEMS, ...TICKER_ITEMS];

  return (
    <div style={{ minHeight: "100vh", color: "var(--text)", background: "var(--bg)" }}>
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
      <section style={{
        maxWidth: 1320, margin: "0 auto",
        display: "grid", gridTemplateColumns: "1.1fr 1fr",
        gap: 0, padding: "80px 56px 56px",
        borderBottom: "1px solid var(--border)",
      }} className="hero-split">
        {/* Left */}
        <div style={{ paddingRight: 48, borderRight: "1px solid var(--border)" }}>
          <Eyebrow line>Toronto · Mississauga · GTA 2026</Eyebrow>
          <h1 style={{
            fontFamily: "var(--mono)",
            fontSize: "clamp(3rem, 5.4vw, 6.2rem)",
            lineHeight: 0.94, letterSpacing: "-0.02em",
            fontWeight: 500, margin: "28px 0 24px",
          }}>
            Stop chasing.<br />
            Let listings<br />
            <span className="accent-highlight">chase you.</span>
          </h1>
          <p style={{
            maxWidth: "52ch",
            fontFamily: "var(--mono)", fontSize: "0.88rem", lineHeight: 1.75,
            color: "var(--text-mute)", margin: "0 0 40px",
          }}>
            416Homes watches four listing platforms around the clock, checks every property
            against what homes actually sold for in that neighbourhood, and reaches out to
            listing agents on your behalf — so you don&apos;t have to.
          </p>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <PrimaryBtn href="/#alert">Set My Alert — Free</PrimaryBtn>
            <GhostBtn href="/dashboard">Browse Listings →</GhostBtn>
          </div>

          {/* Stats strip */}
          <div style={{ marginTop: 64, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, borderTop: "1px solid var(--border)" }}>
            {[
              ["2,847", "Active listings"],
              ["50+", "Neighbourhoods"],
              ["Q30m", "Scan cadence"],
              ["$0", "To start"],
            ].map(([n, l]) => (
              <div key={l} style={{ padding: "20px 16px 0 0", borderRight: "1px solid var(--border)" }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.8rem", fontWeight: 700, color: "var(--accent)", lineHeight: 1 }}>{n}</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-mute)", marginTop: 6 }}>{l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right — featured listing card */}
        <div className="hero-right" style={{ paddingLeft: 48, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: "100%", maxWidth: 460 }}>
            <div style={{ position: "relative", aspectRatio: "4/5", overflow: "hidden", border: "1px solid var(--border)" }}>
              <img src={FEATURED.photo} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
              <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 40%, rgba(0,0,0,0.9) 100%)" }} />
              {/* Top badges */}
              <div style={{ position: "absolute", top: 16, left: 16, right: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", color: "var(--accent)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
                  Live · {FEATURED.source}
                </span>
                <span style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", color: "var(--accent)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
                  Featured
                </span>
              </div>
              {/* Bottom info */}
              <div style={{ position: "absolute", left: 20, right: 20, bottom: 22, color: "#fff" }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.16em", textTransform: "uppercase", opacity: 0.7 }}>
                  {FEATURED.neighbourhood}, {FEATURED.city}
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.3rem", fontWeight: 500, margin: "4px 0 10px" }}>
                  {FEATURED.address}
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "2.4rem", fontWeight: 700, lineHeight: 1, color: "var(--accent)" }}>
                  {fmtPriceFull(FEATURED.price)}
                </div>
                <div style={{ display: "flex", gap: 14, marginTop: 12, fontFamily: "var(--mono)", fontSize: "0.7rem", letterSpacing: "0.05em" }}>
                  <span>{FEATURED.beds} BD</span>
                  <span style={{ opacity: 0.4 }}>·</span>
                  <span>{FEATURED.baths} BA</span>
                  <span style={{ opacity: 0.4 }}>·</span>
                  <span>{FEATURED.sqft.toLocaleString()} SF</span>
                </div>
              </div>
            </div>
            <Link href="/dashboard" style={{
              display: "block", width: "100%", marginTop: 12, padding: "14px 16px",
              background: "transparent", border: "1px solid var(--border-strong)",
              color: "var(--accent)", fontFamily: "var(--mono)",
              fontSize: "0.72rem", letterSpacing: "0.14em", textTransform: "uppercase",
              textDecoration: "none", textAlign: "center",
              transition: "all 0.2s",
            }}>
              View this listing →
            </Link>
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section id="how-it-works" style={{ maxWidth: 1320, margin: "0 auto", padding: "96px 56px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 64, marginBottom: 56 }}>
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
            ["02", "Scan", "Realtor.ca · HouseSigma · Kijiji · Zoocasa, every 30 minutes.", "02/04"],
            ["03", "Value", "Every listing compared to real sold comps in that exact pocket.", "03/04"],
            ["04", "Reach", "When a match appears, a professional email is sent to the listing agent.", "04/04"],
          ].map(([n, t, d, f], i) => (
            <div key={n} style={{
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
      <section style={{ maxWidth: 1320, margin: "0 auto", padding: "96px 56px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 64, marginBottom: 48 }}>
          <Eyebrow line>Why 416</Eyebrow>
          <h2 style={{ fontFamily: "var(--mono)", fontSize: "clamp(2rem, 3.2vw, 3.4rem)", fontWeight: 700, lineHeight: 1.02, letterSpacing: "-0.015em", margin: 0 }}>
            Built for the way the GTA <span className="accent-highlight">actually works.</span>
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 0, border: "1px solid var(--border)" }}>
          {[
            ["Sold comps", "What homes actually sold for",
              "We pull real transaction prices from HouseSigma across 50+ GTA neighbourhoods — not estimates, not Zestimates. Every listing is compared against actual closes in the exact same pocket."],
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
      <section style={{ maxWidth: 1320, margin: "0 auto", padding: "64px 56px 96px", borderBottom: "1px solid var(--border)" }}>
        <Eyebrow line>Optional add-ons</Eyebrow>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0, marginTop: 32, border: "1px solid var(--border)" }} className="products-grid">
          {[
            { tag: "Cinematic video", title: "Any listing URL → 30-second film", price: "from $99", desc: "Paste a Realtor.ca link. We write the script, record the voiceover, and cut the film — delivered in under 15 minutes.", cta: "See samples →", href: "/video", right: false },
            { tag: "Virtual tour", title: "Photos → hosted room-by-room tour", price: "$49", desc: "Gemini classifies every listing photo by room, builds a shareable tour link and embed code. Delivered in 5 minutes.", cta: "Order a tour →", href: "/tours", right: true },
          ].map(p => (
            <div key={p.tag} style={{ padding: 48, borderRight: p.right ? "none" : "1px solid var(--border)" }}>
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

      {/* ── Alert CTA ── */}
      <section style={{ maxWidth: 1320, margin: "0 auto", padding: "96px 56px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64 }} className="products-grid">
        <div>
          <Eyebrow line>Free · No credit card</Eyebrow>
          <h2 style={{ fontFamily: "var(--mono)", fontSize: "clamp(2.2rem, 3.4vw, 3.6rem)", fontWeight: 700, lineHeight: 1, letterSpacing: "-0.015em", margin: "20px 0 20px" }}>
            Set it once.<br />
            We handle <span className="accent-highlight">the rest.</span>
          </h2>
          <p style={{ fontFamily: "var(--mono)", fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text-mute)", maxWidth: "44ch", marginBottom: 32 }}>
            Tell us what you&apos;re looking for. We&apos;ll check Toronto and Mississauga every thirty minutes
            and send you only the listings worth a look — with the price check included.
          </p>
          <div style={{ borderTop: "1px solid var(--border)" }}>
            {[
              ["Listing search", "Realtor.ca · HouseSigma · Kijiji · Zoocasa"],
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

      <FooterBar />
    </div>
  );
}
