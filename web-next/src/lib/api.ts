const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  "https://fouronesixhomes-mcr6b.ondigitalocean.app"
).replace(/\/$/, "");

/** Undo bad https://cdn.zoocasa.com/https://images.expcloud.com/...-1.jpg URLs from older scrapes. */
function fixZoocasaWrappedPhotoUrl(url: string): string {
  if (!url || !url.includes("cdn.zoocasa.com/https://")) return url;
  const inner = url.split("cdn.zoocasa.com/").pop() ?? url;
  if (inner.startsWith("https://") && inner.endsWith("-1.jpg")) {
    return inner.slice(0, -"-1.jpg".length);
  }
  return inner.startsWith("https://") ? inner : url;
}

function coercePhotoUrls(value: unknown): string[] {
  if (!value) return [];
  if (typeof value === "string") {
    const v = fixZoocasaWrappedPhotoUrl(value.trim());
    return /^https?:\/\//i.test(v) ? [v] : [];
  }
  if (Array.isArray(value)) {
    const out: string[] = [];
    for (const item of value) {
      if (typeof item === "string") {
        const u = fixZoocasaWrappedPhotoUrl(item.trim());
        if (/^https?:\/\//i.test(u)) out.push(u);
      } else if (item && typeof item === "object") {
        const obj = item as Record<string, unknown>;
        const candidates = [obj.url, obj.href, obj.src, obj.highResPath, obj.HighResPath];
        for (const cand of candidates) {
          if (typeof cand === "string") {
            const u = fixZoocasaWrappedPhotoUrl(cand.trim());
            if (/^https?:\/\//i.test(u)) out.push(u);
          }
        }
      }
    }
    return out;
  }
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const candidates = [obj.url, obj.href, obj.src, obj.highResPath, obj.HighResPath];
    return candidates
      .filter((v): v is string => typeof v === "string")
      .map((v) => fixZoocasaWrappedPhotoUrl(v.trim()))
      .filter((v) => /^https?:\/\//i.test(v));
  }
  return [];
}

function extractListingPhotos(listing: any): string[] {
  const raw = listing?.raw_data && typeof listing.raw_data === "object" ? listing.raw_data : {};
  const candidates = [
    listing?.photos,
    listing?.photo,
    (raw as { image_root_storage_key?: string }).image_root_storage_key,
    (raw as any).photos,
    (raw as any).photo,
    (raw as any).image,
    (raw as any).images,
    (raw as any).image_url,
    (raw as any).image_urls,
    (raw as any).photo_url,
    (raw as any).photo_urls,
    (raw as any).thumbnail,
    (raw as any).thumbnails,
  ];
  const seen = new Set<string>();
  const photos: string[] = [];
  for (const candidate of candidates) {
    for (const url of coercePhotoUrls(candidate)) {
      if (!seen.has(url)) {
        seen.add(url);
        photos.push(url);
      }
    }
  }
  return photos;
}

/** Parse city from "Street, City, ON, Postal" style address */
function parseCityFromAddress(address: string): string {
  if (!address) return "";
  const parts = address.split(",").map(p => p.trim());
  // Find the part immediately before a 2-letter province code
  for (let i = 0; i < parts.length - 1; i++) {
    if (/^(ON|BC|AB|QC|MB|SK|NS|NB|PE|NL|NT|YT|NU)$/i.test(parts[i + 1])) {
      return parts[i];
    }
  }
  // Fallback: second comma-delimited token
  return parts.length >= 2 ? parts[1] : "";
}

export async function fetchListings(params?: {
  city?: string;
  minPrice?: number;
  maxPrice?: number;
  propertyTypes?: string[];
  limit?: number;
  offset?: number;
}) {
  const queryParams = new URLSearchParams();
  if (params?.city) queryParams.append("city", params.city);
  if (params?.minPrice) queryParams.append("min_price", params.minPrice.toString());
  if (params?.maxPrice) queryParams.append("max_price", params.maxPrice.toString());
  if (params?.propertyTypes?.length) queryParams.append("property_types", params.propertyTypes.join(","));
  queryParams.append("limit", String(params?.limit ?? 20));
  queryParams.append("offset", String(params?.offset ?? 0));

  const url = `${API_BASE}/api/listings?${queryParams.toString()}`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Failed to fetch listings");
  }

  // API returns { listings, total, scan_time } or legacy array.
  const data = await response.json();
  const rawListings = Array.isArray(data) ? data : (data?.listings ?? []);
  return {
    listings: rawListings.map((l: any) => ({
      id: l.id,
      address: l.address,
      price: Number(l.price) || 0,
      beds: Number(l.bedrooms) || 0,
      baths: Number(l.bathrooms) || 0,
      sqft: Number(l.area) || 0,
      city: l.city || parseCityFromAddress(l.address),
      region: l.region || "",
      property_type: l.strategy ?? l.property_type ?? "Unknown",
      source: l.source,
      url: l.url,
      photos: extractListingPhotos(l),
      created_at: l.scraped_at,
      // Scrapers return lat/lng — pass them through
      lat:  l.lat  != null ? Number(l.lat)  : undefined,
      lng:  l.lng  != null ? Number(l.lng)  : undefined,
      neighbourhood:  l.neighbourhood  || undefined,
      transit_score:  l.transit_score  != null ? Number(l.transit_score)  : undefined,
      fair_value:     l.fair_value     != null ? Number(l.fair_value)     : undefined,
      dom:            l.dom            != null ? Number(l.dom)            : undefined,
      floor_plan_url: l.floor_plan_url || undefined,
      is_assignment:  l.is_assignment  || false,
    })),
    total: typeof data?.total === "number" ? data.total : rawListings.length,
    scan_time: data?.scan_time ?? null,
  };
}

export async function fetchValuation(data: {
  neighbourhood: string;
  property_type: string;
  city: string;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  list_price: number;
}) {
  const response = await fetch(`${API_BASE}/api/valuate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Failed to get valuation");
  }

  return response.json();
}

export async function createVideoJob(data: {
  listing_url: string;
  customer_email: string;
  customer_name?: string;
}) {
  const response = await fetch(`${API_BASE}/api/video-jobs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Failed to create video job");
  }

  return response.json();
}

