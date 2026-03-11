import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import hashlib
import re
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

logger = logging.getLogger(__name__)

REDFIN_URLS = {
    "toronto": "https://www.redfin.ca/city/14075/ON/Toronto",
    "mississauga": "https://www.redfin.ca/city/16964/ON/Mississauga",
    "gta": "https://www.redfin.ca/city/14075/ON/Toronto",
}

async def scrape_redfin(area: str = "toronto") -> List[Dict[str, Any]]:
    """Scrape Redfin listings with Scrapling v0.3. For area=gta, scrape both Toronto and Mississauga."""
    try:
        if area.lower() == "gta":
            toronto = await scrape_with_scrapling("toronto")
            mississauga = await scrape_with_scrapling("mississauga")
            return toronto + mississauga
        return await scrape_with_scrapling(area)
    except Exception as e:
        logger.error(f"Redfin scraping failed: {e}")
        return []

async def scrape_with_scrapling(area: str) -> List[Dict[str, Any]]:
    """Scrape Redfin using Scrapling v0.3 StealthyFetcher."""
    url = REDFIN_URLS.get(area.lower(), REDFIN_URLS["gta"])
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
        for card in page.css("[data-rf-test-id='basic-card'], .HomeCard, a[href*='/home/']"):
            try:
                link = card if card.attrib.get("href") else card.css_first("a[href*='/home/']")
                if not link:
                    continue
                href = link.attrib.get("href", "")
                if not href or "/home/" not in href:
                    continue
                full_url = urljoin("https://www.redfin.ca", href) if href.startswith("/") else href
                addr_el = card.css_first("[data-rf-test-id='address'], .link-and-anchor, .fullAddress") or card
                address = (addr_el.text or addr_el.get_all_text() or "").strip()[:300]
                price_el = card.css_first("[data-rf-test-id='price'], .homePriceV2, .price") or card
                price_text = (price_el.text or price_el.get_all_text() or "") if price_el else ""
                price_match = re.search(r'\$?([\d,]+)', price_text.replace(",", ""))
                price = int(price_match.group(1)) if price_match else 0
                if price <= 0:
                    continue
                lid = hashlib.md5(full_url.encode()).hexdigest()[:12]
                listings.append({
                    "id": f"redfin_{lid}",
                    "address": address or "Unknown",
                    "price": price,
                    "bedrooms": "",
                    "bathrooms": "",
                    "area": "",
                    "city": area.title(),
                    "lat": None,
                    "lng": None,
                    "source": "redfin",
                    "url": full_url,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "strategy": "scrapling",
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Redfin Scrapling fetch failed: {e}")
    return listings

async def extract_redfin_listing(element, source: str) -> Dict[str, Any]:
    """Extract listing data from Redfin element using updated selectors"""
    
    try:
        # Address - Redfin uses specific address selectors
        address_elem = await element.querySelector('[data-testid="address"], .homeAddress')
        address = await address_elem.text_content() if address_elem else "N/A"
        
        # Price - updated selector
        price_elem = await element.querySelector('[data-testid="price"], .homePriceV2')
        price_text = await price_elem.text_content() if price_elem else "$0"
        
        # Clean price text and convert to int
        price_match = re.search(r'\$?([\d,]+)', price_text.replace(',', ''))
        price = int(price_match.group(1)) if price_match else 0
        
        # Bedrooms/Bathrooms - Redfin specific selectors
        beds_elem = await element.querySelector('[data-testid="beds"], .beds-baths .beds')
        beds = await beds_elem.text_content() if beds_elem else "0"
        
        baths_elem = await element.querySelector('[data-testid="baths"], .beds-baths .baths')
        baths = await baths_elem.text_content() if baths_elem else "0"
        
        # Square footage
        sqft_elem = await element.querySelector('[data-testid="sqft"], .sqft')
        sqft = await sqft_elem.text_content() if sqft_elem else "0"
        
        # URL
        link_elem = await element.querySelector('a[href*="/home/"]')
        href = await link_elem.get_attribute('href') if link_elem else "#"
        url = urljoin("https://www.redfin.ca", href) if href != "#" else "#"
        
        return {
            "id": f"{source}_{hashlib.md5(address.encode()).hexdigest()[:8]}",
            "address": address.strip(),
            "price": price,
            "bedrooms": beds.strip(),
            "bathrooms": baths.strip(),
            "area": sqft.strip(),
            "lat": None,
            "lng": None,
            "source": source,
            "url": url,
            "scraped_at": datetime.utcnow().isoformat(),
            "strategy": "scrapling"
        }
        
    except Exception as e:
        logger.warning(f"Redfin extraction failed: {e}")
        return None

async def extract_redfin_listing_playwright(element, source: str) -> Dict[str, Any]:
    """Extract listing data from Redfin element using Playwright"""
    
    try:
        # Address
        address = await element.eval_on_selector('[data-testid="address"], .homeAddress', 'el => el.textContent') or "N/A"
        
        # Price
        price_text = await element.eval_on_selector('[data-testid="price"], .homePriceV2', 'el => el.textContent') or "$0"
        price_match = re.search(r'\$?([\d,]+)', price_text.replace(',', ''))
        price = int(price_match.group(1)) if price_match else 0
        
        # Bedrooms/Bathrooms
        beds = await element.eval_on_selector('[data-testid="beds"], .beds-baths .beds', 'el => el.textContent') or "0"
        baths = await element.eval_on_selector('[data-testid="baths"], .beds-baths .baths', 'el => el.textContent') or "0"
        
        # Square footage
        sqft = await element.eval_on_selector('[data-testid="sqft"], .sqft', 'el => el.textContent') or "0"
        
        # URL
        href = await element.eval_on_selector('a[href*="/home/"]', 'el => el.href') or "#"
        url = urljoin("https://www.redfin.ca", href) if href != "#" else "#"
        
        return {
            "id": f"{source}_{hashlib.md5(address.encode()).hexdigest()[:8]}",
            "address": address.strip(),
            "price": price,
            "bedrooms": beds.strip(),
            "bathrooms": baths.strip(),
            "area": sqft.strip(),
            "lat": None,
            "lng": None,
            "source": source,
            "url": url,
            "scraped_at": datetime.utcnow().isoformat(),
            "strategy": "playwright"
        }
        
    except Exception as e:
        logger.warning(f"Redfin Playwright extraction failed: {e}")
        return None
