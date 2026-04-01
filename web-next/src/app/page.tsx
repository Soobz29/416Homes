"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { createAlert } from "@/lib/alerts";
import { fetchListings } from "@/lib/api";
import type { Listing } from "@/types";

const STATIC_TICKER = [
  "🏠 King West 2BR — $899K → Fair Value +4.2% underpriced",
  "🏢 Square One Condo — $549K → Agent contacted ✓",
  "🏡 Port Credit Semi — $1.1M → Comp avg $1.08M -1.8%",
  "📍 Mississauga — 5 new listings matched your alert",
  "🏠 Leslieville Detached — $1.35M → Fair Value +6.1% underpriced",
  "⚡ Eglinton Crosstown corridor — avg +$42K premium in transit-adjacent listings",
  "🏠 Erin Mills 3BR — $1.05M → 5 comps pulled, showing booked",
];

function formatPrice(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${Math.round(n / 1_000)}K`;
  return `$${n}`;
}

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [tickerItems, setTickerItems] = useState<string[]>(STATIC_TICKER);

  // Form state
  const [email, setEmail] = useState("");
  const [toronto, setToronto] = useState(true);
  const [mississauga, setMississauga] = useState(true);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minBeds, setMinBeds] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [neighbourhoods, setNeighbourhoods] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formSuccess, setFormSuccess] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Scroll-reveal
  useEffect(() => {
    const steps = document.querySelectorAll<HTMLElement>(".step,.feat,.ss-item");
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            const el = e.target as HTMLElement;
            el.style.opacity = "1";
            el.style.transform = "translateY(0)";
          }
        });
      },
      { threshold: 0.1 },
    );
    steps.forEach((el) => {
      el.style.opacity = "0";
      el.style.transform = "translateY(18px)";
      el.style.transition = "opacity 0.5s ease,transform 0.5s ease";
      obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);

  // Live ticker from API
  useEffect(() => {
    fetchListings({ city: undefined })
      .then(({ listings }) => {
        if (listings.length > 0) {
          const items = listings.slice(0, 10).map(
            (l: Listing) =>
              `🏠 ${l.address} — ${formatPrice(l.price)} → ${l.beds}bd/${l.baths}ba`,
          );
          setTickerItems(items);
        }
      })
      .catch(() => {
        // Keep static fallback on network failure
      });
  }, []);

  const scrollToId = (id: string) => {
    setMenuOpen(false);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

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
        neighbourhoods: neighbourhoods
          ? neighbourhoods.split(",").map((n) => n.trim()).filter(Boolean)
          : undefined,
      };
      await createAlert(email.trim(), payload);
      setFormSuccess(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  // Duplicate ticker items to allow seamless loop
  const displayTicker = [...tickerItems, ...tickerItems];

  return (
    <div className="min-h-screen bg-[#0a0a08] text-[#f5f4ef] font-['Syne',system-ui,sans-serif]">
      {/* Top nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.75)] px-16 py-6 backdrop-blur-xl max-md:px-6">
        <div className="logo text-[1.3rem] font-extrabold tracking-[0.05em]">
          <span className="text-[#c8a96e]">416</span>
          Homes
          <sub className="ml-1 align-middle font-['DM_Mono',monospace] text-[0.6rem] font-normal tracking-[0.1em] text-[#6b6b60]">
            GTA · MISSISSAUGA
          </sub>
        </div>
        <ul className="hidden list-none gap-10 font-['DM_Mono',monospace] text-[0.72rem] uppercase tracking-[0.1em] text-[#6b6b60] md:flex">
          <li>
            <button
              onClick={() => scrollToId("how")}
              className="bg-transparent text-inherit transition-colors hover:text-[#c8a96e]"
            >
              How It Works
            </button>
          </li>
          <li>
            <button
              onClick={() => scrollToId("features")}
              className="bg-transparent text-inherit transition-colors hover:text-[#c8a96e]"
            >
              Features
            </button>
          </li>
          <li>
            <button
              onClick={() => scrollToId("alert")}
              className="bg-transparent text-inherit transition-colors hover:text-[#c8a96e]"
            >
              Get Started
            </button>
          </li>
        </ul>
        <div className="flex items-center gap-3">
          <button
            className="nav-cta bg-[#c8a96e] px-6 py-2 font-['DM_Mono',monospace] text-[0.72rem] font-medium uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e4c98a]"
            onClick={() => scrollToId("alert")}
          >
            Set My Alert
          </button>
          {/* Hamburger — mobile only */}
          <button
            className="flex flex-col gap-[5px] p-1 md:hidden"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            <span className={`block h-px w-5 bg-[#c8a96e] transition-all ${menuOpen ? "translate-y-[6px] rotate-45" : ""}`} />
            <span className={`block h-px w-5 bg-[#c8a96e] transition-all ${menuOpen ? "opacity-0" : ""}`} />
            <span className={`block h-px w-5 bg-[#c8a96e] transition-all ${menuOpen ? "-translate-y-[6px] -rotate-45" : ""}`} />
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="fixed inset-x-0 top-[4.3rem] z-40 border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.97)] px-6 py-6 md:hidden">
          <ul className="flex flex-col gap-6 font-['DM_Mono',monospace] text-[0.8rem] uppercase tracking-[0.1em] text-[#6b6b60]">
            <li><button onClick={() => scrollToId("how")} className="hover:text-[#c8a96e]">How It Works</button></li>
            <li><button onClick={() => scrollToId("features")} className="hover:text-[#c8a96e]">Features</button></li>
            <li><button onClick={() => scrollToId("alert")} className="hover:text-[#c8a96e]">Get Started</button></li>
            <li><Link href="/dashboard" className="text-[#c8a96e] hover:text-[#e4c98a]" onClick={() => setMenuOpen(false)}>Dashboard →</Link></li>
          </ul>
        </div>
      )}

      {/* Ticker */}
      <div className="fixed left-0 right-0 top-[4.5rem] z-40 border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.9)] py-2 max-md:hidden">
        <div className="flex animate-[ticker_35s_linear_infinite] gap-20 whitespace-nowrap text-[0.68rem] font-['DM_Mono',monospace] text-[#6b6b60]">
          {displayTicker.map((text, idx) => (
            <span key={idx}>{text}</span>
          ))}
        </div>
      </div>

      {/* Hero */}
      <section className="grid min-h-screen grid-cols-1 pt-[7.5rem] md:grid-cols-2">
        <div className="flex flex-col justify-center px-16 pb-16 pt-24 max-md:px-6">
          <div className="mb-8 flex items-center gap-3 font-['DM_Mono',monospace] text-[0.68rem] uppercase tracking-[0.18em] text-[#c8a96e]">
            <span className="h-px w-8 bg-[#c8a96e]" />
            Toronto &amp; Mississauga&apos;s First Autonomous Property Agent
          </div>
          <h1 className="mb-8 text-[clamp(2.8rem,4.5vw,5rem)] font-extrabold leading-[0.95] tracking-[-0.03em]">
            Stop chasing.
            <br />
            Let listings
            <br />
            <span className="text-[#c8a96e]">chase you.</span>
          </h1>
          <div className="mb-10 flex gap-2">
            <span className="border border-[rgba(200,169,110,0.2)] bg-[rgba(200,169,110,0.12)] px-3 py-1 font-['DM_Mono',monospace] text-[0.65rem] uppercase tracking-[0.1em] text-[#c8a96e]">
              Toronto
            </span>
            <span className="border border-[rgba(200,169,110,0.2)] bg-[rgba(200,169,110,0.12)] px-3 py-1 font-['DM_Mono',monospace] text-[0.65rem] uppercase tracking-[0.1em] text-[#c8a96e]">
              Mississauga
            </span>
            <span className="border border-[rgba(200,169,110,0.2)] px-3 py-1 font-['DM_Mono',monospace] text-[0.65rem] uppercase tracking-[0.1em] text-[#c8a96e]">
              50+ Neighbourhoods
            </span>
          </div>
          <p className="mb-10 max-w-[40ch] font-['DM_Mono',monospace] text-[0.88rem] leading-[1.75] text-[#6b6b60]">
            416Homes monitors 4 listing platforms 24/7 across Toronto and Mississauga, valuates every property against
            real sold comps, and emails listing agents on your behalf — while you sleep.
          </p>
          <div className="flex items-center gap-4">
            <Button
              className="bg-[#c8a96e] px-8 py-3 text-[0.88rem] font-bold uppercase tracking-[0.05em] text-black hover:bg-[#e4c98a]"
              onClick={() => scrollToId("alert")}
            >
              Set My Alert Free
            </Button>
            <button
              className="border border-[rgba(200,169,110,0.2)] px-7 py-3 font-['DM_Mono',monospace] text-[0.72rem] uppercase tracking-[0.08em] text-[#f5f4ef] transition-colors hover:border-[#c8a96e] hover:text-[#c8a96e]"
              onClick={() => scrollToId("how")}
            >
              See How →
            </button>
          </div>
        </div>

        {/* Hero card — illustrative example */}
        <div className="relative hidden items-center justify-center p-16 md:flex">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(200,169,110,0.07)_0%,transparent_70%)]" />
          <div className="w-[340px] animate-[float_6s_ease-in-out_infinite] border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.03)] p-8 backdrop-blur-md">
            <div className="mb-6 flex items-center gap-2 font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.15em] text-[#c8a96e]">
              <span className="h-[6px] w-[6px] animate-[pulse_2s_ease-in-out_infinite] rounded-full bg-[#c8a96e]" aria-hidden="true" />
              Agent Working Now
            </div>
            <div className="mb-2 inline-block bg-[rgba(200,169,110,0.1)] px-2 py-1 font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#c8a96e]">
              Mississauga
            </div>
            <div className="mb-1 text-[1rem] font-bold">1480 Erin Mills Pkwy, Unit 12</div>
            <div className="mb-6 font-['DM_Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-[#6b6b60]">
              Erin Mills · Example listing
            </div>
            <div className="mb-2 text-[1.9rem] font-extrabold">$1,049,000</div>
            <div className="mb-6 flex items-center gap-2">
              <span className="bg-[rgba(46,213,115,0.15)] px-2 py-0.5 font-['DM_Mono',monospace] text-[0.62rem] text-[#2ed573]">
                ▲ 4.8% Underpriced
              </span>
              <span className="font-['DM_Mono',monospace] text-[0.62rem] text-[#6b6b60]">vs. 9 comps</span>
            </div>
            <div className="mb-5 grid grid-cols-3 gap-2 border-y border-[rgba(200,169,110,0.2)] py-5">
              {[["3", "Beds"], ["2", "Baths"], ["11", "DOM"]].map(([v, l]) => (
                <div key={l} className="text-center">
                  <div className="text-[1.05rem] font-bold">{v}</div>
                  <div className="mt-1 font-['DM_Mono',monospace] text-[0.58rem] uppercase tracking-[0.08em] text-[#6b6b60]">{l}</div>
                </div>
              ))}
            </div>
            <Link
              href="/dashboard"
              className="block w-full bg-[#c8a96e] px-4 py-3 text-center font-['DM_Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e4c98a]"
            >
              View Live Listings →
            </Link>
          </div>
        </div>
      </section>

      {/* Stats strip */}
      <div className="grid border-y border-[rgba(200,169,110,0.2)] md:grid-cols-4">
        {[
          ["24/7", "Continuous monitoring"],
          ["50+", "GTA neighbourhoods"],
          ["2", "Cities: Toronto & Mississauga"],
          ["$0", "To get started"],
        ].map(([num, label]) => (
          <div key={label} className="ss-item border-r border-[rgba(200,169,110,0.2)] p-10 last:border-r-0">
            <div className="mb-1 text-[2.8rem] font-extrabold text-[#c8a96e]">{num}</div>
            <div className="font-['DM_Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-[#6b6b60]">
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* Process */}
      <section id="how" className="px-16 py-28 max-md:px-6 max-md:py-16">
        <div className="mb-3 font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          Process
        </div>
        <h2 className="mb-16 max-w-[22ch] text-[clamp(1.8rem,3vw,3.2rem)] font-extrabold leading-[1.05] tracking-[-0.02em]">
          Four steps while you live your life
        </h2>
        <div className="grid gap-[2px] md:grid-cols-4">
          {[
            {
              n: "01 / 04",
              icon: "🔍",
              t: "You set your criteria",
              d: "Price, city (Toronto, Mississauga, or both), neighbourhood, property type, beds. Takes 90 seconds.",
            },
            {
              n: "02 / 04",
              icon: "🤖",
              t: "Agent scrapes nightly",
              d: "Hits Realtor.ca, HouseSigma, Zolo, and Zoocasa every night. New listings in your dashboard every morning.",
            },
            {
              n: "03 / 04",
              icon: "📊",
              t: "AI valuates each match",
              d: "Every listing is priced against real sold comps. Overpriced listings are filtered. Underpriced ones flagged with a delta.",
            },
            {
              n: "04 / 04",
              icon: "📨",
              t: "Agent contacts listing agents",
              d: "For qualified matches, 416Homes drafts and sends professional outreach requesting showings — fully autonomous.",
            },
          ].map((s) => (
            <div
              key={s.n}
              className="step border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-10 transition-colors hover:bg-[rgba(200,169,110,0.04)]"
            >
              <div className="mb-5 font-['DM_Mono',monospace] text-[0.62rem] tracking-[0.18em] text-[#c8a96e]">
                {s.n}
              </div>
              <div className="mb-3 text-[1.4rem]">{s.icon}</div>
              <div className="mb-2 text-[1.05rem] font-bold">{s.t}</div>
              <div className="font-['DM_Mono',monospace] text-[0.74rem] leading-[1.7] text-[#6b6b60]">{s.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Intelligence */}
      <section id="features" className="border-y border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.01)] px-16 py-28 max-md:px-6 max-md:py-16">
        <div className="mb-3 font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          Intelligence
        </div>
        <h2 className="mb-16 max-w-[22ch] text-[clamp(1.8rem,3vw,3.2rem)] font-extrabold leading-[1.05] tracking-[-0.02em]">
          Built specifically for the GTA + Mississauga market
        </h2>
        <div className="grid gap-[2px] md:grid-cols-2">
          {[
            {
              label: "Valuation Engine",
              title: "Real Sold Prices, Not Asking",
              desc: "416Homes scrapes actual sold prices from HouseSigma across 50+ Toronto and Mississauga neighbourhoods. The pricing model trains on real transaction data — not agent estimates — and flags listings with a concrete percentage delta versus fair value.",
            },
            {
              label: "Dual-City Coverage",
              title: "Toronto & Mississauga Together",
              desc: "Most tools treat the two cities separately. 416Homes lets you search across both in a single alert — so if you're open to Port Credit or Leslieville, you see the best of both markets ranked by value, not just city.",
            },
            {
              label: "Transit Intelligence",
              title: "Ontario Line & Eglinton Crosstown Scoring",
              desc: "Both lines are still under construction. 416Homes scores each listing's proximity to planned stops, factoring the forward premium these corridors will command — a signal most buyers aren't considering.",
            },
            {
              label: "Unique GTA Segment",
              title: "Pre-Construction Assignment Tracking",
              desc: "The GTA has one of North America's largest pre-construction markets. 416Homes tracks assignment sales — original buyers flipping purchase agreements before closing — a segment invisible to most search tools.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="feat relative overflow-hidden border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-12"
            >
              <div className="mb-3 font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.18em] text-[#c8a96e]">
                {f.label}
              </div>
              <div className="mb-3 text-[1.25rem] font-bold leading-tight">{f.title}</div>
              <div className="font-['DM_Mono',monospace] text-[0.76rem] leading-[1.75] text-[#6b6b60]">
                {f.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Alert section */}
      <section id="alert" className="grid gap-20 px-16 py-28 md:grid-cols-2 max-md:px-6 max-md:py-16">
        <div>
          <div className="mb-3 font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
            Early Access — Free
          </div>
          <h2 className="mb-5 text-[clamp(1.8rem,3vw,3.2rem)] font-extrabold leading-[1.05] tracking-[-0.02em]">
            Set your search.
            <br />
            Walk away.
          </h2>
          <p className="max-w-[38ch] font-['DM_Mono',monospace] text-[0.8rem] leading-[1.8] text-[#6b6b60]">
            Define your criteria once. 416Homes monitors Toronto and Mississauga every night and surfaces only the
            listings worth your attention — with AI valuation included.
          </p>
          <div className="mt-10">
            {[
              ["Gemini 2.0 Flash", "Agent LLM + embeddings", "Free"],
              ["Supabase + pgvector", "Database + semantic search", "Free"],
              ["Browser Use + Playwright", "Autonomous web scraping", "Open Source"],
              ["GitHub Actions", "Nightly cron scheduler", "Free"],
              ["LightGBM + FastAPI", "Valuation model + API", "Open Source"],
            ].map(([name, role, badge]) => (
              <div
                key={name}
                className="flex items-center justify-between border-b border-[rgba(200,169,110,0.2)] py-4 last:border-b-0"
              >
                <div>
                  <div className="text-[0.95rem] font-semibold">{name}</div>
                  <div className="mt-1 font-['DM_Mono',monospace] text-[0.68rem] text-[#6b6b60]">{role}</div>
                </div>
                <span className="border border-[rgba(200,169,110,0.3)] px-2 py-0.5 font-['DM_Mono',monospace] text-[0.58rem] uppercase tracking-[0.1em] text-[#c8a96e]">
                  {badge}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Form — wired to /api/alerts */}
        <div className="border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-10">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div className="text-[1.1rem] font-bold">Create Your Alert</div>
            <Link
              href="/dashboard"
              className="shrink-0 font-['DM_Mono',monospace] text-[0.7rem] uppercase tracking-[0.1em] text-[#c8a96e] no-underline hover:text-[#e4c98a]"
            >
              Sign in or manage alerts →
            </Link>
          </div>
          <p className="mb-8 font-['DM_Mono',monospace] text-[0.72rem] leading-[1.6] text-[#6b6b60]">
            We&apos;ll monitor Toronto + Mississauga and send matches every morning.
          </p>

          {formSuccess ? (
            <div
              aria-live="polite"
              className="border border-[rgba(46,213,115,0.3)] bg-[rgba(46,213,115,0.08)] px-4 py-6 text-center font-['DM_Mono',monospace] text-[0.82rem] text-[#2ed573]"
            >
              ✅ Alert created! Check your inbox for confirmation.
              <br />
              <Link href="/dashboard" className="mt-3 block text-[#c8a96e] hover:text-[#e4c98a]">
                Manage your alerts in the dashboard →
              </Link>
            </div>
          ) : (
            <form onSubmit={handleFormSubmit} noValidate>
              <div className="mb-4">
                <label htmlFor="alert-email" className="mb-1 block font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                  Email Address
                </label>
                <input
                  id="alert-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none transition-colors focus:border-[#c8a96e] placeholder:text-[#6b6b60]"
                  placeholder="you@example.com"
                />
              </div>
              <div className="mb-4">
                <label className="mb-1 block font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                  Cities to Monitor
                </label>
                <div className="flex gap-4 font-['DM_Mono',monospace] text-[0.72rem] text-[#6b6b60]">
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={toronto}
                      onChange={(e) => setToronto(e.target.checked)}
                      className="accent-[#c8a96e]"
                    />
                    Toronto
                  </label>
                  <label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={mississauga}
                      onChange={(e) => setMississauga(e.target.checked)}
                      className="accent-[#c8a96e]"
                    />
                    Mississauga
                  </label>
                </div>
              </div>
              <div className="mb-4 grid gap-3 md:grid-cols-2">
                <div>
                  <label htmlFor="alert-min-price" className="mb-1 block font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                    Min Price
                  </label>
                  <input
                    id="alert-min-price"
                    value={minPrice}
                    onChange={(e) => setMinPrice(e.target.value)}
                    className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none transition-colors focus:border-[#c8a96e] placeholder:text-[#6b6b60]"
                    placeholder="500000"
                  />
                </div>
                <div>
                  <label htmlFor="alert-max-price" className="mb-1 block font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                    Max Price
                  </label>
                  <input
                    id="alert-max-price"
                    value={maxPrice}
                    onChange={(e) => setMaxPrice(e.target.value)}
                    className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none transition-colors focus:border-[#c8a96e] placeholder:text-[#6b6b60]"
                    placeholder="1200000"
                  />
                </div>
              </div>
              <div className="mb-4 grid gap-3 md:grid-cols-2">
                <div>
                  <label htmlFor="alert-min-beds" className="mb-1 block font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                    Min Bedrooms
                  </label>
                  <input
                    id="alert-min-beds"
                    type="number"
                    min="0"
                    value={minBeds}
                    onChange={(e) => setMinBeds(e.target.value)}
                    className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none transition-colors focus:border-[#c8a96e] placeholder:text-[#6b6b60]"
                    placeholder="2"
                  />
                </div>
                <div>
                  <label htmlFor="alert-property-type" className="mb-1 block font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                    Property Type
                  </label>
                  <input
                    id="alert-property-type"
                    value={propertyType}
                    onChange={(e) => setPropertyType(e.target.value)}
                    className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none transition-colors focus:border-[#c8a96e] placeholder:text-[#6b6b60]"
                    placeholder="Condo, Detached..."
                  />
                </div>
              </div>
              <div className="mb-4">
                <label htmlFor="alert-neighbourhoods" className="mb-1 block font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                  Neighbourhoods (optional)
                </label>
                <input
                  id="alert-neighbourhoods"
                  value={neighbourhoods}
                  onChange={(e) => setNeighbourhoods(e.target.value)}
                  className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none transition-colors focus:border-[#c8a96e] placeholder:text-[#6b6b60]"
                  placeholder="Port Credit, King West, Erin Mills..."
                />
              </div>

              {formError && (
                <div aria-live="polite" className="mb-4 border border-[rgba(192,57,43,0.4)] bg-[rgba(192,57,43,0.08)] px-4 py-3 font-['DM_Mono',monospace] text-[0.75rem] text-[#e07060]">
                  {formError}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="mt-1 w-full bg-[#c8a96e] px-4 py-3 font-['Syne',sans-serif] text-[0.88rem] font-bold uppercase tracking-[0.05em] text-black transition-colors hover:bg-[#e4c98a] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Activating..." : "Activate My Agent →"}
              </button>
            </form>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="flex items-center justify-between border-t border-[rgba(200,169,110,0.2)] px-16 py-10 max-md:flex-col max-md:gap-3 max-md:px-6">
        <div className="text-[1.1rem] font-extrabold">
          <span className="text-[#c8a96e]">416</span>Homes
        </div>
        <div className="font-['DM_Mono',monospace] text-[0.62rem] text-[#6b6b60]">
          Covering Toronto &amp; Mississauga · Powered by Gemini + open-source tooling
        </div>
        <div className="font-['DM_Mono',monospace] text-[0.62rem] text-[#6b6b60]">
          © 2025 416Homes · Early Access
        </div>
      </footer>
    </div>
  );
}
