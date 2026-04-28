"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";

const PanoramaViewer = dynamic(() => import("@/components/PanoramaViewer"), { ssr: false });

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000")
).replace(/\/$/, "");

interface Room {
  slug: string;
  name: string;
  photos: string[];
  panorama_url?: string;
}

interface Manifest {
  rooms: Room[];
  listing_url: string;
  address?: string;
  stock_photos?: boolean;
  embed_url?: string;
}

// ---- Demo manifest ----
const DEMO_MANIFEST: Manifest = {
  listing_url: "https://416-homes.vercel.app/tours",
  address: "Sample GTA Listing",
  rooms: [
    {
      slug: "exterior",
      name: "Exterior",
      photos: [
        "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=1600&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1605146769289-440113cc3d00?w=1600&auto=format&fit=crop",
      ],
    },
    {
      slug: "living_room",
      name: "Living Room",
      photos: [
        "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=1600&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=1600&auto=format&fit=crop",
      ],
    },
    {
      slug: "kitchen",
      name: "Kitchen",
      photos: [
        "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1600&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1556909172-54557c7e4fb7?w=1600&auto=format&fit=crop",
      ],
    },
    {
      slug: "dining_room",
      name: "Dining Room",
      photos: [
        "https://images.unsplash.com/photo-1617806118233-18e1de247200?w=1600&auto=format&fit=crop",
      ],
    },
    {
      slug: "bedroom",
      name: "Bedroom",
      photos: [
        "https://images.unsplash.com/photo-1505693314120-0d443867891c?w=1600&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=1600&auto=format&fit=crop",
      ],
    },
    {
      slug: "bathroom",
      name: "Bathroom",
      photos: [
        "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=1600&auto=format&fit=crop",
      ],
    },
    {
      slug: "backyard",
      name: "Backyard",
      photos: [
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1600&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1588854337221-4cf9fa96059c?w=1600&auto=format&fit=crop",
      ],
    },
  ],
};

// ---- Style constants ----
const BG = "#0a0a08";
const GOLD = "#c8a96e";
const GOLD_DIM = "rgba(200,169,110,0.2)";
const TEXT = "#f5f4ef";
const SUBTEXT = "#6b6b60";
const FONT_MONO = "'DM Mono', monospace";
const FONT_DISPLAY = "'Syne', sans-serif";
const SIDEBAR_W = 220;
const HEADER_H = 56;
const THUMB_H = 72;

export default function TourViewerPage() {
  const params = useParams();
  const id = Array.isArray(params.id) ? params.id[0] : params.id;

  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [roomIdx, setRoomIdx] = useState(0);
  const [photoIdx, setPhotoIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imgKey, setImgKey] = useState(0); // forces Ken Burns reset on photo change

  // Fetch manifest on mount
  useEffect(() => {
    if (!id) return;
    if (id.startsWith("demo-")) {
      setManifest(DEMO_MANIFEST);
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/tour-jobs/${id}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const m: Manifest = data.photo_manifest ?? data;
        if (!m.rooms || !Array.isArray(m.rooms)) throw new Error("Tour manifest missing rooms");
        setManifest(m);
      } catch (err) {
        console.error("Tour fetch error:", err);
        setError("Tour not found or not yet ready.");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const goToRoom = useCallback((ri: number) => {
    setRoomIdx(ri);
    setPhotoIdx(0);
    setImgKey((k) => k + 1);
  }, []);

  const goToPhoto = useCallback((pi: number) => {
    setPhotoIdx(pi);
    setImgKey((k) => k + 1);
  }, []);

  const prevPhoto = useCallback(() => {
    if (!manifest) return;
    if (photoIdx > 0) {
      setPhotoIdx((p) => p - 1);
      setImgKey((k) => k + 1);
    } else if (roomIdx > 0) {
      const prevRoom = manifest.rooms[roomIdx - 1];
      setRoomIdx((r) => r - 1);
      setPhotoIdx(prevRoom.photos.length - 1);
      setImgKey((k) => k + 1);
    }
  }, [manifest, roomIdx, photoIdx]);

  const nextPhoto = useCallback(() => {
    if (!manifest) return;
    const room = manifest.rooms[roomIdx];
    if (photoIdx < room.photos.length - 1) {
      setPhotoIdx((p) => p + 1);
      setImgKey((k) => k + 1);
    } else if (roomIdx < manifest.rooms.length - 1) {
      setRoomIdx((r) => r + 1);
      setPhotoIdx(0);
      setImgKey((k) => k + 1);
    }
  }, [manifest, roomIdx, photoIdx]);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") nextPhoto();
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") prevPhoto();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [nextPhoto, prevPhoto]);

  // ── Loading ──
  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: "transparent", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1rem", color: TEXT, fontFamily: FONT_MONO }}>
        <div style={{ width: 40, height: 40, border: `2px solid ${GOLD_DIM}`, borderTopColor: GOLD, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <span style={{ fontSize: "0.8rem", color: SUBTEXT, letterSpacing: "0.1em" }}>Loading your tour...</span>
      </div>
    );
  }

  // ── Error ──
  if (error || !manifest) {
    return (
      <div style={{ minHeight: "100vh", background: "transparent", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1.5rem", color: TEXT, fontFamily: FONT_MONO, padding: "2rem", textAlign: "center" }}>
        <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>Tour not found</div>
        <p style={{ fontSize: "0.78rem", color: SUBTEXT, maxWidth: "36ch", lineHeight: 1.7 }}>{error ?? "This tour link may have expired or the tour is still being generated."}</p>
        <a href="/tours" style={{ display: "inline-block", background: GOLD, color: BG, fontFamily: FONT_DISPLAY, fontWeight: 800, fontSize: "0.85rem", padding: "0.75rem 2rem", textDecoration: "none", letterSpacing: "0.05em", textTransform: "uppercase" }}>← Back to Tour Builder</a>
      </div>
    );
  }

  const isDemo = id?.startsWith("demo-") ?? false;
  const isStockPhotos = !isDemo && manifest.stock_photos === true;
  const displayAddress = manifest.address || "Virtual Tour";

  // ── Matterport / real 3D embed ──
  if (manifest.embed_url) {
    return (
      <div style={{ minHeight: "100vh", background: "transparent", color: TEXT, fontFamily: FONT_MONO }}>
        <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "1rem 2.5rem", borderBottom: `1px solid ${GOLD_DIM}`, background: "rgba(10,10,8,0.95)", position: "sticky", top: 0, zIndex: 40, height: HEADER_H, boxSizing: "border-box" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ fontFamily: FONT_DISPLAY, fontWeight: 900, fontSize: "1rem" }}><span style={{ color: GOLD }}>416</span>Homes</span>
            <span style={{ fontFamily: FONT_MONO, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.1em", color: SUBTEXT }}>3D Tour</span>
            {manifest.listing_url && (
              <a href={manifest.listing_url} target="_blank" rel="noreferrer" style={{ fontFamily: FONT_MONO, fontSize: "0.68rem", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD_DIM}` }}>View Listing ↗</a>
            )}
          </div>
          <a href="/tours" style={{ fontFamily: FONT_MONO, fontSize: "0.7rem", color: SUBTEXT, textDecoration: "none" }}>← Back</a>
        </header>
        <iframe src={manifest.embed_url} style={{ width: "100%", height: `calc(100vh - ${HEADER_H}px)`, border: "none", display: "block" }} allow="fullscreen; vr; xr-spatial-tracking" title="3D Virtual Tour" />
      </div>
    );
  }

  // ── Immersive photo tour ──
  const rooms = manifest.rooms;
  const currentRoom = rooms[roomIdx] ?? rooms[0];
  const currentPhoto = currentRoom?.photos[photoIdx] ?? currentRoom?.photos[0];
  const totalPhotos = rooms.reduce((s, r) => s + r.photos.length, 0);
  const globalPhotoIdx = rooms.slice(0, roomIdx).reduce((s, r) => s + r.photos.length, 0) + photoIdx;

  const hasPrev = roomIdx > 0 || photoIdx > 0;
  const hasNext = roomIdx < rooms.length - 1 || photoIdx < currentRoom.photos.length - 1;

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden", background: "transparent", color: TEXT, fontFamily: FONT_MONO }}>
      <style>{`
        @keyframes kenBurns {
          0%   { transform: scale(1)    translate(0%,   0%); }
          100% { transform: scale(1.08) translate(-1%, -0.5%); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${GOLD_DIM}; border-radius: 2px; }
      `}</style>

      {/* ── Header ── */}
      <header style={{ height: HEADER_H, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 2rem", borderBottom: `1px solid ${GOLD_DIM}`, background: "rgba(10,10,8,0.92)", backdropFilter: "blur(12px)", zIndex: 40 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.9rem", minWidth: 0 }}>
          <span style={{ fontFamily: FONT_DISPLAY, fontWeight: 900, fontSize: "1rem", flexShrink: 0 }}>
            <span style={{ color: GOLD }}>416</span>Homes
          </span>
          <span style={{ fontFamily: FONT_MONO, fontSize: "0.55rem", textTransform: "uppercase", letterSpacing: "0.12em", color: SUBTEXT, flexShrink: 0 }}>Virtual Tour</span>
          {manifest.listing_url && (
            <a href={manifest.listing_url} target="_blank" rel="noreferrer" style={{ fontFamily: FONT_MONO, fontSize: "0.65rem", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD_DIM}`, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "28ch" }}>
              {displayAddress} ↗
            </a>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexShrink: 0 }}>
          <span style={{ fontFamily: FONT_MONO, fontSize: "0.6rem", color: SUBTEXT }}>
            {globalPhotoIdx + 1} / {totalPhotos}
          </span>
          <a href="/tours" style={{ fontFamily: FONT_MONO, fontSize: "0.62rem", textTransform: "uppercase", letterSpacing: "0.1em", color: SUBTEXT, textDecoration: "none", border: `1px solid ${GOLD_DIM}`, padding: "0.35rem 0.8rem" }}>← Back</a>
        </div>
      </header>

      {/* ── Banners ── */}
      {isStockPhotos && (
        <div style={{ flexShrink: 0, background: "rgba(90,90,80,0.15)", borderBottom: `1px solid rgba(150,150,120,0.25)`, padding: "0.45rem 2rem", fontFamily: FONT_MONO, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", color: "#9a9a8a", textAlign: "center" }}>
          ℹ Sample photos shown — listing photos could not be fetched for this source.
        </div>
      )}
      {isDemo && (
        <div style={{ flexShrink: 0, background: "rgba(200,169,110,0.08)", borderBottom: `1px solid rgba(200,169,110,0.2)`, padding: "0.45rem 2rem", fontFamily: FONT_MONO, fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.12em", color: GOLD, textAlign: "center" }}>
          ⬡ Demo Tour · <a href="/tours" style={{ color: GOLD, textDecoration: "underline" }}>Order a real tour →</a>
        </div>
      )}

      {/* ── Body ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* ── Sidebar: room list ── */}
        <aside style={{ width: SIDEBAR_W, flexShrink: 0, background: "rgba(6,6,5,0.95)", borderRight: `1px solid ${GOLD_DIM}`, overflowY: "auto", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "1rem 1.25rem 0.5rem", fontFamily: FONT_MONO, fontSize: "0.52rem", textTransform: "uppercase", letterSpacing: "0.18em", color: SUBTEXT }}>
            Rooms · {rooms.length}
          </div>
          {rooms.map((room, ri) => {
            const active = ri === roomIdx;
            return (
              <button
                key={room.slug}
                type="button"
                onClick={() => goToRoom(ri)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.75rem 1.25rem",
                  background: active ? "rgba(200,169,110,0.1)" : "transparent",
                  borderLeft: active ? `3px solid ${GOLD}` : "3px solid transparent",
                  borderTop: "none",
                  borderRight: "none",
                  borderBottom: `1px solid ${active ? GOLD_DIM : "rgba(200,169,110,0.06)"}`,
                  cursor: "pointer",
                  textAlign: "left",
                  width: "100%",
                  transition: "background 0.15s, border-color 0.15s",
                }}
              >
                {/* Cover thumbnail */}
                {room.photos[0] ? (
                  <img src={room.photos[0]} alt="" style={{ width: 40, height: 30, objectFit: "cover", flexShrink: 0, opacity: active ? 1 : 0.55, border: active ? `1px solid ${GOLD}` : `1px solid ${GOLD_DIM}`, transition: "opacity 0.15s" }} />
                ) : (
                  <div style={{ width: 40, height: 30, flexShrink: 0, background: "#1a1a14", border: `1px solid ${GOLD_DIM}`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT_DISPLAY, fontWeight: 900, fontSize: "0.7rem", color: `${GOLD}60` }}>
                    {room.name.slice(0, 2).toUpperCase()}
                  </div>
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <div style={{ fontFamily: FONT_MONO, fontSize: "0.68rem", fontWeight: active ? 700 : 400, color: active ? GOLD : TEXT, textTransform: "uppercase", letterSpacing: "0.08em", lineHeight: 1.2 }}>
                      {room.name}
                    </div>
                    {room.panorama_url && (
                      <span style={{ fontFamily: FONT_MONO, fontSize: "0.46rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "#c8a96e", background: "rgba(200,169,110,0.12)", border: "1px solid rgba(200,169,110,0.3)", padding: "1px 4px", borderRadius: 2, flexShrink: 0 }}>
                        ◉ 360°
                      </span>
                    )}
                  </div>
                  <div style={{ fontFamily: FONT_MONO, fontSize: "0.55rem", color: SUBTEXT, marginTop: "0.15rem" }}>
                    {room.photos.length} photo{room.photos.length !== 1 ? "s" : ""}
                  </div>
                </div>
              </button>
            );
          })}
        </aside>

        {/* ── Main photo viewport ── */}
        <main style={{ flex: 1, position: "relative", overflow: "hidden", background: "#000" }}>

          {/* 360° panorama sphere — shown when panorama_url is available */}
          {currentRoom?.panorama_url ? (
            <PanoramaViewer
              key={`pano-${roomIdx}`}
              url={currentRoom.panorama_url}
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            />
          ) : (
            /* Flat photo with Ken Burns fallback */
            currentPhoto && (
              <img
                key={imgKey}
                src={currentPhoto}
                alt={`${currentRoom.name} — photo ${photoIdx + 1}`}
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  animation: "kenBurns 9s ease-out forwards, fadeIn 0.35s ease",
                  transformOrigin: "center center",
                }}
              />
            )
          )}

          {/* Bottom gradient for HUD legibility */}
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.15) 40%, transparent 70%)", pointerEvents: "none" }} />
          {/* Top gradient for edge polish */}
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 80, background: "linear-gradient(to bottom, rgba(0,0,0,0.45) 0%, transparent 100%)", pointerEvents: "none" }} />

          {/* ── Left nav arrow ── */}
          {hasPrev && (
            <button type="button" onClick={prevPhoto} aria-label="Previous photo"
              style={{ position: "absolute", left: "1.5rem", top: "50%", transform: "translateY(-50%)", zIndex: 10, width: 52, height: 52, background: "rgba(10,10,8,0.7)", border: `1px solid ${GOLD_DIM}`, color: TEXT, fontSize: "1.6rem", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)", transition: "border-color 0.2s, background 0.2s" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD; (e.currentTarget as HTMLButtonElement).style.background = "rgba(200,169,110,0.15)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD_DIM; (e.currentTarget as HTMLButtonElement).style.background = "rgba(10,10,8,0.7)"; }}
            >‹</button>
          )}

          {/* ── Right nav arrow ── */}
          {hasNext && (
            <button type="button" onClick={nextPhoto} aria-label="Next photo"
              style={{ position: "absolute", right: "1.5rem", top: "50%", transform: "translateY(-50%)", zIndex: 10, width: 52, height: 52, background: "rgba(10,10,8,0.7)", border: `1px solid ${GOLD_DIM}`, color: TEXT, fontSize: "1.6rem", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)", transition: "border-color 0.2s, background 0.2s" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD; (e.currentTarget as HTMLButtonElement).style.background = "rgba(200,169,110,0.15)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD_DIM; (e.currentTarget as HTMLButtonElement).style.background = "rgba(10,10,8,0.7)"; }}
            >›</button>
          )}

          {/* ── Room label + photo counter ── */}
          <div style={{ position: "absolute", bottom: THUMB_H + 12, left: "1.5rem", zIndex: 10 }}>
            <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 900, fontSize: "clamp(1.1rem, 2.5vw, 1.8rem)", color: TEXT, letterSpacing: "-0.01em", lineHeight: 1.1, textShadow: "0 2px 12px rgba(0,0,0,0.8)" }}>
              {currentRoom.name}
            </div>
            <div style={{ fontFamily: FONT_MONO, fontSize: "0.62rem", color: "rgba(245,244,239,0.65)", marginTop: "0.25rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>
              Photo {photoIdx + 1} of {currentRoom.photos.length}
              {roomIdx < rooms.length - 1 && (
                <span style={{ marginLeft: "1rem", color: GOLD, cursor: "pointer" }} onClick={nextPhoto}>
                  {rooms[roomIdx + 1].name} →
                </span>
              )}
            </div>
          </div>

          {/* ── Thumbnail strip ── */}
          <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: THUMB_H, display: "flex", alignItems: "center", gap: 4, padding: "0 1.5rem", background: "rgba(6,6,5,0.88)", borderTop: `1px solid ${GOLD_DIM}`, overflowX: "auto", zIndex: 10 }}>
            {currentRoom.photos.map((photo, pi) => (
              <button
                key={pi}
                type="button"
                onClick={() => goToPhoto(pi)}
                aria-label={`Go to photo ${pi + 1}`}
                style={{ width: 60, height: 44, flexShrink: 0, padding: 0, border: pi === photoIdx ? `2px solid ${GOLD}` : `1px solid ${GOLD_DIM}`, cursor: "pointer", overflow: "hidden", background: "#0f0f0b", opacity: pi === photoIdx ? 1 : 0.55, transition: "opacity 0.2s, border-color 0.2s", outline: "none" }}
              >
                <img src={photo} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
              </button>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
