"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Listing } from "@/types";
import { fetchListings, fetchValuation } from "@/lib/api";
import { getSession, signInWithEmail, signOut } from "@/lib/supabase";
import { Alert, fetchAlerts, createAlert, updateAlert, deleteAlert, generateLinkCode, fetchMe } from "@/lib/alerts";
import { DropdownSelect } from "@/components/DropdownSelect";
import { ErrorBanner } from "@/components/ui/error-banner";
import { ListingCard, ListingCardSkeleton, ListRow } from "@/components/listing-card";

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

/* ── GTA Map component ──────────────────────────────────────────────── */
function GTAMap({ listings, selectedId, onSelect }: {
  listings: Listing[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const hasLocations = listings.some(l => l.lat !== undefined && l.lng !== undefined);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", overflow: "hidden" }}>
      {/* OpenStreetMap embed — GTA area */}
      <iframe
        src="https://www.openstreetmap.org/export/embed.html?bbox=-80.05%2C43.40%2C-78.85%2C44.10&layer=mapnik"
        style={{
          width: "100%",
          height: "100%",
          border: "none",
          filter: "brightness(0.78) saturate(0.65) hue-rotate(10deg)",
        }}
        title="Greater Toronto Area Map"
      />

      {/* Dark overlay for legibility */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to bottom, rgba(11,11,11,0.15), rgba(11,11,11,0.05))",
        pointerEvents: "none",
      }} />

      {/* Status pill */}
      <div style={{
        position: "absolute",
        bottom: 16,
        left: "50%",
        transform: "translateX(-50%)",
        background: "rgba(11,11,11,0.88)",
        backdropFilter: "blur(8px)",
        border: "1px solid var(--border)",
        padding: "8px 16px",
        fontFamily: "var(--mono)",
        fontSize: "0.58rem",
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        color: "var(--text-mute)",
        whiteSpace: "nowrap",
      }}>
        {hasLocations
          ? `◆ ${listings.filter(l => l.lat !== undefined).length} pins · click to focus`
          : "◆ GTA · Toronto & Mississauga · Pins appear when location data is available"}
      </div>

      {/* Selected listing callout */}
      {selectedId && (() => {
        const sel = listings.find(l => l.id === selectedId);
        if (!sel) return null;
        return (
          <div style={{
            position: "absolute", top: 16, left: 16, right: 16,
            background: "rgba(11,11,11,0.92)",
            backdropFilter: "blur(12px)",
            border: "1px solid var(--border-strong)",
            padding: "12px 16px",
          }}>
            <div style={{ fontFamily: "var(--serif)", fontSize: "1.1rem", fontWeight: 500, color: "var(--text)" }}>
              ${sel.price.toLocaleString()}
            </div>
            <div style={{ fontFamily: "var(--sans)", fontSize: "0.75rem", color: "var(--text-mute)", marginTop: 2 }}>
              {sel.address}
            </div>
            <a href={sel.url} target="_blank" rel="noreferrer" style={{
              display: "inline-block", marginTop: 8,
              fontFamily: "var(--mono)", fontSize: "0.58rem", textTransform: "uppercase",
              letterSpacing: "0.1em", color: "var(--accent)", textDecoration: "none",
            }}>
              View listing →
            </a>
          </div>
        );
      })()}
    </div>
  );
}

/* ── Main page ──────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [emailInput, setEmailInput] = useState("");
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"listings" | "valuation" | "videos">("listings");
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    city: "GTA",
    minPrice: "",
    maxPrice: "",
    bedrooms: "",
    bathrooms: "",
    propertyType: "",
  });
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
  const [valuationResult, setValuationResult] = useState<null | { estimated_value: number; confidence: number; price_per_sqft?: number; market_analysis: string }>(null);
  const [valuationLoading, setValuationLoading] = useState(false);
  const [valuationError, setValuationError] = useState<string | null>(null);

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
      <nav style={{
        position: "sticky", top: 0, zIndex: 100,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: 64, padding: "0 40px",
        background: "rgba(11,11,11,0.92)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--border)",
      }}>
        {/* Logo */}
        <div style={{ fontFamily: "var(--serif)", fontSize: "1.4rem", fontWeight: 500 }}>
          <span style={{ color: "var(--accent)" }}>416</span>
          <span style={{ color: "var(--text-mute)" }}>homes</span>
          <span style={{ fontFamily: "var(--mono)", fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text-dim)", marginLeft: 8 }}>Dashboard</span>
        </div>

        {/* Tab buttons — mid nav */}
        <div style={{ display: "flex", gap: 0 }}>
          {[
            ["listings", "Listings"],
            ["valuation", "Valuation"],
            ["videos", "Videos"],
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
        <div style={{
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
              <div style={{ overflowY: "auto", borderRight: "1px solid var(--border)", maxHeight: "calc(100vh - 180px)" }}>
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
              <div className="map-col" style={{ position: "relative" }}>
                <GTAMap
                  listings={listings}
                  selectedId={selectedId}
                  onSelect={(id) => setSelectedId(id)}
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
          <div style={{ maxWidth: 640, margin: "0 auto", padding: "48px 40px" }}>
            <div style={{ fontFamily: "var(--serif)", fontSize: "clamp(1.4rem,2vw,2.2rem)", fontWeight: 500, marginBottom: 32 }}>Property Valuation</div>
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

            <button
              disabled={valuationLoading}
              className="btn-primary"
              style={{ marginTop: 24, width: "100%", textAlign: "center", opacity: valuationLoading ? 0.6 : 1 }}
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

            {valuationResult && (
              <div style={{ marginTop: 28, border: "1px solid var(--border)", padding: 24 }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginBottom: 6 }}>Estimated Value</div>
                <div style={{ fontFamily: "var(--serif)", fontSize: "2.5rem", fontWeight: 500, color: "var(--accent)" }}>
                  ${valuationResult.estimated_value.toLocaleString()}
                </div>
                {valuationResult.price_per_sqft && (
                  <div style={{ fontFamily: "var(--mono)", fontSize: "0.78rem", color: "var(--text)", marginTop: 4 }}>
                    ${Math.round(valuationResult.price_per_sqft).toLocaleString()} / sqft
                  </div>
                )}
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.75rem", color: "var(--text-mute)", marginTop: 8 }}>
                  {valuationResult.market_analysis}
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.65rem", color: "var(--text-dim)", marginTop: 6 }}>
                  Confidence: {Math.round(valuationResult.confidence * 100)}%
                </div>
              </div>
            )}
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
              Order a Video — $199
            </Link>
          </div>
        )}
      </main>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer style={{ borderTop: "1px solid var(--border)", padding: "24px 40px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div style={{ fontFamily: "var(--serif)", fontSize: "1rem", fontWeight: 500 }}>
          <span style={{ color: "var(--accent)" }}>416</span>
          <span style={{ color: "var(--text-mute)" }}>homes</span>
          <span style={{ fontFamily: "var(--mono)", fontSize: "0.5rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", marginLeft: 8 }}>Dashboard</span>
        </div>
        <div style={{ fontFamily: "var(--mono)", fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
          © 2026 416Homes · Toronto Real Estate Intelligence
        </div>
      </footer>
    </div>
  );
}
