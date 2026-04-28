import * as React from "react"
import { ArrowRight, Home, Building2, HardHat, Bed, Bath, Maximize2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatPrice } from "@/lib/utils"
import type { Listing } from "@/types"

interface ListingDestinationCardProps extends React.HTMLAttributes<HTMLDivElement> {
  listing: Listing
  /** HSL string for the glow/gradient theme, e.g. "42 100% 35%" (amber) */
  themeColor?: string
}

function propertyIcon(type: string, isAssignment?: boolean) {
  if (isAssignment) return <HardHat size={14} />
  if (type?.toLowerCase().includes("condo") || type?.toLowerCase().includes("apartment"))
    return <Building2 size={14} />
  return <Home size={14} />
}

/**
 * Visual listing card inspired by DestinationCard (card-21).
 * Adapted for the 416Homes Terminal Broker palette:
 *   – no border-radius (square corners, matching --radius: 0px)
 *   – amber accent glow
 *   – monospace typography
 *   – dark overlay gradient
 */
const ListingDestinationCard = React.forwardRef<HTMLDivElement, ListingDestinationCardProps>(
  ({ className, listing, themeColor = "42 100% 35%", ...props }, ref) => {
    const imageUrl =
      listing.photos?.[0] ||
      "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=600&q=80"

    const label = listing.neighbourhood || listing.city || listing.address.split(",")[0]
    const priceStr = formatPrice(listing.price)
    const statsLine = [
      listing.beds ? `${listing.beds}bd` : null,
      listing.baths ? `${listing.baths}ba` : null,
      listing.sqft ? `${listing.sqft.toLocaleString()} sqft` : null,
    ]
      .filter(Boolean)
      .join(" · ")

    return (
      <div
        ref={ref}
        style={{ "--theme-color": themeColor } as React.CSSProperties}
        className={cn("group w-full h-full", className)}
        {...props}
      >
        <a
          href={listing.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`View listing at ${listing.address}`}
          className="relative block w-full h-full overflow-hidden transition-all duration-500 ease-in-out
                     group-hover:scale-[1.02]"
          style={{
            boxShadow: `0 0 32px -12px hsl(var(--theme-color) / 0.45)`,
            outline: "1px solid rgba(255,176,0,0.20)",
          }}
          onMouseEnter={e => {
            ;(e.currentTarget as HTMLElement).style.boxShadow =
              `0 0 56px -10px hsl(var(--theme-color) / 0.65)`
            ;(e.currentTarget as HTMLElement).style.outline =
              "1px solid rgba(255,176,0,0.55)"
          }}
          onMouseLeave={e => {
            ;(e.currentTarget as HTMLElement).style.boxShadow =
              `0 0 32px -12px hsl(var(--theme-color) / 0.45)`
            ;(e.currentTarget as HTMLElement).style.outline =
              "1px solid rgba(255,176,0,0.20)"
          }}
        >
          {/* Background photo with parallax zoom on hover */}
          <div
            className="absolute inset-0 bg-cover bg-center transition-transform duration-500 ease-in-out group-hover:scale-110"
            style={{ backgroundImage: `url(${imageUrl})` }}
          />

          {/* Gradient overlay — dark-to-amber rising from bottom */}
          <div
            className="absolute inset-0"
            style={{
              background: `linear-gradient(to top, hsl(var(--theme-color) / 0.88), hsl(var(--theme-color) / 0.45) 32%, transparent 62%)`,
            }}
          />

          {/* Top-right badge: assignment / new */}
          {listing.is_assignment && (
            <div
              className="absolute top-3 right-3 z-10 flex items-center gap-1"
              style={{
                fontFamily: "var(--mono)",
                fontSize: "0.52rem",
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--accent)",
                background: "rgba(5,6,10,0.82)",
                border: "1px solid rgba(255,176,0,0.40)",
                padding: "4px 8px",
              }}
            >
              <HardHat size={10} />
              <span>Assignment</span>
            </div>
          )}

          {/* Content */}
          <div className="relative flex flex-col justify-end h-full p-5" style={{ color: "var(--accent)" }}>
            {/* Address + neighbourhood */}
            <p
              style={{
                fontFamily: "var(--mono)",
                fontSize: "0.6rem",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "rgba(255,176,0,0.70)",
                marginBottom: 4,
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              {propertyIcon(listing.property_type, listing.is_assignment)}
              {label}
            </p>

            {/* Price */}
            <h3
              style={{
                fontFamily: "var(--mono)",
                fontSize: "clamp(1.1rem, 2.2vw, 1.5rem)",
                fontWeight: 700,
                letterSpacing: "-0.01em",
                lineHeight: 1.1,
                color: "var(--accent)",
                marginBottom: 4,
              }}
            >
              {priceStr}
            </h3>

            {/* Beds · baths · sqft */}
            {statsLine && (
              <p
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: "0.68rem",
                  color: "rgba(255,176,0,0.80)",
                  marginBottom: 16,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                {listing.beds ? <><Bed size={10} /> {listing.beds}</> : null}
                {listing.baths ? <><Bath size={10} /> {listing.baths}</> : null}
                {listing.sqft ? <><Maximize2 size={10} /> {listing.sqft.toLocaleString()} sqft</> : null}
              </p>
            )}

            {/* CTA bar */}
            <div
              className="flex items-center justify-between transition-all duration-300
                         group-hover:bg-[hsl(var(--theme-color)/0.45)]"
              style={{
                background: "rgba(5,6,10,0.55)",
                backdropFilter: "blur(8px)",
                border: "1px solid rgba(255,176,0,0.25)",
                padding: "11px 14px",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: "0.6rem",
                  fontWeight: 700,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  color: "var(--accent)",
                }}
              >
                View Listing
              </span>
              <ArrowRight
                size={13}
                color="var(--accent)"
                className="transform transition-transform duration-300 group-hover:translate-x-1"
              />
            </div>
          </div>
        </a>
      </div>
    )
  },
)
ListingDestinationCard.displayName = "ListingDestinationCard"

export { ListingDestinationCard }
