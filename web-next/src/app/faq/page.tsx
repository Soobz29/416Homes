"use client";

import { useState } from "react";
import Link from "next/link";
import HouseLogo from "@/components/HouseLogo";

const FAQ_NAV: [string, string][] = [
  ["/dashboard", "LISTINGS"],
  ["/video", "VIDEOS"],
  ["/tours", "TOURS"],
  ["/stats", "STATS"],
  ["/reno", "RENO ROI"],
  ["/faq", "FAQ"],
];

const FAQS: { q: string; a: string }[] = [
  {
    q: "Is this service available across Canada?",
    a: "Currently, 416Homes covers the Greater Toronto Area (Toronto, Mississauga, Brampton, Vaughan, Markham, Richmond Hill, Oakville, Burlington, and Durham Region). We plan to expand to Vancouver and Montreal in 2026.",
  },
  {
    q: "Do I need to be a licensed real estate agent to use this?",
    a: "No. 416Homes is designed for buyers, investors, and realtors. Our autonomous agent handles listing discovery, valuation, and outreach — you decide which opportunities to pursue.",
  },
  {
    q: "How does pricing work in Ontario?",
    a: "In Ontario, buyer agents are typically paid by the seller through a commission split (usually 2.5%). Our cinematic video ($99–$299 CAD) and virtual tour ($49 CAD) products are optional add-ons you can order separately.",
  },
  {
    q: "What is an 'assignment sale'?",
    a: "An assignment sale occurs when a buyer sells their purchase contract before closing. Common in pre-construction condos. In Ontario, assignment sales may be subject to HST and require lawyer review. Always consult legal counsel.",
  },
  {
    q: "Are your valuations MPAC-compliant?",
    a: "Our valuations use LightGBM trained on sold comps from TREB and local MLS data. They are NOT official appraisals and should not replace professional assessment. For mortgage or legal purposes, hire a licensed appraiser.",
  },
  {
    q: "How accurate are your fair value estimates?",
    a: "Our valuation model targets <10% MAPE (Mean Absolute Percentage Error) on comparable sales. Accuracy varies by neighbourhood data density. Always verify with your realtor or appraiser before making an offer.",
  },
  {
    q: "Do you comply with RECO regulations?",
    a: "416Homes is a technology platform, not a licensed brokerage. We do not represent buyers or sellers in transactions. All communications with listing agents are informational. You must work with a licensed RECO member for actual representation.",
  },
  {
    q: "Can I use 416Homes for commercial real estate?",
    a: "Not yet. We currently focus on residential (detached, semi-detached, townhouse, condo). Commercial real estate support is planned for 2027.",
  },
  {
    q: "What happens to my data?",
    a: "We store your email and search preferences in Supabase (hosted in Canada). We never sell your data. You can delete your account anytime by emailing hello@416homes.ca.",
  },
  {
    q: "How do I cancel my alert?",
    a: "Every email alert includes an unsubscribe link at the bottom. Click it to stop receiving matches. You can also email hello@416homes.ca to remove your data entirely.",
  },
];

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
        {FAQ_NAV.map(([href, label]) => (
          <li key={href}>
            <Link href={href} style={{
              fontFamily: "var(--mono)", fontSize: "0.65rem",
              textTransform: "uppercase", letterSpacing: "0.14em",
              color: href === "/faq" ? "var(--accent)" : "var(--text-mute)",
              textDecoration: "none",
            }}>
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
          {[...FAQ_NAV, ["/dashboard", "DASHBOARD"]].map(([href, label]) => (
            <Link key={href} href={href} onClick={() => setMenuOpen(false)} style={{ display: "block", padding: "14px 0", borderBottom: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-mute)", textDecoration: "none" }}>
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <NavBar />

      {/* ── Header ── */}
      <header style={{ borderBottom: "1px solid var(--border)", padding: "64px 80px 56px" }} className="sec-wrap">
        <div style={{ maxWidth: 1320, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
            <div style={{ width: 28, height: 2, background: "var(--accent)" }} />
            <span style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)" }}>
              Frequently Asked Questions
            </span>
          </div>
          <h1 className="page-h1" style={{ ...mono, fontSize: "clamp(2.2rem,4vw,3.2rem)", fontWeight: 800, margin: 0, letterSpacing: "-0.01em" }}>
            Everything you need to know
          </h1>
          <p style={{ ...mono, fontSize: "0.9rem", color: "#8A8876", marginTop: 20, maxWidth: "60ch", lineHeight: 1.7 }}>
            Canadian real estate rules, compliance, and platform details — answered plainly.
          </p>
        </div>
      </header>

      {/* ── FAQ accordion ── */}
      <main style={{ maxWidth: 1320, margin: "0 auto", padding: "56px 80px 80px" }} className="sec-wrap">
        <div style={{ display: "grid", gap: 16 }}>
          {FAQS.map((item, i) => {
            const isOpen = openIndex === i;
            return (
              <div
                key={i}
                style={{
                  border: `1px solid ${isOpen ? "var(--border-strong)" : "var(--border)"}`,
                  background: "#0A0D14",
                  transition: "border-color 0.2s",
                }}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  style={{
                    width: "100%", padding: "24px 32px",
                    background: "transparent", border: "none",
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    cursor: "pointer", textAlign: "left" as const,
                  }}
                >
                  <span style={{ ...mono, fontSize: "1rem", fontWeight: 600, color: "var(--text)", paddingRight: 24 }}>
                    {item.q}
                  </span>
                  <span style={{
                    color: "var(--accent)", fontSize: "1.4rem", lineHeight: 1, flexShrink: 0,
                    transform: isOpen ? "rotate(45deg)" : "rotate(0deg)",
                    transition: "transform 0.3s ease",
                    display: "inline-block",
                  }}>
                    +
                  </span>
                </button>
                {isOpen && (
                  <div style={{
                    padding: "0 32px 32px",
                    borderTop: "1px solid var(--border)",
                  }}>
                    <p style={{ ...mono, fontSize: "0.85rem", lineHeight: 1.8, color: "#8A8876", margin: "20px 0 0" }}>
                      {item.a}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Disclaimer box ── */}
        <div style={{
          marginTop: 80,
          padding: "40px 48px",
          border: "1px solid var(--border-strong)",
          background: "rgba(255,191,0,0.03)",
          textAlign: "center" as const,
        }}>
          <div style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)", marginBottom: 16 }}>
            ◆ Need legal or financial advice?
          </div>
          <div style={{ ...mono, fontSize: "1.8rem", fontWeight: 700, marginBottom: 16 }}>
            Talk to a licensed professional
          </div>
          <p style={{ ...mono, fontSize: "0.85rem", lineHeight: 1.7, color: "#8A8876", maxWidth: 700, margin: "0 auto 28px" }}>
            416Homes provides market intelligence, not legal or financial advice.
            For transactions, mortgages, or tax implications, consult a licensed RECO realtor,
            mortgage broker, or real estate lawyer.
          </p>
          <Link href="/#alert" style={{
            display: "inline-block", padding: "14px 32px",
            background: "var(--accent)", color: "var(--bg)",
            fontFamily: "var(--mono)", fontSize: "0.78rem", fontWeight: 700,
            textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none",
          }}>
            Get Free Listing Alerts →
          </Link>
        </div>
      </main>

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
