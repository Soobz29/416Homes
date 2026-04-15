import asyncio
import logging
import json
import re
import httpx
from typing import List, Dict, Any
from datetime import datetime, timezone

from scraper.stealth_headers import get_stealth_header_generator
from scraper.listing_utils import is_sold_or_inactive, pick_display_address

logger = logging.getLogger(__name__)
HEADER_GEN = get_stealth_header_generator()

ZOOCASA_URLS = [
    # Core GTA cities we care about
    "https://www.zoocasa.com/toronto-on-real-estate",
    "https://www.zoocasa.com/mississauga-on-real-estate",
    "https://www.zoocasa.com/brampton-on-real-estate",
    "https://www.zoocasa.com/vaughan-on-real-estate",
    "https://www.zoocasa.com/markham-on-real-estate",
    "https://www.zoocasa.com/oakville-on-real-estate",
    # Realtor.ca previously covered these regions; mirror them via Zoocasa
    "https://www.zoocasa.com/richmond-hill-on-real-estate",
    "https://www.zoocasa.com/burlington-on-real-estate",
    "https://www.zoocasa.com/ajax-on-real-estate",
    "https://www.zoocasa.com/pickering-on-real-estate",
]

def _detect_region(location_str: str) -> str:
    """Helper to detect GTA region from text."""
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
    return "Toronto"


def _zoocasa_listing_photo(item: Dict[str, Any]) -> str:
    """
    Zoocasa __NEXT_DATA__ historically used a storage key with cdn.zoocasa.com;
    newer payloads use a full https://images.expcloud.com/... URL in the same field.
    """
    key = item.get("image_root_storage_key")
    if not key:
        return ""
    key = str(key).strip()
    if key.startswith("http://") or key.startswith("https://"):
        return key
    return f"https://cdn.zoocasa.com/{key}-1.jpg"


async def _scrape_zoocasa_page(client, url: str) -> list:
    """Scrapes a single Zoocasa city page using __NEXT_DATA__."""
    try:
        headers = HEADER_GEN.generate(profile="chrome")
        headers.update(
            {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

        resp = await client.get(url, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            logger.error(f"Zoocasa page {url} failed with status {resp.status_code}")
            return []
        
        # Extract __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', 
                          resp.text, re.DOTALL)
        if not match:
            logger.warning(f"No __NEXT_DATA__ found on {url}")
            return []
        
        data = json.loads(match.group(1))
        raw = data.get("props", {}).get("pageProps", {}).get("props", {}).get("listings", [])
        
        listings = []
        for item in raw:
            status = item.get("status") or item.get("listing_status") or item.get("listing_status_label") or ""
            if is_sold_or_inactive(status):
                continue
            address = pick_display_address(
                item.get("address"),
                item.get("street_address"),
                item.get("full_address"),
                item.get("display_address"),
                item.get("formatted_address"),
            )
            photo = _zoocasa_listing_photo(item)
            
            region = _detect_region(
                (item.get("neighbourhood") or "") + " " + (item.get("address") or "")
            )
            # Map region to city for DB/dashboard (Toronto boroughs -> Toronto)
            city = "Toronto" if region.startswith("Toronto") else region.split(" ")[0]
            listings.append({
                "id": f"zoocasa_{item.get('id', item.get('slug', ''))}",
                "address": address,
                "price": item.get("price", ""),
                "bedrooms": item.get("bedrooms", ""),
                "bathrooms": item.get("bathrooms", ""),
                "sqft": item.get("square_footage", ""),
                "floor_plan_url": (
                    item.get("virtual_tour_url", "")
                    or item.get("floor_plan_url", "")
                    or item.get("tour_url", "")
                    or ""
                ),
                "neighbourhood": item.get("neighbourhood", ""),
                "url": f"https://www.zoocasa.com{item.get('listing_url_absolute_path', '')}",
                "photo": photo,
                "source": "zoocasa",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "region": region,
                "city": city,
            })
        return listings
    except Exception as e:
        logger.error(f"Error scraping Zoocasa page {url}: {e}")
        return []

async def scrape_listings() -> list:
    """Main entry point for Zoocasa scraper."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_scrape_zoocasa_page(client, url) for url in ZOOCASA_URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    listings = []
    for r in results:
        if isinstance(r, list):
            listings.extend(r)
        elif isinstance(r, Exception):
            logger.error(f"Zoocasa task failed: {r}")
    
    logger.info(f"Zoocasa: scraped {len(listings)} listings across {len(ZOOCASA_URLS)} pages.")
    return listings

# For backward compatibility
async def scrape_zoocasa(area: str = "gta") -> List[Dict[str, Any]]:
    return await scrape_listings()
