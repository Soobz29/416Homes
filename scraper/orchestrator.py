import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
import hashlib

from .kijiji import scrape_kijiji
from .redfin import scrape_redfin
from .zoocasa import scrape_zoocasa
from .housesigma import scrape_housesigma
from .condos_ca import scrape_condos_ca
from .zillow import scrape_zillow
from .realtor_ca import scrape_realtor_ca

logger = logging.getLogger(__name__)


class ScraperError(RuntimeError):
    """Raised by an individual scraper when ALL of its fetch strategies failed.

    A scraper that legitimately found zero listings should still return [] —
    this is reserved for "the scraper is broken" (network, parser, anti-bot).
    """


def dedupe_listings(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate listings based on address + price hash"""
    seen = set()
    deduped = []
    for listing in listings:
        price = listing.get('price') or listing.get('sold_price', 0)
        hash_key = hashlib.md5(
            f"{listing['address']}_{price}".encode()
        ).hexdigest()
        if hash_key not in seen:
            seen.add(hash_key)
            deduped.append(listing)
    return deduped


def _write_run_summary(summary: Dict[str, Any]) -> None:
    """Write per-run summary to scraper/last_run_summary.json for GH Actions guard.

    Format:
      {"total_listings": 142,
       "per_source": {"realtor_ca": {"ok": true, "count": 87, "error": null}, ...},
       "ran_at": "2026-05-16T..."}
    """
    try:
        out = Path(__file__).resolve().parent / "last_run_summary.json"
        out.write_text(json.dumps(summary, indent=2))
        logger.info(f"Wrote run summary to {out}")
    except Exception as e:
        logger.warning(f"Failed to write run summary: {e}")


async def run_all_sources(area: str = "gta") -> List[Dict[str, Any]]:
    """Run all scrapers concurrently. Returns deduplicated GTA listings.

    Raises RuntimeError if >=50% of scrapers fail (pipeline broken).
    Writes scraper/last_run_summary.json for GH Actions to inspect.
    """
    sources = {
        "realtor_ca": scrape_realtor_ca,
        "zoocasa": scrape_zoocasa,
        "housesigma": scrape_housesigma,
        "condos_ca": scrape_condos_ca,
        "zillow": scrape_zillow,
        "kijiji": scrape_kijiji,
        "redfin": scrape_redfin,
    }

    tasks = [
        asyncio.create_task(_run_scraper(source_name, scraper_func, area))
        for source_name, scraper_func in sources.items()
    ]
    results: List[Tuple[str, bool, List[Dict[str, Any]], str]] = await asyncio.gather(*tasks)

    per_source: Dict[str, Dict[str, Any]] = {}
    all_listings: List[Dict[str, Any]] = []
    for source_name, ok, listings, error in results:
        per_source[source_name] = {"ok": ok, "count": len(listings), "error": error}
        if ok:
            all_listings.extend(listings)

    failed = [s for s, r in per_source.items() if not r["ok"]]
    deduped_listings = dedupe_listings(all_listings)

    summary = {
        "total_listings": len(deduped_listings),
        "raw_total": len(all_listings),
        "per_source": per_source,
        "failed_sources": failed,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_run_summary(summary)

    logger.info(f"Scrape summary: {per_source}")
    logger.info(f"Total raw: {len(all_listings)}, deduped: {len(deduped_listings)}, failed: {failed}")

    # If at least half the scrapers crashed, the pipeline is broken — fail loud.
    if failed and len(failed) >= max(1, len(sources) // 2):
        raise RuntimeError(
            f"Scraper pipeline degraded: {len(failed)}/{len(sources)} sources failed: {failed}"
        )

    return deduped_listings


async def _run_scraper(source_name: str, scraper_func, area: str) -> Tuple[str, bool, List[Dict[str, Any]], str]:
    """Run a single scraper. Returns (name, ok, listings, error_msg).

    Never raises — callers inspect the tuple. The orchestrator decides whether
    the overall pipeline is healthy based on the aggregate failure count.
    """
    try:
        logger.info(f"Starting {source_name} scraper for {area}")
        listings = await scraper_func(area)
        if not isinstance(listings, list):
            return (source_name, False, [], f"returned non-list: {type(listings).__name__}")
        logger.info(f"{source_name} found {len(listings)} listings")
        return (source_name, True, listings, "")
    except Exception as e:
        logger.error(f"{source_name} scraper failed: {e}", exc_info=True)
        return (source_name, False, [], str(e))


# Backwards-compat alias kept for any callers still using the old name.
run_scraper_with_error_handling = _run_scraper
