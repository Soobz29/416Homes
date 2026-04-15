export interface Listing {
  id: string;
  address: string;
  price: number;
  beds: number;
  baths: number;
  sqft: number;
  city: string;
  region: string;
  property_type: string;
  source: string;
  url: string;
  photos?: string[];
  created_at: string;
  transit_score?: number | null;
  is_assignment?: boolean | null;
  floor_plan_url?: string | null;
}

export interface VideoJob {
  id: string;
  job_id: string;
  tier: "basic" | "cinematic" | "premium";
  status: "pending" | "generating" | "completed" | "failed";
  listing_url: string;
  video_url?: string;
  created_at: string;
}

export interface Valuation {
  estimated_value: number;
  confidence: number;
  market_analysis: string;
  comparable_sales?: Array<{
    address: string;
    price: number;
    sold_date: string;
  }>;
}

