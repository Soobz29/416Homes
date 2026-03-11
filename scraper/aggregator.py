import asyncio
import logging
from typing import List, Dict, Any
from scraper.realtor_ca import scrape_realtor_ca
from scraper.zoocasa import scrape_zoocasa
from scraper.condos_ca import scrape_condos_ca as scrape_condos
from scraper.kijiji import scrape_kijiji
from listing_agent.activity_log import log_activity

logger = logging.getLogger(__name__)


async def _realtor_ca_wrapper():
    return await scrape_realtor_ca("gta")


async def _zoocasa_wrapper():
    return await scrape_zoocasa("gta")


async def _kijiji_wrapper():
    return await scrape_kijiji("gta")


SCRAPERS = [
    {"name": "realtor_ca", "fn": _realtor_ca_wrapper, "weight": 3},
    {"name": "zoocasa", "fn": _zoocasa_wrapper, "weight": 2},
    {"name": "condos_ca", "fn": scrape_condos, "weight": 2},
    {"name": "kijiji", "fn": _kijiji_wrapper, "weight": 2},
]

def _detect_region(location_str: str) -> str:
    if not location_str: return "Toronto"
    location = location_str.lower()
    region_keywords = {
        "Mississauga": ["mississauga"],
        "Brampton": ["brampton"],
        "Vaughan": ["vaughan", "woodbridge", "maple"],
        "Markham": ["markham", "unionville"],
        "Richmond Hill": ["richmond hill"],
        "Oakville": ["oakville"],
        "Burlington": ["burlington"],
        "Ajax & Pickering": ["ajax", "pickering"],
        "Toronto (Downtown)": ["downtown", "waterfront", "king west",
                             "queen west", "financial district"],
        "Toronto (Scarborough)": ["scarborough", "m1", "m2", "m3"],
        "Toronto (Etobicoke)": ["etobicoke", "m8", "m9"],
        "Toronto (North York)": ["north york", "willowdale", "m2", "m3", "m4", "m5", "m6"],
        "Toronto (Core)": ["toronto", "m4", "m5", "m6"],
    }
    for region, keywords in region_keywords.items():
        if any(kw in location for kw in keywords):
            return region
    return "Toronto"  # default fallback

async def scrape_all_sources(regions=None) -> List[Dict[str, Any]]:
    """
    Run all scrapers concurrently. Deduplicate by address+price.
    If a scraper fails or returns 0 results, log it and continue.
    Always return combined results from whatever sources worked.
    """
    tasks = [_run_scraper(s) for s in SCRAPERS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    seen = set()
    listings = []
    source_counts = {}
    
    for scraper, result in zip(SCRAPERS, results):
        name = scraper["name"]
        if isinstance(result, Exception):
            log_activity("ERROR", f"{name} scraper failed: {result}")
            source_counts[name] = 0
            continue
            
        count = 0
        for listing in result:
            # Standardize region if missing
            if not listing.get("region"):
                listing["region"] = _detect_region(listing.get("address", ""))
                
            # Deduplication key
            addr = str(listing.get('address','')).strip().lower()
            price = str(listing.get('price',''))
            key = f"{addr}_{price}"
            
            if key not in seen and addr:
                seen.add(key)
                listing["source"] = name
                listings.append(listing)
                count += 1
                
        source_counts[name] = count
        log_activity("SCAN", f"{name}: {count} listings")
    
    log_activity("SCAN", 
        f"Total: {len(listings)} unique listings — " +
        ", ".join(f"{k}:{v}" for k,v in source_counts.items())
    )
    return listings

async def _run_scraper(scraper: dict) -> list:
    try:
        # We don't pass regions to all scrapers yet, just run default for and filter in agent if needed
        # realtor_ca handles regions internally if needed, others are city-based
        return await scraper["fn"]() or []
    except Exception as e:
        logger.error(f"{scraper['name']} raised error: {e}")
        return []
