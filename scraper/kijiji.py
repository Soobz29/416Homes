import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
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
    """Scrape Kijiji real estate listings with Scrapling v0.3."""
    try:
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
                    "city": area.title(),
                    "lat": None,
                    "lng": None,
                    "source": "kijiji",
                    "url": full_url,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "strategy": "scrapling",
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Kijiji Scrapling fetch failed: {e}")
    return listings

async def extract_kijiji_listing(element, source: str) -> Dict[str, Any]:
    """Extract listing data from Kijiji element using updated selectors"""
    
    try:
        # Title/Address - Kijiji uses title element
        title_elem = await element.querySelector('h3 a, .title a, [data-testid="listing-title"]')
        title = await title_elem.text_content() if title_elem else "N/A"
        
        # Price - updated selector
        price_elem = await element.querySelector('.price, [data-testid="listing-price"]')
        price_text = await price_elem.text_content() if price_elem else "$0"
        
        # Clean price text and convert to int
        price_match = re.search(r'\$?([\d,]+)', price_text.replace(',', ''))
        price = int(price_match.group(1)) if price_match else 0
        
        # Bedrooms/Bathrooms - look for specific patterns
        beds_elem = await element.querySelector('[data-testid="listing-beds"], .bedrooms')
        beds = await beds_elem.text_content() if beds_elem else "0"
        
        baths_elem = await element.querySelector('[data-testid="listing-baths"], .bathrooms')
        baths = await baths_elem.text_content() if baths_elem else "0"
        
        # URL
        link_elem = await element.querySelector('h3 a, .title a')
        href = await link_elem.get_attribute('href') if link_elem else "#"
        url = urljoin("https://www.kijiji.ca", href) if href != "#" else "#"
        
        # Area/Location
        location_elem = await element.querySelector('.location, [data-testid="listing-location"]')
        area = await location_elem.text_content() if location_elem else "N/A"
        
        return {
            "id": f"{source}_{hashlib.md5(title.encode()).hexdigest()[:8]}",
            "address": title.strip(),
            "price": price,
            "bedrooms": beds.strip(),
            "bathrooms": baths.strip(),
            "area": area.strip(),
            "lat": None,
            "lng": None,
            "source": source,
            "url": url,
            "scraped_at": datetime.utcnow().isoformat(),
            "strategy": "scrapling"
        }
        
    except Exception as e:
        logger.warning(f"Kijiji extraction failed: {e}")
        return None

async def extract_kijiji_listing_playwright(element, source: str) -> Dict[str, Any]:
    """Extract listing data from Kijiji element using Playwright"""
    
    try:
        # Title/Address
        title = await element.eval_on_selector('h3 a, .title a, [data-testid="listing-title"]', 'el => el.textContent') or "N/A"
        
        # Price
        price_text = await element.eval_on_selector('.price, [data-testid="listing-price"]', 'el => el.textContent') or "$0"
        price_match = re.search(r'\$?([\d,]+)', price_text.replace(',', ''))
        price = int(price_match.group(1)) if price_match else 0
        
        # Bedrooms/Bathrooms
        beds = await element.eval_on_selector('[data-testid="listing-beds"], .bedrooms', 'el => el.textContent') or "0"
        baths = await element.eval_on_selector('[data-testid="listing-baths"], .bathrooms', 'el => el.textContent') or "0"
        
        # URL
        href = await element.eval_on_selector('h3 a, .title a', 'el => el.href') or "#"
        url = urljoin("https://www.kijiji.ca", href) if href != "#" else "#"
        
        # Area/Location
        area = await element.eval_on_selector('.location, [data-testid="listing-location"]', 'el => el.textContent') or "N/A"
        
        return {
            "id": f"{source}_{hashlib.md5(title.encode()).hexdigest()[:8]}",
            "address": title.strip(),
            "price": price,
            "bedrooms": beds.strip(),
            "bathrooms": baths.strip(),
            "area": area.strip(),
            "lat": None,
            "lng": None,
            "source": source,
            "url": url,
            "scraped_at": datetime.utcnow().isoformat(),
            "strategy": "playwright"
        }
        
    except Exception as e:
        logger.warning(f"Kijiji Playwright extraction failed: {e}")
        return None
