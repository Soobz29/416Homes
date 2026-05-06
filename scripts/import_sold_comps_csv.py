"""
Import sold comps from a CSV file into Supabase.

Usage:
    python -m scripts.import_sold_comps_csv path/to/comps.csv

Expected CSV columns (headers, case-insensitive — extras are ignored):
    address, city, neighbourhood, sold_price, list_price, bedrooms,
    bathrooms, sqft, property_type, sold_date, days_on_market

Required: address + sold_price (or "price").
Missing columns are tolerated and stored as empty / null.
"""
import csv
import sys
import hashlib
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def _to_int(v: str, default: int = 0) -> int:
    if v is None or v == "":
        return default
    try:
        return int(float(str(v).replace("$", "").replace(",", "").strip()))
    except (TypeError, ValueError):
        return default


def import_csv(path: str) -> int:
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )

    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            address = r.get("address")
            sold_price_raw = r.get("sold_price") or r.get("price") or r.get("close_price")
            if not address or not sold_price_raw:
                continue
            sp = _to_int(sold_price_raw)
            if sp < 50_000 or sp > 20_000_000:
                continue

            uid = hashlib.md5(
                f"{address}{r.get('sold_date', '')}{sp}".encode()
            ).hexdigest()

            rows.append({
                "id": uid,
                "address": address,
                "city": r.get("city", ""),
                "neighbourhood": r.get("neighbourhood", "") or r.get("community", ""),
                "sold_price": sp,
                "list_price": _to_int(r.get("list_price", "")),
                "bedrooms": r.get("bedrooms", "") or r.get("beds", ""),
                "bathrooms": r.get("bathrooms", "") or r.get("baths", ""),
                "sqft": _to_int(r.get("sqft", "") or r.get("area", "")),
                "property_type": r.get("property_type", "") or r.get("type", ""),
                "sold_date": r.get("sold_date", "") or r.get("close_date", ""),
                "days_on_market": _to_int(r.get("days_on_market", "") or r.get("dom", "")),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

    print(f"Parsed {len(rows)} rows from {path}.")

    for i in range(0, len(rows), 100):
        batch = rows[i:i + 100]
        client.table("sold_comps").upsert(batch, on_conflict="id").execute()
        print(f"  Batch {i // 100 + 1}: {len(batch)} rows upserted.")

    print(f"\nImported {len(rows)} sold comps. "
          f"Re-run `python valuation/model.py` to retrain.")
    return len(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_sold_comps_csv path/to/comps.csv")
        sys.exit(1)
    import_csv(sys.argv[1])
