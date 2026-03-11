"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
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

  const scrollToId = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-[#0a0a08] text-[#f5f4ef] font-['Syne',system-ui,sans-serif]">
      {/* Top nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.75)] px-16 py-6 backdrop-blur-xl max-md:px-6">
        <div className="logo text-[1.3rem] font-extrabold tracking-[0.05em]">
          <span className="text-[#c8a96e]">416</span>
          Homes
          <sub className="ml-1 align-middle font-['DM Mono',monospace] text-[0.6rem] font-normal tracking-[0.1em] text-[#6b6b60]">
            GTA · MISSISAUGA
          </sub>
        </div>
        <ul className="nav-links hidden list-none gap-10 font-['DM Mono',monospace] text-[0.72rem] uppercase tracking-[0.1em] text-[#6b6b60] md:flex">
          <li>
            <button
              onClick={() => scrollToId("how")}
              className="bg-transparent text-inherit no-underline transition-colors hover:text-[#c8a96e]"
            >
              How It Works
            </button>
          </li>
          <li>
            <button
              onClick={() => scrollToId("features")}
              className="bg-transparent text-inherit no-underline transition-colors hover:text-[#c8a96e]"
            >
              Features
            </button>
          </li>
          <li>
            <button
              onClick={() => scrollToId("alert")}
              className="bg-transparent text-inherit no-underline transition-colors hover:text-[#c8a96e]"
            >
              Get Started
            </button>
          </li>
        </ul>
        <button
          className="nav-cta bg-[#c8a96e] px-6 py-2 font-['DM Mono',monospace] text-[0.72rem] font-medium uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e4c98a]"
          onClick={() => scrollToId("alert")}
        >
          Set My Alert
        </button>
      </nav>

      {/* Ticker */}
      <div className="ticker fixed left-0 right-0 top-[4.5rem] z-40 border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.9)] py-2 max-md:hidden">
        <div className="ticker-track flex animate-[ticker_35s_linear_infinite] gap-20 whitespace-nowrap text-[0.68rem] font-['DM Mono',monospace] text-[#6b6b60]">
          {[
            "🏠 King West 2BR — $899K → Fair Value +4.2% underpriced",
            "🏢 Square One Condo — $549K → Agent contacted ✓",
            "🏡 Port Credit Semi — $1.1M → Comp avg $1.08M -1.8%",
            "📍 Mississauga — 5 new listings matched your alert",
            "🏠 Leslieville Detached — $1.35M → Fair Value +6.1% underpriced",
            "⚡ Eglinton Crosstown corridor — avg +$42K premium in transit-adjacent listings",
            "🏠 Erin Mills 3BR — $1.05M → 5 comps pulled, showing booked",
          ].flatMap((t, i) => [t, t]).map((text, idx) => (
            <span key={idx} className="tick">
              {text}
            </span>
          ))}
        </div>
      </div>

      {/* Hero */}
      <section className="hero grid min-h-screen grid-cols-1 pt-[7.5rem] md:grid-cols-2">
        <div className="hero-left flex flex-col justify-center px-16 pb-16 pt-24 max-md:px-6">
          <div className="hero-tag mb-8 flex items-center gap-3 font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.18em] text-[#c8a96e]">
            <span className="h-px w-8 bg-[#c8a96e]" />
            Toronto &amp; Mississauga&apos;s First Autonomous Property Agent
          </div>
          <h1 className="hero-h1 mb-8 text-[clamp(2.8rem,4.5vw,5rem)] font-extrabold leading-[0.95] tracking-[-0.03em]">
            Stop chasing.
            <br />
            Let listings
            <br />
            <span className="text-[#c8a96e] not-italic">chase you.</span>
          </h1>
          <div className="city-pills mb-10 flex gap-2">
            <div className="pill active border border-[rgba(200,169,110,0.2)] bg-[rgba(200,169,110,0.12)] px-3 py-1 font-['DM Mono',monospace] text-[0.65rem] uppercase tracking-[0.1em] text-[#c8a96e]">
              Toronto
            </div>
            <div className="pill active border border-[rgba(200,169,110,0.2)] bg-[rgba(200,169,110,0.12)] px-3 py-1 font-['DM Mono',monospace] text-[0.65rem] uppercase tracking-[0.1em] text-[#c8a96e]">
              Mississauga
            </div>
            <div className="pill border border-[rgba(200,169,110,0.2)] px-3 py-1 font-['DM Mono',monospace] text-[0.65rem] uppercase tracking-[0.1em] text-[#c8a96e]">
              50+ Neighbourhoods
            </div>
          </div>
          <p className="hero-sub mb-10 max-w-[40ch] font-['DM Mono',monospace] text-[0.88rem] leading-[1.75] text-[#6b6b60]">
            416Homes monitors 4 listing platforms 24/7 across Toronto and Mississauga, valuates every property against
            real sold comps, and emails listing agents on your behalf — while you sleep.
          </p>
          <div className="hero-actions flex items-center gap-4">
            <Button
              className="btn-p bg-[#c8a96e] px-8 py-3 text-[0.88rem] font-bold uppercase tracking-[0.05em] text-black hover:bg-[#e4c98a]"
              onClick={() => scrollToId("alert")}
            >
              Set My Alert Free
            </Button>
            <button
              className="btn-g border border-[rgba(200,169,110,0.2)] px-7 py-3 font-['DM Mono',monospace] text-[0.72rem] uppercase tracking-[0.08em] text-[#f5f4ef] transition-colors hover:border-[#c8a96e] hover:text-[#c8a96e]"
              onClick={() => scrollToId("how")}
            >
              See How →
            </button>
          </div>
        </div>

        {/* Hero card */}
        <div className="hero-right relative hidden items-center justify-center p-16 md:flex">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(200,169,110,0.07)_0%,transparent_70%)]" />
          <div className="card w-[340px] animate-[float_6s_ease-in-out_infinite] border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.03)] p-8 backdrop-blur-md">
            <div className="card-live mb-6 flex items-center gap-2 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.15em] text-[#c8a96e]">
              <span className="dot h-[6px] w-[6px] animate-[pulse_2s_ease-in-out_infinite] rounded-full bg-[#c8a96e]" />
              Agent Working Now
            </div>
            <div className="card-city mb-2 inline-block bg-[rgba(200,169,110,0.1)] px-2 py-1 font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#c8a96e]">
              Mississauga
            </div>
            <div className="card-addr mb-1 text-[1rem] font-bold">1480 Erin Mills Pkwy, Unit 12</div>
            <div className="card-hood mb-6 font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-[#6b6b60]">
              Erin Mills
            </div>
            <div className="card-price mb-2 text-[1.9rem] font-extrabold">$1,049,000</div>
            <div className="card-val mb-6 flex items-center gap-2">
              <span className="chip-under chip bg-[rgba(46,213,115,0.15)] px-2 py-0.5 font-['DM Mono',monospace] text-[0.62rem] text-[#2ed573]">
                ▲ 4.8% Underpriced
              </span>
              <span className="chip-note font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">vs. 9 comps</span>
            </div>
            <div className="card-stats mb-5 grid grid-cols-3 gap-2 border-y border-[rgba(200,169,110,0.2)] py-5">
              <div className="stat text-center">
                <div className="stat-v text-[1.05rem] font-bold">3</div>
                <div className="stat-l mt-1 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.08em] text-[#6b6b60]">
                  Beds
                </div>
              </div>
              <div className="stat text-center">
                <div className="stat-v text-[1.05rem] font-bold">2</div>
                <div className="stat-l mt-1 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.08em] text-[#6b6b60]">
                  Baths
                </div>
              </div>
              <div className="stat text-center">
                <div className="stat-v text-[1.05rem] font-bold">11</div>
                <div className="stat-l mt-1 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.08em] text-[#6b6b60]">
                  DOM
                </div>
              </div>
            </div>
            <button
              className="card-btn w-full border-none bg-[#c8a96e] px-4 py-3 font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e4c98a]"
              onClick={(e) => {
                const btn = e.currentTarget;
                btn.textContent = "⏳ Drafting email...";
                btn.style.backgroundColor = "#1a1a18";
                btn.style.color = "#c8a96e";
                setTimeout(() => {
                  btn.textContent = "✅ Showing requested!";
                  btn.style.backgroundColor = "rgba(46,213,115,0.12)";
                  btn.style.color = "#2ed573";
                }, 1800);
              }}
            >
              📨 Contact Agent
            </button>
          </div>
        </div>
      </section>

      {/* Stats strip */}
      <div className="stats-strip grid border-y border-[rgba(200,169,110,0.2)] md:grid-cols-4">
        {[
          ["24/7", "Continuous monitoring"],
          ["50+", "GTA neighbourhoods"],
          ["2", "Cities: Toronto & Mississauga"],
          ["$0", "To get started"],
        ].map(([num, label]) => (
          <div key={label} className="ss-item border-r border-[rgba(200,169,110,0.2)] p-10 last:border-r-0">
            <div className="ss-num mb-1 text-[2.8rem] font-extrabold text-[#c8a96e]">{num}</div>
            <div className="ss-label font-['DM Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-[#6b6b60]">
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* Process */}
      <section id="how" className="section px-16 py-28 max-md:px-6 max-md:py-16">
        <div className="sec-tag mb-3 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          Process
        </div>
        <h2 className="sec-h2 mb-16 max-w-[22ch] text-[clamp(1.8rem,3vw,3.2rem)] font-extrabold leading-[1.05] tracking-[-0.02em]">
          Four steps while you live your life
        </h2>
        <div className="steps grid gap-[2px] md:grid-cols-4">
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
              <div className="step-n mb-5 font-['DM Mono',monospace] text-[0.62rem] text-[#c8a96e] tracking-[0.18em]">
                {s.n}
              </div>
              <div className="step-ico mb-3 text-[1.4rem]">{s.icon}</div>
              <div className="step-t mb-2 text-[1.05rem] font-bold">{s.t}</div>
              <div className="step-d font-['DM Mono',monospace] text-[0.74rem] leading-[1.7] text-[#6b6b60]">{s.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Intelligence */}
      <section id="features" className="features border-y border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.01)] px-16 py-28 max-md:px-6 max-md:py-16">
        <div className="sec-tag mb-3 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          Intelligence
        </div>
        <h2 className="sec-h2 mb-16 max-w-[22ch] text-[clamp(1.8rem,3vw,3.2rem)] font-extrabold leading-[1.05] tracking-[-0.02em]">
          Built specifically for the GTA + Mississauga market
        </h2>
        <div className="feat-grid grid gap-[2px] md:grid-cols-2">
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
              <div className="feat-label mb-3 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.18em] text-[#c8a96e]">
                {f.label}
              </div>
              <div className="feat-t mb-3 text-[1.25rem] font-bold leading-tight">{f.title}</div>
              <div className="feat-d font-['DM Mono',monospace] text-[0.76rem] leading-[1.75] text-[#6b6b60]">
                {f.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Alert section */}
      <section id="alert" className="alert-sec grid gap-20 px-16 py-28 md:grid-cols-2 max-md:px-6 max-md:py-16">
        <div>
          <div className="sec-tag mb-3 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
            Early Access — Free
          </div>
          <h2 className="sec-h2 mb-5 text-[clamp(1.8rem,3vw,3.2rem)] font-extrabold leading-[1.05] tracking-[-0.02em]">
            Set your search.
            <br />
            Walk away.
          </h2>
          <p className="max-w-[38ch] font-['DM Mono',monospace] text-[0.8rem] leading-[1.8] text-[#6b6b60]">
            Define your criteria once. 416Homes monitors Toronto and Mississauga every night and surfaces only the
            listings worth your attention — with AI valuation included.
          </p>
          <div className="stack-list mt-10">
            {[
              ["Gemini 2.0 Flash", "Agent LLM + embeddings", "Free"],
              ["Supabase + pgvector", "Database + semantic search", "Free"],
              ["Browser Use + Playwright", "Autonomous web scraping", "Open Source"],
              ["GitHub Actions", "Nightly cron scheduler", "Free"],
              ["LightGBM + FastAPI", "Valuation model + API", "Open Source"],
            ].map(([name, role, badge]) => (
              <div
                key={name}
                className="stack-item flex items-center justify-between border-b border-[rgba(200,169,110,0.2)] py-4 last:border-b-0"
              >
                <div>
                  <div className="stack-name text-[0.95rem] font-semibold">{name}</div>
                  <div className="stack-role mt-1 font-['DM Mono',monospace] text-[0.68rem] text-[#6b6b60]">
                    {role}
                  </div>
                </div>
                <span className="stack-badge border border-[rgba(200,169,110,0.3)] px-2 py-0.5 font-['DM Mono',monospace] text-[0.58rem] uppercase tracking-[0.1em] text-[#c8a96e]">
                  {badge}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Form – non-functional demo, matches copy */}
        <div className="form-box border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-10">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div className="form-t mb-0 text-[1.1rem] font-bold">Create Your Alert</div>
            <Link
              href="/dashboard"
              className="shrink-0 font-['DM Mono',monospace] text-[0.7rem] uppercase tracking-[0.1em] text-[#c8a96e] no-underline hover:text-[#e4c98a]"
            >
              Sign in or manage alerts →
            </Link>
          </div>
          <p className="form-sub mb-8 font-['DM Mono',monospace] text-[0.72rem] leading-[1.6] text-[#6b6b60]">
            We&apos;ll monitor Toronto + Mississauga and send matches every morning.
          </p>
          <div className="fg mb-4" suppressHydrationWarning>
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
              Email Address
            </label>
            <input
              type="email"
              defaultValue=""
              className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none transition-colors placeholder:text-[#6b6b60]"
              placeholder="you@example.com"
            />
          </div>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
              Cities to Monitor
            </label>
            <div className="city-check flex gap-4 font-['DM Mono',monospace] text-[0.72rem] text-[#6b6b60]">
              <label className="flex items-center gap-2">
                <input type="checkbox" defaultChecked className="accent-[#c8a96e]" /> Toronto
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" defaultChecked className="accent-[#c8a96e]" /> Mississauga
              </label>
            </div>
          </div>
          <div className="form-row mb-4 grid gap-3 md:grid-cols-2">
            <div className="fg">
              <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                Min Price
              </label>
              <input
                className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none placeholder:text-[#6b6b60]"
                placeholder="$500,000"
              />
            </div>
            <div className="fg">
              <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                Max Price
              </label>
              <input
                className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none placeholder:text-[#6b6b60]"
                placeholder="$1,200,000"
              />
            </div>
          </div>
          <div className="form-row mb-4 grid gap-3 md:grid-cols-2">
            <div className="fg">
              <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                Min Bedrooms
              </label>
              <input
                className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none placeholder:text-[#6b6b60]"
                placeholder="2"
              />
            </div>
            <div className="fg">
              <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
                Property Type
              </label>
              <input
                className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none placeholder:text-[#6b6b60]"
                placeholder="Condo, Detached..."
              />
            </div>
          </div>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.13em] text-[#6b6b60]">
              Neighbourhoods (optional)
            </label>
            <input
              className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.05)] px-3 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none placeholder:text-[#6b6b60]"
              placeholder="Port Credit, King West, Erin Mills..."
            />
          </div>
          <button className="fs mt-1 w-full bg-[#c8a96e] px-4 py-3 font-['Syne',sans-serif] text-[0.88rem] font-bold uppercase tracking-[0.05em] text-black transition-colors hover:bg-[#e4c98a]">
            Activate My Agent →
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="flex items-center justify-between border-t border-[rgba(200,169,110,0.2)] px-16 py-10 max-md:flex-col max-md:gap-3 max-md:px-6">
        <div className="footer-logo text-[1.1rem] font-extrabold">
          <span className="text-[#c8a96e]">416</span>
          Homes
        </div>
        <div className="footer-copy font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">
          Covering Toronto &amp; Mississauga · Powered by Gemini + open-source tooling
        </div>
        <div className="footer-copy font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">
          © 2025 416Homes · Early Access
        </div>
      </footer>
    </div>
  );
}


