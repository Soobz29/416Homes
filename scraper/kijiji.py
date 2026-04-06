import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

logger = logging.getLogger(__name__)

KIJIJI_URLS = {
    "toronto": "https://www.kijiji.ca/b-real-estate/gta-greater-toronto-area/c34l1700272",
    "mississauga": "https://www.kijiji.ca/b-real-estate/mississauga-peel-region/c34l1700276",
    "gta": "https://www.kijiji.ca/b-real-estate/gta-greater-toronto-area/c34l1700272",
}

async def scrape_kijiji(area: str = "toronto") -> List[Dict[str, Any]]:
    """Scrape Kijiji. For area=gta, scrape both GTA and Mississauga so DB has city=Mississauga listings."""
    try:
        if area.lower() == "gta":
            gta_list = await scrape_with_scrapling("gta")
            miss_list = await scrape_with_scrapling("mississauga")
            return gta_list + miss_list
        return await scrape_with_scrapling(area)
    except Exception as e:
        logger.error(f"Kijiji scraping failed: {e}")
        return []

async def scrape_with_scrapling(area: str) -> List[Dict[str, Any]]:
    """Scrape Kijiji using Scrapling v0.3 StealthyFetcher."""
    url = KIJIJI_URLS.get(area.lower(), KIJIJI_URLS["gta"])
    listings = []
    try:
        page = await StealthyFetcher.async_fetch(
            url,
            headless=True,
            timeout=30000,
            wait=3000,
        )
        if page.status != 200:
            return []
        # Listing cards or links to listing pages
        for card in page.css('[data-testid="listing-card"], .search-item, .info-container'):
            try:
                link = card.css_first("a[href*='/v-real-estate/'], a[href*='/v-housing/']") or card.css_first("a")
                if not link:
                    continue
                href = link.attrib.get("href", "")
                if not href or "/v-" not in href:
                    continue
                full_url = urljoin("https://www.kijiji.ca", href) if href.startswith("/") else href
                title = (link.text or "").strip() or (card.get_all_text() or "")[:200]
                price_el = card.css_first(".price, [data-testid='listing-price']") or card
                price_text = (price_el.text or price_el.get_all_text() or "") if price_el else ""
                price_match = re.search(r'\$?([\d,]+)', price_text.replace(",", ""))
                price = int(price_match.group(1)) if price_match else 0
                if price <= 0:
                    continue
                lid = hashlib.md5(full_url.encode()).hexdigest()[:12]
                listings.append({
                    "id": f"kijiji_{lid}",
                    "address": title or "Unknown",
                    "price": price,
                    "bedrooms": "",
                    "bathrooms": "",
                    "area": "",
                    "city": "Toronto" if area.lower() in ("gta", "toronto") else area.title(),
                    "lat": None,
                    "lng": None,
                    "source": "kijiji",
                    "url": full_url,
                    "photo": "",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "strategy": "scrapling",
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Kijiji Scrapling fetch failed: {e}")
    return listings

