from __future__ import annotations

"""
Quick helper to inspect the production Supabase `listings` table.

Uses SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY from .env.

Run:
    python scripts/check_supabase_listings.py
"""

import os

from dotenv import load_dotenv

try:
    from supabase import create_client  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(f"supabase package not available: {e}")


def main() -> None:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise SystemExit("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY/KEY not set")

    client = create_client(url, key)

    resp = (
        client.table("listings")
        .select("id", count="exact")  # type: ignore[arg-type]
        .limit(1)
        .execute()
    )
    rows = getattr(resp, "data", None) or []
    count = getattr(resp, "count", None)

    print(f"First row present? {bool(rows)}")
    print(f"Total listings count (exact): {count}")


if __name__ == "__main__":
    main()

