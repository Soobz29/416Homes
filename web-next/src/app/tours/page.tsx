"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

/* ── Shared nav primitives ──────────────────────────────────────────── */
function Logo({ sub }: { sub?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 8, fontFamily: "var(--mono)", fontWeight: 800, fontSize: "1.2rem", letterSpacing: "0.02em" }}>
      <span style={{ color: "var(--accent)" }}>416</span>
      <span style={{ color: "var(--text)" }}>Homes</span>
      {sub && <span style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", color: "var(--text-dim)", letterSpacing: "0.14em", textTransform: "uppercase", paddingLeft: 4, fontWeight: 400 }}>{sub}</span>}
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

function PrimaryBtn({ children, onClick, disabled }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: "100%", padding: "15px",
        background: disabled ? "var(--accent-dim)" : "var(--accent)",
        border: "none", color: "var(--bg)",
        fontFamily: "var(--mono)", fontSize: "0.82rem", fontWeight: 700,
        letterSpacing: "0.08em", textTransform: "uppercase", cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: disabled ? "none" : "0 0 22px rgba(255,176,0,0.30), inset 0 1px 0 rgba(255,255,255,0.14)",
        transition: "background 0.2s",
      }}
    >{children}</button>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "12px 14px",
  background: "transparent", border: "1px solid var(--border)",
  color: "var(--text)", fontFamily: "var(--mono)", fontSize: "0.85rem", outline: "none",
};

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-mute)", marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  );
}

/* ── Room map for the 3D dollhouse demo ─────────────────────────────── */
const DEMO_PHOTOS = [
  "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800&q=80",
  "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80",
  "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&q=80",
  "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80",
];

type RoomKey = "living" | "kitchen" | "bedroom" | "bath";
const ROOM_MAP: Record<RoomKey, { name: string; photo: string }> = {
  living:  { name: "Living Room",      photo: DEMO_PHOTOS[0] },
  kitchen: { name: "Kitchen",          photo: DEMO_PHOTOS[1] },
  bedroom: { name: "Primary Bedroom",  photo: DEMO_PHOTOS[2] },
  bath:    { name: "Bathroom",         photo: DEMO_PHOTOS[3] },
};

/* ── 3D Dollhouse SVG ───────────────────────────────────────────────── */
function Dollhouse({ selected, onSelect }: { selected: RoomKey; onSelect: (r: RoomKey) => void }) {
  return (
    <svg viewBox="0 0 800 500" style={{ width: "100%", height: "100%", display: "block" }}>
      {/* Isometric floor */}
      <polygon points="100,350 400,200 700,350 400,500" fill="#1A1A18" stroke="rgba(255,191,0,0.2)" strokeWidth="1" />

      {/* Living room */}
      <g onClick={() => onSelect("living")} style={{ cursor: "pointer" }} opacity={selected === "living" ? 1 : 0.65}>
        <polygon points="100,350 250,275 250,150 100,225"
          fill="#0F1218" stroke={selected === "living" ? "var(--accent)" : "rgba(255,191,0,0.25)"}
          strokeWidth={selected === "living" ? 2 : 1} />
        <text x="175" y="265" fill={selected === "living" ? "var(--accent)" : "#666"}
          fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">LIVING</text>
        {selected === "living" && <circle cx="175" cy="240" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>

      {/* Kitchen */}
      <g onClick={() => onSelect("kitchen")} style={{ cursor: "pointer" }} opacity={selected === "kitchen" ? 1 : 0.65}>
        <polygon points="250,275 400,200 400,100 250,175"
          fill="#0F1218" stroke={selected === "kitchen" ? "var(--accent)" : "rgba(255,191,0,0.25)"}
          strokeWidth={selected === "kitchen" ? 2 : 1} />
        <text x="325" y="222" fill={selected === "kitchen" ? "var(--accent)" : "#666"}
          fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">KITCHEN</text>
        {selected === "kitchen" && <circle cx="325" cy="200" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>

      {/* Bedroom */}
      <g onClick={() => onSelect("bedroom")} style={{ cursor: "pointer" }} opacity={selected === "bedroom" ? 1 : 0.65}>
        <polygon points="400,200 550,275 550,150 400,100"
          fill="#0F1218" stroke={selected === "bedroom" ? "var(--accent)" : "rgba(255,191,0,0.25)"}
          strokeWidth={selected === "bedroom" ? 2 : 1} />
        <text x="475" y="222" fill={selected === "bedroom" ? "var(--accent)" : "#666"}
          fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">BEDROOM</text>
        {selected === "bedroom" && <circle cx="475" cy="200" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>

      {/* Bathroom */}
      <g onClick={() => onSelect("bath")} style={{ cursor: "pointer" }} opacity={selected === "bath" ? 1 : 0.65}>
        <polygon points="550,275 700,350 700,225 550,150"
          fill="#0F1218" stroke={selected === "bath" ? "var(--accent)" : "rgba(255,191,0,0.25)"}
          strokeWidth={selected === "bath" ? 2 : 1} />
        <text x="625" y="262" fill={selected === "bath" ? "var(--accent)" : "#666"}
          fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">BATH</text>
        {selected === "bath" && <circle cx="625" cy="240" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>

      {/* Grid guides */}
      <line x1="400" y1="100" x2="400" y2="500" stroke="rgba(255,255,255,0.04)" strokeWidth="1" strokeDasharray="4 4" />
      <line x1="250" y1="150" x2="550" y2="150" stroke="rgba(255,255,255,0.04)" strokeWidth="1" strokeDasharray="4 4" />
    </svg>
  );
}

/* ── Page ───────────────────────────────────────────────────────────── */
export default function ToursPage() {
  const [selectedRoom, setSelectedRoom] = useState<RoomKey>("living");
  const [url, setUrl] = useState("");
  const [email, setEmail] = useState("");
  const [paid, setPaid] = useState(false);
  const [progress, setProgress] = useState(0);
  const [tourId] = useState(() => Math.floor(Math.random() * 9000 + 1000));
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!paid) return;
    const t = setInterval(() => setProgress(p => {
      if (p >= 100) { clearInterval(t); return 100; }
      return p + 5;
    }), 200);
    return () => clearInterval(t);
  }, [paid]);

  const progressLabel =
    progress < 30  ? "Fetching listing photos…" :
    progress < 60  ? "Classifying rooms with Gemini Vision…" :
    progress < 100 ? "Assembling hosted manifest…" :
    `Tour live: 416homes.ca/tours/${tourId}`;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>

      {/* Nav */}
      <nav style={{
        position: "sticky", top: 0, zIndex: 40,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 56px", height: 64,
        background: "color-mix(in srgb, var(--bg) 82%, transparent)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--border)",
      }}>
        <Link href="/" style={{ textDecoration: "none" }}><Logo sub="GTA" /></Link>
        <ul className="nav-links" style={{ display: "flex", listStyle: "none", gap: 36, margin: 0, padding: 0, fontFamily: "var(--mono)", fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase" }}>
          {[["/dashboard", "Listings"], ["/video", "Videos"], ["/tours", "Virtual Tours"]].map(([href, label]) => (
            <li key={href}>
              <Link href={href} style={{ textDecoration: "none", color: label === "Virtual Tours" ? "var(--accent)" : "var(--text-mute)" }}>{label}</Link>
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
          <Link href="/#alert" style={{ display: "inline-block", padding: "10px 18px", background: "var(--accent)", color: "var(--bg)", fontFamily: "var(--mono)", fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", textDecoration: "none" }}>
            Set My Alert
          </Link>
        </div>
        {menuOpen && (
          <div style={{ position: "fixed", top: 64, left: 0, right: 0, background: "rgba(5,6,10,0.98)", backdropFilter: "blur(20px)", borderBottom: "1px solid var(--border)", padding: "8px 24px 20px", zIndex: 999 }}>
            {[["/dashboard", "Listings"], ["/video", "Videos"], ["/tours", "Virtual Tours"], ["/#alert", "Set My Alert"]].map(([href, label]) => (
              <Link key={href} href={href} onClick={() => setMenuOpen(false)} style={{ display: "block", padding: "14px 0", borderBottom: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-mute)", textDecoration: "none" }}>
                {label}
              </Link>
            ))}
          </div>
        )}
      </nav>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "48px 56px" }}>

        {/* Header */}
        <Eyebrow line>Virtual tour · $49</Eyebrow>
        <h1 style={{ fontFamily: "var(--mono)", fontSize: "clamp(2rem, 3.2vw, 3.2rem)", fontWeight: 700, lineHeight: 1.02, letterSpacing: "-0.015em", margin: "16px 0 12px" }}>
          Listing photos →{" "}
          <span style={{ color: "var(--accent)", background: "linear-gradient(180deg,transparent 60%,rgba(255,176,0,0.18) 60%)", padding: "0 4px" }}>
            hosted room-by-room tour.
          </span>
        </h1>
        <p style={{ fontFamily: "var(--mono)", fontSize: "0.85rem", lineHeight: 1.7, color: "var(--text-mute)", maxWidth: "54ch", marginBottom: 40 }}>
          Gemini Vision classifies every photo by room, assembles a shareable tour,
          and gives you a public link and embed code. Delivered in under five minutes.
        </p>

        {/* Demo — dollhouse + sidebar */}
        <div style={{ marginBottom: 48, border: "1px solid var(--border-strong)", overflow: "hidden", background: "var(--bg-elev)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 0 }}>
            {/* Dollhouse */}
            <div style={{ position: "relative", aspectRatio: "16/10", background: "#000", overflow: "hidden" }}>
              {/* Room photo background */}
              <img
                key={selectedRoom}
                src={ROOM_MAP[selectedRoom].photo}
                alt=""
                style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: 0.45, transition: "opacity 0.4s" }}
              />
              {/* Dark gradient overlay */}
              <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom, rgba(5,6,10,0.35) 0%, rgba(5,6,10,0.6) 100%)", zIndex: 1 }} />
              <div style={{ position: "relative", zIndex: 2 }}>
                <Dollhouse selected={selectedRoom} onSelect={setSelectedRoom} />
              </div>

              {/* Top chrome */}
              <div style={{ position: "absolute", top: 20, left: 20, background: "rgba(5,6,10,0.88)", padding: "10px 16px", border: "1px solid var(--border)", zIndex: 3 }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)" }}>3D Dollhouse</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.05rem", fontWeight: 600, color: "#fff", marginTop: 4 }}>{ROOM_MAP[selectedRoom].name}</div>
              </div>

              {/* Bottom bar */}
              <div style={{ position: "absolute", bottom: 16, left: 16, right: 16, display: "flex", justifyContent: "space-between", alignItems: "center", zIndex: 3 }}>
                <div style={{ background: "rgba(5,6,10,0.88)", padding: "8px 14px", border: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.68rem", color: "#fff" }}>
                  <span style={{ color: "var(--accent)" }}>◆</span> 88 Niagara St, Unit 412 — King West · 2BR 2BA
                </div>
                <div style={{ background: "rgba(5,6,10,0.88)", padding: "8px 12px", border: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.64rem", color: "var(--accent)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                  ⬡ 3D View
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div style={{ padding: 28, borderLeft: "1px solid var(--border)", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <Eyebrow>Interactive demo</Eyebrow>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.05rem", fontWeight: 600, margin: "10px 0 12px" }}>Click any room</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.7rem", lineHeight: 1.6, color: "var(--text-mute)", marginBottom: 16 }}>
                  Matterport-style 3D dollhouse. Click rooms in the model to navigate through the property.
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {(Object.entries(ROOM_MAP) as [RoomKey, { name: string }][]).map(([k, v]) => (
                    <button key={k} onClick={() => setSelectedRoom(k)} style={{
                      padding: "10px 12px", textAlign: "left",
                      background: selectedRoom === k ? "var(--bg-panel)" : "transparent",
                      border: `1px solid ${selectedRoom === k ? "var(--accent)" : "var(--border)"}`,
                      color: selectedRoom === k ? "var(--accent)" : "var(--text)",
                      fontFamily: "var(--mono)", fontSize: "0.68rem",
                      cursor: "pointer", transition: "all 0.15s",
                      display: "flex", alignItems: "center", gap: 8,
                    }}>
                      <span style={{ opacity: selectedRoom === k ? 1 : 0.4 }}>{selectedRoom === k ? "●" : "○"}</span>
                      {v.name}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ paddingTop: 16, borderTop: "1px solid var(--border)", marginTop: 16, fontFamily: "var(--mono)", fontSize: "0.58rem", color: "var(--text-dim)", lineHeight: 1.6, letterSpacing: "0.06em" }}>
                Gemini Vision classifies photos → auto-generates 3D dollhouse + room-by-room gallery.
              </div>
            </div>
          </div>
        </div>

        {/* Order section */}
        <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 64 }}>
          {/* What's included */}
          <div>
            <div style={{ border: "1px solid var(--border)", padding: 28 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 14 }}>What&apos;s included</div>
              {[
                ["Room-by-room classification", "Living, kitchen, bedrooms, bath — automatic"],
                ["Hosted link", "Mobile-friendly, no login required"],
                ["Embed code", "Drop into any listing page or MLS"],
                ["Lifetime hosting", "Yours for as long as the listing is live"],
              ].map(([t, d]) => (
                <div key={t as string} style={{ padding: "12px 0", borderBottom: "1px dotted var(--border)" }}>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.95rem", fontWeight: 600 }}>{t}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text-mute)", marginTop: 2 }}>{d}</div>
                </div>
              ))}
            </div>

            {/* Pricing comparison */}
            <div style={{ marginTop: 24, border: "1px solid var(--border)", padding: 28 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 14 }}>Why 416Homes tours?</div>
              {[
                ["Matterport", "$500+", "Complex setup, equipment needed"],
                ["Virtual staging", "$200–400", "Static images only"],
                ["416Homes", "$49", "From existing photos, 5 minutes"],
              ].map(([name, price, note]) => (
                <div key={name as string} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "10px 0", borderBottom: "1px dotted var(--border)" }}>
                  <div>
                    <span style={{ fontFamily: "var(--mono)", fontSize: "0.85rem", fontWeight: 600, color: name === "416Homes" ? "var(--accent)" : "var(--text)" }}>{name}</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: "0.66rem", color: "var(--text-mute)", marginLeft: 12 }}>{note}</span>
                  </div>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "0.85rem", color: name === "416Homes" ? "var(--accent)" : "var(--text-mute)" }}>{price}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Order form */}
          <div style={{ border: "1px solid var(--border-strong)", padding: 32, background: "var(--bg-elev)", height: "fit-content", position: "sticky", top: 100 }}>
            {!paid ? (
              <>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.3rem", fontWeight: 700, marginBottom: 20 }}>Order a tour</div>
                <FormField label="Listing URL">
                  <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://www.realtor.ca/..." style={inputStyle} />
                </FormField>
                <FormField label="Delivery email">
                  <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" style={inputStyle} />
                </FormField>

                <div style={{ marginTop: 20, padding: "16px 0", borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 20 }}>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-mute)" }}>Total</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "2.4rem", fontWeight: 700 }}>
                    $49 <span style={{ fontSize: "0.7rem", fontFamily: "var(--mono)", color: "var(--text-mute)", letterSpacing: "0.1em", textTransform: "uppercase" }}>CAD</span>
                  </div>
                </div>

                <PrimaryBtn onClick={() => { if (url && email) setPaid(true); }}>
                  Pay &amp; generate →
                </PrimaryBtn>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", color: "var(--text-dim)", textAlign: "center", marginTop: 12 }}>
                  Secure checkout via Stripe
                </div>
              </>
            ) : (
              <>
                <Eyebrow>{progress < 100 ? "Generating" : "Ready"}</Eyebrow>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.4rem", fontWeight: 700, margin: "14px 0 20px" }}>
                  {progress < 100 ? "Building your tour…" : "Your tour is live."}
                </div>
                <div style={{ width: "100%", height: 6, background: "var(--bg)", overflow: "hidden", marginBottom: 16 }}>
                  <div style={{ width: `${progress}%`, height: "100%", background: "var(--accent)", transition: "width 0.2s" }} />
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text-mute)", lineHeight: 1.6 }}>
                  {progressLabel}
                </div>
                {progress >= 100 && (
                  <button
                    onClick={() => { setPaid(false); setProgress(0); setUrl(""); setEmail(""); }}
                    style={{ marginTop: 24, padding: "10px 20px", background: "transparent", border: "1px solid var(--border-strong)", color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "0.68rem", letterSpacing: "0.1em", textTransform: "uppercase", cursor: "pointer" }}
                  >
                    Order another →
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 56px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-mute)" }}>
        <Logo />
        <span>Covering the Greater Toronto Area · Built on real sold data</span>
        <span>© 2026 416Homes · Early Access</span>
      </footer>
    </div>
  );
}
