"""
scraper/aggregator.py — thin wrapper so both the listing_agent scan loop
and any future callers share one entry point.

All real logic lives in scraper/orchestrator.py.
"""
from scraper.orchestrator import run_all_sources


async def scrape_all_sources(area: str = "gta"):
    """Run all scrapers concurrently and return deduplicated listings."""
    return await run_all_sources(area=area)
