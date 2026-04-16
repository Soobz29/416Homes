"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000")
).replace(/\/$/, "");

const TOUR_STEPS = ["pending", "processing", "classifying", "building", "completed", "failed"] as const;
type TourStatus = (typeof TOUR_STEPS)[number];

const STEP_LABELS: Record<string, string> = {
  pending: "Fetching photos",
  processing: "Fetching photos",
  classifying: "Classifying rooms",
  building: "Building tour",
  completed: "Tour ready",
};

const FEATURES = [
  {
    title: "Room-by-room navigation",
    desc: "Buyers click any room to see all photos from that space",
    icon: "⬡",
  },
  {
    title: "Shareable link",
    desc: "Send directly to buyers or embed on any website",
    icon: "↗",
  },
  {
    title: "Works on any listing",
    desc: "Paste a Realtor.ca or Zoocasa URL — we handle the rest",
    icon: "◈",
  },
];

function stepIndex(status: TourStatus): number {
  const map: Record<TourStatus, number> = {
    pending: 0,
    processing: 1,
    classifying: 2,
    building: 3,
    completed: 4,
    failed: -1,
  };
  return map[status] ?? 0;
}

export default function ToursPage() {
  const [listingUrl, setListingUrl] = useState("");
  const [email, setEmail] = useState("");
  const [agentName, setAgentName] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<TourStatus>("pending");
  const [tourUrl, setTourUrl] = useState<string | null>(null);
  const [showProgress, setShowProgress] = useState(false);
  const [embedCopied, setEmbedCopied] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Detect ?status=success return from Stripe (production flow)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("status") === "success") {
      const storedJobId = window.sessionStorage.getItem("tour_job_id");
      if (storedJobId) {
        setJobId(storedJobId);
        setShowProgress(true);
      }
    }
  }, []);

  const pollJob = useCallback(
    async (id: string) => {
      try {
        const res = await fetch(`${API_BASE}/api/tour-jobs/${id}`);
        if (!res.ok) return;
        const data = await res.json();
        const s: TourStatus = data.status ?? "pending";
        setStatus(s);
        if (s === "completed") {
          setTourUrl(data.tour_url ?? null);
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
        if (s === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      } catch (e) {
        console.error("Tour poll error:", e);
      }
    },
    []
  );

  useEffect(() => {
    if (!jobId || !showProgress) return;
    pollJob(jobId);
    pollRef.current = setInterval(() => pollJob(jobId), 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId, showProgress, pollJob]);

  const handleSubmit = useCallback(async () => {
    const trimmedUrl = listingUrl.trim();
    const trimmedEmail = email.trim();

    if (!trimmedUrl) {
      alert("Please enter a listing URL");
      return;
    }
    if (!trimmedEmail || !trimmedEmail.includes("@")) {
      alert("Please enter a valid email address");
      return;
    }

    const fullUrl =
      trimmedUrl.startsWith("http://") || trimmedUrl.startsWith("https://")
        ? trimmedUrl
        : "https://" + trimmedUrl;

    setSubmitLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/tour-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          listing_url: fullUrl,
          agent_email: trimmedEmail,
          agent_name: agentName.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      const id = data.job_id || data.id;
      if (!id) throw new Error("No job ID returned from server");

      if (typeof window !== "undefined") {
        window.sessionStorage.setItem("tour_job_id", id);
      }
      setJobId(id);
      setStatus("pending");
      setTourUrl(null);
      setShowProgress(true);
      setDemoMode(false);
    } catch (err: unknown) {
      console.error("Tour submit error:", err);
      // Demo fallback
      setDemoMode(true);
      const fakeId = "demo-" + Math.random().toString(36).slice(2, 8);
      setJobId(fakeId);
      setStatus("pending");
      setTourUrl(null);
      setShowProgress(true);
      runDemoSimulation(fakeId);
    } finally {
      setSubmitLoading(false);
    }
  }, [listingUrl, email, agentName]);

  function runDemoSimulation(id: string) {
    const transitions: { s: TourStatus; delay: number }[] = [
      { s: "processing", delay: 1500 },
      { s: "classifying", delay: 4000 },
      { s: "building", delay: 7500 },
      { s: "completed", delay: 11000 },
    ];
    transitions.forEach(({ s, delay }) => {
      setTimeout(() => {
        setStatus(s);
        if (s === "completed") {
          setTourUrl(`/tours/${id}`);
        }
      }, delay);
    });
  }

  const embedCode = tourUrl
    ? `<iframe src="${tourUrl}" width="100%" height="600" frameborder="0" allowfullscreen></iframe>`
    : "";

  const handleCopyEmbed = useCallback(() => {
    if (!embedCode) return;
    navigator.clipboard.writeText(embedCode).then(() => {
      setEmbedCopied(true);
      setTimeout(() => setEmbedCopied(false), 2000);
    });
  }, [embedCode]);

  const currentStepIdx = stepIndex(status);
  const progressSteps: { key: TourStatus; label: string }[] = [
    { key: "processing", label: "Fetching photos" },
    { key: "classifying", label: "Classifying rooms" },
    { key: "building", label: "Building tour" },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a08] text-[#f5f4ef]">
      {/* Nav */}
      <nav className="flex items-center justify-between border-b border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.8)] px-16 py-6 backdrop-blur-xl max-md:px-6">
        <div className="logo text-[1.2rem] font-extrabold">
          <span className="text-[#c8a96e]">416</span>
          Homes{" "}
          <span className="align-middle font-['DM_Mono',monospace] text-[0.75rem] font-normal tracking-[0.1em] text-[#6b6b60]">
            TOURS
          </span>
        </div>
        <Link
          href="/"
          className="flex items-center gap-2 font-['DM_Mono',monospace] text-[0.7rem] uppercase tracking-[0.1em] text-[#6b6b60] no-underline hover:text-[#c8a96e]"
        >
          Back to Dashboard
        </Link>
      </nav>

      {/* Hero */}
      <section className="border-b border-[rgba(200,169,110,0.2)] px-16 pb-16 pt-24 max-md:px-6">
        <div className="hero-tag mb-6 flex items-center gap-3 font-['DM_Mono',monospace] text-[0.65rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          <span className="h-px w-6 bg-[#c8a96e]" />
          Virtual Tour Builder
        </div>
        <h1 className="mb-5 max-w-[20ch] text-[clamp(2.2rem,4vw,4rem)] font-extrabold leading-[0.95] tracking-[-0.03em]">
          Interactive Virtual Tours —{" "}
          <span className="text-[#c8a96e]">$49 CAD</span>
        </h1>
        <p className="max-w-[52ch] font-['DM_Mono',monospace] text-[0.85rem] leading-[1.8] text-[#6b6b60]">
          From listing URL to shareable room-by-room tour in minutes. Paste your listing URL below.
        </p>
      </section>

      {/* Order form + progress */}
      <section className="grid gap-16 border-b border-[rgba(200,169,110,0.2)] px-16 py-20 md:grid-cols-2 max-md:px-6">
        {/* Left: cost summary */}
        <div>
          <h2 className="mb-4 text-[1.6rem] font-extrabold tracking-[-0.02em]">
            Generate your virtual tour
          </h2>
          <p className="mb-6 font-['DM_Mono',monospace] text-[0.78rem] leading-[1.8] text-[#6b6b60]">
            Paste any Realtor.ca or Zoocasa listing URL. We fetch all photos, classify each room
            using AI, and build an interactive room-by-room tour — automatically.
          </p>
          <div className="border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-6">
            {[
              ["Price", "$49 CAD"],
              ["Turnaround", "~5 minutes"],
              ["Room detection", "AI-powered"],
              ["Output", "Hosted shareable link"],
              ["Embed", "Copy iframe code"],
            ].map(([label, value], i) => (
              <div
                key={label}
                className={`flex items-center justify-between border-b border-[rgba(200,169,110,0.1)] py-2 font-['DM_Mono',monospace] text-[0.72rem] ${
                  i === 4 ? "border-b-0" : ""
                }`}
              >
                <span className="text-[#6b6b60]">{label}</span>
                <span className={i === 0 ? "text-[1.05rem] font-bold text-[#c8a96e]" : "text-[#f5f4ef]"}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: form or progress */}
        <div>
          {!showProgress ? (
            <div className="border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-10">
              <div className="mb-1 text-[1.1rem] font-bold">Submit Your Listing</div>
              <p className="mb-6 font-['DM_Mono',monospace] text-[0.7rem] leading-[1.6] text-[#6b6b60]">
                Enter your listing URL and we&apos;ll build an interactive tour in minutes.
              </p>

              <div className="mb-4">
                <label className="mb-1 block font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
                  Listing URL *
                </label>
                <input
                  type="text"
                  value={listingUrl}
                  onChange={(e) => setListingUrl(e.target.value)}
                  className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none focus:border-[#c8a96e]"
                  placeholder="https://www.realtor.ca/real-estate/..."
                />
              </div>

              <div className="mb-4">
                <label className="mb-1 block font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
                  Email Address *
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none focus:border-[#c8a96e]"
                  placeholder="agent@yourbrokerage.com"
                />
              </div>

              <div className="mb-6">
                <label className="mb-1 block font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
                  Agent Name (optional)
                </label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  className="w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none focus:border-[#c8a96e]"
                  placeholder="Jane Smith"
                />
              </div>

              <button
                type="button"
                disabled={submitLoading}
                onClick={handleSubmit}
                className="mt-2 w-full bg-[#c8a96e] px-4 py-4 font-['Syne',sans-serif] text-[0.95rem] font-extrabold uppercase tracking-[0.05em] text-black transition-all hover:-translate-y-[1px] hover:bg-[#e4c98a] disabled:cursor-not-allowed disabled:transform-none disabled:opacity-50"
              >
                {submitLoading ? "Processing..." : "Generate Tour — $49 CAD"}
              </button>

              <p className="mt-3 text-center font-['DM_Mono',monospace] text-[0.62rem] text-[#6b6b60]">
                Stripe payment coming soon — free demo for now.
                <br />
                Questions? hello@416homes.ca
              </p>
            </div>
          ) : status === "completed" && tourUrl ? (
            /* Completion */
            <div className="border border-[rgba(46,213,115,0.25)] bg-[rgba(46,213,115,0.05)] p-10">
              <div className="mb-1 text-[1rem] font-bold text-[#2ed573]">Your tour is ready!</div>
              <p className="mb-6 font-['DM_Mono',monospace] text-[0.72rem] text-[#6b6b60]">
                Share the link below or embed it on your website.
              </p>
              <a
                href={tourUrl}
                target="_blank"
                rel="noreferrer"
                className="mb-6 inline-block w-full bg-[#c8a96e] px-6 py-4 text-center font-['Syne',sans-serif] text-[0.95rem] font-extrabold uppercase tracking-[0.05em] text-black no-underline transition-all hover:-translate-y-[1px] hover:bg-[#e4c98a]"
              >
                View Your Tour →
              </a>

              <div className="mt-4">
                <div className="mb-2 font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
                  Embed Code
                </div>
                <div className="relative">
                  <pre className="overflow-x-auto border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.03)] p-4 font-['DM_Mono',monospace] text-[0.65rem] leading-[1.6] text-[#c8a96e] whitespace-pre-wrap break-all">
                    {embedCode}
                  </pre>
                  <button
                    type="button"
                    onClick={handleCopyEmbed}
                    className="mt-2 w-full border border-[rgba(200,169,110,0.3)] py-2 font-['DM_Mono',monospace] text-[0.7rem] uppercase tracking-[0.1em] text-[#c8a96e] transition-colors hover:border-[#c8a96e] hover:bg-[rgba(200,169,110,0.06)]"
                  >
                    {embedCopied ? "Copied!" : "Copy Embed Code"}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Progress */
            <div className="border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-10">
              <div className="mb-1 text-[1rem] font-bold">
                {demoMode ? "Demo — generating tour..." : "Generating your tour..."}
              </div>
              <div className="mb-8 font-['DM_Mono',monospace] text-[0.72rem] text-[#c8a96e]">
                {listingUrl.length > 60 ? listingUrl.slice(0, 60) + "..." : listingUrl}
              </div>

              <div className="flex flex-col gap-0">
                {progressSteps.map((step, i) => {
                  const stepDone = currentStepIdx > i + 1;
                  const stepActive = currentStepIdx === i + 1;
                  return (
                    <div
                      key={step.key}
                      className="flex items-center gap-4 border-b border-[rgba(200,169,110,0.08)] py-4 last:border-b-0"
                    >
                      <div
                        className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border text-[0.75rem] ${
                          stepDone
                            ? "border-[#2ed573] bg-[rgba(46,213,115,0.15)]"
                            : stepActive
                              ? "animate-pulse border-[#c8a96e] bg-[rgba(200,169,110,0.1)]"
                              : "border-[rgba(200,169,110,0.2)] opacity-30"
                        }`}
                      >
                        {stepDone ? "✓" : String(i + 1)}
                      </div>
                      <div>
                        <div className="text-[0.85rem] font-semibold">{step.label}</div>
                        <div className="font-['DM_Mono',monospace] text-[0.68rem] text-[#6b6b60]">
                          {stepDone
                            ? "Complete"
                            : stepActive
                              ? "Working..."
                              : "Waiting..."}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {demoMode && (
                <p className="mt-6 font-['DM_Mono',monospace] text-[0.62rem] text-[#6b6b60]">
                  Demo mode active — connect API for real tour generation.
                </p>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Feature callouts */}
      <section className="border-b border-[rgba(200,169,110,0.2)] px-16 py-20 max-md:px-6">
        <div className="mb-3 font-['DM_Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          What you get
        </div>
        <h2 className="mb-12 text-[clamp(1.6rem,2.5vw,2.8rem)] font-extrabold tracking-[-0.02em]">
          Everything buyers need, nothing they don&apos;t.
        </h2>
        <div className="grid gap-0 md:grid-cols-3">
          {FEATURES.map((f, i) => (
            <div
              key={f.title}
              className={`border-r border-[rgba(200,169,110,0.2)] p-8 last:border-r-0 ${
                i === 0 ? "" : ""
              }`}
            >
              <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-full border border-[rgba(200,169,110,0.35)] font-['DM_Mono',monospace] text-[1rem] text-[#c8a96e]">
                {f.icon}
              </div>
              <div className="mb-2 text-[0.9rem] font-bold">{f.title}</div>
              <div className="font-['DM_Mono',monospace] text-[0.72rem] leading-[1.65] text-[#6b6b60]">
                {f.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className="flex items-center justify-between border-t border-[rgba(200,169,110,0.2)] px-16 py-8 max-md:flex-col max-md:gap-3 max-md:px-6">
        <Link
          href="/"
          className="text-[1rem] font-extrabold no-underline transition-colors hover:text-[#c8a96e]"
        >
          <span className="text-[#c8a96e]">416</span>Homes Tours
        </Link>
        <div className="font-['DM_Mono',monospace] text-[0.6rem] text-[#6b6b60]">
          Interactive virtual tours · Toronto + Mississauga · $49
        </div>
        <div className="font-['DM_Mono',monospace] text-[0.6rem] text-[#6b6b60]">
          © 2025 416Homes · hello@416homes.ca
        </div>
      </footer>
    </div>
  );
}
