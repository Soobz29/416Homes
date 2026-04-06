import { Listing } from "@/types";
import { formatPrice } from "@/lib/utils";

interface ListingCardProps {
  listing: Listing;
}

export function ListingCard({ listing }: ListingCardProps) {
  return (
    <div className="glass-panel overflow-hidden transition-transform duration-300 hover:scale-[1.02]">
      {/* Image placeholder with glassmorphic data overlay */}
      <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-[#1a1a14] to-[#0B0B0B]">
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        {/* Beds / Baths / SqFt pill row */}
        <div className="absolute bottom-3 left-3 right-3 flex gap-2">
          <span className="glass-panel rounded-sm px-2 py-1 font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.08em] text-[#f5f4ef]">
            {listing.beds} bd
          </span>
          <span className="glass-panel rounded-sm px-2 py-1 font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.08em] text-[#f5f4ef]">
            {listing.baths} ba
          </span>
          {listing.sqft > 0 && (
            <span className="glass-panel rounded-sm px-2 py-1 font-['DM_Mono',monospace] text-[0.6rem] uppercase tracking-[0.08em] text-[#f5f4ef]">
              {listing.sqft.toLocaleString()} sqft
            </span>
          )}
        </div>
      </div>

      <div className="p-6">
        <div className="mb-3">
          <h3 className="text-2xl font-bold text-[#D4AF37]">
            {formatPrice(listing.price)}
          </h3>
          <p className="mt-1 text-sm text-[#f5f4ef]/80">{listing.address}</p>
          {(listing.city || listing.region) && (
            <p className="text-xs text-[#6b6b60]">
              {listing.city}
              {listing.city && listing.region ? ", " : ""}
              {listing.region}
            </p>
          )}
        </div>

        <div className="mt-4 flex justify-between text-xs text-[#6b6b60]">
          <span>{listing.property_type}</span>
          <span>{listing.source}</span>
        </div>
      </div>
    </div>
  );
}
