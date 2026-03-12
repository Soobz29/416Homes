import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import hashlib

from .kijiji import scrape_kijiji
from .redfin import scrape_redfin
from .zoocasa import scrape_zoocasa
from .housesigma import scrape_housesigma
from .condos_ca import scrape_condos_ca
from .zillow import scrape_zillow

logger = logging.getLogger(__name__)

def dedupe_listings(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate listings based on address + price hash"""
    seen = set()
    deduped = []
    
    for listing in listings:
        # Create hash from address + price for deduplication (handle both price and sold_price)
        price = listing.get('price') or listing.get('sold_price', 0)
        hash_key = hashlib.md5(
            f"{listing['address']}_{price}".encode()
        ).hexdigest()
        
        if hash_key not in seen:
            seen.add(hash_key)
            deduped.append(listing)
    
    return deduped

async def run_all_sources(area: str = "gta") -> List[Dict[str, Any]]:
    """Run all scrapers concurrently and return deduplicated results"""
    
    # Prioritize Zoocasa for GTA and temporarily exclude realtor.ca
    # (realtor.ca has been returning persistent 403s in CI).
    sources = {
        "zoocasa": scrape_zoocasa,
        "housesigma": scrape_housesigma,
        "condos_ca": scrape_condos_ca,
        "zillow": scrape_zillow,
        "kijiji": scrape_kijiji,
        "redfin": scrape_redfin,
    }
    
    tasks = []
    for source_name, scraper_func in sources.items():
        task = asyncio.create_task(
            run_scraper_with_error_handling(source_name, scraper_func, area)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_listings = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Scraper failed: {result}")
        elif isinstance(result, list):
            all_listings.extend(result)
    
    # Deduplicate listings
    deduped_listings = dedupe_listings(all_listings)
    
    logger.info(f"Total listings found: {len(all_listings)}")
    logger.info(f"After deduplication: {len(deduped_listings)}")
    
    return deduped_listings

async def run_scraper_with_error_handling(
    source_name: str, 
    scraper_func, 
    area: str
) -> List[Dict[str, Any]]:
    """Run individual scraper with error handling"""
    try:
        logger.info(f"Starting {source_name} scraper for {area}")
        listings = await scraper_func(area)
        logger.info(f"{source_name} found {len(listings)} listings")
        return listings
    except Exception as e:
        logger.error(f"{source_name} scraper failed: {e}")
        return []
