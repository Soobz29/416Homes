const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export async function fetchListings(params?: {
  city?: string;
  minPrice?: number;
  maxPrice?: number;
  propertyTypes?: string[];
}) {
  const queryParams = new URLSearchParams();
  if (params?.city) queryParams.append("city", params.city);
  if (params?.minPrice) queryParams.append("min_price", params.minPrice.toString());
  if (params?.maxPrice) queryParams.append("max_price", params.maxPrice.toString());
  if (params?.propertyTypes?.length) queryParams.append("property_types", params.propertyTypes.join(","));

  const url = `${API_BASE}/api/listings?${queryParams.toString()}`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Failed to fetch listings");
  }

  // FastAPI returns listings with bedrooms/bathrooms/area strings.
  const data = await response.json();
  return {
    listings: (data as any[]).map((l) => ({
      id: l.id,
      address: l.address,
      price: Number(l.price) || 0,
      beds: Number(l.bedrooms) || 0,
      baths: Number(l.bathrooms) || 0,
      sqft: Number(l.area) || 0,
      city: "", // not present on backend response today
      region: "",
      property_type: l.strategy ?? "Unknown",
      source: l.source,
      url: l.url,
      photos: [],
      created_at: l.scraped_at,
    })),
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

