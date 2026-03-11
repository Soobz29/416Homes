#!/usr/bin/env python3
"""
Integration test: API reachability, Supabase listings, Mississauga filter, and cities in DB.
Run from 416homesV3:
  python scripts/test_integration.py
  API_BASE_URL=https://... python scripts/test_integration.py
"""
import asyncio
import os
import sys
from collections import Counter

# Load .env from project root so SUPABASE_* and API_BASE_URL are set
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

# Default to same URL the Telegram worker should use
DEFAULT_API = os.getenv("API_BASE_URL", "https://web-production-61e684.up.railway.app").rstrip("/")


def ok(msg: str) -> str:
    return f"[OK]   {msg}"


def fail(msg: str) -> str:
    return f"[FAIL] {msg}"


async def check_api_health(base: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{base}/api/health")
            if r.status_code == 200:
                return True, ok("API is reachable")
            return False, fail(f"API returned HTTP {r.status_code}")
    except Exception as e:
        return False, fail(f"API not reachable: {e}")


async def check_api_listings(base: str) -> tuple[bool, str, int]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{base}/api/listings", params={"limit": 5})
            r.raise_for_status()
            data = r.json()
            listings = data.get("listings", data) if isinstance(data, dict) else data
            if not isinstance(listings, list):
                listings = []
            total = data.get("total", len(listings)) if isinstance(data, dict) else len(listings)
            if total > 0 or len(listings) > 0:
                return True, ok(f"Supabase/API has listings (total={total})"), total
            return False, fail("Supabase has no listings (API returned 0)"), 0
    except Exception as e:
        return False, fail(f"Failed to fetch listings: {e}"), 0


async def check_mississauga(base: str) -> tuple[bool, str, int]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{base}/api/listings",
                params={"city": "Mississauga", "limit": 100},
            )
            r.raise_for_status()
            data = r.json()
            listings = data.get("listings", data) if isinstance(data, dict) else data
            if not isinstance(listings, list):
                listings = []
            total = data.get("total", len(listings)) if isinstance(data, dict) else len(listings)
            if total > 0:
                return True, ok(f"Mississauga listings exist ({total})"), total
            return False, fail("Mississauga listings do not exist (0)"), 0
    except Exception as e:
        return False, fail(f"Mississauga check failed: {e}"), 0


def get_cities_from_supabase() -> tuple[bool, list[tuple[str, int]]]:
    """List cities and counts in listings table (requires SUPABASE_URL + key). Returns [(city, count), ...]."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        return False, []
    try:
        from supabase import create_client
        client = create_client(url, key)
        result = client.table("listings").select("city").execute()
        rows = result.data or []
        cities = [str(r.get("city", "")).strip() for r in rows if r.get("city")]
        counts = Counter(c for c in cities if c)
        return True, sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    except Exception as e:
        return False, []


async def main():
    base = os.getenv("API_BASE_URL", DEFAULT_API).strip().rstrip("/")
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        base = sys.argv[1].rstrip("/")

    print("416Homes integration check")
    print("=" * 50)
    print(f"API_BASE_URL: {base}\n")

    # 1. API reachable
    ok_health, msg_health = await check_api_health(base)
    print(msg_health)

    # 2. Supabase has listings (via API)
    ok_listings, msg_listings, total = await check_api_listings(base)
    print(msg_listings)

    # 3. Mississauga
    ok_miss, msg_miss, miss_count = await check_mississauga(base)
    print(msg_miss)

    # 4. List of all cities (from Supabase if available)
    print("\nCities in database (from Supabase):")
    have_supabase, city_counts = get_cities_from_supabase()
    if have_supabase and city_counts:
        for city, count in city_counts:
            print(f"  • {city}: {count} listings")
    elif have_supabase:
        print("  (no cities or empty table)")
    else:
        if not os.getenv("SUPABASE_URL"):
            print("  (SUPABASE_URL not set - set it to see cities)")
        else:
            print("  (could not query Supabase - check SUPABASE_KEY / SUPABASE_SERVICE_ROLE_KEY)")

    print("\n" + "=" * 50)
    if ok_health and ok_listings:
        print("Summary: API and listings OK. Telegram /listings should work if API_BASE_URL is set on the worker.")
    else:
        print("Summary: Fix the failed checks above (API URL, Supabase, or scraper).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
