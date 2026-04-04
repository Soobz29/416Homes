"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Listing } from "@/types";
import { fetchListings, fetchValuation } from "@/lib/api";
import { getSession, signInWithEmail, signOut } from "@/lib/supabase";
import { Alert, fetchAlerts, createAlert, updateAlert, deleteAlert, generateLinkCode, fetchMe } from "@/lib/alerts";
import { DropdownSelect } from "@/components/DropdownSelect";
import { ErrorBanner } from "@/components/ui/error-banner";

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
  const [meError, setMeError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [valuationForm, setValuationForm] = useState({
    neighbourhood: "", city: "Toronto", bedrooms: "", bathrooms: "", sqft: "", list_price: "",
  });
  const [valuationResult, setValuationResult] = useState<null | { estimated_value: number; confidence: number; price_per_sqft?: number; market_analysis: string }>(null);
  const [valuationLoading, setValuationLoading] = useState(false);
  const [valuationError, setValuationError] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    // Hydrate Supabase session on mount
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

  useEffect(() => {
    if (activeTab === "listings") {
      void loadListings();
    }
  }, [activeTab, filters]);

  async function loadListings() {
    try {
      setLoading(true);
      setListingsError(null);
      const data = await fetchListings({
        city: filters.city === "GTA" ? undefined : filters.city,
        minPrice: filters.minPrice ? Number(filters.minPrice) : undefined,
        maxPrice: filters.maxPrice ? Number(filters.maxPrice) : undefined,
        propertyTypes: filters.propertyType ? [filters.propertyType] : undefined,
      });
      setListings(data.listings || []);
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
        setAuthMessage(
          "Error sending confirmation email. Check Supabase Auth → Email (SMTP): " +
            "Resend username 'resend', password = API key, sender = verified domain or onboarding@resend.dev."
        );
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
      setAlerts((prev) => [created, ...prev]);
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
      setAlerts((prev) => prev.filter((a) => a.id !== alert.id));
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
      setMeError(msg.includes("401") || msg.includes("Missing") ? "Sign in required." : `${msg}. Set NEXT_PUBLIC_API_URL to your Railway API URL in Vercel.`);
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
      setLinkMessage(
        expires_at
          ? `Code valid for 30 minutes until ${new Date(expires_at).toLocaleTimeString()} (UTC).`
          : null,
      );
    } catch (e: any) {
      console.error("Failed to generate link code", e);
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
      console.error("Failed to check link status", e);
      setMeError(e instanceof Error ? e.message : "Could not reach backend");
    } finally {
      setCheckingLinked(false);
    }
  }

  async function handleToggleAlert(alert: Alert) {
    if (!sessionEmail) return;
    try {
      setAlertActionError(null);
      const updated = await updateAlert(sessionEmail, alert.id, {
        is_active: !alert.is_active,
      });
      setAlerts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
    } catch (e) {
      setAlertActionError(e instanceof Error ? e.message : "Failed to update alert.");
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a08] text-[#f5f4ef]">
      {/* Nav */}
      <nav className="fixed left-0 right-0 top-0 z-50 flex items-center justify-between border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.75)] px-16 py-6 backdrop-blur-xl max-md:px-6">
        <div className="logo text-[1.3rem] font-extrabold tracking-[0.05em]">
          <span className="text-[#c8a96e]">416</span>
          Homes
          <sub className="ml-1 align-middle font-['DM Mono',monospace] text-[0.6rem] font-normal tracking-[0.1em] text-[#6b6b60]">
            DASHBOARD
          </sub>
        </div>
        <ul className="nav-links hidden list-none gap-10 font-['DM Mono',monospace] text-[0.72rem] uppercase tracking-[0.1em] text-[#6b6b60] md:flex">
          <li>
            <button
              onClick={() => setActiveTab("listings")}
              className="bg-transparent text-inherit"
            >
              Properties
            </button>
          </li>
          <li>
            <button
              onClick={() => setActiveTab("valuation")}
              className="bg-transparent text-inherit"
            >
              Valuation
            </button>
          </li>
          <li>
            <button
              onClick={() => setActiveTab("videos")}
              className="bg-transparent text-inherit"
            >
              Videos
            </button>
          </li>
        </ul>
        <button className="nav-cta flex items-center gap-2 bg-[#c8a96e] px-6 py-2 font-['DM Mono',monospace] text-[0.72rem] font-medium uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e4c98a]">
          <span className="hidden md:inline">Back to 416Homes</span>
          <Link href="/" className="md:hidden">
            Home
          </Link>
        </button>
      </nav>

      {/* Hero */}
      <section className="dashboard-hero border-b border-[rgba(200,169,110,0.2)] bg-[radial-gradient(circle_at_top,rgba(200,169,110,0.14),transparent_55%)] px-16 pb-8 pt-24 max-md:px-6">
        <div className="mx-auto grid max-w-[1120px] items-center gap-8 md:grid-cols-[2fr,1.2fr]">
          <div>
            <p className="dashboard-hero-eyebrow mb-3 font-['DM Mono',monospace] text-[0.7rem] uppercase tracking-[0.18em] text-[#6b6b60]">
              Toronto · Mississauga · GTA
            </p>
            <h1 className="dashboard-hero-title mb-3 text-[clamp(2rem,3vw,2.8rem)] font-extrabold tracking-[-0.02em]">
              Your <span className="text-[#c8a96e]">GTA real estate</span> dashboard.
            </h1>
            <p className="dashboard-hero-sub max-w-xl font-['DM Mono',monospace] text-[0.8rem] leading-relaxed text-[#6b6b60]">
              Browse fresh listings across Toronto and Mississauga, run quick valuations on any address, and order
              listing videos when it&apos;s time to sell.
            </p>
            <div className="mt-6" suppressHydrationWarning>
              {!mounted ? (
                <div className="flex flex-col gap-2 rounded-xl border border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.7)] p-4 max-w-md">
                  <span className="text-[0.7rem] font-['DM Mono',monospace] uppercase tracking-[0.12em] text-[#6b6b60]">
                    Early access login
                  </span>
                  <div className="flex flex-wrap gap-2 rounded-full bg-[#6b6b60]/30 px-4 py-3 font-['DM Mono',monospace] text-[0.72rem] text-[#6b6b60]">
                    Loading…
                  </div>
                </div>
              ) : sessionEmail ? (
                <div className="inline-flex items-center gap-3 rounded-full border border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.7)] px-4 py-2">
                  <span className="font-['DM Mono',monospace] text-[0.7rem] text-[#6b6b60]">
                    Signed in as <span className="text-[#f5f4ef]">{sessionEmail}</span>
                  </span>
                  <button
                    onClick={handleSignOut}
                    className="text-[0.7rem] font-['DM Mono',monospace] uppercase tracking-[0.1em] text-[#c8a96e]"
                  >
                    Sign out
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-2 rounded-xl border border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.7)] p-4 max-w-md">
                  <span className="text-[0.7rem] font-['DM Mono',monospace] uppercase tracking-[0.12em] text-[#6b6b60]">
                    Early access login
                  </span>
                  <div className="flex flex-wrap gap-2">
                    <input
                      type="email"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      placeholder="you@example.com"
                      className="flex-1 min-w-[10rem] border border-[rgba(200,169,110,0.2)] bg-transparent px-3 py-2 font-['DM Mono',monospace] text-[0.8rem] text-[#f5f4ef] outline-none placeholder:text-[#6b6b60]"
                    />
                    <button
                      type="button"
                      onClick={handleAuthSubmit}
                      className="rounded-full bg-[#c8a96e] px-4 py-2 font-['DM Mono',monospace] text-[0.72rem] uppercase tracking-[0.12em] text-black hover:bg-[#e4c98a]"
                    >
                      Send link
                    </button>
                  </div>
                  {authMessage && (
                    <div className="mt-1">
                      <p className={`text-[0.7rem] font-['DM Mono',monospace] ${authMessage.includes("Too many") ? "text-[#e4a84a]" : "text-[#6b6b60]"}`}>
                        {authMessage}
                      </p>
                      {authMessage.includes("Too many") && (
                        <p className="mt-0.5 text-[0.65rem] font-['DM Mono',monospace] text-[#6b6b60]">
                          Wait 1–5 minutes, or try a different email address.
                        </p>
                      )}
                      {authMessage.includes("Error sending confirmation") && (
                        <p className="mt-0.5 text-[0.65rem] font-['DM Mono',monospace] text-[#6b6b60]">
                          In Resend, ensure the sender domain is verified or use onboarding@resend.dev for testing.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="dashboard-hero-metrics grid grid-cols-2 gap-3">
            <div className="dashboard-hero-metric rounded-[14px] border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-4">
              <div className="dashboard-hero-metric-label font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.11em] text-[#6b6b60]">
                Active listings
              </div>
              <div className="dashboard-hero-metric-value text-[1.35rem] font-bold text-[#c8a96e]">
                GTA‑wide
              </div>
              <p className="mt-1 text-[0.72rem] text-[#6b6b60]">
                Pulled from Realtor.ca, Zoocasa, Kijiji and more.
              </p>
            </div>
            <div className="dashboard-hero-metric rounded-[14px] border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-4">
              <div className="dashboard-hero-metric-label font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.11em] text-[#6b6b60]">
                Scan cadence
              </div>
              <div className="dashboard-hero-metric-value text-[1.35rem] font-bold text-[#c8a96e]">
                Every 30 min
              </div>
              <p className="mt-1 text-[0.72rem] text-[#6b6b60]">
                Nightly full scans plus on‑demand refreshes for hot listings.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Tab nav */}
      <div className="tab-nav sticky top-0 z-40 border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.8)] backdrop-blur-xl">
        <div className="tab-nav-inner flex justify-center px-16 max-md:px-6">
          {[
            ["listings", "Listings"],
            ["valuation", "Valuation"],
            ["videos", "Videos"],
          ].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`tab-btn border-b-2 px-6 py-5 font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.1em] transition-colors ${
                activeTab === id ? "border-[#c8a96e] text-[#c8a96e]" : "border-transparent text-[#6b6b60]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="px-16 py-16 max-md:px-6">
        {activeTab === "listings" && (
          <div className="tab-content">
            {/* Filters */}
            <div className="card mb-6 border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-6 backdrop-blur-md">
              <h2 className="mb-4 text-[1.1rem] font-bold text-[#f5f4ef]">Search Filters</h2>
              <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
                <DropdownSelect
                  options={CITIES}
                  value={filters.city}
                  onChange={(city) => setFilters({ ...filters, city })}
                  placeholder="All GTA"
                />
                <input
                  type="number"
                  placeholder="Min Price"
                  value={filters.minPrice}
                  onChange={(e) => setFilters({ ...filters, minPrice: e.target.value })}
                  className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.8)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
                />
                <input
                  type="number"
                  placeholder="Max Price"
                  value={filters.maxPrice}
                  onChange={(e) => setFilters({ ...filters, maxPrice: e.target.value })}
                  className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.8)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
                />
                <DropdownSelect
                  options={BED_OPTIONS}
                  value={filters.bedrooms}
                  onChange={(bedrooms) => setFilters({ ...filters, bedrooms })}
                  placeholder="Any Beds"
                />
                <DropdownSelect
                  options={BATH_OPTIONS}
                  value={filters.bathrooms}
                  onChange={(bathrooms) => setFilters({ ...filters, bathrooms })}
                  placeholder="Any Baths"
                />
                <DropdownSelect
                  options={PROPERTY_TYPES}
                  value={filters.propertyType}
                  onChange={(propertyType) => setFilters({ ...filters, propertyType })}
                  placeholder="Any type"
                />
                <button
                  onClick={() => loadListings(0)}
                  className="btn w-full bg-[#c8a96e] px-4 py-3 font-['Syne',sans-serif] text-[0.88rem] font-bold uppercase tracking-[0.05em] text-black hover:bg-[#e4c98a]"
                >
                  Search
                </button>
              </div>
            </div>

            {/* My alerts */}
            <div className="card mb-6 border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-6 backdrop-blur-md">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-[1rem] font-bold text-[#f5f4ef]">My alerts</h2>
                  <p className="mt-1 font-['DM Mono',monospace] text-[0.72rem] text-[#6b6b60]">
                    Alerts are tied to your email and power both dashboard views and Telegram notifications.
                  </p>
                </div>
                {sessionEmail && (
                  <div className="text-right">
                    {telegramLinked ? (
                      <div className="inline-block rounded-lg border border-[rgba(200,169,110,0.3)] bg-[rgba(200,169,110,0.06)] px-4 py-2 text-center">
                        <div className="text-[1.1rem]">✅</div>
                        <p className="font-['DM Mono',monospace] text-[0.75rem] font-semibold text-[#f5f4ef]">Connected</p>
                        <p className="font-['DM Mono',monospace] text-[0.65rem] text-[#6b6b60]">You&apos;ll receive alerts in Telegram</p>
                      </div>
                    ) : linkCode ? (
                      <div className="space-y-2 text-right">
                        <div className="rounded-lg border border-[rgba(200,169,110,0.3)] bg-[rgba(0,0,0,0.2)] p-3 font-['DM Mono',monospace]">
                          <p className="text-[0.65rem] text-[#6b6b60] mb-1">Your link code (valid 30 min):</p>
                          <p className="text-[1rem] font-semibold text-[#f5f4ef] tracking-wider">{linkCode}</p>
                          {linkMessage && <p className="mt-1 text-[0.65rem] text-[#6b6b60]">{linkMessage}</p>}
                        </div>
                        <div className="text-[0.68rem] text-[#6b6b60] space-y-0.5">
                          <p>1. Open Telegram and find <strong className="text-[#c8a96e]">@Homes_Alertsbot</strong> (or your 416Homes Alerts bot)</p>
                          <p>2. Send: <code className="bg-[rgba(255,255,255,0.06)] px-1 rounded">/link {linkCode}</code></p>
                          <p>3. Wait for confirmation, then click below.</p>
                        </div>
                        <button
                          type="button"
                          onClick={handleCheckLinked}
                          disabled={checkingLinked}
                          className="mt-1 rounded-full border border-[rgba(200,169,110,0.4)] px-3 py-1.5 font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-[#c8a96e] hover:border-[#e4c98a] disabled:opacity-50"
                        >
                          {checkingLinked ? "Checking…" : "I've linked it, check status"}
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-1 text-right">
                        <button
                          onClick={handleGenerateLinkCode}
                          disabled={linkLoading}
                          className="rounded-full border border-[rgba(200,169,110,0.4)] px-3 py-1.5 font-['DM Mono',monospace] text-[0.7rem] uppercase tracking-[0.11em] text-[#c8a96e] hover:border-[#e4c98a]"
                        >
                          {linkLoading ? "Generating…" : "Connect Telegram"}
                        </button>
                        {(linkMessage || meError) && !linkCode && (
                          <p className="text-[0.65rem] font-['DM Mono',monospace] text-[#e4a84a]">
                            {meError ?? linkMessage}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {sessionEmail ? (
                <>
                  <div className="mt-4 grid gap-2 md:grid-cols-2 lg:grid-cols-4">
                    <DropdownSelect
                      options={CITIES}
                      value={alertForm.city}
                      onChange={(city) => setAlertForm({ ...alertForm, city })}
                      placeholder="All GTA"
                      className="[&_button]:px-2 [&_button]:py-1.5 [&_button]:text-[0.78rem]"
                    />
                    <input
                      type="number"
                      placeholder="Min beds"
                      value={alertForm.minBeds}
                      onChange={(e) => setAlertForm({ ...alertForm, minBeds: e.target.value })}
                      className="border border-[rgba(200,169,110,0.2)] bg-transparent px-2 py-1.5 text-[0.78rem] font-['DM Mono',monospace] text-[#f5f4ef] placeholder:text-[#6b6b60]"
                    />
                    <input
                      type="number"
                      placeholder="Min price"
                      value={alertForm.minPrice}
                      onChange={(e) => setAlertForm({ ...alertForm, minPrice: e.target.value })}
                      className="border border-[rgba(200,169,110,0.2)] bg-transparent px-2 py-1.5 text-[0.78rem] font-['DM Mono',monospace] text-[#f5f4ef] placeholder:text-[#6b6b60]"
                    />
                    <input
                      type="number"
                      placeholder="Max price"
                      value={alertForm.maxPrice}
                      onChange={(e) => setAlertForm({ ...alertForm, maxPrice: e.target.value })}
                      className="border border-[rgba(200,169,110,0.2)] bg-transparent px-2 py-1.5 text-[0.78rem] font-['DM Mono',monospace] text-[#f5f4ef] placeholder:text-[#6b6b60]"
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[0.7rem] text-[#6b6b60]">Property types:</span>
                      {PROPERTY_TYPES.filter((p) => p.value).map((p) => (
                        <label key={p.value} className="flex items-center gap-1.5 font-['DM Mono',monospace] text-[0.72rem] text-[#f5f4ef]">
                          <input
                            type="checkbox"
                            checked={alertForm.propertyTypes.includes(p.value)}
                            onChange={(e) => {
                              const next = e.target.checked
                                ? [...alertForm.propertyTypes, p.value]
                                : alertForm.propertyTypes.filter((x) => x !== p.value);
                              setAlertForm({ ...alertForm, propertyTypes: next });
                            }}
                            className="rounded border-[rgba(200,169,110,0.4)]"
                          />
                          {p.label}
                        </label>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={handleCreateAlert}
                    className="mt-3 rounded-full bg-[#c8a96e] px-4 py-2 font-['DM Mono',monospace] text-[0.74rem] uppercase tracking-[0.12em] text-black hover:bg-[#e4c98a]"
                  >
                    Save alert
                  </button>

                  <div className="mt-4 border-t border-[rgba(200,169,110,0.2)] pt-3">
                    {(alertsError || alertActionError) && (
                      <div className="mb-3">
                        <ErrorBanner
                          message={(alertsError || alertActionError)!}
                          onDismiss={() => { setAlertsError(null); setAlertActionError(null); }}
                        />
                      </div>
                    )}
                    {alertsLoading ? (
                      <p className="font-['DM Mono',monospace] text-[0.72rem] text-[#6b6b60]">Loading alerts...</p>
                    ) : alerts.length === 0 ? (
                      <p className="font-['DM Mono',monospace] text-[0.72rem] text-[#6b6b60]">
                        No alerts yet. Create your first one above.
                      </p>
                    ) : (
                      <ul className="space-y-2">
                        {alerts.map((a) => (
                          <li
                            key={a.id}
                            className="flex flex-nowrap items-center justify-between gap-3 rounded-md border border-[rgba(200,169,110,0.25)] px-3 py-2"
                          >
                            <div className="min-w-0 flex-1">
                              <div className="text-[0.8rem] font-semibold text-[#f5f4ef]">
                                {(a.cities && a.cities.join(", ")) || "GTA"}
                                {(a.property_types && a.property_types.length) ? ` · ${a.property_types.join(", ")}` : ""}
                              </div>
                              <div className="text-[0.7rem] font-['DM Mono',monospace] text-[#6b6b60]">
                                {a.min_price ? `$${a.min_price.toLocaleString()}` : "Any"} –{" "}
                                {a.max_price ? `$${a.max_price.toLocaleString()}` : "Any"} •{" "}
                                {a.min_beds ? `${a.min_beds}+ beds` : "Any beds"}
                              </div>
                            </div>
                            <div className="flex flex-shrink-0 flex-nowrap items-center gap-2 border-l border-[rgba(200,169,110,0.2)] pl-3">
                              <button
                                type="button"
                                onClick={() => handleToggleAlert(a)}
                                className={`rounded px-2 py-1 font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.1em] ${
                                  a.is_active
                                    ? "bg-[rgba(46,213,115,0.2)] text-[#2ed573]"
                                    : "bg-[rgba(255,255,255,0.06)] text-[#6b6b60]"
                                }`}
                              >
                                {a.is_active ? "On" : "Off"}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteAlert(a)}
                                className="rounded border border-[rgba(231,76,60,0.5)] px-2 py-1 font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-[#e74c3c] hover:bg-[rgba(231,76,60,0.15)] hover:text-[#ff6b6b]"
                                title="Delete this alert"
                              >
                                Delete
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              ) : (
                <p className="mt-3 font-['DM Mono',monospace] text-[0.72rem] text-[#6b6b60]">
                  Sign in with your email above to create and manage alerts.
                </p>
              )}
            </div>

            {/* Listings */}
            {listingsError && (
              <div className="mb-4">
                <ErrorBanner message={listingsError} onDismiss={() => setListingsError(null)} />
              </div>
            )}
            {loading ? (
              <div className="flex h-64 items-center justify-center">
                <div className="loading-spinner h-10 w-10 animate-spin rounded-full border-[3px] border-[rgba(200,169,110,0.2)] border-t-[#c8a96e]" />
              </div>
            ) : (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {listings.map((l) => (
                  <div
                    key={l.id}
                    className="listing-card card border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-6 backdrop-blur-md transition-all hover:-translate-y-1 hover:border-[rgba(200,169,110,0.4)] hover:shadow-xl"
                  >
                    <div className="mb-4 flex items-start justify-between">
                      <div>
                        <h3 className="mb-1 text-[0.9rem] font-semibold leading-tight">{l.address}</h3>
                        <p className="text-[1.6rem] font-extrabold tracking-[0.03em] text-[#c8a96e]">
                          ${l.price.toLocaleString()}
                        </p>
                      </div>
                      <span className="inline-block border border-[rgba(200,169,110,0.35)] px-2 py-0.5 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.12em] text-[#c8a96e]">
                        {(l.source || "").toUpperCase()}
                      </span>
                    </div>
                    <div className="mb-4 grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="stat-value text-[1.05rem] font-bold">{l.beds || "—"}</div>
                        <div className="stat-label mt-1 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.08em] text-[#6b6b60]">
                          Beds
                        </div>
                      </div>
                      <div>
                        <div className="stat-value text-[1.05rem] font-bold">{l.baths || "—"}</div>
                        <div className="stat-label mt-1 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.08em] text-[#6b6b60]">
                          Baths
                        </div>
                      </div>
                      <div>
                        <div className="stat-value text-[1.05rem] font-bold">
                          {l.sqft ? l.sqft.toLocaleString() : "—"}
                        </div>
                        <div className="stat-label mt-1 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.08em] text-[#6b6b60]">
                          Sq Ft
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <a
                        href={l.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[0.78rem] font-['DM Mono',monospace] uppercase tracking-[0.08em] text-[#f5f4ef] no-underline"
                      >
                        View Listing →
                      </a>
                      <button
                        className="btn bg-[#c8a96e] px-4 py-2 font-['Syne',sans-serif] text-[0.8rem] font-bold uppercase tracking-[0.08em] text-black hover:bg-[#e4c98a]"
                        onClick={() => {
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
                      >
                        Valuate
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "valuation" && (
          <div className="tab-content mx-auto max-w-[60rem]">
            <div className="card border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-6 backdrop-blur-md">
              <h2 className="mb-6 text-[clamp(1.4rem,2vw,2.2rem)] font-extrabold tracking-[-0.02em]">
                Property Valuation
              </h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {[
                  { label: "City", key: "city", placeholder: "Toronto" },
                  { label: "Neighbourhood", key: "neighbourhood", placeholder: "King West" },
                  { label: "Bedrooms", key: "bedrooms", placeholder: "3" },
                  { label: "Bathrooms", key: "bathrooms", placeholder: "2" },
                  { label: "Sq Ft", key: "sqft", placeholder: "1200" },
                  { label: "List Price", key: "list_price", placeholder: "750000" },
                ].map(({ label, key, placeholder }) => (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="font-[‘DM Mono’,monospace] text-[0.65rem] uppercase tracking-[0.08em] text-[#6b6b60]">{label}</label>
                    <input
                      type="text"
                      placeholder={placeholder}
                      value={valuationForm[key as keyof typeof valuationForm]}
                      onChange={e => setValuationForm(f => ({ ...f, [key]: e.target.value }))}
                      className="border border-[rgba(200,169,110,0.2)] bg-transparent px-3 py-2 font-[‘DM Mono’,monospace] text-[0.8rem] text-[#f5f4ef] outline-none placeholder:text-[#6b6b60] focus:border-[#c8a96e]"
                    />
                  </div>
                ))}
              </div>
              <button
                disabled={valuationLoading}
                className="mt-5 bg-[#c8a96e] px-6 py-2.5 font-[‘Syne’,sans-serif] text-[0.85rem] font-bold uppercase tracking-[0.08em] text-black hover:bg-[#e4c98a] disabled:opacity-50"
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
                {valuationLoading ? "Estimating…" : "Get Valuation"}
              </button>
              {valuationError && (
                <p className="mt-4 font-[‘DM Mono’,monospace] text-[0.78rem] text-red-400">{valuationError}</p>
              )}
              {valuationResult && (
                <div className="mt-6 border border-[rgba(200,169,110,0.2)] p-5">
                  <p className="font-[‘DM Mono’,monospace] text-[0.65rem] uppercase tracking-[0.1em] text-[#6b6b60]">Estimated Value</p>
                  <p className="text-[2rem] font-extrabold text-[#c8a96e]">
                    ${valuationResult.estimated_value.toLocaleString()}
                  </p>
                  {valuationResult.price_per_sqft && (
                    <p className="mt-1 font-[‘DM Mono’,monospace] text-[0.78rem] text-[#f5f4ef]">
                      ${Math.round(valuationResult.price_per_sqft).toLocaleString()} / sqft
                    </p>
                  )}
                  <p className="mt-2 font-[‘DM Mono’,monospace] text-[0.78rem] text-[#6b6b60]">
                    {valuationResult.market_analysis}
                  </p>
                  <p className="mt-1 font-[‘DM Mono’,monospace] text-[0.65rem] text-[#6b6b60]">
                    Confidence: {Math.round(valuationResult.confidence * 100)}%
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "videos" && (
          <div className="tab-content flex flex-col items-center justify-center px-4 py-16 text-center">
            <p className="mb-6 font-['DM Mono',monospace] text-[0.72rem] uppercase tracking-[0.1em] text-[#6b6b60]">
              Professional listing videos for GTA agents
            </p>
            <h2 className="mb-4 text-[clamp(1.6rem,2.5vw,2.8rem)] font-extrabold text-[#f5f4ef]">
              Turn any listing into a <span className="text-[#c8a96e]">cinematic video</span>
            </h2>
            <p className="mb-10 max-w-xl font-['DM Mono',monospace] text-[0.8rem] text-[#6b6b60]">
              Paste a Realtor.ca or Zillow URL. We write the script, record the voiceover, and add music — your
              polished 30-second video is ready in under 15 minutes.
            </p>
            <Link
              href="/video"
              className="btn rounded-full bg-[#c8a96e] px-10 py-4 font-['Syne',sans-serif] text-[0.9rem] font-bold uppercase tracking-[0.08em] text-black no-underline hover:bg-[#e4c98a]"
            >
              Order a Video →
            </Link>
          </div>
        )}
      </main>

      <footer className="border-t border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.8)] px-16 py-10 max-md:flex-col max-md:gap-3 max-md:px-6">
        <div className="footer-logo text-[1.1rem] font-extrabold">
          <span className="text-[#c8a96e]">416</span>
          Homes Dashboard
        </div>
        <div className="footer-copy font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">
          Toronto Real Estate Intelligence Platform
        </div>
        <div className="footer-copy font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">
          © 2024 416Homes · Dashboard
        </div>
      </footer>
    </div>
  );
}


