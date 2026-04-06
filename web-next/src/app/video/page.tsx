"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000")).replace(/\/$/, "");
const STEP_ORDER = ["scrape", "script", "audio", "animate", "assemble"] as const;
const STEP_MAP: Record<string, [string, string]> = {
  scrape: ["iScrape", "mScrape"],
  script: ["iScript", "mScript"],
  audio: ["iAudio", "mAudio"],
  animate: ["iAnimate", "mAnimate"],
  assemble: ["iAssemble", "mAssemble"],
  complete: ["iAssemble", "mAssemble"],
};

type Tier = "basic" | "cinematic" | "premium";
const TIERS: { id: Tier; price: number; title: string; badge?: string; features: string[] }[] = [
  { id: "basic", price: 99, title: "Basic", features: ["Ken Burns photo transitions", "Professional voiceover narration", "Background music", "40–60 second video"] },
  { id: "cinematic", price: 249, title: "Cinematic", badge: "Most Popular", features: ["Everything in Basic", "Cinematic animated clips", "Smooth camera movements", "Professional transitions"] },
  { id: "premium", price: 299, title: "Premium", features: ["Everything in Cinematic", "Photo enhancement", "Color grading", "Priority processing"] },
];

const VOICES: { id: string; name: string; desc: string }[] = [
  { id: "female_luxury", name: "Warm Female", desc: "Smooth & confident" },
  { id: "male_luxury", name: "Deep Male", desc: "Warm & authoritative" },
  { id: "male_deep", name: "Premium Male", desc: "Rich & cinematic" },
];

function VideoOrderForm({
  uploadMethod,
  setUploadMethod,
  selectedVoice,
  setSelectedVoice,
  tier,
  price,
  submitLoading,
  onSubmit,
  formListingUrl,
  setFormListingUrl,
  formEmail,
  setFormEmail,
  formName,
  setFormName,
  formCustomAddress,
  setFormCustomAddress,
  formCustomPrice,
  setFormCustomPrice,
  formCustomBeds,
  setFormCustomBeds,
  setFormCustomPhotos,
  setFormCustomMusic,
}: {
  uploadMethod: "url" | "custom";
  setUploadMethod: (m: "url" | "custom") => void;
  selectedVoice: string;
  setSelectedVoice: (v: string) => void;
  tier: Tier;
  price: number;
  submitLoading: boolean;
  onSubmit: () => void;
  formListingUrl: string;
  setFormListingUrl: (s: string) => void;
  formEmail: string;
  setFormEmail: (s: string) => void;
  formName: string;
  setFormName: (s: string) => void;
  formCustomAddress: string;
  setFormCustomAddress: (s: string) => void;
  formCustomPrice: string;
  setFormCustomPrice: (s: string) => void;
  formCustomBeds: string;
  setFormCustomBeds: (s: string) => void;
  setFormCustomPhotos: (f: FileList | null) => void;
  setFormCustomMusic: (f: File | null) => void;
}) {
  return (
    <div className="order-form border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.025)] p-10">
      <div className="form-title mb-1 text-[1.1rem] font-bold">Submit Your Listing</div>
      <p className="form-sub mb-6 font-['DM Mono',monospace] text-[0.7rem] leading-[1.6] text-[#6b6b60]">
        Provide a listing URL or upload custom photos. Your selected tier will be attached to this order.
      </p>
      <div className="method-toggle mb-6 flex gap-4">
        <button
          type="button"
          onClick={() => setUploadMethod("url")}
          className={`submit-btn border px-4 py-2 text-[0.8rem] transition-colors ${
            uploadMethod === "url"
              ? "border-[#D4AF37] bg-[#D4AF37] text-[#0B0B0B]"
              : "border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.025)] text-[#f5f4ef]"
          }`}
        >
          Fetch by URL
        </button>
        <button
          type="button"
          onClick={() => setUploadMethod("custom")}
          className={`submit-btn border px-4 py-2 text-[0.8rem] transition-colors ${
            uploadMethod === "custom"
              ? "border-[#D4AF37] bg-[#D4AF37] text-[#0B0B0B]"
              : "border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.025)] text-[#f5f4ef]"
          }`}
        >
          Custom Upload
        </button>
      </div>
      {uploadMethod === "url" && (
        <div className="fg mb-4">
          <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
            Listing URL *
          </label>
          <input
            type="text"
            value={formListingUrl}
            onChange={(e) => setFormListingUrl(e.target.value)}
            className="fi w-full border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
            placeholder="zoocasa.com/oakville-on-real-estate/136-n-park-blvd"
          />
        </div>
      )}
      {uploadMethod === "custom" && (
        <>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
              Listing Address *
            </label>
            <input
              type="text"
              value={formCustomAddress}
              onChange={(e) => setFormCustomAddress(e.target.value)}
              className="fi w-full border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
              placeholder="123 Main St, Toronto"
            />
          </div>
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div className="fg">
              <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
                Price
              </label>
              <input
                type="text"
                value={formCustomPrice}
                onChange={(e) => setFormCustomPrice(e.target.value)}
                className="fi w-full border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
                placeholder="$1,149,000"
              />
            </div>
            <div className="fg">
              <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
                Beds & Baths
              </label>
              <input
                type="text"
                value={formCustomBeds}
                onChange={(e) => setFormCustomBeds(e.target.value)}
                className="fi w-full border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
                placeholder="3 Beds, 2 Baths"
              />
            </div>
          </div>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
              Photos (Min 4, Max 10) *
            </label>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              className="fi w-full border border-[rgba(212,175,55,0.2)] bg-transparent px-4 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
              onChange={(e) => setFormCustomPhotos(e.target.files)}
            />
          </div>
          <div className="fg mb-4">
            <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
              Custom Music (Optional MP3)
            </label>
            <input
              type="file"
              accept="audio/mpeg,audio/mp3"
              className="fi w-full border border-[rgba(212,175,55,0.2)] bg-transparent px-4 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
              onChange={(e) => setFormCustomMusic(e.target.files?.[0] ?? null)}
            />
            <p className="mt-1 font-['DM Mono',monospace] text-[0.6rem] text-[#6b6b60]">
              If provided, we&apos;ll use this track instead of the default background music.
            </p>
          </div>
        </>
      )}
      <div className="fg mb-4">
        <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
          Your Email *
        </label>
        <input
          type="email"
          value={formEmail}
          onChange={(e) => setFormEmail(e.target.value)}
          className="fi w-full border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
          placeholder="agent@yourbrokerage.com"
        />
      </div>
      <div className="fg mb-4">
        <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
          Your Name
        </label>
        <input
          type="text"
          value={formName}
          onChange={(e) => setFormName(e.target.value)}
          className="fi w-full border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
          placeholder="Jane Smith"
        />
      </div>
      <div className="fg mb-4">
        <label className="fl mb-1 block font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.15em] text-[#6b6b60]">
          Voiceover Style
        </label>
        <div className="voice-select grid grid-cols-3 gap-2">
          {VOICES.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => setSelectedVoice(v.id)}
              className={`voice-opt cursor-pointer border p-3 text-center transition-colors ${
                selectedVoice === v.id
                  ? "border-[#D4AF37] bg-[rgba(212,175,55,0.08)]"
                  : "border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.02)] hover:border-[rgba(212,175,55,0.5)]"
              }`}
            >
              <div className="voice-name text-[0.82rem] font-semibold">{v.name}</div>
              <div className="voice-desc mt-1 font-['DM Mono',monospace] text-[0.6rem] text-[#6b6b60]">{v.desc}</div>
            </button>
          ))}
        </div>
      </div>
      <button
        type="button"
        disabled={submitLoading}
        onClick={onSubmit}
        className="submit-btn mt-2 w-full bg-[#D4AF37] px-4 py-4 font-['Syne',sans-serif] text-[0.95rem] font-extrabold uppercase tracking-[0.05em] text-black transition-all hover:-translate-y-[1px] hover:bg-[#F3E5AB] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
      >
        {submitLoading ? "Processing..." : `Order ${tier.charAt(0).toUpperCase() + tier.slice(1)} — $${price} CAD →`}
      </button>
      <p className="form-note mt-3 text-center font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">
        Secure payment via Stripe. Video delivered to your email when ready.
        <br />
        Questions? hello@416homes.ca
      </p>
    </div>
  );
}

function ProgressPanel({
  progressAddr,
  stepMessages,
  stepStates,
  downloadVisible,
  downloadSubtitle,
  jobId,
  videoUrl,
  videoLoadError,
  onVideoError,
}: {
  progressAddr: string;
  stepMessages: Record<string, string>;
  stepStates: Record<string, "pending" | "active" | "done">;
  downloadVisible: boolean;
  downloadSubtitle: string;
  jobId: string | null;
  videoUrl: string | null;
  videoLoadError: boolean;
  onVideoError: () => void;
}) {
  const steps = [
    { key: "scrape", label: "Fetching listing & photos", icon: "🔗", msgKey: "scrape" },
    { key: "script", label: "Writing voiceover script", icon: "✍️", msgKey: "script" },
    { key: "audio", label: "Recording narration + music", icon: "🎙️", msgKey: "audio" },
    { key: "animate", label: "Animating listing photos", icon: "🎬", msgKey: "animate" },
    { key: "assemble", label: "Assembling final video", icon: "📽️", msgKey: "assemble" },
  ];
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000")).replace(/\/$/, "");
  return (
    <div className="progress-panel border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.025)] p-10">
      <div className="prog-title mb-1 text-[1rem] font-bold">Generating your video...</div>
      <div className="prog-addr mb-8 font-['DM Mono',monospace] text-[0.72rem] text-[#D4AF37]">{progressAddr}</div>
      <div className="prog-steps flex flex-col gap-0">
        {steps.map((s) => (
          <div key={s.key} className="prog-step flex items-center gap-4 border-b border-[rgba(212,175,55,0.08)] py-4 last:border-b-0">
            <div
              className={`prog-icon flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border text-[0.75rem] ${
                stepStates[s.key] === "done"
                  ? "border-[#2ed573] bg-[rgba(46,213,115,0.15)]"
                  : stepStates[s.key] === "active"
                    ? "animate-pulse border-[#D4AF37] bg-[rgba(212,175,55,0.1)]"
                    : "border-[rgba(212,175,55,0.2)] opacity-30"
              }`}
            >
              {stepStates[s.key] === "done" ? "✓" : s.icon}
            </div>
            <div>
              <div className="prog-label text-[0.85rem] font-semibold">{s.label}</div>
              <div className="prog-msg font-['DM Mono',monospace] text-[0.68rem] text-[#6b6b60]">
                {stepMessages[s.msgKey] || (stepStates[s.key] === "pending" ? "Waiting..." : "Processing...")}
              </div>
            </div>
          </div>
        ))}
      </div>
      {downloadVisible && (
        <div className="download-block mt-8 border border-[rgba(46,213,115,0.2)] bg-[rgba(46,213,115,0.05)] p-6">
          <div className="dl-title text-[#2ed573] text-[1rem] font-bold">✅ Your video is ready!</div>
          <div className="dl-sub mb-4 font-['DM Mono',monospace] text-[0.7rem] text-[#6b6b60]">{downloadSubtitle}</div>
          {videoUrl && (
            <div className="mb-4 max-w-[640px] overflow-hidden rounded-lg bg-black">
              <video
                src={videoUrl}
                controls
                playsInline
                preload="metadata"
                className="w-full"
                onError={onVideoError}
              />
              {videoLoadError && (
                <p className="py-4 text-center text-sm text-[#6b6b60]">Video could not be loaded. Use the Download button below.</p>
              )}
            </div>
          )}
          <a
            href={videoUrl || (jobId ? `${apiBase}/video/download/${jobId}` : "#") || "#"}
            download
            className="dl-btn inline-block bg-[#2ed573] px-6 py-3 font-['Syne',sans-serif] text-[0.85rem] font-bold text-[#0B0B0B] no-underline"
          >
            ⬇ Download Video
          </a>
        </div>
      )}
    </div>
  );
}

export default function VideoPage() {
  const [tier, setTier] = useState<Tier>("cinematic");
  const [uploadMethod, setUploadMethod] = useState<"url" | "custom">("url");
  const [selectedVoice, setSelectedVoice] = useState("female_luxury");
  const [orderFormVisible, setOrderFormVisible] = useState(true);
  const [progressVisible, setProgressVisible] = useState(false);
  const [progressAddr, setProgressAddr] = useState("");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [stepMessages, setStepMessages] = useState<Record<string, string>>({});
  const [stepStates, setStepStates] = useState<Record<string, "pending" | "active" | "done">>({});
  const [downloadVisible, setDownloadVisible] = useState(false);
  const [downloadSubtitle, setDownloadSubtitle] = useState("");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoLoadError, setVideoLoadError] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [formListingUrl, setFormListingUrl] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formName, setFormName] = useState("");
  const [formCustomAddress, setFormCustomAddress] = useState("");
  const [formCustomPrice, setFormCustomPrice] = useState("");
  const [formCustomBeds, setFormCustomBeds] = useState("");
  const [formCustomPhotos, setFormCustomPhotos] = useState<FileList | null>(null);
  const [formCustomMusic, setFormCustomMusic] = useState<File | null>(null);

  const price = tier === "basic" ? 99 : tier === "cinematic" ? 249 : 299;

  const selectTier = useCallback((t: Tier, p: number) => {
    setTier(t);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem("selectedTier", t);
      window.sessionStorage.setItem("selectedPrice", String(p));
    }
  }, []);

  const showProgress = useCallback((jobId: string, addr: string) => {
    setCurrentJobId(jobId);
    setProgressAddr(addr);
    setOrderFormVisible(false);
    setProgressVisible(true);
    setStepMessages({});
    setStepStates({ scrape: "active", script: "pending", audio: "pending", animate: "pending", assemble: "pending" });
    setDownloadVisible(false);
    setVideoUrl(null);
    setVideoLoadError(false);
  }, []);

  const updateProgressFromApi = useCallback((data: { status?: string; progress_step?: string; progress_message?: string; listing_address?: string; error?: string; video_url?: string }, jobId: string | null) => {
    const step = data.progress_step || "scrape";
    const idx = STEP_ORDER.indexOf(step as typeof STEP_ORDER[number]);
    const next: Record<string, "pending" | "active" | "done"> = {};
    STEP_ORDER.forEach((s, i) => {
      if (i < idx) next[s] = "done";
      else if (i === idx) next[s] = "active";
      else next[s] = "pending";
    });
    setStepStates(next);
    setStepMessages((prev) => ({ ...prev, [step]: data.progress_message || "Processing..." }));
    if (data.status === "complete" || data.status === "completed") {
      STEP_ORDER.forEach((s) => (next[s] = "done"));
      setStepStates(next);
      setDownloadVisible(true);
      setDownloadSubtitle(data.listing_address || "Your listing video is ready");
      const playUrl = data.video_url || (jobId ? `${API_BASE}/video/download/${jobId}` : null);
      setVideoUrl(playUrl);
      setVideoLoadError(false);
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    if (data.status === "failed") {
      setStepMessages((prev) => ({ ...prev, assemble: `Error: ${data.error || "Unknown"}` }));
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
  }, []);

  useEffect(() => {
    if (!currentJobId || !progressVisible) return;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/video-jobs/${currentJobId}`);
        const data = await res.json();
        updateProgressFromApi(data, currentJobId);
      } catch (e) {
        console.error("Poll error:", e);
      }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [currentJobId, progressVisible, updateProgressFromApi]);

  const handleSubmit = useCallback(async () => {
    const email = formEmail.trim();
    if (!email || !email.includes("@")) {
      alert("Please enter a valid email address");
      return;
    }
    setSubmitLoading(true);

    try {
      if (uploadMethod === "url") {
        let url = formListingUrl.trim();
        if (!url) {
          alert("Please enter a listing URL");
          setSubmitLoading(false);
          return;
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
          url = "https://" + url;
        }

        const res = await fetch(`${API_BASE}/api/video-jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            listing_url: url,
            agent_email: email,
            agent_name: formName.trim(),
            voice: selectedVoice,
            tier,
            price_cad: price,
            use_veo: tier !== "basic",
          }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error((err as { detail?: string }).detail || `Server error ${res.status}`);
        }

        const data = await res.json();
        const jobId = data.job_id || data.id;
        if (jobId) {
          showProgress(jobId, url.length > 60 ? url.slice(0, 60) + "..." : url);
        } else {
          throw new Error("No job ID returned from server");
        }
      } else {
        const address = formCustomAddress.trim();
        if (!address) {
          alert("Please enter a listing address");
          setSubmitLoading(false);
          return;
        }
        const files = formCustomPhotos;
        if (!files || files.length < 4 || files.length > 10) {
          alert("Please upload between 4 and 10 photos");
          setSubmitLoading(false);
          return;
        }

        const formData = new FormData();
        formData.append("address", address);
        formData.append("price", formCustomPrice);
        formData.append("beds", formCustomBeds);
        formData.append("baths", "");
        formData.append("agent_email", email);
        formData.append("agent_name", formName.trim());
        formData.append("voice", selectedVoice);
        for (let i = 0; i < files.length; i++) {
          formData.append("photos", files[i]);
        }
        if (formCustomMusic) formData.append("music", formCustomMusic);

        const res = await fetch(`${API_BASE}/api/video-jobs/custom`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error((err as { detail?: string }).detail || `Server error ${res.status}`);
        }

        const data = await res.json();
        const jobId = data.job_id || data.id;
        if (jobId) {
          showProgress(jobId, address);
        } else {
          throw new Error("No job ID returned from server");
        }
      }
    } catch (err: unknown) {
      console.error("Submit error:", err);
      const message = err instanceof Error ? err.message : "Unknown error";
      alert(`Something went wrong: ${message}. Running demo mode.`);
      simulateDemo();
    } finally {
      setSubmitLoading(false);
    }
  }, [uploadMethod, formListingUrl, formEmail, formName, formCustomAddress, formCustomPrice, formCustomBeds, formCustomPhotos, formCustomMusic, selectedVoice, tier, price, showProgress]);

  function simulateDemo() {
    const jobId = "demo-" + Math.random().toString(36).slice(2, 8);
    showProgress(jobId, formListingUrl || formCustomAddress || "Demo listing");
    const steps = [
      { step: "scrape", msg: "Found 6 photos · 218 Broadview Ave", delay: 1500 },
      { step: "script", msg: 'Script complete · "Where Heritage Meets Modern Luxury"', delay: 3500 },
      { step: "audio", msg: "Voiceover recorded · Cinematic music generated", delay: 6000 },
      { step: "animate", msg: "All 6 clips animated with dolly shots", delay: 10000 },
      { step: "assemble", msg: "Final video assembled · 1920×1080 MP4", delay: 13000 },
    ];
    steps.forEach(({ step, msg, delay }) => {
      setTimeout(() => {
        setStepStates((prev) => {
          const next = { ...prev };
          const idx = STEP_ORDER.indexOf(step as typeof STEP_ORDER[number]);
          STEP_ORDER.forEach((s, i) => {
            if (i < idx) next[s] = "done";
            else if (i === idx) next[s] = "active";
            else next[s] = "pending";
          });
          return next;
        });
        setStepMessages((prev) => ({ ...prev, [step]: msg }));
      }, delay);
    });
    setTimeout(() => {
      setStepStates({ scrape: "done", script: "done", audio: "done", animate: "done", assemble: "done" });
      setDownloadVisible(true);
      setDownloadSubtitle("Demo mode — connect API for real video generation");
    }, 15000);
  }

  return (
    <div className="min-h-screen bg-[#0B0B0B] text-[#f5f4ef]">
      {/* Nav */}
      <nav className="flex items-center justify-between border-b border-[rgba(212,175,55,0.2)] bg-[rgba(10,10,8,0.8)] px-16 py-6 backdrop-blur-xl max-md:px-6">
        <div className="logo text-[1.2rem] font-extrabold">
          <span className="text-[#D4AF37]">416</span>
          Homes <span className="align-middle font-['DM Mono',monospace] text-[0.75rem] font-normal tracking-[0.1em] text-[#6b6b60]">
            VIDEO
          </span>
        </div>
        <Link
          href="/"
          className="nav-back flex items-center gap-2 font-['DM Mono',monospace] text-[0.7rem] uppercase tracking-[0.1em] text-[#6b6b60] no-underline hover:text-[#D4AF37]"
        >
          ← Back to 416Homes
        </Link>
      </nav>

      {/* Hero */}
      <section className="hero grid gap-12 border-b border-[rgba(212,175,55,0.2)] px-16 pb-16 pt-24 md:grid-cols-2 max-md:px-6">
        <div>
          <div className="hero-tag mb-6 flex items-center gap-3 font-['DM Mono',monospace] text-[0.65rem] uppercase tracking-[0.2em] text-[#D4AF37]">
            <span className="h-px w-6 bg-[#D4AF37]" />
            Cinematic Listing Videos for GTA Agents
          </div>
          <h1 className="mb-6 font-display text-[clamp(2.5rem,4vw,4.5rem)] font-bold leading-[0.95] tracking-[-0.02em]">
            Professional listing
            <br />
            videos from <span className="text-[#D4AF37]">$
              {tier === "basic" ? "99" : tier === "cinematic" ? "249" : "299"}.</span>
            <br />
            Not $5,000.
          </h1>
          <p className="hero-sub mb-8 max-w-[44ch] font-['DM Mono',monospace] text-[0.85rem] leading-[1.8] text-[#6b6b60]">
            Paste any Realtor.ca or Zillow URL. We animate your listing photos, write the narration,
            record the voiceover, and deliver a polished 30-second video — in under 15 minutes.
          </p>
          <div className="price-block mb-10 flex items-baseline gap-6">
            <div className="price-main text-[3rem] font-extrabold text-[#D4AF37]">
              {tier === "basic" ? "$99" : tier === "cinematic" ? "$249" : "$299"}
            </div>
            <div className="price-compare font-['DM Mono',monospace] text-[0.75rem] leading-[1.5] text-[#6b6b60]">
              Tiered per-listing pricing
              <br />
              <span className="line-through text-[#555]">Industry avg: $1,000–$5,000</span>
            </div>
          </div>
          <button
            className="submit-btn inline-block bg-[#D4AF37] px-10 py-4 font-['Syne',sans-serif] text-[0.95rem] font-extrabold uppercase tracking-[0.05em] text-black transition-all hover:-translate-y-[1px] hover:bg-[#F3E5AB]"
            onClick={() => {
              const el = document.getElementById("order");
              if (el) el.scrollIntoView({ behavior: "smooth" });
            }}
          >
            Order a Video →
          </button>
        </div>

        {/* Video preview — HTML5 sample (use NEXT_PUBLIC_HERO_VIDEO_URL for your own sample) */}
        <div className="video-preview relative aspect-[16/9] overflow-hidden border border-[rgba(212,175,55,0.2)] bg-black">
          <div className="video-preview-inner relative h-full w-full overflow-hidden bg-black">
            <video
              className="absolute left-0 top-0 h-full w-full object-cover"
              src={process.env.NEXT_PUBLIC_HERO_VIDEO_URL || "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"}
              controls
              playsInline
              loop
              muted
              autoPlay
              preload="metadata"
              title="416Homes sample — listing video"
            />
            <div className="vp-caption absolute bottom-[8%] left-0 right-0 px-6">
              <div className="vp-headline mb-1 text-[1.1rem] font-bold">
                Where Heritage Meets Modern Luxury
              </div>
              <div className="vp-address font-['DM Mono',monospace] text-[0.65rem] text-[#6b6b60]">
                218 Broadview Ave, Leslieville ·{" "}
                <span className="vp-price-tag font-bold text-[#D4AF37]">$1,149,000</span>
              </div>
            </div>
            <div className="vp-badge absolute right-[5%] top-[10%] border border-[rgba(212,175,55,0.2)] bg-[rgba(10,10,8,0.7)] px-2 py-1 font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.1em] text-[#D4AF37]">
              Sample Video
            </div>
          </div>
        </div>
      </section>

      {/* Process */}
      <section className="process border-b border-[rgba(212,175,55,0.2)] px-16 py-20 max-md:px-6">
        <div className="sec-tag mb-3 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#D4AF37]">
          How It Works
        </div>
        <h2 className="sec-h mb-12 font-display text-[clamp(1.6rem,2.5vw,2.8rem)] font-bold tracking-[-0.01em]">
          Five steps, one URL, one video.
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
              t: "Script written for your listing",
              d: "We write a 30-second cinematic voiceover script tailored to the property details and neighbourhood.",
              tool: "Gemini 2.0",
            },
            {
              n: "03",
              icon: "🎙️",
              t: "Voiceover recorded",
              d: "ElevenLabs generates professional narration. Choose from warm female or deep male voice.",
              tool: "ElevenLabs",
            },
            {
              n: "04",
              icon: "🎬",
              t: "Photos animated",
              d: "Each photo gets a cinematic dolly shot, pan, or zoom — luxury motion styling.",
              tool: "Calico",
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
              className="step relative border-r border-[rgba(212,175,55,0.2)] p-8 last:border-r-0"
            >
              <div className="step-n mb-4 font-['DM Mono',monospace] text-[0.6rem] text-[#D4AF37] tracking-[0.15em]">
                {s.n}
              </div>
              <div className="step-ico mb-3 text-[1.3rem]">{s.icon}</div>
              <div className="step-t mb-2 text-[0.9rem] font-bold">{s.t}</div>
              <div className="step-d font-['DM Mono',monospace] text-[0.68rem] leading-[1.65] text-[#6b6b60]">
                {s.d}
              </div>
              {s.tool && (
                <div className="step-tool mt-2 inline-block border border-[rgba(212,175,55,0.2)] px-1.5 py-0.5 font-['DM Mono',monospace] text-[0.58rem] text-[#D4AF37]">
                  {s.tool}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Order section — matches API server video page */}
      <section id="order" className="order-section grid gap-16 border-b border-[rgba(212,175,55,0.2)] px-16 py-20 md:grid-cols-2 max-md:px-6">
        <div className="order-info">
          <h2 className="mb-4 text-[2rem] font-extrabold tracking-[-0.02em]">
            Order your listing video
          </h2>
          <p className="mb-6 font-['DM Mono',monospace] text-[0.78rem] leading-[1.8] text-[#6b6b60]">
            Paste your listing URL below. We&apos;ll scrape the photos, write the script, record the voiceover,
            animate the images, and assemble your video — all automatically. Download ready in ~12 minutes.
          </p>
          <div className="cost-breakdown border border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.025)] p-6">
            {[
              ["Basic", "$99 CAD"],
              ["Cinematic (Most Popular)", "$249 CAD"],
              ["Premium", "$299 CAD"],
              ["Turnaround time", "~12 minutes"],
              ["Video length", "30 seconds"],
              ["Format", "1920×1080 MP4"],
              ["Revisions", "1 free revision"],
              ["You pay", `$${price}`],
            ].map(([label, value], i) => (
              <div
                key={label}
                className={`cost-row flex items-center justify-between border-b border-[rgba(212,175,55,0.1)] py-2 text-[0.72rem] font-['DM Mono',monospace] ${
                  i === 7 ? "border-b-0 text-[0.85rem] font-bold" : ""
                }`}
              >
                <span className="cost-label text-[#6b6b60]">{label}</span>
                <span className={`cost-value ${i === 7 ? "text-[1.1rem] text-[#D4AF37]" : "text-[#f5f4ef]"}`}>
                  {value}
                </span>
              </div>
            ))}
          </div>
          {/* Tier cards */}
          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-3">
            {TIERS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => selectTier(t.id, t.price)}
                className={`relative cursor-pointer border p-6 text-left transition-colors ${
                  tier === t.id
                    ? "border-[#D4AF37] bg-[rgba(212,175,55,0.08)]"
                    : "border-[rgba(212,175,55,0.2)] bg-[rgba(255,255,255,0.025)] hover:border-[rgba(212,175,55,0.5)]"
                }`}
              >
                {t.badge && (
                  <span className="absolute right-4 top-4 bg-[#D4AF37] px-2 py-0.5 font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.1em] text-[#0B0B0B]">
                    {t.badge}
                  </span>
                )}
                <h3 className="mb-1 text-[1.1rem] font-bold">{t.title}</h3>
                <p className="mb-3 text-[1.4rem] font-extrabold text-[#D4AF37]">${t.price}</p>
                <ul className="list-none pl-0 font-['DM Mono',monospace] text-[0.7rem] leading-[1.7] text-[#6b6b60]">
                  {t.features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </button>
            ))}
          </div>
        </div>

        {/* Order form or progress panel */}
        {orderFormVisible && (
          <VideoOrderForm
            uploadMethod={uploadMethod}
            setUploadMethod={setUploadMethod}
            selectedVoice={selectedVoice}
            setSelectedVoice={setSelectedVoice}
            tier={tier}
            price={price}
            submitLoading={submitLoading}
            onSubmit={handleSubmit}
            formListingUrl={formListingUrl}
            setFormListingUrl={setFormListingUrl}
            formEmail={formEmail}
            setFormEmail={setFormEmail}
            formName={formName}
            setFormName={setFormName}
            formCustomAddress={formCustomAddress}
            setFormCustomAddress={setFormCustomAddress}
            formCustomPrice={formCustomPrice}
            setFormCustomPrice={setFormCustomPrice}
            formCustomBeds={formCustomBeds}
            setFormCustomBeds={setFormCustomBeds}
            setFormCustomPhotos={setFormCustomPhotos}
            setFormCustomMusic={setFormCustomMusic}
          />
        )}
        {progressVisible && (
          <ProgressPanel
            progressAddr={progressAddr}
            stepMessages={stepMessages}
            stepStates={stepStates}
            downloadVisible={downloadVisible}
            downloadSubtitle={downloadSubtitle}
            jobId={currentJobId}
            videoUrl={videoUrl}
            videoLoadError={videoLoadError}
            onVideoError={() => setVideoLoadError(true)}
          />
        )}
      </section>

      {/* Social proof + FAQ text left as-is in HTML; we can port those 1:1 next if you want the full page parity. */}

      <footer className="flex items-center justify-between border-t border-[rgba(212,175,55,0.2)] px-16 py-8 max-md:flex-col max-md:gap-3 max-md:px-6">
        <div className="footer-logo text-[1rem] font-extrabold">
          <span className="text-[#D4AF37]">416</span>
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


