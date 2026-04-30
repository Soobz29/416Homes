"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import HouseLogo from "@/components/HouseLogo";
import ScrollExpandHero from "@/components/ui/scroll-expand-hero";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000")).replace(/\/$/, "");
const STEP_ORDER = ["scrape", "script", "audio", "animate", "assemble"] as const;

type Tier = "basic" | "cinematic" | "premium";

const TIERS: { id: Tier; price: number; label: string; delivery: string; badge?: string; features: string[] }[] = [
  {
    id: "basic", price: 99, label: "Basic", delivery: "delivered in 20 min",
    features: ["15-second cut", "Royalty-free music", "MP4 + square crop"],
  },
  {
    id: "cinematic", price: 249, label: "Cinematic", delivery: "delivered in 15 min", badge: "Most Popular",
    features: ["30-second film", "Narration included", "Custom script from listing copy", "4K + vertical"],
  },
  {
    id: "premium", price: 299, label: "Premium", delivery: "delivered in 12 min",
    features: ["Everything in Cinematic", "AI-generated b-roll", "Aerial-style shots", "Priority queue"],
  },
];

const DEMO_VIDEO_SRC = "https://upwkbeyzmdfdkwoaayub.supabase.co/storage/v1/object/sign/416homevideo/5314533739356475027.mp4?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zYTEyZTQyMC1mMGZiLTQ4YzEtYTQ1OC00NjRkZTQ0MTdkMTciLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiI0MTZob21ldmlkZW8vNTMxNDUzMzczOTM1NjQ3NTAyNy5tcDQiLCJpYXQiOjE3NzY3MDA5NzgsImV4cCI6MTgwODIzNjk3OH0.GipcwNQCMjJkRZyFJlhlLbyiciHFW0-k47odpXpdBKg";
const DEMO_POSTER = "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=1280&q=80";

/* ── Progress panel (Terminal Broker style) ────────────────────────── */
function ProgressPanel({
  progressAddr, stepMessages, stepStates,
  downloadVisible, downloadSubtitle, jobId, videoUrl, videoLoadError, onVideoError,
  revisionVisible, revisionNotes, onRevisionNotesChange, onSubmitRevision,
  revisionSubmitting, revisionMessage, revisionSuccess,
}: {
  progressAddr: string;
  stepMessages: Record<string, string>;
  stepStates: Record<string, "pending" | "active" | "done">;
  downloadVisible: boolean; downloadSubtitle: string;
  jobId: string | null; videoUrl: string | null;
  videoLoadError: boolean; onVideoError: () => void;
  revisionVisible: boolean; revisionNotes: string;
  onRevisionNotesChange: (n: string) => void; onSubmitRevision: () => void;
  revisionSubmitting: boolean; revisionMessage: string | null; revisionSuccess: boolean;
}) {
  const apiBase = API_BASE;
  const steps = [
    { key: "scrape",   label: "Fetching listing & photos"   },
    { key: "script",   label: "Writing voiceover script"    },
    { key: "audio",    label: "Recording narration + music" },
    { key: "animate",  label: "Animating listing photos"    },
    { key: "assemble", label: "Assembling final video"      },
  ];

  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };
  return (
    <div style={{ border: "1px solid var(--border-strong)", background: "var(--bg-elev)", padding: 40 }}>
      <div style={{ ...mono, fontSize: "0.55rem", textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--accent)", marginBottom: 8 }}>
        ◆ Processing
      </div>
      <div style={{ ...mono, fontSize: "1.1rem", fontWeight: 500, color: "var(--text)", marginBottom: 32 }}>
        {progressAddr}
      </div>
      {steps.map(s => (
        <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 0", borderBottom: "1px solid rgba(212,175,55,0.08)" }}>
          <div style={{
            width: 28, height: 28, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            border: `1px solid ${stepStates[s.key] === "done" ? "#2ed573" : stepStates[s.key] === "active" ? "var(--accent)" : "var(--border)"}`,
            background: stepStates[s.key] === "done" ? "rgba(46,213,115,0.12)" : stepStates[s.key] === "active" ? "rgba(212,175,55,0.1)" : "transparent",
            color: stepStates[s.key] === "done" ? "#2ed573" : "var(--accent)",
            fontSize: "0.7rem",
          }}>
            {stepStates[s.key] === "done" ? "✓" : "◈"}
          </div>
          <div>
            <div style={{ ...mono, fontSize: "0.82rem", fontWeight: 500, color: stepStates[s.key] === "pending" ? "var(--text-dim)" : "var(--text)" }}>{s.label}</div>
            <div style={{ ...mono, fontSize: "0.62rem", color: "var(--text-dim)", marginTop: 2 }}>
              {stepMessages[s.key] || (stepStates[s.key] === "active" ? "Processing…" : "Waiting")}
            </div>
          </div>
        </div>
      ))}

      {downloadVisible && (
        <div style={{ marginTop: 32, padding: 24, border: "1px solid rgba(46,213,115,0.25)", background: "rgba(46,213,115,0.05)" }}>
          <div style={{ ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "#2ed573", marginBottom: 8 }}>
            ◆ Video ready
          </div>
          <div style={{ ...mono, fontSize: "0.75rem", color: "var(--text-mute)", marginBottom: 16 }}>{downloadSubtitle}</div>
          {videoUrl && (
            <video src={videoUrl} controls playsInline preload="metadata"
              style={{ width: "100%", background: "#000", marginBottom: 16 }}
              onError={onVideoError} />
          )}
          <a href={videoUrl || (jobId ? `${apiBase}/video/download/${jobId}` : "#") || "#"} download
            style={{
              display: "inline-block", padding: "12px 24px",
              background: "#2ed573", color: "#000",
              fontFamily: "var(--mono)", fontSize: "0.72rem", fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.1em", textDecoration: "none",
            }}>
            Download MP4
          </a>

          {revisionVisible && (
            <div style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 20 }}>
              <div style={{ ...mono, fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--accent)", marginBottom: 8 }}>
                Request Free Revision
              </div>
              <textarea value={revisionNotes} onChange={e => onRevisionNotesChange(e.target.value)}
                placeholder="e.g. Use jazz music, open with kitchen shot, slower voiceover"
                style={{ width: "100%", minHeight: 80, resize: "vertical", padding: 12, border: "1px solid var(--border)", background: "rgba(255,255,255,0.04)", color: "var(--text)", fontFamily: "var(--mono)", fontSize: "0.78rem", outline: "none" }} />
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 10 }}>
                <button onClick={onSubmitRevision} disabled={revisionSubmitting}
                  style={{ padding: "10px 20px", background: "var(--accent)", color: "#000", fontFamily: "var(--mono)", fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", border: "none", cursor: "pointer" }}>
                  {revisionSubmitting ? "Submitting…" : "Submit Revision"}
                </button>
                {revisionMessage && (
                  <span style={{ fontFamily: "var(--mono)", fontSize: "0.65rem", color: revisionSuccess ? "#2ed573" : "#cf6357" }}>
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

/* ── Main page ──────────────────────────────────────────────────────── */
const VIDEO_NAV: [string, string][] = [["/dashboard","Listings"],["/#how-it-works","How It Works"],["/tours","Virtual Tours"],["/stats","Stats"],["/reno","Reno ROI"],["/faq","FAQ"]];

export default function VideoPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [tier, setTier] = useState<Tier>("cinematic");
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
  const [formListingUrl, setFormListingUrl] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [revisionNotes, setRevisionNotes] = useState("");
  const [revisionSubmitting, setRevisionSubmitting] = useState(false);
  const [revisionMessage, setRevisionMessage] = useState<string | null>(null);
  const [revisionSuccess, setRevisionSuccess] = useState(false);
  const [revisionVisible, setRevisionVisible] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const pollFailCount = useRef(0);
  const [videoInputMode, setVideoInputMode] = useState<"url" | "upload">("url");
  const [videoFiles, setVideoFiles] = useState<File[]>([]);
  const [videoFilePreviews, setVideoFilePreviews] = useState<string[]>([]);
  const [videoUploading, setVideoUploading] = useState(false);
  const videoFileRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const price = TIERS.find(t => t.id === tier)?.price ?? 249;

  const selectTier = useCallback((t: Tier) => setTier(t), []);

  const showProgress = useCallback((jobId: string, addr: string) => {
    pollFailCount.current = 0;
    setJobError(null);
    setCurrentJobId(jobId); setProgressAddr(addr);
    setOrderFormVisible(false); setProgressVisible(true);
    setStepMessages({});
    setStepStates({ scrape: "active", script: "pending", audio: "pending", animate: "pending", assemble: "pending" });
    setDownloadVisible(false); setVideoUrl(null); setVideoLoadError(false);
    setRevisionNotes(""); setRevisionSubmitting(false);
    setRevisionMessage(null); setRevisionSuccess(false); setRevisionVisible(false);
  }, []);

  const updateProgressFromApi = useCallback((data: { status?: string; progress_step?: string; progress_message?: string; listing_address?: string; error?: string; video_url?: string; revision_count?: number }, jobId: string | null) => {
    const step = data.progress_step || "scrape";
    const idx = STEP_ORDER.indexOf(step as typeof STEP_ORDER[number]);
    const next: Record<string, "pending" | "active" | "done"> = {};
    STEP_ORDER.forEach((s, i) => { next[s] = i < idx ? "done" : i === idx ? "active" : "pending"; });
    setStepStates(next);
    setStepMessages(prev => ({ ...prev, [step]: data.progress_message || "Processing…" }));
    if (data.status === "complete" || data.status === "completed") {
      STEP_ORDER.forEach(s => (next[s] = "done")); setStepStates(next);
      setDownloadVisible(true); setDownloadSubtitle(data.listing_address || "Your listing video is ready");
      setVideoUrl(data.video_url || (jobId ? `${API_BASE}/video/download/${jobId}` : null));
      setVideoLoadError(false); setRevisionVisible(!data.revision_count);
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    }
    if (data.status === "failed") {
      setStepMessages(prev => ({ ...prev, assemble: `Error: ${data.error || "Unknown"}` }));
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    }
  }, []);

  const submitRevision = useCallback(async () => {
    if (!revisionNotes.trim()) { setRevisionMessage("Describe what to change."); return; }
    if (!currentJobId) { setRevisionMessage("No active job found."); return; }
    setRevisionSubmitting(true);
    try {
      const resp = await fetch(`${API_BASE}/api/video-jobs/${currentJobId}/revision`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: revisionNotes.trim() }),
      });
      if (!resp.ok) throw new Error("Failed to submit revision.");
      setRevisionSuccess(true); setRevisionMessage("Revision submitted — updated video within 24 hours."); setRevisionVisible(false);
    } catch (err) {
      setRevisionSuccess(false); setRevisionMessage(err instanceof Error ? err.message : "Network error.");
    } finally { setRevisionSubmitting(false); }
  }, [currentJobId, revisionNotes]);

  useEffect(() => {
    if (!currentJobId || !progressVisible) return;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/video-jobs/${currentJobId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        pollFailCount.current = 0;
        updateProgressFromApi(await res.json(), currentJobId);
      } catch (e) {
        console.error("Poll error:", e);
        pollFailCount.current += 1;
        if (pollFailCount.current >= 4) {
          if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
          setJobError("Lost connection to the server. Refresh the page to check your job status.");
        }
      }
    };
    poll(); pollRef.current = setInterval(poll, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [currentJobId, progressVisible, updateProgressFromApi]);

  const handleVideoFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).slice(0, 9);
    setVideoFiles(files);
    setVideoFilePreviews(files.map(f => URL.createObjectURL(f)));
  };

  const handleSubmit = useCallback(async () => {
    if (!formEmail.trim() || !formEmail.includes("@")) { alert("Valid email required"); return; }
    let url = formListingUrl.trim();
    if (videoInputMode === "upload") {
      if (videoFiles.length === 0) { alert("Please select at least one photo"); return; }
      setVideoUploading(true);
      try {
        const formData = new FormData();
        videoFiles.forEach(f => formData.append("files", f));
        const res = await fetch(`${API_BASE}/api/upload-photos`, { method: "POST", body: formData });
        if (res.ok) {
          const data = await res.json();
          url = "upload://" + JSON.stringify(data.urls);
        }
      } catch { /* fall through */ }
      finally { setVideoUploading(false); }
      if (!url) url = "https://416-homes.vercel.app";
    } else {
      if (!url) { alert("Listing URL required"); return; }
      if (!url.startsWith("http")) url = "https://" + url;
    }
    setSubmitLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/video-jobs`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listing_url: url, agent_email: formEmail.trim(), voice: "female_luxury", tier, price_cad: price, use_veo: tier !== "basic" }),
      });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error((err as { detail?: string }).detail || `Error ${res.status}`); }
      const data = await res.json();
      const jobId = data.job_id || data.id;
      if (jobId) showProgress(jobId, url.length > 60 ? url.slice(0, 60) + "…" : url);
      else throw new Error("No job ID returned");
    } catch (err: unknown) {
      console.error(err);
      const msg = err instanceof Error ? err.message : "Could not reach the server.";
      setJobError(`Submission failed — ${msg}. Please try again.`);
    } finally { setSubmitLoading(false); }
  }, [formListingUrl, formEmail, tier, price, showProgress, videoInputMode, videoFiles]);

  /* ── Shared styles ── */
  const mono: React.CSSProperties = { fontFamily: "var(--mono)" };

  return (
    <div style={{ minHeight: "100vh", background: "transparent", color: "var(--text)" }}>

      {/* ── Nav ─────────────────────────────────────────────────────── */}
      <nav className="nav-bar" style={{
        position: "sticky", top: 0, zIndex: 100,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: 64, padding: "0 56px",
        background: "rgba(11,11,11,0.92)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--border)",
      }}>
        <Link href="/" style={{ textDecoration: "none" }}>
          <HouseLogo size={28} />
        </Link>
        <ul className="nav-links" style={{ display: "flex", listStyle: "none", gap: 36, margin: 0, padding: 0, ...mono, fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
          {VIDEO_NAV.map(([href, label]) => (
            <li key={href}><Link href={href} style={{ color: "inherit", textDecoration: "none" }}>{label}</Link></li>
          ))}
          <li><span style={{ color: "var(--accent)", borderBottom: "1px solid var(--accent)", paddingBottom: 2 }}>Videos</span></li>
        </ul>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button className="hamburger-btn" onClick={() => setMenuOpen(!menuOpen)}
            style={{ background: "transparent", border: "none", color: "var(--text)", fontSize: "1.4rem", cursor: "pointer", padding: "4px 8px", lineHeight: 1 }}>
            {menuOpen ? "✕" : "☰"}
          </button>
          <Link href="/#alert" className="btn-primary nav-cta" style={{ fontSize: "0.72rem", padding: "10px 20px" }}>
            Set My Alert
          </Link>
        </div>
        {menuOpen && (
          <div style={{ position: "fixed", top: 64, left: 0, right: 0, background: "rgba(5,6,10,0.98)", backdropFilter: "blur(20px)", borderBottom: "1px solid var(--border)", padding: "8px 24px 20px", zIndex: 999 }}>
            {[...VIDEO_NAV, ["/video","Videos (current)"], ["/#alert","Set My Alert"]].map(([href, label]) => (
              <Link key={href} href={href} onClick={() => setMenuOpen(false)} style={{ display: "block", padding: "14px 0", borderBottom: "1px solid var(--border)", fontFamily: "var(--mono)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-mute)", textDecoration: "none" }}>
                {label}
              </Link>
            ))}
          </div>
        )}
      </nav>

      {/* ── Hero — scroll-expanding video preview ────────────────────── */}
      <ScrollExpandHero
        mediaSrc={DEMO_VIDEO_SRC}
        posterSrc={DEMO_POSTER}
        title="Any Listing URL"
        date="$99 – $299 CAD"
        scrollToExpand="Scroll to preview"
      >
        {/* Revealed after full expansion — description + specs */}
        <div className="sec-wrap sec-pad-lg" style={{ maxWidth: 1320, margin: "0 auto", padding: "64px 56px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, ...mono, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--accent)", marginBottom: 20 }}>
            <span style={{ height: 1, width: 28, background: "var(--accent)", flexShrink: 0 }} />
            Sample Output
          </div>
          <p style={{ ...mono, fontSize: "0.88rem", color: "var(--text-mute)", maxWidth: "60ch", lineHeight: 1.8, marginBottom: 40 }}>
            Paste a Realtor.ca, Zillow, or HouseSigma URL. We pull the photos,
            write the script, record narration, and deliver an MP4 to your inbox.
          </p>
          <div className="stats-numbers-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "18px 32px", marginBottom: 40, borderTop: "1px solid var(--border)", paddingTop: 28 }}>
            {[["Duration","00:28"],["Resolution","3840×2160"],["Narration","Professional"],["Delivery","MP4 + vertical"]].map(([l, v]) => (
              <div key={l}>
                <div style={{ ...mono, fontSize: "0.5rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--text-dim)", marginBottom: 6 }}>{l}</div>
                <div style={{ ...mono, fontSize: "1rem", fontWeight: 600, color: "var(--text)" }}>{v}</div>
              </div>
            ))}
          </div>
          <a href="#order" className="btn-primary" style={{ textDecoration: "none" }}>Order a Video →</a>
        </div>
      </ScrollExpandHero>

      {/* ── Order section ────────────────────────────────────────────── */}
      {orderFormVisible && (
        <section id="order" className="sec-wrap sec-pad-lg" style={{ maxWidth: 1320, margin: "0 auto", padding: "72px 56px 64px", borderBottom: "1px solid var(--border)" }}>

          {/* Input mode toggle */}
          <div style={{ display: "flex", marginBottom: 16, border: "1px solid var(--border)" }}>
            {(["url", "upload"] as const).map(mode => (
              <button key={mode} onClick={() => setVideoInputMode(mode)} style={{
                flex: 1, padding: "10px 6px", border: "none",
                background: videoInputMode === mode ? "var(--accent)" : "transparent",
                color: videoInputMode === mode ? "#000" : "var(--text-dim)",
                ...mono, fontSize: "0.6rem", fontWeight: 700,
                letterSpacing: "0.1em", textTransform: "uppercase", cursor: "pointer",
              }}>
                {mode === "url" ? "Listing URL" : "Upload Photos"}
              </button>
            ))}
          </div>

          {videoInputMode === "url" ? (
            /* Listing URL */
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: "block", ...mono, fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.13em", color: "var(--text-dim)", marginBottom: 8 }}>
                Listing URL
              </label>
              <input
                type="text"
                value={formListingUrl}
                onChange={e => setFormListingUrl(e.target.value)}
                placeholder="https://www.realtor.ca/real-estate/..."
                style={{
                  width: "100%", padding: "14px 16px",
                  border: "1px solid var(--border)", background: "rgba(255,255,255,0.03)",
                  ...mono, fontSize: "0.85rem", color: "var(--text)", outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={e => { e.currentTarget.style.borderColor = "var(--border-strong)"; }}
                onBlur={e => { e.currentTarget.style.borderColor = "var(--border)"; }}
              />
            </div>
          ) : (
            /* Photo upload */
            <div style={{ marginBottom: 8 }}>
              <label style={{ display: "block", ...mono, fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.13em", color: "var(--text-dim)", marginBottom: 8 }}>
                Upload listing photos (up to 9)
              </label>
              <label style={{
                display: "block", border: "2px dashed var(--border)", padding: "24px 16px",
                textAlign: "center", cursor: "pointer",
                ...mono, fontSize: "0.78rem", color: "var(--text-dim)",
                transition: "border-color 0.2s", lineHeight: 1.7,
              }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--accent)")}
                onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
              >
                <input ref={videoFileRef} type="file" accept="image/*" multiple
                  onChange={handleVideoFileChange} style={{ display: "none" }} />
                {videoFiles.length === 0
                  ? <>📸 Click to select photos<br /><span style={{ fontSize: "0.62rem" }}>JPG · PNG · WEBP · up to 9</span></>
                  : `${videoFiles.length} photo${videoFiles.length !== 1 ? "s" : ""} selected ✓`}
              </label>
              {videoFilePreviews.length > 0 && (
                <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
                  {videoFilePreviews.map((src, i) => (
                    <img key={i} src={src} alt="" style={{ width: 52, height: 52, objectFit: "cover", border: "1px solid var(--border)" }} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Email */}
          <div style={{ marginBottom: 40 }}>
            <label style={{ display: "block", ...mono, fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.13em", color: "var(--text-dim)", marginBottom: 8, marginTop: 16 }}>
              Delivery Email
            </label>
            <input
              type="email"
              value={formEmail}
              onChange={e => setFormEmail(e.target.value)}
              placeholder="agent@yourbrokerage.com"
              style={{
                width: "100%", padding: "14px 16px",
                border: "1px solid var(--border)", background: "rgba(255,255,255,0.03)",
                ...mono, fontSize: "0.85rem", color: "var(--text)", outline: "none",
                transition: "border-color 0.2s",
              }}
              onFocus={e => { e.currentTarget.style.borderColor = "var(--border-strong)"; }}
              onBlur={e => { e.currentTarget.style.borderColor = "var(--border)"; }}
            />
          </div>

          {/* Pricing grid */}
          <div className="tiers-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", border: "1px solid var(--border)" }}>
            {TIERS.map((t, i) => (
              <div
                key={t.id}
                className="tier-card"
                onClick={() => selectTier(t.id)}
                style={{
                  position: "relative", padding: 32, cursor: "pointer",
                  borderRight: i < 2 ? "1px solid var(--border)" : "none",
                  background: tier === t.id ? "rgba(212,175,55,0.06)" : "transparent",
                  borderTop: tier === t.id ? "2px solid var(--accent)" : "2px solid transparent",
                  transition: "background 0.2s, border-top-color 0.2s",
                }}
              >
                {t.badge && (
                  <div style={{
                    position: "absolute", top: -1, left: "50%", transform: "translateX(-50%)",
                    background: "var(--accent)", padding: "3px 12px",
                    ...mono, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "#000",
                    whiteSpace: "nowrap",
                  }}>
                    {t.badge}
                  </div>
                )}
                <div style={{ ...mono, fontSize: "0.58rem", textTransform: "uppercase", letterSpacing: "0.14em", color: "var(--accent)", marginBottom: 12 }}>
                  {t.label}
                </div>
                <div style={{ ...mono, fontSize: "2.4rem", fontWeight: 500, color: "var(--text)", lineHeight: 1, marginBottom: 6 }}>
                  ${t.price}
                </div>
                <div style={{ ...mono, fontSize: "0.6rem", color: "var(--text-dim)", marginBottom: 24 }}>
                  CAD · {t.delivery}
                </div>
                <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                  {t.features.map(f => (
                    <li key={f} style={{ ...mono, fontSize: "0.7rem", color: "var(--text-mute)", display: "flex", alignItems: "baseline", gap: 8 }}>
                      <span style={{ color: "var(--accent)", fontSize: "0.6rem" }}>+</span> {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Checkout bar */}
          <div style={{
            marginTop: 24, display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "24px 32px", border: "1px solid var(--border)", background: "var(--bg-elev)",
          }}>
            <div>
              <div style={{ ...mono, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.13em", color: "var(--text-dim)", marginBottom: 6 }}>
                Total Today
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                <span style={{ ...mono, fontSize: "2.2rem", fontWeight: 500, color: "var(--text)" }}>${price}</span>
                <span style={{ ...mono, fontSize: "0.75rem", color: "var(--text-dim)" }}>CAD</span>
              </div>
            </div>
            <button
              onClick={handleSubmit}
              disabled={submitLoading}
              style={{
                padding: "18px 40px",
                background: submitLoading ? "var(--accent-dim)" : "var(--accent)",
                color: "#000", border: "none", cursor: submitLoading ? "not-allowed" : "pointer",
                ...mono, fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.12em",
                transition: "background 0.2s",
              }}
              onMouseEnter={e => { if (!submitLoading) e.currentTarget.style.background = "var(--accent-hi)"; }}
              onMouseLeave={e => { if (!submitLoading) e.currentTarget.style.background = "var(--accent)"; }}
            >
              {submitLoading ? "Processing…" : "Order Video →"}
            </button>
            {jobError && !progressVisible && (
              <div style={{ marginTop: 16, padding: "14px 18px", border: "1px solid #8b3a3a", background: "rgba(139,58,58,0.08)", ...mono, fontSize: "0.74rem", color: "#cf6357", lineHeight: 1.6 }}>
                ◆ {jobError}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Progress panel ───────────────────────────────────────────── */}
      {progressVisible && (
        <section className="sec-wrap sec-pad-lg" style={{ maxWidth: 1320, margin: "0 auto", padding: "72px 56px", borderBottom: "1px solid var(--border)" }}>
          {jobError ? (
            <div style={{ border: "1px solid #8b3a3a", background: "rgba(139,58,58,0.08)", padding: "28px 32px", maxWidth: 640 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.15em", color: "#cf6357", marginBottom: 10 }}>
                ◆ Job failed
              </div>
              <p style={{ fontFamily: "var(--mono)", fontSize: "0.82rem", color: "var(--text-mute)", lineHeight: 1.7, marginBottom: 20 }}>
                {jobError}
              </p>
              <button
                onClick={() => { setProgressVisible(false); setOrderFormVisible(true); setJobError(null); setCurrentJobId(null); }}
                style={{ padding: "12px 24px", border: "1px solid var(--border-strong)", background: "transparent", fontFamily: "var(--mono)", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--text)", cursor: "pointer" }}
                onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
                onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
              >
                ← Try again
              </button>
            </div>
          ) : (
            <ProgressPanel
              progressAddr={progressAddr} stepMessages={stepMessages} stepStates={stepStates}
              downloadVisible={downloadVisible} downloadSubtitle={downloadSubtitle}
              jobId={currentJobId} videoUrl={videoUrl}
              videoLoadError={videoLoadError} onVideoError={() => setVideoLoadError(true)}
              revisionVisible={revisionVisible} revisionNotes={revisionNotes}
              onRevisionNotesChange={setRevisionNotes} onSubmitRevision={submitRevision}
              revisionSubmitting={revisionSubmitting} revisionMessage={revisionMessage}
              revisionSuccess={revisionSuccess}
            />
          )}
        </section>
      )}

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="sec-wrap footer-bar" style={{
        maxWidth: 1320, margin: "0 auto", padding: "32px 56px",
        borderTop: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <HouseLogo size={22} />
        <div style={{ ...mono, fontSize: "0.6rem", color: "var(--text-dim)" }}>
          Covering the Greater Toronto Area · Built on real sold data
        </div>
        <div style={{ ...mono, fontSize: "0.6rem", color: "var(--text-dim)" }}>
          © 2026 416Homes · Early Access
        </div>
      </footer>
    </div>
  );
}
