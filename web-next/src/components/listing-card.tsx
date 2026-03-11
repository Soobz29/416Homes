import { Listing } from "@/types";
import { formatPrice } from "@/lib/utils";

interface ListingCardProps {
  listing: Listing;
}

export function ListingCard({ listing }: ListingCardProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/40 hover:shadow-lg transition-shadow">
      <div className="aspect-video bg-gradient-to-br from-slate-900 to-slate-800 relative" />
      <div className="p-6">
        <div className="mb-3">
          <h3 className="text-2xl font-bold text-[#d4af37]">
            {formatPrice(listing.price)}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">{listing.address}</p>
          {(listing.city || listing.region) && (
            <p className="text-xs text-muted-foreground">
              {listing.city}
              {listing.city && listing.region ? ", " : ""}
              {listing.region}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4 text-sm text-slate-200">
          <span>{listing.beds} beds</span>
          <span>{listing.baths} baths</span>
          {listing.sqft > 0 && <span>{listing.sqft.toLocaleString()} sqft</span>}
        </div>

        <div className="mt-4 text-xs text-slate-400 flex justify-between">
          <span>{listing.property_type}</span>
          <span>{listing.source}</span>
        </div>
      </div>
    </div>
  );
}

