"use client";

import { useState } from "react";
import Link from "next/link";

export default function VideoPage() {
  const [tier, setTier] = useState<"basic" | "cinematic" | "premium">("cinematic");

  const selectTier = (t: "basic" | "cinematic" | "premium", price: number) => {
    setTier(t);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem("selectedTier", t);
      window.sessionStorage.setItem("selectedPrice", String(price));
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a08] text-[#f5f4ef]">
      {/* Nav */}
      <nav className="flex items-center justify-between border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.8)] px-16 py-6 backdrop-blur-xl max-md:px-6">
        <div className="logo text-[1.2rem] font-extrabold">
          <span className="text-[#c8a96e]">416</span>
          Homes <span className="align-middle font-['DM Mono',monospace] text-[0.75rem] font-normal tracking-[0.1em] text-[#6b6b60]">
            VIDEO
          </span>
        </div>
        <Link
          href="/"
          className="nav-back flex items-center gap-2 font-['DM Mono',monospace] text-[0.7rem] uppercase tracking-[0.1em] text-[#6b6b60] no-underline hover:text-[#c8a96e]"
        >
          ← Back to 416Homes
        </Link>
      </nav>

      {/* Hero */}
      <section className="hero grid gap-12 border-b border-[rgba(200,169,110,0.2)] px-16 pb-16 pt-24 md:grid-cols-2 max-md:px-6">
        <div>
          <div className="hero-tag mb-6 flex items-center gap-3 font-['DM Mono',monospace] text-[0.65rem] uppercase tracking-[0.2em] text-[#c8a96e]">
            <span className="h-px w-6 bg-[#c8a96e]" />
            Cinematic Listing Videos for GTA Agents
          </div>
          <h1 className="mb-6 text-[clamp(2.5rem,4vw,4.5rem)] font-extrabold leading-[0.95] tracking-[-0.03em]">
            Professional listing
            <br />
            videos from <span className="text-[#c8a96e]">$
              {tier === "basic" ? "99" : tier === "cinematic" ? "249" : "299"}.</span>
            <br />
            Not $5,000.
          </h1>
          <p className="hero-sub mb-8 max-w-[44ch] font-['DM Mono',monospace] text-[0.85rem] leading-[1.8] text-[#6b6b60]">
            Paste any Realtor.ca or Zillow URL. Our AI pipeline animates your listing photos, writes the narration,
            records the voiceover, and delivers a polished 30-second video — in under 15 minutes.
          </p>
          <div className="price-block mb-10 flex items-baseline gap-6">
            <div className="price-main text-[3rem] font-extrabold text-[#c8a96e]">
              {tier === "basic" ? "$99" : tier === "cinematic" ? "$249" : "$299"}
            </div>
            <div className="price-compare font-['DM Mono',monospace] text-[0.75rem] leading-[1.5] text-[#6b6b60]">
              Tiered per-listing pricing
              <br />
              <span className="line-through text-[#555]">Industry avg: $1,000–$5,000</span>
            </div>
          </div>
          <button
            className="submit-btn inline-block bg-[#c8a96e] px-10 py-4 font-['Syne',sans-serif] text-[0.95rem] font-extrabold uppercase tracking-[0.05em] text-black transition-all hover:-translate-y-[1px] hover:bg-[#e4c98a]"
            onClick={() => {
              const el = document.getElementById("order");
              if (el) el.scrollIntoView({ behavior: "smooth" });
            }}
          >
            Order a Video →
          </button>
        </div>

        {/* Video preview — Vimeo sample */}
        <div className="video-preview relative aspect-[16/9] overflow-hidden border border-[rgba(200,169,110,0.2)] bg-black">
          <div className="video-preview-inner relative h-full w-full overflow-hidden bg-black">
            <div className="relative w-full" style={{ paddingTop: "56.25%" }}>
              <iframe
                src="https://player.vimeo.com/video/1172407404?badge=0&autopause=0&player_id=0&app_id=58479&autoplay=1&loop=1"
                className="absolute left-0 top-0 h-full w-full border-0"
                allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share"
                referrerPolicy="strict-origin-when-cross-origin"
                title="416Homes Sample — 30 Sec"
              />
            </div>
            <div className="vp-caption absolute bottom-[8%] left-0 right-0 px-6">
              <div className="vp-headline mb-1 text-[1.1rem] font-bold">
                Where Heritage Meets Modern Luxury
              </div>
              <div className="vp-address font-['DM Mono',monospace] text-[0.65rem] text-[#6b6b60]">
                218 Broadview Ave, Leslieville ·{" "}
                <span className="vp-price-tag font-bold text-[#c8a96e]">$1,149,000</span>
              </div>
            </div>
            <div className="vp-badge absolute right-[5%] top-[10%] border border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.7)] px-2 py-1 font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.1em] text-[#c8a96e]">
              AI Generated
            </div>
          </div>
        </div>
      </section>

      {/* Process */}
      <section className="process border-b border-[rgba(200,169,110,0.2)] px-16 py-20 max-md:px-6">
        <div className="sec-tag mb-3 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          How It Works
        </div>
        <h2 className="sec-h mb-12 text-[clamp(1.6rem,2.5vw,2.8rem)] font-extrabold tracking-[-0.02em]">
          Five AI tools, one URL, one video.
        </h2>
        <div className="steps grid gap-0 md:grid-cols-5">
          {[
            {
              n: "01",
              icon: "🔗",
              t: "Paste listing URL",
              d: "Realtor.ca or Zillow. We scrape the best 6 photos and all property details automatically.",
              tool: "",
            },
            {
              n: "02",
              icon: "✍️",
              t: "AI writes the script",
              d: "Gemini analyzes the listing and writes a 30-second cinematic voiceover script tailored to the property.",
              tool: "Gemini 2.0",
            },
            {
              n: "03",
              icon: "🎙️",
              t: "AI records narration",
              d: "ElevenLabs generates professional narration. Choose from warm female or deep male voice.",
              tool: "ElevenLabs",
            },
            {
              n: "04",
              icon: "🎬",
              t: "Photos animated",
              d: "Each photo gets a cinematic dolly shot, pan, or zoom — luxury motion styling from Calico AI.",
              tool: "Calico AI",
            },
            {
              n: "05",
              icon: "📥",
              t: "Download MP4",
              d: "Final video assembled with captions, music, and narration. Ready to post on Instagram, MLS, or email.",
              tool: "~12 min total",
            },
          ].map((s) => (
            <div
              key={s.n}
              className="step relative border-r border-[rgba(200,169,110,0.2)] p-8 last:border-r-0"
            >
              <div className="step-n mb-4 font-['DM Mono',monospace] text-[0.6rem] text-[#c8a96e] tracking-[0.15em]">
                {s.n}
              </div>
              <div className="step-ico mb-3 text-[1.3rem]">{s.icon}</div>
              <div className="step-t mb-2 text-[0.9rem] font-bold">{s.t}</div>
              <div className="step-d font-['DM Mono',monospace] text-[0.68rem] leading-[1.65] text-[#6b6b60]">
                {s.d}
              </div>
              {s.tool && (
                <div className="step-tool mt-2 inline-block border border-[rgba(200,169,110,0.2)] px-1.5 py-0.5 font-['DM Mono',monospace] text-[0.58rem] text-[#c8a96e]">
                  {s.tool}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Order section (structure + copy) */}
      <section id="order" className="order-section grid gap-16 border-b border-[rgba(200,169,110,0.2)] px-16 py-20 md:grid-cols-2 max-md:px-6">
        <div className="order-info">
          <h2 className="mb-4 text-[2rem] font-extrabold tracking-[-0.02em]">
            Order your listing video
          </h2>
          <p className="mb-6 font-['DM Mono',monospace] text-[0.78rem] leading-[1.8] text-[#6b6b60]">
            Paste your listing URL below. We&apos;ll scrape the photos, write the script, record the voiceover,
            animate the images, and assemble your video — all automatically. Download ready in ~12 minutes.
          </p>
          <div className="cost-breakdown border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-6">
            {[
              ["Basic", "$99 CAD"],
              ["Cinematic (Most Popular)", "$249 CAD"],
              ["Premium", "$299 CAD"],
              ["Turnaround time", "~12 minutes"],
              ["Video length", "30 seconds"],
              ["Format", "1920×1080 MP4"],
              ["Revisions", "1 free revision"],
              ["You pay", tier === "basic" ? "$99" : tier === "cinematic" ? "$249" : "$299"],
            ].map(([label, value], i) => (
              <div
                key={label}
                className={`cost-row flex items-center justify-between border-b border-[rgba(200,169,110,0.1)] py-2 text-[0.72rem] font-['DM Mono',monospace] ${
                  i === 7 ? "border-b-0 text-[0.85rem] font-bold" : ""
                }`}
              >
                <span className="cost-label text-[#6b6b60]">{label}</span>
                <span className={`cost-value ${i === 7 ? "text-[1.1rem] text-[#c8a96e]" : "text-[#f5f4ef]"}`}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Simplified non-functional form clone */}
        <div className="order-form border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-10">
          <div className="form-title mb-1 text-[1.1rem] font-bold">Submit Your Listing</div>
          <p className="form-sub mb-6 font-['DM Mono',monospace] text-[0.7rem] leading-[1.6] text-[#6b6b60]">
            Provide a listing URL. Your selected tier will be attached to this order.
          </p>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
              Listing URL *
            </label>
            <input
              type="url"
              className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
              placeholder="https://www.realtor.ca/real-estate/..."
            />
          </div>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
              Your Email *
            </label>
            <input
              type="email"
              className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
              placeholder="agent@yourbrokerage.com"
            />
          </div>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
              Voiceover Style
            </label>
            <div className="voice-select grid grid-cols-3 gap-2">
              {[
                ["Warm Female", "Smooth & confident"],
                ["Deep Male", "Warm & authoritative"],
                ["Premium Male", "Rich & cinematic"],
              ].map(([name, desc]) => (
                <div
                  key={name}
                  className="voice-opt cursor-pointer border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] p-3 text-center text-sm"
                >
                  <div className="voice-name text-[0.82rem] font-semibold">{name}</div>
                  <div className="voice-desc mt-1 font-['DM Mono',monospace] text-[0.6rem] text-[#6b6b60]">
                    {desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <button className="submit-btn mt-2 w-full bg-[#c8a96e] px-4 py-4 font-['Syne',sans-serif] text-[0.95rem] font-extrabold uppercase tracking-[0.05em] text-black transition-all hover:-translate-y-[1px] hover:bg-[#e4c98a]">
            Order Video — $
            {tier === "basic" ? "99" : tier === "cinematic" ? "249" : "299"} CAD →
          </button>
          <p className="form-note mt-3 text-center font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">
            Secure payment via Stripe. Video delivered to your email when ready.
            <br />
            Questions? hello@416homes.ca
          </p>
        </div>
      </section>

      {/* Social proof + FAQ text left as-is in HTML; we can port those 1:1 next if you want the full page parity. */}

      <footer className="flex items-center justify-between border-t border-[rgba(200,169,110,0.2)] px-16 py-8 max-md:flex-col max-md:gap-3 max-md:px-6">
        <div className="footer-logo text-[1rem] font-extrabold">
          <span className="text-[#c8a96e]">416</span>
          Homes Video
        </div>
        <div className="footer-copy font-['DM Mono',monospace] text-[0.6rem] text-[#6b6b60]">
          Cinematic listing videos · Toronto + Mississauga · From $199
        </div>
        <div className="footer-copy font-['DM Mono',monospace] text-[0.6rem] text-[#6b6b60]">
          © 2025 416Homes · hello@416homes.ca
        </div>
      </footer>
    </div>
  );
}


