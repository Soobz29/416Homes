"""
Zoocasa public sold-comps scraper.

Zoocasa exposes sold listings at URLs like:
  https://www.zoocasa.com/toronto-on-real-estate/sold

Unlike HouseSigma these pages are mostly Cloudflare-free and reachable with a
standard headless browser.  Reuses browser_util.create_browser() so it works
on both Linux/CI (Playwright) and Windows (DrissionPage / UC Chrome).

Usage:
    python -m scraper.zoocasa_sold              # all GTA cities → stdout summary
    python -m scraper.zoocasa_sold toronto      # one city
"""

import asyncio
import hashlib
import logging
import re
import time
import random
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

SOLD_URLS: Dict[str, str] = {
    "toronto":     "https://www.zoocasa.com/toronto-on-real-estate/sold",
    "mississauga": "https://www.zoocasa.com/mississauga-on-real-estate/sold",
    "brampton":    "https://www.zoocasa.com/brampton-on-real-estate/sold",
    "markham":     "https://www.zoocasa.com/markham-on-real-estate/sold",
    "vaughan":     "https://www.zoocasa.com/vaughan-on-real-estate/sold",
    "richmond_hill": "https://www.zoocasa.com/richmond-hill-on-real-estate/sold",
    "oakville":    "https://www.zoocasa.com/oakville-on-real-estate/sold",
    "ajax":        "https://www.zoocasa.com/ajax-on-real-estate/sold",
    "pickering":   "https://www.zoocasa.com/pickering-on-real-estate/sold",
}

# CSS selectors to try for property cards (Zoocasa changes these periodically)
_CARD_SELECTORS = [
    '[data-testid="listing-card"]',
    '[data-testid="property-card"]',
    '.listing-card',
    '.property-card',
    'article[class*="listing"]',
    'article[class*="property"]',
    'li[class*="listing"]',
    'li[class*="property"]',
    'a[href*="-real-estate/"]',   # fallback: any internal RE link
]


def _parse_price(text: str) -> int:
    """Extract integer price from text like '$1,250,000'."""
    m = re.search(r'[\$]?([\d,]+)', text.replace(" ", ""))
    if not m:
        return 0
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return 0


def _scrape_city_sync(city: str, area_name: str) -> List[Dict[str, Any]]:
    """Scrape one city's sold page. Returns list of sold_comps rows."""
    from .browser_util import create_browser

    url = SOLD_URLS.get(city)
    if not url:
        return []

    page = None
    rows: List[Dict[str, Any]] = []

    try:
        page = create_browser(headless=True)
        logger.info(f"ZoocasaSold [{city}]: loading {url}")
        page.get(url, retry=1, interval=2, timeout=30)
        time.sleep(random.uniform(3, 6))

        # Scroll to trigger lazy-load
        for _ in range(6):
            page.scroll.down(random.randint(600, 900))
            time.sleep(random.uniform(1.0, 2.5))

        # Try each card selector until we find elements
        cards = []
        for sel in _CARD_SELECTORS:
            cards = page.eles(sel)
            if len(cards) >= 3:
                logger.info(f"ZoocasaSold [{city}]: found {len(cards)} cards with selector '{sel}'")
                break

        if not cards:
            # Last resort: grab all anchors with /sold/ or /-real-estate/ in href
            cards = [
                e for e in page.eles("tag:a")
                if ("/sold" in (e.attr("href") or "") or
                    "-real-estate/" in (e.attr("href") or ""))
            ]
            logger.info(f"ZoocasaSold [{city}]: fallback — {len(cards)} anchor elements")

        for card in cards:
            try:
                text = card.text or ""
                href = card.attr("href") or ""
                if not text and not href:
                    continue

                lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

                price = 0
                address = ""
                beds = ""
                baths = ""
                sqft_val = 0
                prop_type = ""
                sold_date = ""

                for line in lines:
                    # Price detection
                    if re.search(r'\$[\d,]+', line):
                        candidate = _parse_price(line)
                        if 50_000 < candidate < 15_000_000:
                            price = candidate
                    # Beds
                    elif re.search(r'\d+\s*(bed|bd|bdrm)', line, re.I):
                        m = re.search(r'(\d+)', line)
                        if m:
                            beds = m.group(1)
                    # Baths
                    elif re.search(r'\d+\s*(bath|ba)', line, re.I):
                        m = re.search(r'(\d+)', line)
                        if m:
                            baths = m.group(1)
                    # Sqft
                    elif re.search(r'[\d,]+\s*(sq\.?\s*ft|sqft|sf)', line, re.I):
                        m = re.search(r'([\d,]+)', line)
                        if m:
                            try:
                                sqft_val = int(m.group(1).replace(",", ""))
                            except ValueError:
                                pass
                    # Property type
                    elif re.search(r'(detached|semi|condo|townhouse|bungalow|townhome)', line, re.I):
                        prop_type = line.strip()
                    # Address heuristic: contains a number + street suffix
                    elif re.search(r'\d+.*(st|ave|rd|dr|blvd|cres|way|ct|pl|ln|trail|circ|gate)', line, re.I):
                        if not address:
                            address = line
                    # Date
                    elif re.search(r'sold', line, re.I):
                        dm = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                        if dm:
                            sold_date = dm.group(1)

                # If we got a price but no address, use href as address fallback
                if price > 0 and not address and href:
                    # Extract address-like slug from URL path
                    slug = href.rstrip("/").split("/")[-1]
                    address = slug.replace("-", " ").title()

                if price < 50_000:
                    continue

                full_url = href if href.startswith("http") else f"https://www.zoocasa.com{href}"
                uid = hashlib.md5(f"zoocasa_sold_{full_url}{price}".encode()).hexdigest()

                rows.append({
                    "id": uid,
                    "address": address or f"Listing, {area_name}",
                    "city": area_name,
                    "neighbourhood": area_name,
                    "sold_price": price,
                    "list_price": int(price * 1.01),   # rough estimate if not shown
                    "bedrooms": beds,
                    "bathrooms": baths,
                    "sqft": sqft_val,
                    "property_type": prop_type,
                    "sold_date": sold_date,
                    "days_on_market": 0,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                continue

        logger.info(f"ZoocasaSold [{city}]: parsed {len(rows)} sold comps")

    except Exception as e:
        logger.error(f"ZoocasaSold [{city}]: failed — {e}")
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass

    return rows


async def scrape_zoocasa_sold(areas: List[str] | None = None) -> List[Dict[str, Any]]:
    """
    Async entry point. Scrapes one or more cities from SOLD_URLS.
    Defaults to all cities if areas is None.
    """
    if areas is None:
        areas = list(SOLD_URLS.keys())

    all_rows: List[Dict[str, Any]] = []
    for city in areas:
        area_name = city.replace("_", " ").title()
        rows = await asyncio.to_thread(_scrape_city_sync, city, area_name)
        all_rows.extend(rows)

    return all_rows


def upsert_to_supabase(rows: List[Dict[str, Any]]) -> int:
    """Upsert scraped sold comps into the Supabase sold_comps table."""
    import os
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )
    total = 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i + 100]
        client.table("sold_comps").upsert(batch, on_conflict="id").execute()
        total += len(batch)
    return total


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    areas_arg = sys.argv[1:] if len(sys.argv) > 1 else None

    rows = asyncio.run(scrape_zoocasa_sold(areas_arg))
    print(f"\nScraped {len(rows)} sold comps total.")

    if rows:
        n = upsert_to_supabase(rows)
        print(f"Upserted {n} rows into sold_comps.")
        print("Re-run `python valuation/model.py` to retrain.")
    else:
        print("No rows — check browser logs above.")
