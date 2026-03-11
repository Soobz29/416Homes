"""
Zillow scraper - targets https://www.zillow.com/mississauga-on/ and Toronto
Uses DrissionPage + Edge to bypass bot protection and scrape listing cards.

DOM structure (verified via browser inspection):
- Multiple <a> tags per listing, all sharing the same href containing '/homedetails/'
- One <a> has the Price text (e.g. "C$989,999")
- Another <a> has the Address text (e.g. "7438 Magistrate Ter, Mississauga, ON L5W 1L2")
- Group by href, merge price + address from the different links
"""
import asyncio
import logging
import hashlib
import re
import time
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

AREA_URLS = {
    "toronto": "https://www.zillow.com/toronto-on/",
    "mississauga": "https://www.zillow.com/mississauga-on/",
    "gta": "https://www.zillow.com/toronto-on/",
}

def _scrape_zillow_sync(area: str) -> List[Dict[str, Any]]:
    """Synchronous scraping using DrissionPage + Edge."""
    from .browser_util import create_browser

    url = AREA_URLS.get(area, AREA_URLS["gta"])
    listings = []
    page = None

    try:
        page = create_browser(headless=False)
        logger.info(f"Zillow: navigating to {url}")
        page.get(url, retry=1, interval=1, timeout=20)
        time.sleep(10)  # wait for React render

        # Scroll to load more cards
        for _ in range(3):
            page.scroll.down(500)
            time.sleep(1)

        # Group all <a href="/homedetails/..."> by their href
        link_groups = defaultdict(list)
        all_links = page.eles('tag:a')
        for link in all_links:
            href = link.attr('href') or ''
            if '/homedetails/' not in href:
                continue
            text = (link.text or '').strip()
            if text:
                link_groups[href].append(text)

        logger.info(f"Zillow: found {len(link_groups)} unique listing links")

        for href, texts in link_groups.items():
            try:
                price = 0
                address = ''
                beds = ''
                baths = ''
                sqft = ''

                for text in texts:
                    # Price link contains $
                    if '$' in text and not price:
                        price_match = re.search(r'[\$C]*\$([\d,]+)', text)
                        if price_match:
                            price = int(price_match.group(1).replace(',', ''))
                    # Address link contains comma and state/province
                    elif (',' in text and ('ON' in text or 'Ontario' in text)) or re.search(r'\d+\s+\w+\s+(st|ave|rd|dr|blvd|cres|way|ct|ter|pl|ln|trail|circ)', text, re.IGNORECASE):
                        address = text
                    # Beds/baths might be in one of the links
                    if re.search(r'(\d+)\s*(bd|bed)', text, re.IGNORECASE):
                        m = re.search(r'(\d+)\s*(bd|bed)', text, re.IGNORECASE)
                        if m: beds = m.group(1)
                    if re.search(r'(\d+)\s*(ba|bath)', text, re.IGNORECASE):
                        m = re.search(r'(\d+)\s*(ba|bath)', text, re.IGNORECASE)
                        if m: baths = m.group(1)
                    if re.search(r'([\d,]+)\s*(sqft|sq)', text, re.IGNORECASE):
                        m = re.search(r'([\d,]+)\s*(sqft|sq)', text, re.IGNORECASE)
                        if m: sqft = m.group(1).replace(',', '')

                if price > 0:
                    full_url = href if href.startswith('http') else f"https://www.zillow.com{href}"
                    lid = hashlib.md5(full_url.encode()).hexdigest()[:12]
                    city = "Mississauga" if "mississauga" in (address + href).lower() else "Toronto"

                    listings.append({
                        "id": f"zillow_{lid}",
                        "source": "zillow",
                        "url": full_url,
                        "address": address or "Unknown",
                        "city": city,
                        "price": price,
                        "bedrooms": beds,
                        "bathrooms": baths,
                        "sqft": sqft,
                        "lat": None,
                        "lng": None,
                        "scraped_at": datetime.utcnow().isoformat(),
                    })
            except Exception:
                continue

    except Exception as e:
        logger.error(f"Zillow scraping failed: {e}")
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass

    logger.info(f"Zillow: scraped {len(listings)} listings")
    return listings


async def scrape_zillow(area: str = "gta") -> List[Dict[str, Any]]:
    """Async wrapper around the sync DrissionPage scraper."""
    return await asyncio.to_thread(_scrape_zillow_sync, area)
