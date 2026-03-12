#!/usr/bin/env python3
"""
Run a full nightly-style scan: scrape all sources, then replace Supabase
listings with the new set (removes old listings, stores only current ones).
Prioritizes real addresses (badge-only / "Just listed" are already filtered out
by the aggregator).

Usage:
  python scripts/run_nightly_scan.py
  # Or via Railway:
  railway run python scripts/run_nightly_scan.py
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Project root
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
os.chdir(_root)

try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nightly_scan")


async def main():
    logger.info("Starting nightly scan (scrape all sources -> replace Supabase)...")

    try:
        from scraper.aggregator import scrape_all_sources
        listings = await scrape_all_sources()
    except Exception as e:
        logger.exception("Scraper failed: %s", e)
        sys.exit(1)

    logger.info("Scrape complete: %d listings (already filtered to real addresses)", len(listings))

    # Exclude HouseSigma sold comps; keep only regular listings
    regular = [
        L for L in listings
        if L.get("source") != "housesigma" and "sold_price" not in L
    ]
    logger.info("Regular listings to store: %d", len(regular))

    if not regular:
        logger.warning("No regular listings to store. Clearing Supabase anyway.")
    else:
        # Optional: enrich so city/address are filled (no UNKNOWN)
        try:
            from listing_agent import enrich_listings_strict
            regular = await enrich_listings_strict(regular)
            logger.info("Enriched %d listings", len(regular))
        except Exception as e:
            logger.warning("Enrichment skipped: %s", e)

    try:
        from memory.store import replace_listings
        stored = await replace_listings(regular)
        logger.info("Supabase replaced: %d listings stored (old ones removed)", stored)
    except Exception as e:
        logger.exception("Failed to replace listings in Supabase: %s", e)
        sys.exit(1)

    logger.info("Nightly scan finished. Dashboard and Telegram will show the new set.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
