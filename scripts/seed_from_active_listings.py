"""
Bootstrap sold_comps from already-scraped active listings.

Each active listing becomes a proxy sold-comp at 99% of list price.
This is a free way to ground the LightGBM valuation model in real GTA
market shape without paying for sold-comp data.

Usage:
    python -m scripts.seed_from_active_listings
"""
import os
import hashlib
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def seed() -> int:
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )
    # Pull active listings with the columns the model needs
    actives = (
        client.table("listings")
        .select("id,address,city,neighbourhood,price,bedrooms,bathrooms,sqft,property_type,scraped_at")
        .not_.is_("price", "null")
        .not_.is_("sqft", "null")
        .execute()
        .data
    )
    print(f"Pulled {len(actives)} active listings from Supabase.")

    rows = []
    for a in actives:
        try:
            price = int(a.get("price") or 0)
            sqft = int(a.get("sqft") or 0)
        except (TypeError, ValueError):
            continue
        if price < 50_000 or price > 10_000_000:
            continue
        if sqft < 200 or sqft > 12_000:
            continue
        sp = int(price * 0.99)  # rough proxy: GTA sale-to-list is ~0.97-1.05
        uid = hashlib.md5(f"active_{a['id']}".encode()).hexdigest()
        rows.append({
            "id": uid,
            "address": a.get("address", ""),
            "city": a.get("city", ""),
            "neighbourhood": a.get("neighbourhood", ""),
            "sold_price": sp,
            "list_price": price,
            "bedrooms": str(a.get("bedrooms", "") or ""),
            "bathrooms": str(a.get("bathrooms", "") or ""),
            "sqft": sqft,
            "property_type": a.get("property_type", "") or "",
            "sold_date": datetime.now(timezone.utc).date().isoformat(),
            "days_on_market": 0,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })

    print(f"After cleaning: {len(rows)} usable proxy comps.")

    # Upsert in batches of 100
    for i in range(0, len(rows), 100):
        batch = rows[i:i + 100]
        client.table("sold_comps").upsert(batch, on_conflict="id").execute()
        print(f"  Batch {i // 100 + 1}: {len(batch)} rows upserted.")

    print(f"\nDone. Re-run `python valuation/model.py` to retrain on the new data.")
    return len(rows)


if __name__ == "__main__":
    seed()
