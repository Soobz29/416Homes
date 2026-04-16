"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000")
).replace(/\/$/, "");

interface Room {
  slug: string;
  name: string;
  photos: string[];
}

interface Manifest {
  rooms: Room[];
  listing_url: string;
  address?: string;
}

// ---- Demo manifest (shown for any demo-* ID so users see a real working tour) ----
const DEMO_MANIFEST: Manifest = {
  listing_url: "https://416-homes.vercel.app/tours",
  address: "Sample GTA Listing",
  rooms: [
    {
      slug: "exterior",
      name: "Exterior",
      photos: [
        "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=900&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1605146769289-440113cc3d00?w=900&auto=format&fit=crop",
      ],
    },
    {
      slug: "living_room",
      name: "Living Room",
      photos: [
        "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=900&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=900&auto=format&fit=crop",
      ],
    },
    {
      slug: "kitchen",
      name: "Kitchen",
      photos: [
        "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=900&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1556909172-54557c7e4fb7?w=900&auto=format&fit=crop",
      ],
    },
    {
      slug: "bedroom",
      name: "Primary Bedroom",
      photos: [
        "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=900&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=900&auto=format&fit=crop",
      ],
    },
    {
      slug: "bathroom",
      name: "Bathroom",
      photos: [
        "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=900&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=900&auto=format&fit=crop",
      ],
    },
    {
      slug: "dining_room",
      name: "Dining Room",
      photos: [
        "https://images.unsplash.com/photo-1556742393-d75f468bfcb0?w=900&auto=format&fit=crop",
      ],
    },
    {
      slug: "backyard",
      name: "Backyard",
      photos: [
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=900&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=900&auto=format&fit=crop",
      ],
    },
  ],
};

// ---- Inline style constants ----
const BG = "#0a0a08";
const GOLD = "#c8a96e";
const GOLD_DIM = "rgba(200,169,110,0.2)";
const TEXT = "#f5f4ef";
const SUBTEXT = "#6b6b60";
const FONT_MONO = "'DM Mono', monospace";
const FONT_DISPLAY = "'Syne', sans-serif";

export default function TourViewerPage() {
  const params = useParams();
  const id = Array.isArray(params.id) ? params.id[0] : params.id;

  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [photoIndex, setPhotoIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch manifest on mount
  useEffect(() => {
    if (!id) return;
    // Demo IDs (generated client-side when API is unavailable) use hardcoded sample data
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
        if (!m.rooms || !Array.isArray(m.rooms)) {
          throw new Error("Tour manifest missing rooms");
        }
        setManifest(m);
      } catch (err) {
        console.error("Tour fetch error:", err);
        setError("Tour not found or not yet ready.");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  // Keyboard navigation
  useEffect(() => {
    if (!selectedRoom) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        setPhotoIndex((prev) => (prev + 1) % selectedRoom.photos.length);
      } else if (e.key === "ArrowLeft") {
        setPhotoIndex((prev) => (prev - 1 + selectedRoom.photos.length) % selectedRoom.photos.length);
      } else if (e.key === "Escape") {
        setSelectedRoom(null);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [selectedRoom]);

  const openRoom = useCallback((room: Room) => {
    setSelectedRoom(room);
    setPhotoIndex(0);
  }, []);

  const closeRoom = useCallback(() => {
    setSelectedRoom(null);
  }, []);

  const prevPhoto = useCallback(() => {
    if (!selectedRoom) return;
    setPhotoIndex((prev) => (prev - 1 + selectedRoom.photos.length) % selectedRoom.photos.length);
  }, [selectedRoom]);

  const nextPhoto = useCallback(() => {
    if (!selectedRoom) return;
    setPhotoIndex((prev) => (prev + 1) % selectedRoom.photos.length);
  }, [selectedRoom]);

  // --- Loading state ---
  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: BG,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1rem",
          color: TEXT,
          fontFamily: FONT_MONO,
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            border: `2px solid ${GOLD_DIM}`,
            borderTopColor: GOLD,
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <span style={{ fontSize: "0.8rem", color: SUBTEXT, letterSpacing: "0.1em" }}>
          Loading your tour...
        </span>
      </div>
    );
  }

  // --- Error state ---
  if (error || !manifest) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: BG,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1.5rem",
          color: TEXT,
          fontFamily: FONT_MONO,
          padding: "2rem",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>Tour not found</div>
        <p style={{ fontSize: "0.78rem", color: SUBTEXT, maxWidth: "36ch", lineHeight: 1.7 }}>
          {error ?? "This tour link may have expired or the tour is still being generated."}
        </p>
        <a
          href="/tours"
          style={{
            display: "inline-block",
            background: GOLD,
            color: BG,
            fontFamily: FONT_DISPLAY,
            fontWeight: 800,
            fontSize: "0.85rem",
            padding: "0.75rem 2rem",
            textDecoration: "none",
            letterSpacing: "0.05em",
            textTransform: "uppercase",
          }}
        >
          ← Back to Tour Builder
        </a>
      </div>
    );
  }

  const isDemo = id?.startsWith("demo-") ?? false;
  const displayAddress = manifest.address || (manifest.listing_url ? "View Listing" : "416Homes Virtual Tour");

  return (
    <div style={{ minHeight: "100vh", background: BG, color: TEXT }}>
      {/* Top bar */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "1rem 2.5rem",
          borderBottom: `1px solid ${GOLD_DIM}`,
          background: "rgba(10,10,8,0.85)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 40,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", minWidth: 0 }}>
          <span style={{ fontFamily: FONT_DISPLAY, fontWeight: 900, fontSize: "1rem", flexShrink: 0 }}>
            <span style={{ color: GOLD }}>416</span>Homes
          </span>
          <span
            style={{
              fontFamily: FONT_MONO,
              fontSize: "0.6rem",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              color: SUBTEXT,
              flexShrink: 0,
            }}
          >
            Virtual Tour
          </span>
          {manifest.listing_url && (
            <a
              href={manifest.listing_url}
              target="_blank"
              rel="noreferrer"
              style={{
                fontFamily: FONT_MONO,
                fontSize: "0.68rem",
                color: GOLD,
                textDecoration: "none",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: "30ch",
                borderBottom: `1px solid ${GOLD_DIM}`,
              }}
            >
              {displayAddress} ↗
            </a>
          )}
        </div>

        <a
          href="/tours"
          style={{
            fontFamily: FONT_MONO,
            fontSize: "0.65rem",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            color: SUBTEXT,
            textDecoration: "none",
            border: `1px solid ${GOLD_DIM}`,
            padding: "0.4rem 0.9rem",
            transition: "color 0.2s, border-color 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.color = GOLD;
            (e.currentTarget as HTMLAnchorElement).style.borderColor = GOLD;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.color = SUBTEXT;
            (e.currentTarget as HTMLAnchorElement).style.borderColor = GOLD_DIM;
          }}
        >
          ← Back
        </a>
      </header>

      {/* Demo banner */}
      {isDemo && (
        <div
          style={{
            background: "rgba(200,169,110,0.1)",
            borderBottom: `1px solid rgba(200,169,110,0.25)`,
            padding: "0.6rem 2.5rem",
            fontFamily: FONT_MONO,
            fontSize: "0.62rem",
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: GOLD,
            textAlign: "center",
          }}
        >
          ⬡ Demo Tour — This is a sample. Real tours are generated from your listing photos.{" "}
          <a href="/tours" style={{ color: GOLD, textDecoration: "underline" }}>
            Generate yours →
          </a>
        </div>
      )}

      {/* Room grid */}
      <main style={{ padding: "3rem 2.5rem 4rem", maxWidth: 1280, margin: "0 auto" }}>
        <div style={{ marginBottom: "2.5rem" }}>
          <div
            style={{
              fontFamily: FONT_MONO,
              fontSize: "0.6rem",
              textTransform: "uppercase",
              letterSpacing: "0.2em",
              color: GOLD,
              marginBottom: "0.5rem",
            }}
          >
            Room-by-Room Tour
          </div>
          <h1
            style={{
              fontFamily: FONT_DISPLAY,
              fontSize: "clamp(1.6rem, 3vw, 2.5rem)",
              fontWeight: 900,
              letterSpacing: "-0.02em",
              margin: 0,
            }}
          >
            {manifest.rooms.length} room{manifest.rooms.length !== 1 ? "s" : ""} · Click to explore
          </h1>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "1px",
          }}
        >
          {manifest.rooms.map((room) => (
            <RoomCard key={room.slug} room={room} onClick={() => openRoom(room)} />
          ))}
        </div>
      </main>

      {/* Lightbox */}
      {selectedRoom && (
        <Lightbox
          room={selectedRoom}
          photoIndex={photoIndex}
          onClose={closeRoom}
          onPrev={prevPhoto}
          onNext={nextPhoto}
        />
      )}
    </div>
  );
}

// ---- Room Card ----
function RoomCard({ room, onClick }: { room: Room; onClick: () => void }) {
  const [hovered, setHovered] = useState(false);
  const coverPhoto = room.photos[0];

  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: "relative",
        display: "block",
        width: "100%",
        aspectRatio: "4/3",
        overflow: "hidden",
        background: "#0f0f0b",
        border: hovered ? `1px solid ${GOLD}` : `1px solid ${GOLD_DIM}`,
        boxShadow: hovered ? `0 0 20px rgba(200,169,110,0.2)` : "none",
        cursor: "pointer",
        padding: 0,
        transform: hovered ? "scale(1.02)" : "scale(1)",
        transition: "transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease",
      }}
    >
      {/* Photo */}
      {coverPhoto ? (
        <img
          src={coverPhoto}
          alt={room.name}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transition: "opacity 0.3s ease",
          }}
        />
      ) : (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "linear-gradient(135deg, #1a1a14 0%, #0b0b0b 100%)",
            fontFamily: FONT_DISPLAY,
            fontSize: "2rem",
            fontWeight: 900,
            color: `${GOLD}40`,
          }}
        >
          {room.name.slice(0, 2).toUpperCase()}
        </div>
      )}

      {/* Gradient overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.1) 60%, transparent 100%)",
        }}
      />

      {/* Photo count badge */}
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          background: "rgba(10,10,8,0.7)",
          border: `1px solid ${GOLD_DIM}`,
          padding: "0.2rem 0.6rem",
          fontFamily: FONT_MONO,
          fontSize: "0.58rem",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: GOLD,
          backdropFilter: "blur(4px)",
        }}
      >
        {room.photos.length} photo{room.photos.length !== 1 ? "s" : ""}
      </div>

      {/* Room name */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "1rem 1.25rem",
          fontFamily: FONT_MONO,
          fontSize: "0.8rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: GOLD,
        }}
      >
        {room.name}
      </div>
    </button>
  );
}

// ---- Lightbox ----
function Lightbox({
  room,
  photoIndex,
  onClose,
  onPrev,
  onNext,
}: {
  room: Room;
  photoIndex: number;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
}) {
  const currentPhoto = room.photos[photoIndex];
  const total = room.photos.length;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        background: "rgba(5,5,4,0.97)",
        display: "flex",
        flexDirection: "column",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Lightbox top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "1rem 1.5rem",
          borderBottom: `1px solid ${GOLD_DIM}`,
          flexShrink: 0,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: FONT_MONO,
              fontSize: "0.65rem",
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              color: GOLD,
              marginBottom: "0.15rem",
            }}
          >
            {room.name}
          </div>
          <div
            style={{
              fontFamily: FONT_MONO,
              fontSize: "0.6rem",
              color: SUBTEXT,
            }}
          >
            Photo {photoIndex + 1} of {total}
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          style={{
            background: "none",
            border: `1px solid ${GOLD_DIM}`,
            color: TEXT,
            fontFamily: FONT_MONO,
            fontSize: "1.1rem",
            width: 36,
            height: 36,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            transition: "border-color 0.2s, color 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD;
            (e.currentTarget as HTMLButtonElement).style.color = GOLD;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD_DIM;
            (e.currentTarget as HTMLButtonElement).style.color = TEXT;
          }}
          aria-label="Close lightbox"
        >
          ×
        </button>
      </div>

      {/* Photo area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          overflow: "hidden",
          padding: "1.5rem",
        }}
      >
        {/* Left arrow */}
        {total > 1 && (
          <button
            type="button"
            onClick={onPrev}
            style={{
              position: "absolute",
              left: "1rem",
              zIndex: 2,
              background: "rgba(10,10,8,0.75)",
              border: `1px solid ${GOLD_DIM}`,
              color: TEXT,
              fontFamily: FONT_MONO,
              fontSize: "1.2rem",
              width: 44,
              height: 44,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "border-color 0.2s, background 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD;
              (e.currentTarget as HTMLButtonElement).style.background = `rgba(200,169,110,0.12)`;
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD_DIM;
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(10,10,8,0.75)";
            }}
            aria-label="Previous photo"
          >
            ‹
          </button>
        )}

        {/* Main photo */}
        {currentPhoto && (
          <img
            key={currentPhoto}
            src={currentPhoto}
            alt={`${room.name} — photo ${photoIndex + 1}`}
            style={{
              maxWidth: "100%",
              maxHeight: "100%",
              objectFit: "contain",
              display: "block",
            }}
          />
        )}

        {/* Right arrow */}
        {total > 1 && (
          <button
            type="button"
            onClick={onNext}
            style={{
              position: "absolute",
              right: "1rem",
              zIndex: 2,
              background: "rgba(10,10,8,0.75)",
              border: `1px solid ${GOLD_DIM}`,
              color: TEXT,
              fontFamily: FONT_MONO,
              fontSize: "1.2rem",
              width: 44,
              height: 44,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "border-color 0.2s, background 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD;
              (e.currentTarget as HTMLButtonElement).style.background = `rgba(200,169,110,0.12)`;
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD_DIM;
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(10,10,8,0.75)";
            }}
            aria-label="Next photo"
          >
            ›
          </button>
        )}
      </div>

      {/* Photo strip thumbnails */}
      {total > 1 && (
        <div
          style={{
            display: "flex",
            gap: 4,
            padding: "0.75rem 1.5rem",
            overflowX: "auto",
            borderTop: `1px solid ${GOLD_DIM}`,
            flexShrink: 0,
          }}
        >
          {room.photos.map((photo, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                // navigate directly — parent state updated via prop
                const diff = i - photoIndex;
                if (diff === 0) return;
                // Call prev/next as many times as needed; for simplicity use a direct setter
                // We expose index via a workaround: call onPrev/onNext based on direction
                // Actually for direct navigation we need the parent to expose setPhotoIndex.
                // Since we only have onPrev/onNext, chain calls:
                for (let j = 0; j < Math.abs(diff); j++) {
                  diff > 0 ? onNext() : onPrev();
                }
              }}
              style={{
                width: 56,
                height: 40,
                flexShrink: 0,
                padding: 0,
                border: i === photoIndex ? `2px solid ${GOLD}` : `1px solid ${GOLD_DIM}`,
                cursor: "pointer",
                overflow: "hidden",
                background: "#0f0f0b",
                opacity: i === photoIndex ? 1 : 0.5,
                transition: "opacity 0.2s, border-color 0.2s",
              }}
              aria-label={`Go to photo ${i + 1}`}
            >
              <img
                src={photo}
                alt=""
                style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
