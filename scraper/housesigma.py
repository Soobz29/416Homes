"""
HouseSigma scraper - targets https://housesigma.com/
Uses DrissionPage + Edge to bypass bot protection and scrape sold comps.
"""
import asyncio
import logging
import hashlib
import re
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

AREA_URLS = {
    # municipality IDs: Toronto=10343, Mississauga=10420
    # list_status=[3] = sold
    "toronto": "https://housesigma.com/web/en/map?municipality=10343&community=all&house_type=all&list_status=%5B3%5D",
    "mississauga": "https://housesigma.com/web/en/map?municipality=10420&community=all&house_type=all&list_status=%5B3%5D",
    "gta": "https://housesigma.com/web/en/map?municipality=10343&community=all&house_type=all&list_status=%5B3%5D",
}

# Neighbourhood lookup
TORONTO_NEIGHBORHOODS = [
    "King West", "Queen West", "Liberty Village", "CityPlace", "Entertainment District",
    "Yorkville", "Rosedale", "The Annex", "Kensington Market", "Chinatown",
    "Distillery District", "Leslieville", "Riverside", "Beaches",
    "Scarborough", "North York", "Etobicoke", "East York", "York",
    "Mississauga City Centre", "Port Credit", "Streetsville", "Meadowvale",
]

def _scrape_housesigma_sync(area: str, days_back: int = 30) -> List[Dict[str, Any]]:
    """Synchronous scraping using DrissionPage + Edge."""
    from .browser_util import create_browser

    url = AREA_URLS.get(area, AREA_URLS["gta"])
    listings = []
    page = None

    try:
        page = create_browser(headless=True)
        logger.info(f"HouseSigma: navigating to {url}")
        page.get(url, retry=1, interval=1, timeout=25)
        time.sleep(12)  # HouseSigma has heavy JS + map loading

        # Scroll to load sold cards
        for _ in range(3):
            page.scroll.down(500)
            time.sleep(1)

        # HouseSigma shows listing cards; grab all anchor tags
        all_links = page.eles('tag:a')
        for link in all_links:
            try:
                href = link.attr('href') or ''
                text = link.text or ''

                if '$' not in text:
                    continue
                # HouseSigma listing links contain /listing/ or /house/
                if '/listing/' not in href and '/house/' not in href:
                    continue

                lines = [l.strip() for l in text.split('\n') if l.strip()]
                price = 0
                address = ''
                beds = ''
                baths = ''
                sold_date = None

                sqft = ""
                for line in lines:
                    if '$' in line:
                        price_str = re.sub(r'[^\d]', '', line)
                        try:
                            price = int(price_str)
                        except ValueError:
                            pass
                    elif re.search(r'\d+\s*(bed|bd)', line, re.IGNORECASE):
                        m = re.search(r'(\d+)', line)
                        if m: beds = m.group(1)
                    elif re.search(r'\d+\s*(bath|ba)', line, re.IGNORECASE):
                        m = re.search(r'(\d+)', line)
                        if m: baths = m.group(1)
                    elif re.search(r'[\d,]+\s*(sq\.?\s*ft|sqft)', line, re.IGNORECASE):
                        m = re.search(r'([\d,]+)', line)
                        if m:
                            try:
                                sqft = str(int(m.group(1).replace(",", "")))
                            except ValueError:
                                pass
                    elif re.search(r'(st|ave|rd|dr|blvd|cres|way|ct|pl|ln|trail|circ)', line, re.IGNORECASE):
                        address = line
                    elif re.search(r'(sold|closed)', line, re.IGNORECASE):
                        # try to get a date
                        date_m = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                        if date_m:
                            sold_date = date_m.group(1)

                if not address and len(lines) > 1:
                    address = lines[1] if lines[0].startswith('$') else lines[0]

                if price > 0:
                    full_url = href if href.startswith('http') else f"https://housesigma.com{href}"
                    lid = hashlib.md5(full_url.encode()).hexdigest()[:12]
                    city = "Mississauga" if "mississauga" in address.lower() else "Toronto"

                    listings.append({
                        "id": f"housesigma_{lid}",
                        "source": "housesigma",
                        "url": full_url,
                        "address": address,
                        "city": city,
                        "sold_price": price,
                        "list_price": 0,
                        "bedrooms": beds,
                        "bathrooms": baths,
                        "sqft": sqft,
                        "property_type": "",
                        "sold_date": sold_date or "",
                        "days_on_market": 0,
                        "neighbourhood": "",
                        "lat": None,
                        "lng": None,
                        "scraped_at": datetime.utcnow().isoformat(),
                    })
            except Exception:
                continue

    except Exception as e:
        logger.error(f"HouseSigma scraping failed: {e}")
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass

    logger.info(f"HouseSigma: scraped {len(listings)} listings")
    return listings


async def scrape_housesigma(area: str = "gta", days_back: int = 30) -> List[Dict[str, Any]]:
    """Async wrapper around the sync DrissionPage scraper."""
    return await asyncio.to_thread(_scrape_housesigma_sync, area, days_back)


async def get_neighborhood_comps(neighbourhood: str, days_back: int = 30) -> List[Dict[str, Any]]:
    """Get comparable sold properties for a specific neighborhood."""
    all_comps = await scrape_housesigma("gta", days_back)
    neighbourhood_lower = neighbourhood.lower()
    return [c for c in all_comps if neighbourhood_lower in c.get("neighbourhood", "").lower()
            or neighbourhood_lower in c.get("address", "").lower()]
