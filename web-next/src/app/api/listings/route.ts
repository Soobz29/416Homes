import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy route — forwards /api/listings requests to the DO backend server-side,
 * completely bypassing browser CORS restrictions.
 *
 * Uses a 25-second AbortController timeout (Vercel Hobby limit is 60s,
 * but the DO backend cold-start is ~30s — we give 25s then 502 so the
 * browser can retry rather than hanging indefinitely).
 */
const BACKEND = (
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://fouronesixhomes-mcr6b.ondigitalocean.app"
).replace(/\/$/, "");

export const dynamic = "force-dynamic"; // never cache this route

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const upstream = `${BACKEND}/api/listings?${searchParams.toString()}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 25_000);

  try {
    const res = await fetch(upstream, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });

    clearTimeout(timer);

    if (!res.ok) {
      return NextResponse.json(
        { listings: [], total: 0, scan_time: null, error: `upstream ${res.status}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    clearTimeout(timer);
    const isTimeout = err instanceof Error && err.name === "AbortError";
    console.error("[listings proxy] fetch failed:", err);
    return NextResponse.json(
      {
        listings: [],
        total: 0,
        scan_time: null,
        error: isTimeout ? "upstream timeout" : "upstream unreachable",
      },
      { status: 502 }
    );
  }
}
