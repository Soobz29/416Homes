import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy route — forwards /api/listings requests to the DO backend server-side,
 * completely bypassing browser CORS restrictions.
 */
const BACKEND =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://fouronesixhomes-mcr6b.ondigitalocean.app";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const upstream = `${BACKEND}/api/listings?${searchParams.toString()}`;

  try {
    const res = await fetch(upstream, {
      headers: { Accept: "application/json" },
      next: { revalidate: 60 }, // cache 60 s on Vercel edge
    });

    if (!res.ok) {
      return NextResponse.json(
        { listings: [], total: 0, scan_time: null, error: `upstream ${res.status}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("[listings proxy] fetch failed:", err);
    return NextResponse.json(
      { listings: [], total: 0, scan_time: null, error: "upstream unreachable" },
      { status: 502 }
    );
  }
}
