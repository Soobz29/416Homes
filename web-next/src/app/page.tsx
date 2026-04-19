"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { createAlert, generateLinkCode } from "@/lib/alerts";
import { fetchListings } from "@/lib/api";
import type { Listing } from "@/types";

const TELEGRAM_BOT = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "Homes_Alertsbot";

const STATIC_TICKER = [
  "◆ King West 2BR · $899K · Fair Value +4.2%",
  "◆ Square One Condo · $549K · Agent contacted",
  "◆ Port Credit Semi · $1.1M · Comp avg $1.08M",
  "◆ GTA · 5 new listings matched alerts this morning",
  "◆ Leslieville Detached · $1.35M · Fair Value +6.1%",
  "◆ Eglinton Crosstown open · transit-adjacent listings tracking +$38K premium",
  "◆ Erin Mills 3BR · $1.05M · 5 comps · showing booked",
];

function formatPrice(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${Math.round(n / 1_000)}K`;
  return `$${n}`;
}
function formatPriceFull(n: number) {
  return "$" + n.toLocaleString("en-CA");
}

/* ── Inline design-system components ───────────────────────────────── */
function Eyebrow({ children, line }: { children: React.ReactNode; line?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)" }}>
      {line && <span style={{ height: 1, width: 28, background: "var(--accent)", flexShrink: 0 }} />}
      {children}
    </div>
  );
}

function PrimaryBtn({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: "14px 28px",
        background: hov ? "var(--accent-hi)" : "var(--accent)",
        color: "#000",
        fontFamily: "var(--sans)",
        fontWeight: 700,
        fontSize: "0.82rem",
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        border: "none",
        cursor: "pointer",
        transition: "background 0.2s ease",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </button>
  );
}

function GhostBtn({ children, href, onClick }: { children: React.ReactNode; href?: string; onClick?: () => void }) {
  const [hov, setHov] = useState(false);
  const style: React.CSSProperties = {
    padding: "14px 28px",
    background: hov ? "rgba(212,175,55,0.06)" : "transparent",
    color: "var(--text)",
    fontFamily: "var(--sans)",
    fontWeight: 700,
    fontSize: "0.82rem",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
    border: `1px solid ${hov ? "var(--accent)" : "var(--border-strong)"}`,
    cursor: "pointer",
    transition: "border-color 0.2s ease, background 0.2s ease",
    whiteSpace: "nowrap",
    textDecoration: "none",
    display: "inline-block",
  };
  if (href) {
    return (
      <Link href={href} style={style} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}>
        {children}
      </Link>
    );
  }
  return (
    <button style={style} onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}>
      {children}
    </button>
  );
}

/* ── Main page ──────────────────────────────────────────────────────── */
export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [tickerItems, setTickerItems] = useState<string[]>(STATIC_TICKER);
  const [featuredListing, setFeaturedListing] = useState<Listing | null>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  // Form state
  const [email, setEmail] = useState("");
  const [toronto, setToronto] = useState(true);
  const [mississauga, setMississauga] = useState(true);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minBeds, setMinBeds] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [notifyMethod, setNotifyMethod] = useState<"email" | "telegram" | "both">("email");

  const [submitting, setSubmitting] = useState(false);
  const [formSuccess, setFormSuccess] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [telegramCode, setTelegramCode] = useState<string | null>(null);

  const scrollToId = (id: string) => {
    setMenuOpen(false);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  // Live ticker + featured listing from API
  useEffect(() => {
    fetchListings({ city: undefined })
      .then(({ listings }) => {
        if (listings.length > 0) {
          const items = listings.slice(0, 8).map(
            (l: Listing) => `◆ ${l.address} · ${formatPrice(l.price)} · ${l.beds}bd/${l.baths}ba`,
          );
          setTickerItems(items);
          setFeaturedListing(listings[0] ?? null);
        }
      })
      .catch(() => { /* keep static fallback */ });
  }, []);

  async function handleFormSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setFormError("Please enter a valid email address.");
      return;
    }
    if (!toronto && !mississauga) {
      setFormError("Select at least one city to monitor.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const cities: string[] = [];
      if (toronto) cities.push("Toronto");
      if (mississauga) cities.push("Mississauga");
      const payload = {
        cities,
        min_price: minPrice ? Number(minPrice.replace(/\D/g, "")) : undefined,
        max_price: maxPrice ? Number(maxPrice.replace(/\D/g, "")) : undefined,
        min_beds: minBeds ? Number(minBeds) : undefined,
        property_types: propertyType ? [propertyType] : undefined,
      };
      await createAlert(email.trim(), payload);

      // Generate Telegram link code if requested
      if (notifyMethod === "telegram" || notifyMethod === "both") {
        try {
          const { code } = await generateLinkCode(email.trim());
          setTelegramCode(code);
        } catch {
          // Non-fatal — email alert still created
        }
      }

      setFormSuccess(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  const displayTicker = [...tickerItems, ...tickerItems];
  const featuredPhoto = featuredListing?.photos?.[0];

  const inputStyle: React.CSSProperties = {
    width: "100%",
    border: "1px solid var(--border)",
    background: "rgba(255,255,255,0.04)",
    padding: "10px 12px",
    fontFamily: "var(--mono)",
    fontSize: "0.82rem",
    color: "var(--text)",
    outline: "none",
    transition: "border-color 0.2s",
  };
  const labelStyle: React.CSSProperties = {
    display: "block",
    marginBottom: 6,
    fontFamily: "var(--mono)",
    fontSize: "0.58rem",
    textTransform: "uppercase",
    letterSpacing: "0.13em",
    color: "var(--text-dim)",
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>

      {/* ── Nav ─────────────────────────────────────────────────────── */}
      <nav style={{
        position: "sticky", top: 0, zIndex: 100,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: 64, padding: "0 56px",
        background: "rgba(11,11,11,0.92)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--border)",
      }}>
        {/* Logo — Terminal Broker: bold mono */}
        <div style={{ fontFamily: "var(--mono)", fontSize: "1.1rem", fontWeight: 500, letterSpacing: "-0.02em" }}>
          <span style={{ color: "var(--accent)", fontWeight: 700 }}>416</span>
          <span style={{ color: "var(--text)" }}> Homes</span>
          <span style={{ color: "var(--text-dim)", fontSize: "0.6rem", marginLeft: 6, letterSpacing: "0.1em", textTransform: "uppercase" }}>GTA</span>
        </div>

        {/* Nav links — desktop */}
        <ul style={{ display: "flex", listStyle: "none", gap: 36, fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }} className="max-md:hidden">
          <li><button onClick={() => scrollToId("how")} style={{ background: "transparent", color: "inherit", cursor: "pointer", border: "none", fontFamily: "inherit", fontSize: "inherit", textTransform: "inherit", letterSpacing: "inherit" }}>How It Works</button></li>
          <li><button onClick={() => scrollToId("alert")} style={{ background: "transparent", color: "inherit", cursor: "pointer", border: "none", fontFamily: "inherit", fontSize: "inherit", textTransform: "inherit", letterSpacing: "inherit" }}>Set Alert</button></li>
          <li><Link href="/dashboard" style={{ color: "inherit", textDecoration: "none" }}>Dashboard</Link></li>
        </ul>

        {/* CTA */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button className="btn-primary max-md:hidden" onClick={() => scrollToId("alert")}>
            Set My Alert — Free
          </button>
          {/* Hamburger */}
          <button
            style={{ display: "none", flexDirection: "column", gap: 5, padding: 4, background: "transparent", border: "none", cursor: "pointer" }}
            className="md:hidden"
            onClick={() => setMenuOpen(o => !o)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
          >
            {[0, 1, 2].map(i => (
              <span key={i} style={{ display: "block", height: 1, width: 20, background: "var(--accent)" }} />
            ))}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      {menuOpen && (
        <div style={{ position: "fixed", inset: "64px 0 auto 0", zIndex: 99, background: "rgba(11,11,11,0.97)", borderBottom: "1px solid var(--border)", padding: "24px 24px" }}>
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 20, fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
            <li><button onClick={() => scrollToId("how")} style={{ background: "transparent", color: "inherit", cursor: "pointer", border: "none" }}>How It Works</button></li>
            <li><button onClick={() => scrollToId("alert")} style={{ background: "transparent", color: "inherit", cursor: "pointer", border: "none" }}>Set Alert</button></li>
            <li><Link href="/dashboard" style={{ color: "var(--accent)", textDecoration: "none" }} onClick={() => setMenuOpen(false)}>Dashboard →</Link></li>
          </ul>
        </div>
      )}

      {/* ── Ticker — sticky below nav ────────────────────────────────── */}
      <div style={{
        position: "sticky", top: 64, zIndex: 98,
        height: 36, overflow: "hidden",
        background: "rgba(11,11,11,0.88)",
        borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center",
      }}>
        <div
          className="ticker-track"
          style={{
            display: "flex", alignItems: "center", gap: 48,
            animation: "ticker 35s linear infinite",
            fontFamily: "var(--mono)",
            fontSize: "0.6rem",
            color: "var(--text-dim)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            whiteSpace: "nowrap",
          }}
        >
          {displayTicker.map((text, idx) => (
            <span key={idx}>{text}</span>
          ))}
        </div>
      </div>

      {/* ── Hero — 2-col split ────────────────────────────────────────── */}
      <section style={{
        maxWidth: 1320, margin: "0 auto",
        display: "grid", gridTemplateColumns: "1.1fr 1fr",
        alignItems: "stretch",
        gap: 0,
        padding: "80px 56px 64px",
        minHeight: "max(68vh, 580px)",
        borderBottom: "1px solid var(--border)",
      }} className="hero-split">

        {/* Left */}
        <div style={{ paddingRight: 56, borderRight: "1px solid var(--border)" }}>
          <Eyebrow line>Toronto · Mississauga · GTA 2026</Eyebrow>

          {/* Terminal Broker headline — bold mono, amber accent */}
          <h1 style={{
            fontFamily: "var(--mono)",
            fontSize: "clamp(2.6rem, 5vw, 5.6rem)",
            lineHeight: 1.0,
            fontWeight: 500,
            margin: "28px 0 28px",
            color: "var(--text)",
            letterSpacing: "-0.02em",
          }}>
            Stop chasing.<br />Let listings<br />
            <span style={{ color: "var(--accent)" }}>chase you.</span>
          </h1>

          <p style={{ fontFamily: "var(--mono)", fontSize: "0.88rem", color: "var(--text-mute)", maxWidth: "46ch", lineHeight: 1.75, marginBottom: 36 }}>
            416Homes watches four listing platforms around the clock,
            checks every property against what homes actually sold for
            in that neighbourhood, and reaches out to listing agents
            on your behalf — so you don't have to.
          </p>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <PrimaryBtn onClick={() => scrollToId("alert")}>Set My Alert — Free</PrimaryBtn>
            <GhostBtn href="/dashboard">Browse Listings →</GhostBtn>
          </div>

          {/* 4-col stats strip */}
          <div style={{
            marginTop: 64,
            display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
            borderTop: "1px solid var(--border)",
          }}>
            {[
              ["24/7", "Continuous monitoring"],
              ["50+", "GTA neighbourhoods"],
              ["2", "Cities: Toronto & Mississauga"],
              ["$0", "To get started"],
            ].map(([n, l], i) => (
              <div key={l} style={{
                padding: "20px 16px 0 0",
                borderRight: i < 3 ? "1px solid var(--border)" : "none",
              }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.8rem", fontWeight: 500, color: "var(--accent)" }}>{n}</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.55rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-mute)", marginTop: 6 }}>{l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right — featured listing card (terminal broker style) */}
        <div className="hero-right" style={{ paddingLeft: 56, display: "flex", flexDirection: "column" }}>
          <div style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            position: "relative",
            background: "var(--bg-elev)",
            border: "1px solid var(--border-strong)",
            overflow: "hidden",
            minHeight: 520,
          }}>
            {/* Photo area */}
            <div style={{ position: "relative", flex: 1, minHeight: 0, background: "#0d0d0a" }}>
              {/* Placeholder */}
              {!featuredPhoto && (
                <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "3rem", fontWeight: 700, color: "var(--border)", userSelect: "none" }}>416</span>
                </div>
              )}

              {featuredPhoto && (
                <img
                  src={featuredPhoto}
                  alt={featuredListing?.address ?? "Featured listing"}
                  style={{
                    position: "absolute", inset: 0, width: "100%", height: "100%",
                    objectFit: "cover",
                    opacity: imgLoaded && !imgError ? 1 : 0,
                    transition: "opacity 0.6s",
                  }}
                  onLoad={() => setImgLoaded(true)}
                  onError={() => setImgError(true)}
                />
              )}

              {/* Top badges */}
              <div style={{ position: "absolute", top: 16, left: 16, right: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--accent)" }}>
                  Live · {featuredListing?.source?.toUpperCase() ?? "GTA"}
                </span>
                <span style={{ fontFamily: "var(--mono)", fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--accent)" }}>
                  Featured
                </span>
              </div>

              {/* Bottom gradient */}
              <div style={{
                position: "absolute", bottom: 0, left: 0, right: 0, height: "65%",
                background: "linear-gradient(to top, rgba(11,11,11,0.98) 0%, rgba(11,11,11,0.5) 60%, transparent 100%)",
              }} />

              {/* Listing info overlay */}
              {featuredListing && (
                <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, padding: "24px 24px 20px" }}>
                  {/* Neighbourhood */}
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--text-dim)", marginBottom: 8 }}>
                    {featuredListing.city ?? "GTA"}, Ontario
                  </div>
                  {/* Address — bold mono terminal style */}
                  <div style={{ fontFamily: "var(--mono)", fontSize: "1.25rem", fontWeight: 500, color: "var(--text)", lineHeight: 1.25, marginBottom: 12 }}>
                    {featuredListing.address}
                  </div>
                  {/* Price — large gold mono */}
                  <div style={{ fontFamily: "var(--mono)", fontSize: "1.8rem", fontWeight: 500, color: "var(--accent)", marginBottom: 10, letterSpacing: "-0.01em" }}>
                    {formatPriceFull(featuredListing.price)}
                  </div>
                  {/* Beds · Baths · Sqft */}
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.65rem", color: "var(--text-dim)", letterSpacing: "0.08em" }}>
                    {[
                      featuredListing.beds && `${featuredListing.beds} BD`,
                      featuredListing.baths && `${featuredListing.baths} BA`,
                      featuredListing.sqft && `${featuredListing.sqft.toLocaleString()} SF`,
                    ].filter(Boolean).join(" · ")}
                  </div>
                </div>
              )}
            </div>

            {/* VIEW THIS LISTING bottom panel */}
            <a
              href={featuredListing?.url ?? "/dashboard"}
              target={featuredListing?.url ? "_blank" : undefined}
              rel="noreferrer"
              style={{
                display: "block", padding: "18px 24px",
                borderTop: "1px solid var(--border-strong)",
                fontFamily: "var(--mono)", fontSize: "0.65rem",
                textTransform: "uppercase", letterSpacing: "0.14em",
                color: "var(--accent)", textDecoration: "none",
                textAlign: "center",
                background: "rgba(212,175,55,0.04)",
                transition: "background 0.2s",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(212,175,55,0.10)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(212,175,55,0.04)")}
            >
              View This Listing →
            </a>
          </div>
        </div>
      </section>

      {/* ── How It Works — horizontal 4-col grid ─────────────────────── */}
      <section id="how" style={{ borderBottom: "1px solid var(--border)" }}>
        <div style={{ maxWidth: 1320, margin: "0 auto", padding: "72px 56px 0" }}>
          <Eyebrow line>How it works</Eyebrow>
        </div>
        <div
          className="how-grid"
          style={{
            maxWidth: 1320, margin: "48px auto 0",
            display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
            borderTop: "1px solid var(--border)",
          }}
        >
          {[
            { t: "Set your criteria",           d: "Price range, cities, neighbourhood, property type and minimum beds. 90 seconds." },
            { t: "We scan every night",          d: "Checks Realtor.ca, HouseSigma, Zoocasa and more. Fresh listings every morning." },
            { t: "Every listing gets priced",    d: "Each property compared against what similar homes in that area actually sold for." },
            { t: "We reach out to the agent",    d: "When something matches, a professional note goes to the listing agent automatically." },
          ].map((step, i) => (
            <div key={i} style={{
              padding: "48px 32px",
              borderRight: i < 3 ? "1px solid var(--border)" : "none",
              borderBottom: "1px solid var(--border)",
            }}>
              <div style={{ fontFamily: "var(--serif)", fontSize: "3.6rem", fontWeight: 300, color: "var(--accent)", opacity: 0.45, lineHeight: 1, marginBottom: 24 }}>
                {String(i + 1).padStart(2, "0")}
              </div>
              <h3 style={{ fontFamily: "var(--serif)", fontSize: "1.3rem", fontWeight: 500, color: "var(--text)", marginBottom: 12, lineHeight: 1.2 }}>
                {step.t}
              </h3>
              <p style={{ fontFamily: "var(--sans)", fontSize: "0.88rem", color: "var(--text-mute)", lineHeight: 1.75 }}>
                {step.d}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Products strip — Video + Tours ───────────────────────────── */}
      <section style={{ borderBottom: "1px solid var(--border)" }}>
        <div style={{ maxWidth: 1320, margin: "0 auto", padding: "72px 56px 0" }}>
          <Eyebrow line>Premium services</Eyebrow>
        </div>
        <div
          className="products-grid"
          style={{ maxWidth: 1320, margin: "48px auto 0", display: "grid", gridTemplateColumns: "1fr 1fr", borderTop: "1px solid var(--border)" }}
        >
          {[
            {
              tag: "Video",
              price: "$199",
              title: "Cinematic Listing Videos",
              desc: "Paste any listing URL. We write the script, record AI voiceover, add music — your 30-second video is ready in under 15 minutes.",
              cta: "Order a Video",
              href: "/video",
            },
            {
              tag: "Tours",
              price: "$99",
              title: "Virtual Tour Package",
              desc: "Professional virtual tour walkthrough from your listing photos. Narrated, scored, ready to share with buyers in 24 hours.",
              cta: "Book Tours",
              href: "/video",
            },
          ].map((p, i) => (
            <div key={i} style={{
              padding: "48px 40px",
              borderRight: i === 0 ? "1px solid var(--border)" : "none",
              borderBottom: "1px solid var(--border)",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <Eyebrow>{p.tag}</Eyebrow>
                <span style={{ fontFamily: "var(--serif)", fontSize: "1.4rem", fontWeight: 500, color: "var(--accent)" }}>{p.price}</span>
              </div>
              <h3 style={{ fontFamily: "var(--serif)", fontSize: "1.6rem", fontWeight: 500, color: "var(--text)", marginBottom: 12 }}>{p.title}</h3>
              <p style={{ fontFamily: "var(--sans)", fontSize: "0.88rem", color: "var(--text-mute)", lineHeight: 1.75, marginBottom: 28 }}>{p.desc}</p>
              <GhostBtn href={p.href}>{p.cta} →</GhostBtn>
            </div>
          ))}
        </div>
      </section>

      {/* ── Alert section ────────────────────────────────────────────── */}
      <section id="alert" style={{ maxWidth: 1320, margin: "0 auto", padding: "80px 56px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, borderBottom: "1px solid var(--border)" }} className="hero-split">

        {/* Left — feature list */}
        <div>
          <Eyebrow line>Free to start</Eyebrow>
          <h2 style={{ fontFamily: "var(--serif)", fontSize: "clamp(1.8rem, 3vw, 3.2rem)", fontWeight: 500, lineHeight: 1.05, margin: "24px 0 20px" }}>
            Set it once.<br />We handle the rest.
          </h2>
          <p style={{ fontFamily: "var(--sans)", fontSize: "0.88rem", lineHeight: 1.8, color: "var(--text-mute)", maxWidth: "38ch", marginBottom: 40 }}>
            Tell us what you&apos;re looking for. We check Toronto and Mississauga every night
            and send you only the listings that are actually worth a look.
          </p>
          <div>
            {[
              ["Listing search", "Realtor.ca, HouseSigma, Zoocasa, Kijiji", "Free"],
              ["Price checks", "Compared against real sold comps", "Free"],
              ["Agent outreach", "Professional email sent on your behalf", "Free"],
              ["Morning digest", "New matches delivered daily", "Free"],
              ["Dashboard", "All your listings, alerts, and history", "Free"],
              ["Telegram alerts", "Get matches in your Telegram DMs", "Free"],
            ].map(([name, role, badge]) => (
              <div key={name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", padding: "16px 0" }}>
                <div>
                  <div style={{ fontFamily: "var(--sans)", fontSize: "0.95rem", fontWeight: 600, marginBottom: 2, color: "var(--text)" }}>{name}</div>
                  <div style={{ fontFamily: "var(--sans)", fontSize: "0.78rem", color: "var(--text-mute)" }}>{role}</div>
                </div>
                <span style={{ border: "1px solid var(--border-strong)", padding: "3px 8px", fontFamily: "var(--mono)", fontSize: "0.55rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--accent)" }}>{badge}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right — form card */}
        <div>
          <div style={{ background: "var(--bg-elev)", border: "1px solid var(--border)", padding: 40 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <div style={{ fontFamily: "var(--serif)", fontSize: "1.3rem", fontWeight: 500 }}>Create Your Alert</div>
              <Link href="/dashboard" style={{ fontFamily: "var(--mono)", fontSize: "0.66rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--accent)", textDecoration: "none" }}>
                Manage alerts →
              </Link>
            </div>
            <p style={{ fontFamily: "var(--sans)", fontSize: "0.82rem", lineHeight: 1.6, color: "var(--text-mute)", marginBottom: 28 }}>
              We&apos;ll watch Toronto and Mississauga every night and send you matches every morning.
            </p>

            {formSuccess ? (
              <div aria-live="polite" style={{ border: "1px solid rgba(46,213,115,0.3)", background: "rgba(46,213,115,0.06)", padding: "20px 24px", textAlign: "center" }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.82rem", color: "#2ed573", marginBottom: 8 }}>
                  ✓ Alert created — matches start tomorrow morning
                </div>

                {/* Telegram connect block */}
                {telegramCode && (
                  <div style={{ marginTop: 20, padding: "20px", background: "var(--bg)", border: "1px solid var(--border)", textAlign: "left" }}>
                    <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 10 }}>
                      ◆ Connect Telegram
                    </div>
                    <p style={{ fontFamily: "var(--sans)", fontSize: "0.82rem", color: "var(--text-mute)", marginBottom: 12, lineHeight: 1.5 }}>
                      Open <strong style={{ color: "var(--text)" }}>@{TELEGRAM_BOT}</strong> on Telegram and send:
                    </p>
                    <div style={{
                      fontFamily: "var(--mono)",
                      fontSize: "1.1rem",
                      fontWeight: 700,
                      color: "var(--accent)",
                      letterSpacing: "0.1em",
                      padding: "10px 14px",
                      background: "var(--bg-elev)",
                      border: "1px solid var(--border)",
                      marginBottom: 14,
                    }}>
                      /link {telegramCode}
                    </div>
                    <a
                      href={`https://t.me/${TELEGRAM_BOT}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ display: "inline-block", padding: "8px 18px", border: "1px solid var(--border-strong)", color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none" }}
                    >
                      Open @{TELEGRAM_BOT} →
                    </a>
                  </div>
                )}

                <Link href="/dashboard" style={{ display: "inline-block", marginTop: 16, fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--accent)", textDecoration: "none", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  View dashboard →
                </Link>
              </div>
            ) : (
              <form onSubmit={handleFormSubmit} noValidate>
                {/* Email */}
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Email Address</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} required style={inputStyle} placeholder="you@example.com" />
                </div>

                {/* Cities */}
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Cities to Monitor</label>
                  <div style={{ display: "flex", gap: 24, fontFamily: "var(--sans)", fontSize: "0.88rem", color: "var(--text-mute)" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                      <input type="checkbox" checked={toronto} onChange={e => setToronto(e.target.checked)} style={{ accentColor: "var(--accent)" }} />
                      Toronto
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                      <input type="checkbox" checked={mississauga} onChange={e => setMississauga(e.target.checked)} style={{ accentColor: "var(--accent)" }} />
                      Mississauga
                    </label>
                  </div>
                </div>

                {/* Price range */}
                <div style={{ marginBottom: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={labelStyle}>Min Price</label>
                    <input value={minPrice} onChange={e => setMinPrice(e.target.value)} style={inputStyle} placeholder="500,000" />
                  </div>
                  <div>
                    <label style={labelStyle}>Max Price</label>
                    <input value={maxPrice} onChange={e => setMaxPrice(e.target.value)} style={inputStyle} placeholder="1,200,000" />
                  </div>
                </div>

                {/* Beds + property type */}
                <div style={{ marginBottom: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={labelStyle}>Min Bedrooms</label>
                    <input type="number" min="0" value={minBeds} onChange={e => setMinBeds(e.target.value)} style={inputStyle} placeholder="2" />
                  </div>
                  <div>
                    <label style={labelStyle}>Property Type</label>
                    <input value={propertyType} onChange={e => setPropertyType(e.target.value)} style={inputStyle} placeholder="Condo, Detached..." />
                  </div>
                </div>

                {/* Notification method */}
                <div style={{ marginBottom: 24 }}>
                  <label style={labelStyle}>Notify Me Via</label>
                  <div style={{ display: "flex", gap: 0, border: "1px solid var(--border)" }}>
                    {(["email", "telegram", "both"] as const).map((method, i) => (
                      <button
                        key={method}
                        type="button"
                        onClick={() => setNotifyMethod(method)}
                        style={{
                          flex: 1,
                          padding: "9px 4px",
                          fontFamily: "var(--mono)",
                          fontSize: "0.6rem",
                          textTransform: "uppercase",
                          letterSpacing: "0.08em",
                          border: "none",
                          borderRight: i < 2 ? "1px solid var(--border)" : "none",
                          cursor: "pointer",
                          background: notifyMethod === method ? "var(--accent)" : "transparent",
                          color: notifyMethod === method ? "#000" : "var(--text-mute)",
                          transition: "background 0.15s ease, color 0.15s ease",
                        }}
                      >
                        {method === "email" ? "📧 Email" : method === "telegram" ? "✈️ Telegram" : "📧+✈️ Both"}
                      </button>
                    ))}
                  </div>
                  {(notifyMethod === "telegram" || notifyMethod === "both") && (
                    <p style={{ marginTop: 8, fontFamily: "var(--mono)", fontSize: "0.6rem", color: "var(--text-dim)", lineHeight: 1.5 }}>
                      After submitting, you&apos;ll get a link code to connect @{TELEGRAM_BOT}.
                    </p>
                  )}
                </div>

                {formError && (
                  <div style={{ marginBottom: 16, padding: "10px 14px", border: "1px solid rgba(231,76,60,0.4)", background: "rgba(231,76,60,0.06)", fontFamily: "var(--mono)", fontSize: "0.72rem", color: "#e74c3c" }}>
                    {formError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary"
                  style={{ width: "100%", textAlign: "center", opacity: submitting ? 0.6 : 1 }}
                >
                  {submitting ? "Setting up..." : "Create Alert — Free"}
                </button>
              </form>
            )}
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "32px 56px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div style={{ fontFamily: "var(--serif)", fontSize: "1.1rem", fontWeight: 500 }}>
          <span style={{ color: "var(--accent)" }}>416</span>
          <span style={{ color: "var(--text-mute)" }}>homes</span>
        </div>
        <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text-dim)" }}>
          © 2026 416Homes · Toronto Real Estate Intelligence
        </div>
        <div style={{ display: "flex", gap: 24, fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>
          <Link href="/dashboard" style={{ color: "var(--text-dim)", textDecoration: "none" }}>Dashboard</Link>
          <Link href="/video" style={{ color: "var(--text-dim)", textDecoration: "none" }}>Videos</Link>
        </div>
      </footer>
    </div>
  );
}
