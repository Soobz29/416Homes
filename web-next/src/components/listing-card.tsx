"use client";

import { useState } from "react";
import { Listing } from "@/types";
import { formatPrice } from "@/lib/utils";
import { HoverCardWrapper } from "@/components/ui/hover-card-wrapper";

interface ListingCardProps {
  listing: Listing;
  index?: number;
  onValuate?: (listing: Listing) => void;
}

const SOURCE_COLORS: Record<string, string> = {
  zoocasa:     "#5B3CF5",
  kijiji:      "#E8003D",
  redfin:      "#C82021",
  housesigma:  "#FF6B35",
  "realtor.ca": "#D40511",
};

function getInitials(address: string): string {
  const parts = address.trim().split(/\s+/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : address.slice(0, 2).toUpperCase();
}

export function ListingCard({ listing, index = 0, onValuate }: ListingCardProps) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  const photo = listing.photos?.[0];
  const showPhoto = !!photo && !imgError;
  const sourceKey = (listing.source || "").toLowerCase();
  const badgeColor = SOURCE_COLORS[sourceKey] ?? "#6b6b60";

  return (
    <HoverCardWrapper>
      <div
        className="card-enter overflow-hidden rounded-xl"
        style={{
          animationDelay: `${index * 60}ms`,
          boxShadow: "0 0 0 1px rgba(212,175,55,0.2), 0 8px 32px rgba(0,0,0,0.4)",
        }}
      >
        {/* Image / Placeholder */}
        <div className="relative aspect-[4/3] overflow-hidden bg-gradient-to-br from-[#1a1a14] to-[#0B0B0B]">
          {/* Placeholder — always rendered; hidden once image loads */}
          <div
            className={`absolute inset-0 flex items-center justify-center transition-opacity duration-500 ${showPhoto && imgLoaded ? "opacity-0" : "opacity-100"}`}
          >
            <span className="font-display select-none text-5xl font-bold text-[#D4AF37]/25">
              {getInitials(listing.address)}
            </span>
          </div>

          {/* Photo */}
          {showPhoto && (
            <img
              src={photo}
              alt={listing.address}
              className={`absolute inset-0 h-full w-full object-cover transition-all duration-500 hover:scale-105 ${imgLoaded ? "opacity-100" : "opacity-0"}`}
              onLoad={() => setImgLoaded(true)}
              onError={() => setImgError(true)}
            />
          )}

          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent" />

          {/* Source badge */}
          <span
            className="absolute right-3 top-3 rounded-full px-2.5 py-1 font-['DM_Mono',monospace] text-[0.58rem] uppercase tracking-[0.12em] text-white backdrop-blur-sm"
            style={{ backgroundColor: `${badgeColor}cc` }}
          >
            {(listing.source || "").toUpperCase()}
          </span>

          {/* Transit score badge */}
          {listing.transit_score != null && (
            <span
              className="absolute bottom-3 left-3 rounded-full px-2.5 py-1 font-['DM_Mono',monospace] text-[0.58rem] uppercase tracking-[0.12em] text-white backdrop-blur-sm"
              style={{ backgroundColor: "rgba(22,120,76,0.85)" }}
              title="Transit proximity score: Ontario Line / Eglinton Crosstown"
            >
              Transit {listing.transit_score}/10
            </span>
          )}
        </div>

        {/* Info panel */}
        <div className="glass-panel p-5">
          <div className="mb-3">
            <div className="font-display text-[1.8rem] font-bold text-gold-gradient">
              {formatPrice(listing.price)}
            </div>
            <div className="mt-0.5 font-['DM_Mono',monospace] text-[0.72rem] leading-snug text-[#6b6b60]">
              {listing.address}
            </div>
          </div>

          <div className="mb-4 grid grid-cols-3 gap-2 border-y border-[rgba(212,175,55,0.15)] py-3 text-center">
            {(
              [
                ["Beds",   listing.beds  || "—"],
                ["Baths",  listing.baths || "—"],
                ["Sq Ft",  listing.sqft  ? listing.sqft.toLocaleString() : "—"],
              ] as [string, string | number][]
            ).map(([label, val]) => (
              <div key={label}>
                <div className="text-[1rem] font-bold">{val}</div>
                <div className="mt-0.5 font-['DM_Mono',monospace] text-[0.55rem] uppercase tracking-[0.1em] text-[#6b6b60]">
                  {label}
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <a
              href={listing.url}
              target="_blank"
              rel="noreferrer"
              className="flex-1 border border-[rgba(212,175,55,0.3)] py-2 text-center font-['DM_Mono',monospace] text-[0.68rem] uppercase tracking-[0.08em] text-[#f5f4ef] no-underline transition-colors hover:border-[#D4AF37] hover:text-[#D4AF37]"
            >
              View Listing →
            </a>
            {onValuate && (
              <button
                className="flex-1 rounded-none gold-gradient gold-glow py-2 font-['DM_Mono',monospace] text-[0.68rem] font-bold uppercase tracking-[0.12em] text-black transition-opacity hover:opacity-95"
                onClick={() => onValuate(listing)}
              >
                Valuate
              </button>
            )}
          </div>
        </div>
      </div>
    </HoverCardWrapper>
  );
}
