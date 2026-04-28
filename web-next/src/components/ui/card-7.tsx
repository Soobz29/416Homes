"use client"

import { useRef, useState } from "react"
import Image from "next/image"
import type { Listing } from "@/types"

interface ListingTiltCardProps {
  listing: Listing
  onClick?: () => void
}

const FALLBACK_PHOTO = "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&q=80"

function formatPrice(p: number) {
  if (p >= 1_000_000) return `$${(p / 1_000_000).toFixed(2)}M`
  return `$${(p / 1_000).toFixed(0)}K`
}

export function ListingTiltCard({ listing, onClick }: ListingTiltCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [tilt, setTilt] = useState({ x: 0, y: 0, active: false })

  const photo = listing.photos?.[0] ?? FALLBACK_PHOTO

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current
    if (!card) return
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const rotateX = ((y / rect.height) - 0.5) * -16
    const rotateY = ((x / rect.width) - 0.5) * 16
    setTilt({ x: rotateX, y: rotateY, active: true })
  }

  const handleMouseLeave = () => setTilt({ x: 0, y: 0, active: false })

  const beds = listing.beds ?? 0
  const baths = listing.baths ?? 0
  const sqft = listing.sqft ?? 0

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick ?? (() => listing.url && window.open(listing.url, "_blank"))}
      style={{
        position: "relative",
        width: "100%",
        height: 320,
        cursor: "pointer",
        perspective: "1000px",
        userSelect: "none",
      }}
    >
      {/* Tilt wrapper */}
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: tilt.active
            ? `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg) scale3d(1.03,1.03,1.03)`
            : "rotateX(0deg) rotateY(0deg) scale3d(1,1,1)",
          transition: tilt.active ? "transform 0.05s linear" : "transform 0.35s ease",
          transformStyle: "preserve-3d",
          position: "relative",
          overflow: "hidden",
          border: "1px solid rgba(255,176,0,0.20)",
          boxShadow: tilt.active
            ? "0 24px 60px rgba(0,0,0,0.55), 0 0 30px rgba(255,176,0,0.12)"
            : "0 8px 32px rgba(0,0,0,0.35)",
        }}
      >
        {/* Background photo */}
        <Image
          src={photo}
          alt={listing.address}
          fill
          sizes="(max-width: 768px) 100vw, 300px"
          style={{ objectFit: "cover" }}
          onError={(e) => {
            const el = e.currentTarget as HTMLImageElement
            el.src = FALLBACK_PHOTO
          }}
        />

        {/* Dark gradient overlay */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "linear-gradient(to bottom, rgba(5,6,10,0.25) 0%, rgba(5,6,10,0.72) 100%)",
          }}
        />

        {/* Amber border shimmer on hover */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            border: `1px solid rgba(255,176,0,${tilt.active ? 0.55 : 0.20})`,
            transition: "border-color 0.2s",
            pointerEvents: "none",
          }}
        />

        {/* Property type badge — top left */}
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            background: "rgba(5,6,10,0.75)",
            border: "1px solid rgba(255,176,0,0.35)",
            backdropFilter: "blur(6px)",
            padding: "3px 10px",
            fontFamily: "var(--mono)",
            fontSize: "0.6rem",
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "var(--accent)",
          }}
        >
          {listing.property_type ?? "Listing"}
        </div>

        {/* 3D Tour badge — top right */}
        {listing.floor_plan_url && (
          <div
            style={{
              position: "absolute",
              top: 12,
              right: 12,
              background: "rgba(255,176,0,0.15)",
              border: "1px solid rgba(255,176,0,0.50)",
              backdropFilter: "blur(6px)",
              padding: "3px 10px",
              fontFamily: "var(--mono)",
              fontSize: "0.6rem",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--accent)",
            }}
          >
            ⬡ 3D Tour
          </div>
        )}

        {/* Bottom glassmorphism header */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            background: "rgba(5,6,10,0.72)",
            backdropFilter: "blur(12px)",
            borderTop: "1px solid rgba(255,176,0,0.20)",
            padding: "14px 16px 16px",
            transform: "translateZ(20px)",
          }}
        >
          {/* Price */}
          <div
            style={{
              fontFamily: "var(--mono)",
              fontSize: "1.25rem",
              fontWeight: 700,
              color: "var(--accent)",
              letterSpacing: "-0.01em",
              lineHeight: 1,
              marginBottom: 6,
            }}
          >
            {formatPrice(listing.price)}
          </div>

          {/* Address */}
          <div
            style={{
              fontFamily: "var(--mono)",
              fontSize: "0.72rem",
              color: "var(--text)",
              letterSpacing: "0.02em",
              marginBottom: 8,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {listing.address}
          </div>

          {/* Stats row */}
          <div
            style={{
              display: "flex",
              gap: 14,
              fontFamily: "var(--mono)",
              fontSize: "0.62rem",
              letterSpacing: "0.1em",
              color: "var(--text-mute)",
              textTransform: "uppercase",
            }}
          >
            {beds > 0 && <span>{beds} bed{beds !== 1 ? "s" : ""}</span>}
            {baths > 0 && <span>{baths} bath{baths !== 1 ? "s" : ""}</span>}
            {sqft > 0 && <span>{sqft.toLocaleString()} sqft</span>}
            {listing.transit_score != null && (
              <span style={{ marginLeft: "auto", color: listing.transit_score >= 7 ? "#4ade80" : listing.transit_score >= 5 ? "var(--accent)" : "var(--text-mute)" }}>
                ◉ Transit {listing.transit_score}/10
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
