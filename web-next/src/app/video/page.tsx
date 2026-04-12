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

const SOCIAL_PROOF = [
  {
    quote:
      "\"Saved me $3,200 on my last listing. The video looked just as good as what my usual production company delivers - honestly couldn't tell the difference.\"",
    author: "Marcus T.",
    role: "Sales Rep · RE/MAX Toronto",
  },
  {
    quote:
      "\"I ordered three videos in one afternoon. At $199 each I can now offer video to every single client, not just the million-dollar listings. Total game changer.\"",
    author: "Priya S.",
    role: "Broker · Right At Home Realty",
  },
  {
    quote:
      "\"The Mississauga condo I listed with a 416Homes video got 3x the showing requests versus my previous listings with just photos. Listing sold in 6 days.\"",
    author: "David K.",
    role: "Agent · Royal LePage Mississauga",
  },
];

const FAQ_ITEMS = [
  {
    q: "How long does it actually take?",
    a: "Typically 10-15 minutes from URL submission to downloadable MP4. The main bottleneck is image animation - each of 6 photos takes ~45 seconds to process through our rendering engine.",
  },
  {
    q: "Does it work for Mississauga listings?",
    a: "Yes - any Realtor.ca or Zillow listing URL works, regardless of city. We're built for the full GTA market including Mississauga, Brampton, and Oakville.",
  },
  {
    q: "What if the listing photos are bad?",
    a: "The animation works best on well-lit, staged photos. If photos are dark or cluttered, we apply a Ken Burns effect (smooth zoom/pan) rather than full cinematic motion. The result is still professional.",
  },
  {
    q: "Can I get a revision?",
    a: "Yes - one free revision is included. Email us with what you'd like changed (different voice, script edits, different photos) and we'll regenerate within 24 hours.",
  },
  {
    q: "Do I own the video?",
    a: "Yes, full commercial rights. Use it on MLS, Instagram Reels, YouTube, email campaigns, wherever you want. No attribution required.",
  },
  {
    q: "What format is the output?",
    a: "1920×1080 MP4 (Full HD), 30 seconds, ~80-120MB. Compatible with all social platforms, email, and MLS video upload fields.",
  },
];

function parseBedsBaths(raw: string): { beds: string; baths: string } {
  const bedsMatch = raw.match(/(\d+)\s*(?:bed|br)/i);
  const bathsMatch = raw.match(/(\d+(?:\.\d)?)\s*(?:bath|ba)/i);
  const beds = bedsMatch ? bedsMatch[1] : raw.replace(/\D/g, "").trim();
  const baths = bathsMatch ? bathsMatch[1] : "";
  return { beds, baths };
}

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
    <div className="order-form border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-10">
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
              ? "border-[#c8a96e] bg-[#c8a96e] text-[#0a0a08]"
              : "border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] text-[#f5f4ef]"
          }`}
        >
          Fetch by URL
        </button>
        <button
          type="button"
          onClick={() => setUploadMethod("custom")}
          className={`submit-btn border px-4 py-2 text-[0.8rem] transition-colors ${
            uploadMethod === "custom"
              ? "border-[#c8a96e] bg-[#c8a96e] text-[#0a0a08]"
              : "border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] text-[#f5f4ef]"
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
            className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
              className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
                className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
                className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
              className="fi w-full border border-[rgba(200,169,110,0.2)] bg-transparent px-4 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
              className="fi w-full border border-[rgba(200,169,110,0.2)] bg-transparent px-4 py-2 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
          className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
          className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.04)] px-4 py-3 font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef]"
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
                  ? "border-[#c8a96e] bg-[rgba(200,169,110,0.08)]"
                  : "border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.02)] hover:border-[rgba(200,169,110,0.5)]"
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
        className="submit-btn mt-2 w-full bg-[#c8a96e] px-4 py-4 font-['Syne',sans-serif] text-[0.95rem] font-extrabold uppercase tracking-[0.05em] text-black transition-all hover:-translate-y-[1px] hover:bg-[#e4c98a] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
      >
        {submitLoading ? "Processing..." : `Order ${tier.charAt(0).toUpperCase() + tier.slice(1)} - $${price} CAD`}
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
  revisionVisible,
  revisionNotes,
  onRevisionNotesChange,
  onSubmitRevision,
  revisionSubmitting,
  revisionMessage,
  revisionSuccess,
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
  revisionVisible: boolean;
  revisionNotes: string;
  onRevisionNotesChange: (notes: string) => void;
  onSubmitRevision: () => void;
  revisionSubmitting: boolean;
  revisionMessage: string | null;
  revisionSuccess: boolean;
}) {
  const steps = [
    { key: "scrape", label: "Fetching listing & photos", icon: "1", msgKey: "scrape" },
    { key: "script", label: "Writing voiceover script", icon: "2", msgKey: "script" },
    { key: "audio", label: "Recording narration + music", icon: "3", msgKey: "audio" },
    { key: "animate", label: "Animating listing photos", icon: "4", msgKey: "animate" },
    { key: "assemble", label: "Assembling final video", icon: "5", msgKey: "assemble" },
  ];
  const apiBase = (process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000")).replace(/\/$/, "");
  return (
    <div className="progress-panel border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-10">
      <div className="prog-title mb-1 text-[1rem] font-bold">Generating your video...</div>
      <div className="prog-addr mb-8 font-['DM Mono',monospace] text-[0.72rem] text-[#c8a96e]">{progressAddr}</div>
      <div className="prog-steps flex flex-col gap-0">
        {steps.map((s) => (
          <div key={s.key} className="prog-step flex items-center gap-4 border-b border-[rgba(200,169,110,0.08)] py-4 last:border-b-0">
            <div
              className={`prog-icon flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border text-[0.75rem] ${
                stepStates[s.key] === "done"
                  ? "border-[#2ed573] bg-[rgba(46,213,115,0.15)]"
                  : stepStates[s.key] === "active"
                    ? "animate-pulse border-[#c8a96e] bg-[rgba(200,169,110,0.1)]"
                    : "border-[rgba(200,169,110,0.2)] opacity-30"
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
          <div className="dl-title text-[#2ed573] text-[1rem] font-bold">Your video is ready.</div>
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
            className="dl-btn inline-block bg-[#2ed573] px-6 py-3 font-['Syne',sans-serif] text-[0.85rem] font-bold text-[#0a0a08] no-underline"
          >
            Download Video
          </a>
          {revisionVisible && (
            <div className="mt-8 rounded-[12px] border border-[rgba(200,169,110,0.25)] p-6">
              <div className="mb-3 font-['DM_Mono',monospace] text-[0.72rem] uppercase tracking-[0.1em] text-[#c8a96e]">
                Request Free Revision
              </div>
              <p className="mb-4 text-[0.85rem] leading-[1.5] text-[rgba(245,244,239,0.7)]">
                One free revision is included. Describe what you&apos;d like changed - different voice tone, music style,
                scene order, or script edits.
              </p>
              <textarea
                value={revisionNotes}
                onChange={(e) => onRevisionNotesChange(e.target.value)}
                placeholder="e.g. Make the voiceover slower and use jazz music instead of orchestral. Open with the kitchen shot."
                className="min-h-[84px] w-full resize-y border border-[rgba(200,169,110,0.25)] bg-[rgba(255,255,255,0.05)] p-3 font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] outline-none"
              />
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={onSubmitRevision}
                  disabled={revisionSubmitting}
                  className="bg-[#c8a96e] px-5 py-2 font-['DM_Mono',monospace] text-[0.75rem] font-bold uppercase tracking-[0.08em] text-[#0a0a08] disabled:opacity-60"
                >
                  {revisionSubmitting ? "Submitting..." : "Submit Revision"}
                </button>
                {revisionMessage && (
                  <span
                    className={`font-['DM_Mono',monospace] text-[0.72rem] ${
                      revisionSuccess ? "text-[#49ca84]" : "text-[#cf6357]"
                    }`}
                  >
                    {revisionMessage}
                  </span>
                )}
              </div>
            </div>
          )}
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
  const [revisionNotes, setRevisionNotes] = useState("");
  const [revisionSubmitting, setRevisionSubmitting] = useState(false);
  const [revisionMessage, setRevisionMessage] = useState<string | null>(null);
  const [revisionSuccess, setRevisionSuccess] = useState(false);
  const [revisionVisible, setRevisionVisible] = useState(false);

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
    setRevisionNotes("");
    setRevisionSubmitting(false);
    setRevisionMessage(null);
    setRevisionSuccess(false);
    setRevisionVisible(false);
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
      setRevisionVisible(!(data as { revision_count?: number }).revision_count);
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

    if (data.status === "revision_requested") {
      setRevisionVisible(false);
      setRevisionSuccess(true);
      setRevisionMessage("Revision submitted - we will send the updated video within 24 hours.");
    }
  }, []);

  const submitRevision = useCallback(async () => {
    const notes = revisionNotes.trim();
    if (!notes) {
      setRevisionSuccess(false);
      setRevisionMessage("Please describe what you would like changed.");
      return;
    }
    if (!currentJobId) {
      setRevisionSuccess(false);
      setRevisionMessage("No active job found.");
      return;
    }
    setRevisionSubmitting(true);
    setRevisionMessage("Submitting...");
    setRevisionSuccess(false);
    try {
      const resp = await fetch(`${API_BASE}/api/video-jobs/${currentJobId}/revision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({} as { detail?: string }));
        throw new Error(err.detail || "Failed to submit revision. Please email us directly.");
      }
      setRevisionSuccess(true);
      setRevisionMessage("Revision submitted - we will send the updated video within 24 hours.");
      setRevisionVisible(false);
    } catch (err: unknown) {
      setRevisionSuccess(false);
      setRevisionMessage(err instanceof Error ? err.message : "Network error. Please email us directly.");
    } finally {
      setRevisionSubmitting(false);
    }
  }, [currentJobId, revisionNotes]);

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
        const { beds: parsedBeds, baths: parsedBaths } = parseBedsBaths(formCustomBeds);
        formData.append("beds", parsedBeds);
        formData.append("baths", parsedBaths);
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
      setDownloadSubtitle("Demo mode - connect API for real video generation");
    }, 15000);
  }

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
          Back to 416Homes
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
            Paste any Realtor.ca or Zillow URL. We animate your listing photos, write the narration,
            record the voiceover, and deliver a polished 30-second video - in under 15 minutes.
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
            Order a Video
          </button>
        </div>

        {/* Video preview */}
        <div className="video-preview relative aspect-[16/9] overflow-hidden border border-[rgba(200,169,110,0.2)] bg-black">
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
              title="416Homes sample listing video"
            />
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
              Sample Video
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
          Five steps, one URL, one video.
        </h2>
        <div className="steps grid gap-0 md:grid-cols-5">
          {[
            {
              n: "01",
              icon: "URL",
              t: "Paste listing URL",
              d: "Realtor.ca or Zillow. We scrape the best 6 photos and all property details automatically.",
              tool: "",
            },
            {
              n: "02",
              icon: "Script",
              t: "Script crafted for your listing",
              d: "We analyze the listing details and write a 30-second cinematic voiceover script tailored to the property.",
              tool: "Script studio",
            },
            {
              n: "03",
              icon: "Voice",
              t: "Narration recorded",
              d: "Professional narration is recorded with premium voices and paired with cinematic music.",
              tool: "Voice studio",
            },
            {
              n: "04",
              icon: "Motion",
              t: "Photos brought to life",
              d: "Each photo gets a cinematic dolly shot, pan, or zoom - with luxury motion styling that feels like a custom shoot.",
              tool: "Motion studio",
            },
            {
              n: "05",
              icon: "Deliver",
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
              <div className="step-ico mb-3 inline-flex min-h-8 min-w-8 items-center justify-center rounded-full border border-[rgba(200,169,110,0.35)] px-3 font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.1em] text-[#c8a96e]">{s.icon}</div>
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

      {/* Order section — matches API server video page */}
      <section id="order" className="order-section grid gap-16 border-b border-[rgba(200,169,110,0.2)] px-16 py-20 md:grid-cols-2 max-md:px-6">
        <div className="order-info">
          <h2 className="mb-4 text-[2rem] font-extrabold tracking-[-0.02em]">
            Order your listing video
          </h2>
          <p className="mb-6 font-['DM Mono',monospace] text-[0.78rem] leading-[1.8] text-[#6b6b60]">
            Paste your listing URL below. We&apos;ll scrape the photos, write the script, record the voiceover,
            animate the images, and assemble your video - all automatically. Download ready in ~12 minutes.
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
              ["You pay", `$${price}`],
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
          {/* Tier cards */}
          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-3">
            {TIERS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => selectTier(t.id, t.price)}
                className={`relative cursor-pointer border p-6 text-left transition-colors ${
                  tier === t.id
                    ? "border-[#c8a96e] bg-[rgba(200,169,110,0.08)]"
                    : "border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] hover:border-[rgba(200,169,110,0.5)]"
                }`}
              >
                {t.badge && (
                  <span className="absolute right-4 top-4 bg-[#c8a96e] px-2 py-0.5 font-['DM Mono',monospace] text-[0.6rem] uppercase tracking-[0.1em] text-[#0a0a08]">
                    {t.badge}
                  </span>
                )}
                <h3 className="mb-1 text-[1.1rem] font-bold">{t.title}</h3>
                <p className="mb-3 text-[1.4rem] font-extrabold text-[#c8a96e]">${t.price}</p>
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
            revisionVisible={revisionVisible}
            revisionNotes={revisionNotes}
            onRevisionNotesChange={setRevisionNotes}
            onSubmitRevision={submitRevision}
            revisionSubmitting={revisionSubmitting}
            revisionMessage={revisionMessage}
            revisionSuccess={revisionSuccess}
          />
        )}
      </section>

      {/* Social proof */}
      <section className="grid gap-[2px] border-b border-[rgba(200,169,110,0.2)] px-16 py-16 md:grid-cols-3 max-md:px-6">
        {SOCIAL_PROOF.map((item) => (
          <div
            key={item.author}
            className="border border-[rgba(200,169,110,0.2)] bg-[rgba(255,255,255,0.025)] p-8"
          >
            <div className="mb-4 text-[0.85rem] tracking-[0.1em] text-[#c8a96e]">★★★★★</div>
            <p className="mb-5 font-['DM Mono',monospace] text-[0.78rem] leading-[1.7] text-[#6b6b60]">{item.quote}</p>
            <div className="text-[0.85rem] font-bold">{item.author}</div>
            <div className="font-['DM Mono',monospace] text-[0.62rem] text-[#6b6b60]">{item.role}</div>
          </div>
        ))}
      </section>

      {/* FAQ */}
      <section className="px-16 py-20 max-md:px-6">
        <div className="mb-3 font-['DM Mono',monospace] text-[0.62rem] uppercase tracking-[0.2em] text-[#c8a96e]">
          Questions
        </div>
        <h2 className="mb-12 text-[clamp(1.6rem,2.5vw,2.8rem)] font-extrabold tracking-[-0.02em]">
          Frequently asked.
        </h2>
        <div className="grid gap-8 md:grid-cols-2">
          {FAQ_ITEMS.map((item) => (
            <div key={item.q} className="border-b border-[rgba(200,169,110,0.2)] pb-6">
              <div className="mb-2 text-[0.95rem] font-bold">{item.q}</div>
              <div className="font-['DM Mono',monospace] text-[0.74rem] leading-[1.7] text-[#6b6b60]">{item.a}</div>
            </div>
          ))}
        </div>
      </section>

      <footer className="flex items-center justify-between border-t border-[rgba(200,169,110,0.2)] px-16 py-8 max-md:flex-col max-md:gap-3 max-md:px-6">
        <Link href="/" className="footer-logo text-[1rem] font-extrabold transition-colors hover:text-[#c8a96e]">
          <span className="text-[#c8a96e]">416</span>
          Homes Video
        </Link>
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


