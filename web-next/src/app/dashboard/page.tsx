"use client";

import { useEffect, useState } from "react";
import dynamicImport from "next/dynamic";
import HouseLogo from "@/components/HouseLogo";
import Link from "next/link";
import { Listing } from "@/types";
import { fetchListings, fetchValuation } from "@/lib/api";

import { getSession, signInWithEmail, signOut } from "@/lib/supabase";
import { Alert, fetchAlerts, createAlert, updateAlert, deleteAlert, generateLinkCode, fetchMe } from "@/lib/alerts";
import { DropdownSelect } from "@/components/DropdownSelect";
import { ErrorBanner } from "@/components/ui/error-banner";
import { ListingCard, ListingCardSkeleton, ListRow } from "@/components/listing-card";

/* ── Reno ROI data (dashboard tab) ─────────────────────────────────── */
const DASH_RENO_TYPES = [
  { id: "kitchen_full",   label: "Kitchen — Full Renovation",  roi: 0.90, roiRange: "85–95%",   timeMonths: 18, risk: "Low",      typical: "$40K–$80K" },
  { id: "kitchen_minor",  label: "Kitchen — Minor Refresh",     roi: 1.05, roiRange: "95–115%",  timeMonths: 6,  risk: "Low",      typical: "$10K–$25K" },
  { id: "bathroom_prim",  label: "Primary Bathroom",            roi: 0.75, roiRange: "70–82%",   timeMonths: 14, risk: "Medium",   typical: "$20K–$45K" },
  { id: "bathroom_add",   label: "Add a Bathroom",              roi: 0.70, roiRange: "65–78%",   timeMonths: 24, risk: "Medium",   typical: "$15K–$35K" },
  { id: "basement",       label: "Basement — Finish & Suite",   roi: 0.65, roiRange: "60–72%",   timeMonths: 30, risk: "Medium",   typical: "$50K–$100K" },
  { id: "paint_cosmetic", label: "Paint + Cosmetic Updates",    roi: 1.25, roiRange: "100–150%", timeMonths: 4,  risk: "Very Low", typical: "$5K–$15K" },
  { id: "windows",        label: "New Windows & Doors",         roi: 0.67, roiRange: "60–75%",   timeMonths: 24, risk: "Low",      typical: "$15K–$40K" },
  { id: "deck_outdoor",   label: "Deck / Outdoor Living",       roi: 0.62, roiRange: "55–70%",   timeMonths: 18, risk: "Low",      typical: "$20K–$60K" },
  { id: "addition",       label: "Room Addition / Extension",   roi: 0.60, roiRange: "50–70%",   timeMonths: 48, risk: "High",     typical: "$80K–$200K" },
];
const DASH_RISK_COLORS: Record<string, string> = {
  "Very Low": "#2ed573", "Low": "#7bed9f", "Medium": "#ffa502", "High": "#cf6357",
};

/* ── Virtual tour dollhouse (dashboard tab) ──────────────────────────── */
const DASH_DEMO_PHOTOS = [
  "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800&q=80",
  "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80",
  "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&q=80",
  "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80",
];
type DashRoomKey = "living" | "kitchen" | "bedroom" | "bath";
const DASH_ROOM_MAP: Record<DashRoomKey, { name: string; photo: string }> = {
  living:  { name: "Living Room",     photo: DASH_DEMO_PHOTOS[0] },
  kitchen: { name: "Kitchen",         photo: DASH_DEMO_PHOTOS[1] },
  bedroom: { name: "Primary Bedroom", photo: DASH_DEMO_PHOTOS[2] },
  bath:    { name: "Bathroom",        photo: DASH_DEMO_PHOTOS[3] },
};
function DashDollhouse({ selected, onSelect }: { selected: DashRoomKey; onSelect: (r: DashRoomKey) => void }) {
  return (
    <svg viewBox="0 0 800 500" style={{ width: "100%", height: "100%", display: "block" }}>
      <polygon points="100,350 400,200 700,350 400,500" fill="#1A1A18" stroke="rgba(255,191,0,0.2)" strokeWidth="1" />
      <g onClick={() => onSelect("living")} style={{ cursor: "pointer" }} opacity={selected === "living" ? 1 : 0.65}>
        <polygon points="100,350 250,275 250,150 100,225" fill="#0F1218" stroke={selected === "living" ? "var(--accent)" : "rgba(255,191,0,0.25)"} strokeWidth={selected === "living" ? 2 : 1} />
        <text x="175" y="265" fill={selected === "living" ? "var(--accent)" : "#666"} fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">LIVING</text>
        {selected === "living" && <circle cx="175" cy="240" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>
      <g onClick={() => onSelect("kitchen")} style={{ cursor: "pointer" }} opacity={selected === "kitchen" ? 1 : 0.65}>
        <polygon points="250,275 400,200 400,100 250,175" fill="#0F1218" stroke={selected === "kitchen" ? "var(--accent)" : "rgba(255,191,0,0.25)"} strokeWidth={selected === "kitchen" ? 2 : 1} />
        <text x="325" y="222" fill={selected === "kitchen" ? "var(--accent)" : "#666"} fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">KITCHEN</text>
        {selected === "kitchen" && <circle cx="325" cy="200" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>
      <g onClick={() => onSelect("bedroom")} style={{ cursor: "pointer" }} opacity={selected === "bedroom" ? 1 : 0.65}>
        <polygon points="400,200 550,275 550,150 400,100" fill="#0F1218" stroke={selected === "bedroom" ? "var(--accent)" : "rgba(255,191,0,0.25)"} strokeWidth={selected === "bedroom" ? 2 : 1} />
        <text x="475" y="222" fill={selected === "bedroom" ? "var(--accent)" : "#666"} fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">BEDROOM</text>
        {selected === "bedroom" && <circle cx="475" cy="200" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>
      <g onClick={() => onSelect("bath")} style={{ cursor: "pointer" }} opacity={selected === "bath" ? 1 : 0.65}>
        <polygon points="550,275 700,350 700,225 550,150" fill="#0F1218" stroke={selected === "bath" ? "var(--accent)" : "rgba(255,191,0,0.25)"} strokeWidth={selected === "bath" ? 2 : 1} />
        <text x="625" y="262" fill={selected === "bath" ? "var(--accent)" : "#666"} fontSize="10" fontFamily="'JetBrains Mono',monospace" textAnchor="middle" letterSpacing="1">BATH</text>
        {selected === "bath" && <circle cx="625" cy="240" r="18" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.6" />}
      </g>
      <line x1="400" y1="100" x2="400" y2="500" stroke="rgba(255,255,255,0.04)" strokeWidth="1" strokeDasharray="4 4" />
      <line x1="250" y1="150" x2="550" y2="150" stroke="rgba(255,255,255,0.04)" strokeWidth="1" strokeDasharray="4 4" />
    </svg>
  );
}

const CITIES = [
  { value: "GTA", label: "All GTA" },
  { value: "Toronto", label: "Toronto" },
  { value: "Downtown", label: "Downtown" },
  { value: "North York", label: "North York" },
  { value: "Scarborough", label: "Scarborough" },
  { value: "Etobicoke", label: "Etobicoke" },
  { value: "Mississauga", label: "Mississauga" },
  { value: "Brampton", label: "Brampton" },
  { value: "Vaughan", label: "Vaughan" },
  { value: "Markham", label: "Markham" },
  { value: "Richmond Hill", label: "Richmond Hill" },
  { value: "Oakville", label: "Oakville" },
  { value: "Burlington", label: "Burlington" },
  { value: "Ajax", label: "Ajax" },
  { value: "Pickering", label: "Pickering" },
  { value: "Whitby", label: "Whitby" },
  { value: "Oshawa", label: "Oshawa" },
  { value: "Milton", label: "Milton" },
];

const PROPERTY_TYPES = [
  { value: "", label: "Any type" },
  { value: "Condo", label: "Condo" },
  { value: "Apartment", label: "Apartment" },
  { value: "Townhouse", label: "Townhouse" },
  { value: "Detached", label: "Detached" },
  { value: "Semi-Detached", label: "Semi-Detached" },
  { value: "House", label: "House" },
];

const BED_OPTIONS = [
  { value: "", label: "Any Beds" },
  { value: "1", label: "1+ Beds" },
  { value: "2", label: "2+ Beds" },
  { value: "3", label: "3+ Beds" },
  { value: "4", label: "4+ Beds" },
];

const BATH_OPTIONS = [
  { value: "", label: "Any Baths" },
  { value: "1", label: "1+ Baths" },
  { value: "2", label: "2+ Baths" },
  { value: "3", label: "3+ Baths" },
];

const LISTINGS_PAGE_SIZE = 36;
const TELEGRAM_BOT = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "Homes_Alertsbot";

/* ── MarketInsightsBar ───────────────────────────────────────────────── */
function MarketInsightsBar({ listings, total }: { listings: Listing[]; total: number }) {
  const withVal   = listings.filter(l => l.fair_value != null);
  const under     = withVal.filter(l => (l.fair_value ?? 0) >= 3).length;
  const over      = withVal.filter(l => (l.fair_value ?? 0) <= -3).length;
  const fair      = withVal.length - under - over;
  const domArr    = listings.filter(l => l.dom != null).map(l => l.dom!);
  const avgDom    = domArr.length ? Math.round(domArr.reduce((s, d) => s + d, 0) / domArr.length) : null;
  const psfArr    = listings.filter(l => l.sqft > 0 && l.price > 0).map(l => l.price / l.sqft);
  const avgPsf    = psfArr.length ? Math.round(psfArr.reduce((s, p) => s + p, 0) / psfArr.length) : null;

  const mono: React.CSSProperties = { fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.08em" };

  return (
    <div style={{
      padding: "8px 20px", borderBottom: "1px solid var(--border)",
      background: "rgba(255,191,0,0.02)",
      display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap",
    }}>
      <span style={{ ...mono, color: "var(--text-dim)" }}>
        ◆ {total.toLocaleString()} listings
      </span>
      {withVal.length > 0 && (
        <>
          <span style={{ ...mono, color: "#2ed573" }}>
            ↓ {Math.round(under / withVal.length * 100)}% underpriced
          </span>
          <span style={{ ...mono, color: "#cf6357" }}>
            ↑ {Math.round(over / withVal.length * 100)}% overpriced
          </span>
          <span style={{ ...mono, color: "var(--text-dim)" }}>
            ≈ {Math.round(fair / withVal.length * 100)}% fair
          </span>
        </>
      )}
      {avgDom != null && (
        <span style={{ ...mono, color: "var(--text-dim)" }}>· avg {avgDom}d DOM</span>
      )}
      {avgPsf != null && (
        <span style={{ ...mono, color: "var(--text-dim)" }}>· ${avgPsf.toLocaleString()}/sf avg</span>
      )}
    </div>
  );
}


const GTAMap = dynamicImport(() => import("@/components/GTAMap"), { ssr: false });

/* ── Main page ──────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [emailInput, setEmailInput] = useState("");
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"listings" | "valuation" | "videos" | "reno" | "tour">("listings");
  /* ── Reno tab state ── */
  const [renoSelectedId, setRenoSelectedId] = useState("kitchen_full");
  const [renoHomeValue, setRenoHomeValue] = useState("");
  const [renoBudget, setRenoBudget] = useState("");
  const [renoResult, setRenoResult] = useState<null | { roiPct: number; addedValue: number; newValue: number; roiDollars: number; risk: string; roiRange: string; timeMonths: number; typical: string }>(null);
  /* ── Tour tab state ── */
  const [tourRoom, setTourRoom] = useState<DashRoomKey>("living");
  const [tourUrl, setTourUrl] = useState("");
  const [tourEmail, setTourEmail] = useState("");
  const [tourPaid, setTourPaid] = useState(false);
  const [tourProgress, setTourProgress] = useState(0);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    city:         "GTA",
    minPrice:     "",
    maxPrice:     "",
    bedrooms:     "",
    bathrooms:    "",
    propertyType: "",
  });

  // Read URL search params on client mount (avoids useSearchParams + Suspense requirement)
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const city = p.get("city");
    const minPrice = p.get("minPrice");
    const maxPrice = p.get("maxPrice");
    const bedrooms = p.get("bedrooms");
    const propertyType = p.get("propertyType");
    if (city || minPrice || maxPrice || bedrooms || propertyType) {
      setFilters(prev => ({
        ...prev,
        city:         city         || prev.city,
        minPrice:     minPrice     || prev.minPrice,
        maxPrice:     maxPrice     || prev.maxPrice,
        bedrooms:     bedrooms     || prev.bedrooms,
        propertyType: propertyType || prev.propertyType,
      }));
    }
  }, []);
  const [listingsError, setListingsError] = useState<string | null>(null);
  const [listingsPage, setListingsPage] = useState(0);
  const [totalListings, setTotalListings] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertsError, setAlertsError] = useState<string | null>(null);
  const [alertActionError, setAlertActionError] = useState<string | null>(null);
  const [alertForm, setAlertForm] = useState({
    city: "GTA",
    minPrice: "",
    maxPrice: "",
    minBeds: "",
    propertyTypes: [] as string[],
  });
  const [linkCode, setLinkCode] = useState<string | null>(null);
  const [linkExpiresAt, setLinkExpiresAt] = useState<string | null>(null);
  const [linkMessage, setLinkMessage] = useState<string | null>(null);
  const [linkLoading, setLinkLoading] = useState(false);
  const [telegramLinked, setTelegramLinked] = useState(false);
  const [checkingLinked, setCheckingLinked] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [meError, setMeError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [valuationForm, setValuationForm] = useState({
    neighbourhood: "", city: "Toronto", bedrooms: "", bathrooms: "", sqft: "", list_price: "",
  });
  const [valuationCondition, setValuationCondition] = useState<"excellent"|"good"|"fair"|"poor">("good");
  const [valuationResult, setValuationResult] = useState<null | { estimated_value: number; confidence: number; price_per_sqft?: number; market_analysis: string }>(null);
  const [valuationLoading, setValuationLoading] = useState(false);
  const [valuationError, setValuationError] = useState<string | null>(null);

  /* Condition multipliers — applied to estimated_value on the frontend */
  const CONDITION_MULT: Record<string, number> = {
    excellent: 1.12,
    good:      1.00,
    fair:      0.92,
    poor:      0.82,
  };

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    void (async () => {
      try {
        const session = await getSession();
        const email = session?.user?.email ?? null;
        setSessionEmail(email);
        if (email) {
          void loadAlerts(email);
          void loadMe(email);
        }
      } catch (e) {
        console.error("Failed to load Supabase session", e);
      }
    })();
  }, []);

  useEffect(() => { setListingsPage(0); }, [filters]);

  useEffect(() => {
    if (activeTab === "listings") void loadListings();
  }, [activeTab, filters, listingsPage]);

  // Tour product has its own dedicated page (/tours) — no in-dashboard fake progress.

  async function triggerScan() {
    setScanLoading(true);
    setScanMessage(null);
    try {
      const apiBase = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
      await fetch(`${apiBase}/api/initiate-scan`, { method: "POST" });
      setScanMessage("Scan started — listings refresh in ~2 minutes.");
      setTimeout(() => { void loadListings(); }, 120_000);
    } catch {
      setScanMessage("Could not reach the API to start a scan.");
    } finally {
      setScanLoading(false);
    }
  }

  async function loadListings() {
    try {
      setLoading(true);
      setListingsError(null);
      const data = await fetchListings({
        city: filters.city === "GTA" ? undefined : filters.city,
        minPrice: filters.minPrice ? Number(filters.minPrice) : undefined,
        maxPrice: filters.maxPrice ? Number(filters.maxPrice) : undefined,
        propertyTypes: filters.propertyType ? [filters.propertyType] : undefined,
        limit: LISTINGS_PAGE_SIZE,
        offset: listingsPage * LISTINGS_PAGE_SIZE,
      });
      setListings(data.listings || []);
      setTotalListings(typeof data.total === "number" ? data.total : 0);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to load listings.";
      setListingsError(msg);
      setListings([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadAlerts(email: string) {
    try {
      setAlertsLoading(true);
      setAlertsError(null);
      const data = await fetchAlerts(email);
      setAlerts(data);
    } catch (e) {
      setAlertsError(e instanceof Error ? e.message : "Failed to load alerts.");
    } finally {
      setAlertsLoading(false);
    }
  }

  async function handleAuthSubmit() {
    try {
      setAuthMessage(null);
      await signInWithEmail(emailInput);
      setAuthMessage("Magic link sent. Check your email and reopen the dashboard from that link.");
    } catch (e: any) {
      const msg = e?.message ?? "Failed to send magic link";
      if (/rate limit/i.test(msg)) {
        setAuthMessage("Too many login attempts. Please wait a few minutes and try again.");
      } else if (/confirmation email|error sending|smtp|sending email/i.test(msg)) {
        setAuthMessage("Error sending confirmation email. Check Supabase Auth → Email (SMTP).");
      } else {
        setAuthMessage(msg);
      }
    }
  }

  async function handleSignOut() {
    try {
      await signOut();
      setSessionEmail(null);
      setAlerts([]);
    } catch (e) {
      console.error("Sign out failed", e);
    }
  }

  async function handleCreateAlert() {
    if (!sessionEmail) return;
    try {
      setAlertActionError(null);
      const payload = {
        min_price: alertForm.minPrice ? Number(alertForm.minPrice) : undefined,
        max_price: alertForm.maxPrice ? Number(alertForm.maxPrice) : undefined,
        min_beds: alertForm.minBeds ? Number(alertForm.minBeds) : undefined,
        cities: alertForm.city === "GTA" ? ["GTA"] : [alertForm.city],
        property_types: alertForm.propertyTypes.length ? alertForm.propertyTypes : undefined,
      };
      const created = await createAlert(sessionEmail, payload);
      setAlerts(prev => [created, ...prev]);
      setAlertForm({ city: "GTA", minPrice: "", maxPrice: "", minBeds: "", propertyTypes: [] });
    } catch (e) {
      setAlertActionError(e instanceof Error ? e.message : "Failed to create alert.");
    }
  }

  async function handleDeleteAlert(alert: Alert) {
    if (!sessionEmail) return;
    if (!confirm("Delete this alert?")) return;
    try {
      setAlertActionError(null);
      await deleteAlert(sessionEmail, alert.id);
      setAlerts(prev => prev.filter(a => a.id !== alert.id));
    } catch (e) {
      setAlertActionError(e instanceof Error ? e.message : "Failed to delete alert.");
    }
  }

  async function loadMe(email: string) {
    try {
      setMeError(null);
      const me = await fetchMe(email);
      setTelegramLinked(!!me?.telegram_chat_id);
    } catch (e: unknown) {
      console.error("Failed to load /api/me", e);
      const msg = e instanceof Error ? e.message : "Could not reach backend";
      setMeError(msg.includes("401") || msg.includes("Missing")
        ? "Sign in required."
        : `${msg}. Set NEXT_PUBLIC_API_URL to your Railway API URL in Vercel.`);
    }
  }

  async function handleGenerateLinkCode() {
    const email = sessionEmail?.trim();
    if (!email) {
      setLinkMessage("Please sign in first to connect Telegram.");
      return;
    }
    try {
      setLinkLoading(true);
      setLinkMessage(null);
      setMeError(null);
      const { code, expires_at } = await generateLinkCode(email);
      setLinkCode(code);
      setLinkExpiresAt(expires_at ?? null);
      setLinkMessage(expires_at
        ? `Code valid until ${new Date(expires_at).toLocaleTimeString()}`
        : null);
    } catch (e: any) {
      setLinkMessage(e?.message ?? "Failed to generate link code");
    } finally {
      setLinkLoading(false);
    }
  }

  async function handleCheckLinked() {
    if (!sessionEmail) return;
    try {
      setCheckingLinked(true);
      setMeError(null);
      const me = await fetchMe(sessionEmail);
      setTelegramLinked(!!me?.telegram_chat_id);
      if (me?.telegram_chat_id) {
        setLinkCode(null);
        setLinkExpiresAt(null);
        setLinkMessage(null);
      }
    } catch (e: unknown) {
      setMeError(e instanceof Error ? e.message : "Could not reach backend");
    } finally {
      setCheckingLinked(false);
    }
  }

  async function handleToggleAlert(alert: Alert) {
    if (!sessionEmail) return;
    try {
      setAlertActionError(null);
      const updated = await updateAlert(sessionEmail, alert.id, { is_active: !alert.is_active });
      setAlerts(prev => prev.map(a => a.id === updated.id ? updated : a));
    } catch (e) {
      setAlertActionError(e instanceof Error ? e.message : "Failed to update alert.");
    }
  }

  // ── Shared styles ──────────────────────────────────────────────────────
  const monoSm: React.CSSProperties = { fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase" as const, letterSpacing: "0.1em" };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>

      {/* ── Nav ──────────────────────────────────────────────────────── */}
      <nav className="dash-nav" style={{
        position: "sticky", top: 0, zIndex: 100,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: 64, padding: "0 40px",
        background: "rgba(11,11,11,0.92)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--border)",
      }}>
        {/* Logo */}
        <Link href="/" style={{ textDecoration: "none" }}>
          <HouseLogo size={28} />
        </Link>

        {/* Tab buttons — mid nav */}
        <div className="dash-nav-tabs" style={{ display: "flex", gap: 0, overflowX: "auto", WebkitOverflowScrolling: "touch" as any }}>
          {[
            ["listings", "Listings"],
            ["valuation", "Valuation"],
            ["videos", "Videos"],
            ["reno", "Reno ROI"],
            ["tour", "Virtual Tour"],
          ].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              style={{
                padding: "0 20px",
                height: 64,
                fontFamily: "var(--mono)",
                fontSize: "0.65rem",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                background: "transparent",
                border: "none",
                borderBottom: `2px solid ${activeTab === id ? "var(--accent)" : "transparent"}`,
                color: activeTab === id ? "var(--accent)" : "var(--text-dim)",
                cursor: "pointer",
                transition: "color 0.2s, border-color 0.2s",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Auth + Back */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }} suppressHydrationWarning>
          {mounted && (
            sessionEmail ? (
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ ...monoSm, color: "var(--text-dim)" }}>
                  {sessionEmail.split("@")[0]}
                </span>
                <button onClick={handleSignOut} style={{ ...monoSm, background: "transparent", border: "none", color: "var(--accent)", cursor: "pointer" }}>
                  Sign out
                </button>
              </div>
            ) : null
          )}
          <Link href="/" style={{
            padding: "8px 16px",
            background: "var(--accent)",
            color: "#000",
            fontFamily: "var(--mono)",
            fontSize: "0.62rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            textDecoration: "none",
            fontWeight: 700,
          }}>
            ← Home
          </Link>
        </div>
      </nav>

      {/* ── Filter bar (listings tab only) ────────────────────────────── */}
      {activeTab === "listings" && (
        <div className="filter-bar" style={{
          position: "sticky", top: 64, zIndex: 90,
          background: "rgba(11,11,11,0.9)",
          backdropFilter: "blur(16px)",
          borderBottom: "1px solid var(--border)",
          padding: "10px 24px",
          display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
        }}>
          <DropdownSelect
            options={CITIES}
            value={filters.city}
            onChange={city => setFilters({ ...filters, city })}
            placeholder="All GTA"
          />
          <input
            type="number"
            placeholder="Min Price"
            value={filters.minPrice}
            onChange={e => setFilters({ ...filters, minPrice: e.target.value })}
            style={{ border: "1px solid var(--border)", background: "transparent", padding: "6px 10px", fontFamily: "var(--mono)", fontSize: "0.78rem", color: "var(--text)", width: 120, outline: "none" }}
          />
          <input
            type="number"
            placeholder="Max Price"
            value={filters.maxPrice}
            onChange={e => setFilters({ ...filters, maxPrice: e.target.value })}
            style={{ border: "1px solid var(--border)", background: "transparent", padding: "6px 10px", fontFamily: "var(--mono)", fontSize: "0.78rem", color: "var(--text)", width: 120, outline: "none" }}
          />
          <DropdownSelect
            options={BED_OPTIONS}
            value={filters.bedrooms}
            onChange={bedrooms => setFilters({ ...filters, bedrooms })}
            placeholder="Any Beds"
          />
          <DropdownSelect
            options={BATH_OPTIONS}
            value={filters.bathrooms}
            onChange={bathrooms => setFilters({ ...filters, bathrooms })}
            placeholder="Any Baths"
          />
          <DropdownSelect
            options={PROPERTY_TYPES}
            value={filters.propertyType}
            onChange={propertyType => setFilters({ ...filters, propertyType })}
            placeholder="Any type"
          />
          <button
            onClick={loadListings}
            style={{ padding: "7px 18px", background: "var(--accent)", color: "#000", fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.08em", border: "none", cursor: "pointer", fontWeight: 700 }}
          >
            Search
          </button>
          <button
            onClick={() => void triggerScan()}
            disabled={scanLoading}
            style={{ padding: "7px 14px", background: "transparent", border: "1px solid var(--border-strong)", color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.08em", cursor: "pointer", opacity: scanLoading ? 0.5 : 1 }}
          >
            {scanLoading ? "Scanning..." : "↻ Refresh"}
          </button>
          {scanMessage && <span style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-dim)" }}>{scanMessage}</span>}
          <span style={{ marginLeft: "auto", fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-dim)" }}>
            {totalListings.toLocaleString()} listings
          </span>
        </div>
      )}

      {/* ── Main content ──────────────────────────────────────────────── */}
      <main>

        {/* ── LISTINGS TAB ──────────────────────────────────────────── */}
        {activeTab === "listings" && (
          <>
            {/* My alerts + Telegram card */}
            <div style={{ borderBottom: "1px solid var(--border)", padding: "20px 40px", background: "var(--bg-panel)" }}>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: 24 }}>

                {/* Alerts section */}
                <div style={{ flex: "1 1 400px" }}>
                  <div style={{ fontFamily: "var(--serif)", fontSize: "1.1rem", fontWeight: 500, marginBottom: 4 }}>My Alerts</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-dim)", marginBottom: 16 }}>
                    Alerts power email + Telegram notifications.
                  </div>

                  {sessionEmail ? (
                    <>
                      {/* Alert form */}
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                        <DropdownSelect
                          options={CITIES}
                          value={alertForm.city}
                          onChange={city => setAlertForm({ ...alertForm, city })}
                          placeholder="All GTA"
                          className="[&_button]:px-2 [&_button]:py-1.5 [&_button]:text-[0.78rem]"
                        />
                        <input
                          type="number" placeholder="Min beds" value={alertForm.minBeds}
                          onChange={e => setAlertForm({ ...alertForm, minBeds: e.target.value })}
                          style={{ border: "1px solid var(--border)", background: "transparent", padding: "5px 8px", fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text)", width: 90, outline: "none" }}
                        />
                        <input
                          type="number" placeholder="Min $" value={alertForm.minPrice}
                          onChange={e => setAlertForm({ ...alertForm, minPrice: e.target.value })}
                          style={{ border: "1px solid var(--border)", background: "transparent", padding: "5px 8px", fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text)", width: 90, outline: "none" }}
                        />
                        <input
                          type="number" placeholder="Max $" value={alertForm.maxPrice}
                          onChange={e => setAlertForm({ ...alertForm, maxPrice: e.target.value })}
                          style={{ border: "1px solid var(--border)", background: "transparent", padding: "5px 8px", fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text)", width: 90, outline: "none" }}
                        />
                        <button
                          onClick={handleCreateAlert}
                          style={{ padding: "5px 14px", background: "var(--accent)", color: "#000", fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.08em", border: "none", cursor: "pointer", fontWeight: 700 }}
                        >
                          + Save
                        </button>
                      </div>

                      {(alertsError || alertActionError) && (
                        <div style={{ marginBottom: 8 }}>
                          <ErrorBanner
                            message={(alertsError || alertActionError)!}
                            onDismiss={() => { setAlertsError(null); setAlertActionError(null); }}
                          />
                        </div>
                      )}

                      {alertsLoading ? (
                        <span style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text-dim)" }}>Loading alerts...</span>
                      ) : alerts.length === 0 ? (
                        <span style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text-dim)" }}>No alerts yet.</span>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {alerts.map(a => (
                            <div key={a.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, border: "1px solid var(--border)", padding: "8px 12px" }}>
                              <div>
                                <span style={{ fontFamily: "var(--sans)", fontSize: "0.82rem", color: "var(--text)", fontWeight: 600 }}>
                                  {(a.cities?.join(", ")) || "GTA"}
                                  {(a.property_types?.length) ? ` · ${a.property_types.join(", ")}` : ""}
                                </span>
                                <span style={{ fontFamily: "var(--mono)", fontSize: "0.64rem", color: "var(--text-dim)", marginLeft: 10 }}>
                                  {a.min_price ? `$${a.min_price.toLocaleString()}` : "Any"} – {a.max_price ? `$${a.max_price.toLocaleString()}` : "Any"} · {a.min_beds ? `${a.min_beds}+ beds` : "Any beds"}
                                </span>
                              </div>
                              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                                <button
                                  onClick={() => handleToggleAlert(a)}
                                  style={{
                                    padding: "3px 8px",
                                    fontFamily: "var(--mono)", fontSize: "0.6rem",
                                    textTransform: "uppercase", letterSpacing: "0.08em",
                                    border: "none", cursor: "pointer",
                                    background: a.is_active ? "rgba(46,213,115,0.15)" : "rgba(255,255,255,0.06)",
                                    color: a.is_active ? "#2ed573" : "var(--text-dim)",
                                  }}
                                >
                                  {a.is_active ? "On" : "Off"}
                                </button>
                                <button
                                  onClick={() => handleDeleteAlert(a)}
                                  style={{ padding: "3px 8px", fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.08em", border: "1px solid rgba(231,76,60,0.5)", color: "#e74c3c", background: "transparent", cursor: "pointer" }}
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    // Sign in form
                    <div style={{ maxWidth: 340 }}>
                      <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 8 }}>Sign in to manage alerts</div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <input
                          type="email"
                          value={emailInput}
                          onChange={e => setEmailInput(e.target.value)}
                          placeholder="you@example.com"
                          style={{ flex: 1, border: "1px solid var(--border)", background: "transparent", padding: "8px 10px", fontFamily: "var(--mono)", fontSize: "0.78rem", color: "var(--text)", outline: "none" }}
                        />
                        <button
                          onClick={handleAuthSubmit}
                          style={{ padding: "8px 16px", background: "var(--accent)", color: "#000", fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.1em", border: "none", cursor: "pointer", fontWeight: 700 }}
                        >
                          Send link
                        </button>
                      </div>
                      {authMessage && (
                        <p style={{ marginTop: 8, fontFamily: "var(--mono)", fontSize: "0.65rem", color: authMessage.includes("Too many") ? "#e4a84a" : "var(--text-dim)" }}>
                          {authMessage}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Telegram connect */}
                {sessionEmail && (
                  <div style={{ flex: "0 0 260px" }}>
                    <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--accent)", marginBottom: 10 }}>
                      ✈️ Telegram Alerts
                    </div>
                    {telegramLinked ? (
                      <div style={{ border: "1px solid var(--border-strong)", padding: "12px 16px", background: "rgba(212,175,55,0.04)" }}>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--accent)" }}>✓ Connected</div>
                        <div style={{ fontFamily: "var(--sans)", fontSize: "0.75rem", color: "var(--text-mute)", marginTop: 4 }}>
                          You&apos;ll receive matching alerts in Telegram DMs.
                        </div>
                      </div>
                    ) : linkCode ? (
                      <div style={{ border: "1px solid var(--border)", padding: "14px" }}>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", color: "var(--text-dim)", marginBottom: 8 }}>
                          Open @{TELEGRAM_BOT} and send:
                        </div>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "1rem", fontWeight: 700, color: "var(--accent)", letterSpacing: "0.1em", marginBottom: 10 }}>
                          /link {linkCode}
                        </div>
                        {linkMessage && <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", color: "var(--text-dim)", marginBottom: 10 }}>{linkMessage}</div>}
                        <a href={`https://t.me/${TELEGRAM_BOT}`} target="_blank" rel="noreferrer" style={{ display: "inline-block", marginBottom: 10, fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--accent)", textDecoration: "none", border: "1px solid var(--border-strong)", padding: "5px 10px" }}>
                          Open Telegram →
                        </a>
                        <br />
                        <button
                          onClick={handleCheckLinked}
                          disabled={checkingLinked}
                          style={{ marginTop: 4, fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-mute)", background: "transparent", border: "1px solid var(--border)", padding: "5px 10px", cursor: "pointer" }}
                        >
                          {checkingLinked ? "Checking..." : "I linked it — verify"}
                        </button>
                      </div>
                    ) : (
                      <div>
                        <button
                          onClick={handleGenerateLinkCode}
                          disabled={linkLoading}
                          style={{ padding: "9px 18px", background: "transparent", border: "1px solid var(--border-strong)", color: "var(--accent)", fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.1em", cursor: "pointer", display: "block", width: "100%" }}
                        >
                          {linkLoading ? "Generating..." : "Connect Telegram →"}
                        </button>
                        {(linkMessage || meError) && !linkCode && (
                          <p style={{ marginTop: 6, fontFamily: "var(--mono)", fontSize: "0.62rem", color: "#e4a84a" }}>
                            {meError ?? linkMessage}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Errors */}
            {listingsError && (
              <div style={{ padding: "0 40px" }}>
                <ErrorBanner message={listingsError} onDismiss={() => setListingsError(null)} />
              </div>
            )}

            {/* ── Split view: List | Map ───────────────────────────── */}
            <div
              className="split-view"
              style={{ display: "grid", gridTemplateColumns: "440px 1fr", minHeight: 640 }}
            >
              {/* List column */}
              <div className="list-col" style={{ overflowY: "auto", borderRight: "1px solid var(--border)", maxHeight: "calc(100vh - 180px)", display: "flex", flexDirection: "column" }}>
                {/* Market insights bar */}
                {!loading && listings.length > 0 && (
                  <MarketInsightsBar listings={listings} total={totalListings} />
                )}
                {loading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", gap: 12 }}>
                      <div style={{ width: 56, height: 56, background: "linear-gradient(90deg,#1a1a14 25%,#222218 50%,#1a1a14 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.4s infinite", flexShrink: 0 }} />
                      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                        {[70, 50, 40].map(w => (
                          <div key={w} style={{ height: 12, width: `${w}%`, background: "linear-gradient(90deg,#1a1a14 25%,#222218 50%,#1a1a14 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.4s infinite" }} />
                        ))}
                      </div>
                    </div>
                  ))
                ) : listings.length === 0 ? (
                  <div style={{ padding: "60px 24px", textAlign: "center" }}>
                    <div style={{ fontSize: "2rem", color: "var(--border)", marginBottom: 12 }}>◎</div>
                    <div style={{ fontFamily: "var(--serif)", fontSize: "1.1rem", color: "var(--text-mute)" }}>No listings match your filters</div>
                    <div style={{ fontFamily: "var(--sans)", fontSize: "0.82rem", color: "var(--text-dim)", marginTop: 6 }}>Try a broader area or price range</div>
                  </div>
                ) : (
                  listings.map(l => (
                    <ListRow
                      key={l.id}
                      listing={l}
                      active={l.id === selectedId}
                      onClick={() => setSelectedId(l.id === selectedId ? null : l.id)}
                      onValuate={() => {
                        setValuationForm({
                          neighbourhood: "",
                          city: l.city || "Toronto",
                          bedrooms: l.beds > 0 ? String(l.beds) : "",
                          bathrooms: l.baths > 0 ? String(l.baths) : "",
                          sqft: l.sqft > 0 ? String(l.sqft) : "",
                          list_price: l.price > 0 ? String(l.price) : "",
                        });
                        setValuationResult(null);
                        setValuationError(null);
                        setActiveTab("valuation");
                      }}
                    />
                  ))
                )}
              </div>

              {/* Map column */}
              <div className="map-col" style={{ position: "relative", height: "calc(100vh - 180px)" }}>
                <GTAMap
                  listings={listings}
                  selectedId={selectedId}
                  onSelect={id => setSelectedId(id === selectedId ? null : id)}
                />
              </div>
            </div>

            {/* Pagination */}
            {!loading && totalListings > LISTINGS_PAGE_SIZE && (
              <div style={{ padding: "24px 40px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "center", gap: 20 }}>
                <button
                  disabled={listingsPage <= 0}
                  onClick={() => setListingsPage(p => Math.max(0, p - 1))}
                  className="btn-ghost"
                  style={{ opacity: listingsPage <= 0 ? 0.4 : 1, cursor: listingsPage <= 0 ? "not-allowed" : "pointer", padding: "8px 20px" }}
                >
                  ← Previous
                </button>
                <span style={{ fontFamily: "var(--mono)", fontSize: "0.7rem", color: "var(--text-mute)" }}>
                  Page {listingsPage + 1} / {Math.max(1, Math.ceil(totalListings / LISTINGS_PAGE_SIZE))}
                </span>
                <button
                  disabled={(listingsPage + 1) * LISTINGS_PAGE_SIZE >= totalListings}
                  onClick={() => setListingsPage(p => p + 1)}
                  className="btn-ghost"
                  style={{ opacity: (listingsPage + 1) * LISTINGS_PAGE_SIZE >= totalListings ? 0.4 : 1, cursor: (listingsPage + 1) * LISTINGS_PAGE_SIZE >= totalListings ? "not-allowed" : "pointer", padding: "8px 20px" }}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}

        {/* ── VALUATION TAB ─────────────────────────────────────────── */}
        {activeTab === "valuation" && (
          <div style={{ maxWidth: 680, margin: "0 auto", padding: "48px 40px" }}>
            <div style={{ fontFamily: "var(--serif)", fontSize: "clamp(1.4rem,2vw,2.2rem)", fontWeight: 500, marginBottom: 8 }}>Property Valuation</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-dim)", marginBottom: 28 }}>LightGBM model trained on GTA sold comps · $600/sqft fallback when model unavailable</div>

            {/* Input grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 14 }}>
              {[
                { label: "City", key: "city", placeholder: "Toronto" },
                { label: "Neighbourhood", key: "neighbourhood", placeholder: "King West" },
                { label: "Bedrooms", key: "bedrooms", placeholder: "3" },
                { label: "Bathrooms", key: "bathrooms", placeholder: "2" },
                { label: "Sq Ft", key: "sqft", placeholder: "1200" },
                { label: "List Price", key: "list_price", placeholder: "750000" },
              ].map(({ label, key, placeholder }) => (
                <div key={key}>
                  <label style={{ display: "block", fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 6 }}>{label}</label>
                  <input
                    type="text"
                    placeholder={placeholder}
                    value={valuationForm[key as keyof typeof valuationForm]}
                    onChange={e => setValuationForm(f => ({ ...f, [key]: e.target.value }))}
                    style={{ width: "100%", border: "1px solid var(--border)", background: "transparent", padding: "9px 12px", fontFamily: "var(--mono)", fontSize: "0.8rem", color: "var(--text)", outline: "none" }}
                  />
                </div>
              ))}
            </div>

            {/* Property condition slider */}
            <div style={{ marginTop: 20 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 10 }}>Property Condition</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0, border: "1px solid var(--border)", overflow: "hidden" }}>
                {(["poor","fair","good","excellent"] as const).map((c, i) => {
                  const labels = { poor: "Poor\n−18%", fair: "Fair\n−8%", good: "Good\n±0%", excellent: "Excellent\n+12%" };
                  const active = valuationCondition === c;
                  return (
                    <button key={c} onClick={() => setValuationCondition(c)} style={{
                      padding: "10px 8px", background: active ? "rgba(255,191,0,0.1)" : "transparent",
                      border: "none", borderRight: i < 3 ? "1px solid var(--border)" : "none",
                      borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
                      cursor: "pointer", textAlign: "center",
                    }}>
                      <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.06em", color: active ? "var(--accent)" : "var(--text-mute)", fontWeight: active ? 700 : 400 }}>{c}</div>
                      <div style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", color: active ? "var(--accent)" : "var(--text-dim)", marginTop: 3 }}>{labels[c].split("\n")[1]}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            <button
              disabled={valuationLoading}
              className="btn-primary"
              style={{ marginTop: 20, width: "100%", textAlign: "center", opacity: valuationLoading ? 0.6 : 1 }}
              onClick={async () => {
                setValuationLoading(true);
                setValuationError(null);
                setValuationResult(null);
                try {
                  const result = await fetchValuation({
                    neighbourhood: valuationForm.neighbourhood,
                    property_type: "",
                    city: valuationForm.city,
                    bedrooms: Number(valuationForm.bedrooms) || 0,
                    bathrooms: Number(valuationForm.bathrooms) || 0,
                    sqft: Number(valuationForm.sqft) || 0,
                    list_price: Number(valuationForm.list_price) || 0,
                  });
                  setValuationResult(result);
                } catch {
                  setValuationError("Valuation failed — check API connection.");
                } finally {
                  setValuationLoading(false);
                }
              }}
            >
              {valuationLoading ? "Estimating..." : "Get Valuation"}
            </button>

            {valuationError && (
              <p style={{ marginTop: 16, fontFamily: "var(--mono)", fontSize: "0.78rem", color: "#e74c3c" }}>{valuationError}</p>
            )}

            {valuationResult && (() => {
              const condMult  = CONDITION_MULT[valuationCondition] ?? 1;
              const baseVal   = valuationResult.estimated_value;
              const adjVal    = Math.round(baseVal * condMult);
              const rangeLow  = Math.round(adjVal * 0.92);
              const rangeHigh = Math.round(adjVal * 1.08);
              const conf      = valuationResult.confidence;
              const confLabel = conf >= 0.82 ? "High" : conf >= 0.72 ? "Medium" : "Low";
              const confColor = conf >= 0.82 ? "#2ed573" : conf >= 0.72 ? "#ffa502" : "#cf6357";
              const listPrice = Number(valuationForm.list_price) || 0;
              const delta     = listPrice > 0 ? ((adjVal - listPrice) / listPrice) * 100 : null;
              return (
                <div style={{ marginTop: 24, border: "1px solid var(--border)", overflow: "hidden" }}>
                  {/* Header */}
                  <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", background: "var(--bg-elev)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text-dim)", marginBottom: 6 }}>
                          Estimated Value · {valuationCondition.charAt(0).toUpperCase() + valuationCondition.slice(1)} condition
                        </div>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "2.6rem", fontWeight: 700, color: "var(--accent)", lineHeight: 1 }}>
                          ${adjVal.toLocaleString("en-CA")}
                        </div>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-dim)", marginTop: 6 }}>
                          Range: ${rangeLow.toLocaleString("en-CA")} – ${rangeHigh.toLocaleString("en-CA")}
                        </div>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
                        {/* Confidence badge */}
                        <span style={{ border: `1px solid ${confColor}`, padding: "4px 10px", fontFamily: "var(--mono)", fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.12em", color: confColor }}>
                          {confLabel} confidence · {Math.round(conf * 100)}%
                        </span>
                        {/* Vs list price */}
                        {delta != null && (
                          <span style={{ border: "1px solid var(--border)", padding: "4px 10px", fontFamily: "var(--mono)", fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.12em", color: delta > 3 ? "#2ed573" : delta < -3 ? "#cf6357" : "var(--text-mute)" }}>
                            {delta > 0 ? "↑" : "↓"} {Math.abs(delta).toFixed(1)}% vs list
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {/* Details row */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)" }}>
                    {[
                      { label: "$/sqft", value: valuationResult.price_per_sqft ? `$${Math.round(valuationResult.price_per_sqft * condMult).toLocaleString()}` : "—" },
                      { label: "Condition adj.", value: condMult !== 1 ? `${condMult > 1 ? "+" : ""}${Math.round((condMult - 1) * 100)}%` : "None (Good)" },
                      { label: "Analysis", value: valuationResult.market_analysis.slice(0, 28) + "…" },
                    ].map(({ label, value }, i) => (
                      <div key={label} style={{ padding: "14px 20px", borderRight: i < 2 ? "1px solid var(--border)" : "none" }}>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "0.54rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 4 }}>{label}</div>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "0.8rem", color: "var(--text)" }}>{value}</div>
                      </div>
                    ))}
                  </div>
                  {/* Full analysis */}
                  <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text-mute)", lineHeight: 1.6 }}>
                    {valuationResult.market_analysis}
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* ── VIDEOS TAB ────────────────────────────────────────────── */}
        {activeTab === "videos" && (
          <div style={{ padding: "80px 40px", textAlign: "center", maxWidth: 640, margin: "0 auto" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 20 }}>
              Professional listing videos · GTA agents
            </div>
            <h2 style={{ fontFamily: "var(--serif)", fontSize: "clamp(2rem, 3vw, 3.2rem)", fontWeight: 500, marginBottom: 20 }}>
              Turn any listing into a{" "}
              <em style={{ color: "var(--accent)", fontStyle: "italic" }}>cinematic video</em>
            </h2>
            <p style={{ fontFamily: "var(--sans)", fontSize: "0.9rem", color: "var(--text-mute)", lineHeight: 1.7, marginBottom: 40, maxWidth: "44ch", margin: "0 auto 40px" }}>
              Paste a Realtor.ca or Zillow URL. We write the script, record the voiceover,
              and add music — your polished 30-second video is ready in under 15 minutes.
            </p>
            <Link href="/video" className="btn-primary" style={{ textDecoration: "none", display: "inline-block" }}>
              Order a Video — from $99
            </Link>
          </div>
        )}
        {/* ── RENO ROI TAB ───────────────────────────────────────── */}
        {activeTab === "reno" && (
          <div style={{ maxWidth: 960, margin: "0 auto", padding: "48px 40px" }}>
            <div style={{ fontFamily: "var(--serif)", fontSize: "clamp(1.4rem,2vw,2.2rem)", fontWeight: 500, marginBottom: 8 }}>Renovation ROI Calculator</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-dim)", marginBottom: 32 }}>GTA market averages · select a renovation type, enter your numbers</div>

            {/* Reno type grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 8, marginBottom: 28 }}>
              {DASH_RENO_TYPES.map(rt => (
                <button key={rt.id} onClick={() => setRenoSelectedId(rt.id)} style={{
                  padding: "12px 14px", textAlign: "left", cursor: "pointer",
                  background: renoSelectedId === rt.id ? "rgba(255,191,0,0.08)" : "transparent",
                  border: `1px solid ${renoSelectedId === rt.id ? "var(--accent)" : "var(--border)"}`,
                  color: renoSelectedId === rt.id ? "var(--accent)" : "var(--text)",
                  fontFamily: "var(--mono)", fontSize: "0.68rem", transition: "all 0.15s",
                }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{rt.label}</div>
                  <div style={{ fontSize: "0.58rem", color: "var(--text-dim)" }}>ROI: {rt.roiRange} · {rt.typical}</div>
                </button>
              ))}
            </div>

            {/* Inputs */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
              {[
                { label: "Current home value ($)", val: renoHomeValue, set: setRenoHomeValue, placeholder: "850000" },
                { label: "Renovation budget ($)", val: renoBudget, set: setRenoBudget, placeholder: "40000" },
              ].map(({ label, val, set, placeholder }) => (
                <div key={label}>
                  <label style={{ display: "block", fontFamily: "var(--mono)", fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 6 }}>{label}</label>
                  <input type="number" placeholder={placeholder} value={val} onChange={e => set(e.target.value)}
                    style={{ width: "100%", border: "1px solid var(--border)", background: "transparent", padding: "9px 12px", fontFamily: "var(--mono)", fontSize: "0.8rem", color: "var(--text)", outline: "none" }} />
                </div>
              ))}
            </div>

            <button
              className="btn-primary"
              style={{ marginBottom: 28 }}
              onClick={() => {
                const hv = Number(renoHomeValue.replace(/,/g, ""));
                const b  = Number(renoBudget.replace(/,/g, ""));
                if (!hv || !b) return;
                const rt = DASH_RENO_TYPES.find(r => r.id === renoSelectedId)!;
                const addedValue = Math.round(b * rt.roi);
                const roiDollars = addedValue - b;
                const roiPct     = ((addedValue - b) / b) * 100;
                setRenoResult({ roiPct, addedValue, newValue: hv + addedValue, roiDollars, risk: rt.risk, roiRange: rt.roiRange, timeMonths: rt.timeMonths, typical: rt.typical });
              }}
            >
              Calculate ROI
            </button>

            {renoResult && (
              <div style={{ border: "1px solid var(--border-strong)", background: "var(--bg-elev)", overflow: "hidden" }}>
                <div style={{ padding: "20px 28px", borderBottom: "1px solid var(--border)", background: "rgba(255,191,0,0.04)" }}>
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.56rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 6 }}>
                    ROI Analysis · {DASH_RENO_TYPES.find(r => r.id === renoSelectedId)?.label}
                  </div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                    <span style={{ fontFamily: "var(--mono)", fontSize: "2.8rem", fontWeight: 700, color: renoResult.roiDollars >= 0 ? "var(--accent)" : "#cf6357", lineHeight: 1 }}>
                      {renoResult.roiPct >= 0 ? "+" : ""}{renoResult.roiPct.toFixed(1)}%
                    </span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: "0.72rem", color: "var(--text-mute)" }}>return on renovation spend</span>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
                  {[
                    { label: "Renovation Budget",   value: `$${Number(renoBudget).toLocaleString()}`,            color: "var(--text)" },
                    { label: "Value Added",          value: `$${renoResult.addedValue.toLocaleString()}`,          color: renoResult.roiDollars >= 0 ? "#2ed573" : "#cf6357" },
                    { label: "Current Home Value",   value: `$${Number(renoHomeValue).toLocaleString()}`,          color: "var(--text)" },
                    { label: "Est. Post-Reno Value", value: `$${renoResult.newValue.toLocaleString()}`,            color: "var(--accent)" },
                    { label: "Net Gain / Loss",      value: `${renoResult.roiDollars >= 0 ? "+" : ""}$${renoResult.roiDollars.toLocaleString()}`, color: renoResult.roiDollars >= 0 ? "#2ed573" : "#cf6357" },
                    { label: "GTA ROI Range",        value: renoResult.roiRange,                                   color: "var(--text-mute)" },
                  ].map(({ label, value, color }, i) => (
                    <div key={label} style={{ padding: "16px 24px", borderBottom: i < 4 ? "1px solid var(--border)" : "none", borderRight: i % 2 === 0 ? "1px solid var(--border)" : "none" }}>
                      <div style={{ fontFamily: "var(--mono)", fontSize: "0.54rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 4 }}>{label}</div>
                      <div style={{ fontFamily: "var(--mono)", fontSize: "1rem", fontWeight: 600, color }}>{value}</div>
                    </div>
                  ))}
                </div>
                <div style={{ padding: "14px 28px", borderTop: "1px solid var(--border)", display: "flex", gap: 24, flexWrap: "wrap" }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: DASH_RISK_COLORS[renoResult.risk] ?? "var(--text)" }}>Risk: {renoResult.risk}</span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-mute)" }}>Typical: {renoResult.typical}</span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", color: "var(--text-mute)" }}>Timeline: ~{renoResult.timeMonths} months</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── VIRTUAL TOUR TAB ────────────────────────────────────── */}
        {activeTab === "tour" && (
          <div style={{ maxWidth: 600, margin: "0 auto", padding: "80px 40px", textAlign: "center" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: "0.62rem", letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 16 }}>◆ Virtual Tours</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: "1.5rem", fontWeight: 700, marginBottom: 16 }}>Order on the dedicated tours page.</div>
            <p style={{ fontFamily: "var(--mono)", fontSize: "0.78rem", lineHeight: 1.7, color: "var(--text-mute)", maxWidth: "42ch", margin: "0 auto 32px" }}>
              Paste a listing URL or upload photos. Your tour is generated and hosted in under 5 minutes.
            </p>
            <Link href="/tours" style={{
              display: "inline-block", padding: "14px 32px",
              background: "var(--accent)", color: "var(--bg)",
              fontFamily: "var(--mono)", fontSize: "0.82rem", fontWeight: 700,
              letterSpacing: "0.08em", textTransform: "uppercase", textDecoration: "none",
            }}>
              Order a tour — $49 →
            </Link>
          </div>
        )}
      </main>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "24px 40px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <HouseLogo size={24} />
        <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
          © 2026 416Homes · Toronto Real Estate Intelligence
        </div>
      </footer>
    </div>
  );
}
