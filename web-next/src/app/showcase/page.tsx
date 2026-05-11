"use client";

import { useState } from "react";
import Link from "next/link";
import HouseLogo from "@/components/HouseLogo";
import { TOUR_SHOWCASE_ITEMS } from "@/lib/tour-showcase";

export default function ShowcasePage() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div style={{ minHeight: "100vh", background: "transparent", color: "var(--text)" }}>
      <nav
        className="nav-bar"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 40,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 56px",
          height: 64,
          background: "color-mix(in srgb, var(--bg) 82%, transparent)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <Link href="/" style={{ textDecoration: "none" }}>
          <HouseLogo size={28} />
        </Link>
        <ul
          className="nav-links"
          style={{
            display: "flex",
            listStyle: "none",
            gap: 36,
            margin: 0,
            padding: 0,
            fontFamily: "var(--mono)",
            fontSize: "0.68rem",
            letterSpacing: "0.14em",
            textTransform: "uppercase",
          }}
        >
          {[
            ["/dashboard", "Listings"],
            ["/video", "Videos"],
            ["/tours", "Virtual Tours"],
            ["/showcase", "Showcase"],
          ].map(([href, label]) => (
            <li key={href}>
              <Link
                href={href}
                style={{
                  textDecoration: "none",
                  color: label === "Showcase" ? "var(--accent)" : "var(--text-mute)",
                }}
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Link
            href="/tours#order"
            className="nav-cta"
            style={{
              display: "inline-block",
              padding: "10px 18px",
              background: "var(--accent)",
              color: "var(--bg)",
              fontFamily: "var(--mono)",
              fontSize: "0.68rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              textDecoration: "none",
            }}
          >
            Start a Tour
          </Link>
          <button
            className="hamburger-btn"
            onClick={() => setMenuOpen(!menuOpen)}
            style={{ background: "transparent", border: "none", color: "var(--text)", fontSize: "1.4rem", cursor: "pointer", padding: "4px 8px", lineHeight: 1 }}
          >
            {menuOpen ? "✕" : "☰"}
          </button>
        </div>
        {menuOpen && (
          <div style={{ position: "fixed", top: 64, left: 0, right: 0, background: "rgba(5,6,10,0.98)", backdropFilter: "blur(20px)", borderBottom: "1px solid var(--border)", padding: "8px 24px 20px", zIndex: 999 }}>
            {[
              ["/dashboard", "Listings"],
              ["/video", "Videos"],
              ["/tours", "Virtual Tours"],
              ["/showcase", "Showcase"],
              ["/tours#order", "Start a Tour"],
            ].map(([href, label]) => (
              <Link key={href} href={href} onClick={() => setMenuOpen(false)} style={{ display: "block", padding: "14px 0", borderBottom: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.14em", color: href === "/showcase" ? "var(--accent)" : "var(--text-mute)", textDecoration: "none" }}>
                {label}
              </Link>
            ))}
          </div>
        )}
      </nav>

      <section
        className="sec-wrap sec-pad-lg"
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "64px 56px 40px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            fontFamily: "var(--mono)",
            fontSize: "0.62rem",
            textTransform: "uppercase",
            letterSpacing: "0.18em",
            color: "var(--accent)",
            marginBottom: 20,
          }}
        >
          <span style={{ height: 1, width: 28, background: "var(--accent)", flexShrink: 0 }} />
          Tour Showcase
        </div>
        <h1
          className="page-h1"
          style={{
            fontFamily: "var(--mono)",
            fontSize: "clamp(2.3rem, 4.2vw, 4.4rem)",
            fontWeight: 700,
            lineHeight: 1.04,
            letterSpacing: "-0.02em",
            margin: "0 0 16px",
          }}
        >
          Browse the tours before you order one.
        </h1>
        <p
          style={{
            fontFamily: "var(--mono)",
            fontSize: "0.88rem",
            color: "var(--text-mute)",
            maxWidth: "64ch",
            lineHeight: 1.8,
            marginBottom: 28,
          }}
        >
          416Homes now supports two lanes: a fast photo-based room tour and a hosted
          3D walkthrough flow for scans and immersive assets. The demos below show the
          current experience we can ship today.
        </p>
        <div className="showcase-hero-actions" style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <Link
            href="/tours#order"
            style={{
              display: "inline-block",
              padding: "13px 24px",
              background: "var(--accent)",
              color: "var(--bg)",
              fontFamily: "var(--mono)",
              fontSize: "0.74rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              textDecoration: "none",
            }}
          >
            Create a Tour →
          </Link>
          <Link
            href="/tours"
            style={{
              display: "inline-block",
              padding: "13px 24px",
              border: "1px solid var(--border-strong)",
              color: "var(--text)",
              fontFamily: "var(--mono)",
              fontSize: "0.74rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              textDecoration: "none",
            }}
          >
            Compare Formats →
          </Link>
        </div>
      </section>

      <section
        className="sec-wrap sec-pad-lg"
        style={{ maxWidth: 1200, margin: "0 auto", padding: "36px 56px 72px" }}
      >
        <div className="showcase-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24 }}>
          {TOUR_SHOWCASE_ITEMS.map((item) => (
            <article
              key={item.id}
              className="showcase-card"
              style={{
                border: "1px solid var(--border)",
                background: "var(--bg-elev)",
                overflow: "hidden",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div style={{ position: "relative", aspectRatio: "16 / 10", background: "#0a0a08" }}>
                <img
                  src={item.previewImage}
                  alt={item.title}
                  style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
                />
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: "linear-gradient(to top, rgba(5,6,10,0.85) 0%, rgba(5,6,10,0.05) 60%)",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: 18,
                    bottom: 18,
                    right: 18,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-end",
                    gap: 16,
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: "0.54rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.16em",
                        color: "var(--accent)",
                        marginBottom: 8,
                      }}
                    >
                      {item.badge}
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: "1.1rem", fontWeight: 600, color: "#fff" }}>
                      {item.title}
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "rgba(255,255,255,0.72)", marginTop: 4 }}>
                      {item.location}
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.74rem", color: "var(--text-mute)", lineHeight: 1.8 }}>
                  {item.summary}
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-dim)", lineHeight: 1.7 }}>
                  {item.detail}
                </div>
                <Link
                  href={item.href}
                  style={{
                    marginTop: "auto",
                    display: "inline-block",
                    padding: "13px 18px",
                    border: "1px solid var(--border-strong)",
                    color: "var(--accent)",
                    fontFamily: "var(--mono)",
                    fontSize: "0.68rem",
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    textDecoration: "none",
                    textAlign: "center",
                  }}
                >
                  {item.cta}
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
