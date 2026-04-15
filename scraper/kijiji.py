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

def _extract_photo_from_card(card) -> str:
    """Extract best-effort listing image URL from a Kijiji listing card."""
    try:
        selectors = [
            "img",
            "picture img",
            "[data-testid='listing-image'] img",
            "[data-testid='image'] img",
        ]
        for selector in selectors:
            for img in card.css(selector):
                attrs = img.attrib or {}
                for key in ("src", "data-src", "data-original", "data-url"):
                    val = (attrs.get(key) or "").strip()
                    if val.startswith("http://") or val.startswith("https://"):
                        return val
                srcset = (attrs.get("srcset") or attrs.get("data-srcset") or "").strip()
                if srcset:
                    first = srcset.split(",")[0].strip().split(" ")[0].strip()
                    if first.startswith("http://") or first.startswith("https://"):
                        return first
    except Exception:
        return ""
    return ""

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
                photo = _extract_photo_from_card(card)
                lid = hashlib.md5(full_url.encode()).hexdigest()[:12]
                # Extract sqft from card text (e.g. "1,234 sq. ft." / "1234sqft")
                all_text = card.get_all_text() or ""
                sqft = ""
                sqft_m = re.search(r'([\d,]+)\s*sq\.?\s*ft', all_text, re.IGNORECASE)
                if sqft_m:
                    try:
                        sqft = str(int(sqft_m.group(1).replace(",", "")))
                    except ValueError:
                        pass
                listings.append({
                    "id": f"kijiji_{lid}",
                    "address": title or "Unknown",
                    "price": price,
                    "bedrooms": "",
                    "bathrooms": "",
                    "area": sqft,
                    "city": "Toronto" if area.lower() in ("gta", "toronto") else area.title(),
                    "lat": None,
                    "lng": None,
                    "source": "kijiji",
                    "url": full_url,
                    "photo": photo,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "strategy": "scrapling",
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Kijiji Scrapling fetch failed: {e}")
    return listings

