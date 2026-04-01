import asyncio
import logging
import hashlib
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List

import httpx

from scraper.rate_limiter import async_retry, get_rate_limiter, get_request_stats, random_jitter
from scraper.stealth_headers import get_stealth_header_generator
from scraper.browser_use import AREA_URLS as REALTOR_MAP_URLS
from scraper.browser_util import create_browser
from scraper.listing_utils import pick_display_address, looks_like_real_address
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from scraper.crawler import CrawlPage

logger = logging.getLogger(__name__)

def _scrapling_available() -> bool:
    """Return True if Scrapling v0.3 StealthyFetcher is available."""
    try:
        from scrapling.fetchers import StealthyFetcher  # noqa: F401
        return True
    except Exception:
        return False

REALTOR_DOMAIN = "realtor.ca"
RATE_LIMITER = get_rate_limiter()
REQ_STATS = get_request_stats()
HEADER_GEN = get_stealth_header_generator()


def _get_httpx_proxies():
    """
    Build an httpx proxies mapping from environment variables.

    Prefers SCRAPER_HTTP_PROXY, then HTTP_PROXY / HTTPS_PROXY.
    """
    proxy = (
        os.getenv("SCRAPER_HTTP_PROXY")
        or os.getenv("HTTP_PROXY")
        or os.getenv("HTTPS_PROXY")
    )
    if not proxy:
        return None
    return {
        "http://": proxy,
        "https://": proxy,
    }


def _get_proxy_for_curl_cffi() -> str | None:
    """
    curl_cffi expects a single proxy URL string.
    Prefer SCRAPER_HTTP_PROXY, then HTTPS_PROXY/HTTP_PROXY.
    """
    return (
        os.getenv("SCRAPER_HTTP_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )


def _curl_cffi_available() -> bool:
    try:
        import curl_cffi.requests  # noqa: F401
        return True
    except Exception:
        return False


def _realtor_post_via_curl_cffi(headers: dict, data: dict) -> tuple[int, dict | None]:
    """
    Attempt PropertySearch_Post using curl_cffi (TLS/browser impersonation).
    Returns (status_code, json_or_none).
    """
    try:
        from curl_cffi import requests as creq

        proxy = _get_proxy_for_curl_cffi()
        proxies = {"http": proxy, "https": proxy} if proxy else None

        # First, harvest cookies with a GET to the map page (Cloudflare checks often require this).
        s = creq.Session(impersonate="chrome120")
        s.get(
            "https://www.realtor.ca/map",
            headers={
                "User-Agent": headers.get("User-Agent") or headers.get("user-agent") or "",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.realtor.ca/",
            },
            proxies=proxies,
            timeout=20,
        )

        resp = s.post(
            "https://api2.realtor.ca/Listing.svc/PropertySearch_Post",
            headers=headers,
            data=data,
            proxies=proxies,
            timeout=30,
        )
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, None
    except Exception as e:
        logger.debug(f"curl_cffi realtor API failed: {e}")
        return 0, None

def _parse_sqft(raw: str) -> str:
    """Parse SizeInterior string like '1,200 sq ft' or '111.5 m2' into a sqft integer string."""
    if not raw:
        return ""
    # Already a plain number
    m = re.search(r"([\d,]+(?:\.\d+)?)", str(raw).replace(" ", ""))
    if not m:
        return ""
    try:
        value = float(m.group(1).replace(",", ""))
        # If the unit mentions m2/sqm, convert to sqft
        if re.search(r"m.?2|sqm", str(raw), re.IGNORECASE):
            value = value * 10.7639
        return str(int(value)) if value > 0 else ""
    except Exception:
        return ""


GTA_REGIONS = {
    "Toronto Downtown": {
        "LatitudeMin": "43.63", "LatitudeMax": "43.70",
        "LongitudeMin": "-79.42", "LongitudeMax": "-79.35"
    },
    "Toronto East (Scarborough)": {
        "LatitudeMin": "43.70", "LatitudeMax": "43.82",
        "LongitudeMin": "-79.28", "LongitudeMax": "-79.16"
    },
    "Toronto West (Etobicoke)": {
        "LatitudeMin": "43.60", "LatitudeMax": "43.73",
        "LongitudeMin": "-79.56", "LongitudeMax": "-79.42"
    },
    "Toronto North (North York)": {
        "LatitudeMin": "43.73", "LatitudeMax": "43.82",
        "LongitudeMin": "-79.48", "LongitudeMax": "-79.35"
    },
    "Mississauga": {
        "LatitudeMin": "43.54", "LatitudeMax": "43.65",
        "LongitudeMin": "-79.72", "LongitudeMax": "-79.55"
    },
    "Brampton": {
        "LatitudeMin": "43.65", "LatitudeMax": "43.78",
        "LongitudeMin": "-79.82", "LongitudeMax": "-79.65"
    },
    "Vaughan": {
        "LatitudeMin": "43.78", "LatitudeMax": "43.88",
        "LongitudeMin": "-79.62", "LongitudeMax": "-79.45"
    },
    "Markham": {
        "LatitudeMin": "43.82", "LatitudeMax": "43.92",
        "LongitudeMin": "-79.35", "LongitudeMax": "-79.20"
    },
    "Richmond Hill": {
        "LatitudeMin": "43.85", "LatitudeMax": "43.93",
        "LongitudeMin": "-79.48", "LongitudeMax": "-79.35"
    },
    "Oakville": {
        "LatitudeMin": "43.42", "LatitudeMax": "43.55",
        "LongitudeMin": "-79.75", "LongitudeMax": "-79.60"
    },
    "Burlington": {
        "LatitudeMin": "43.32", "LatitudeMax": "43.43",
        "LongitudeMin": "-79.85", "LongitudeMax": "-79.72"
    },
    "Ajax & Pickering": {
        "LatitudeMin": "43.82", "LatitudeMax": "43.93",
        "LongitudeMin": "-79.10", "LongitudeMax": "-78.95"
    }
}

async def _get_session_headers(client) -> dict:
    """Visit homepage first to get session cookies and build stealth headers."""
    base_headers = HEADER_GEN.generate(profile="chrome")
    try:
        await client.get(
            "https://www.realtor.ca",
            headers={"user-agent": base_headers.get("User-Agent", "") or base_headers.get("user-agent", "")},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Failed to harvest session cookies: {e}")

    # Adapt the generated navigation headers for the XHR-style API calls.
    headers = dict(base_headers)
    headers.update(
        {
            "content-type": "application/x-www-form-urlencoded",
            "referer": "https://www.realtor.ca/map",
            "origin": "https://www.realtor.ca",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "x-requested-with": "XMLHttpRequest",
        }
    )
    # Normalize header casing for httpx.
    if "user-agent" in headers and "User-Agent" not in headers:
        headers["User-Agent"] = headers["user-agent"]
    return headers

async def scrape_listings(regions=None, max_price=5000000, min_price=400000) -> list:
    """Scrapes multiple GTA regions. Shares a single client with session cookies."""
    if regions is None:
        regions = list(GTA_REGIONS.keys())
    
    logger.info(f"Starting multi-region scan: {regions}")
    
    all_listings: List[Dict[str, Any]] = []
    seen_ids = set()

    proxies = _get_httpx_proxies()
    client_kwargs: Dict[str, Any] = {
        "follow_redirects": True,
        "cookies": {},  # shared cookie jar across requests
        "timeout": 20,
    }
    if proxies:
        client_kwargs["proxies"] = proxies

    async with httpx.AsyncClient(**client_kwargs) as client:
        headers = await _get_session_headers(client)

        # We process regions sequentially with delays to be safe
        for name in regions:
            if name not in GTA_REGIONS:
                continue

            base_delay = random.uniform(2, 5)
            jitter = random_jitter()
            delay = base_delay + jitter
            logger.info(f"Waiting {delay:.2f}s before scraping {name}...")
            await asyncio.sleep(delay)

            try:
                result = await _scrape_region(client, headers, name, GTA_REGIONS[name], min_price, max_price)
                for listing in result:
                    if listing["id"] not in seen_ids:
                        seen_ids.add(listing["id"])
                        all_listings.append(listing)
            except Exception as e:
                logger.error(f"Region {name} scrape failed: {e}")

    # Log per-domain stats for visibility
    summary = await REQ_STATS.summary(REALTOR_DOMAIN)
    logger.info(f"GTA scan complete. Found {len(all_listings)} unique listings. {summary}")
    return all_listings


@async_retry(domain=REALTOR_DOMAIN)
async def _post_search(client: httpx.AsyncClient, headers: dict, data: dict) -> httpx.Response:
    return await client.post(
        "https://api2.realtor.ca/Listing.svc/PropertySearch_Post",
        headers=headers,
        data=data,
    )

async def _scrape_region(client, headers: dict, name: str, coords: dict, min_price: int, max_price: int) -> list:
    """Scrapes a single bounding box region using the shared client."""
    listings = []
    try:
        await RATE_LIMITER.acquire(REALTOR_DOMAIN)
        resp = await _post_search(
            client,
            headers,
            {
                "CultureId": "1",
                "ApplicationId": "1",
                "RecordsPerPage": "50",
                "MaximumResults": "50",
                "LatitudeMin": coords["LatitudeMin"],
                "LatitudeMax": coords["LatitudeMax"],
                "LongitudeMin": coords["LongitudeMin"],
                "LongitudeMax": coords["LongitudeMax"],
                "PriceMin": str(min_price),
                "PriceMax": str(max_price),
                "TransactionTypeId": "2",
                "PropertySearchTypeId": "1",
                "PropertyTypeGroupID": "1",
                "Version": "7.0",
                "CurrentPage": "1",
            },
        )

        if resp.status_code != 200:
            logger.error(f"Region {name} failed with status {resp.status_code}")
            if resp.status_code in (403, 429):
                await REQ_STATS.record_block(REALTOR_DOMAIN, resp.status_code)

            # Hybrid fallback: try the same API call with curl_cffi impersonation.
            if resp.status_code == 403 and _curl_cffi_available():
                status, data = await asyncio.to_thread(
                    _realtor_post_via_curl_cffi,
                    headers,
                    {
                        "CultureId": "1",
                        "ApplicationId": "1",
                        "RecordsPerPage": "50",
                        "MaximumResults": "50",
                        "LatitudeMin": coords["LatitudeMin"],
                        "LatitudeMax": coords["LatitudeMax"],
                        "LongitudeMin": coords["LongitudeMin"],
                        "LongitudeMax": coords["LongitudeMax"],
                        "PriceMin": str(min_price),
                        "PriceMax": str(max_price),
                        "TransactionTypeId": "2",
                        "PropertySearchTypeId": "1",
                        "PropertyTypeGroupID": "1",
                        "Version": "7.0",
                        "CurrentPage": "1",
                    },
                )
                if status == 200 and isinstance(data, dict):
                    results = data.get("Results", []) or []
                    for item in results:
                        mls = item.get("MlsNumber", "")
                        price_raw = item.get("Property", {}).get("Price", "0")
                        try:
                            price = int(
                                str(price_raw)
                                .replace("$", "")
                                .replace(",", "")
                                .replace(" ", "")
                                .strip()
                            )
                        except Exception:
                            price = 0
                        addr_obj = item.get("Property", {}).get("Address", {})
                        address_text = addr_obj.get("AddressText", "Unknown Address")
                        if price >= 100000:
                            listings.append(
                                {
                                    "id": f"realtor_ca_{mls}",
                                    "source": "realtor_ca",
                                    "region": name,
                                    "url": f"https://www.realtor.ca{item.get('RelativeDetailsURL', '')}",
                                    "address": pick_display_address(address_text.replace("Just listed", "").strip() or None),
                                    "city": name.split(" (")[0] if " (" in name else name,
                                    "price": price,
                                    "bedrooms": item.get("Building", {}).get("Bedrooms", ""),
                                    "bathrooms": item.get("Building", {}).get("BathroomTotal", ""),
                                    "sqft": _parse_sqft(item.get("Building", {}).get("SizeInterior", "")),
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )
                    if listings:
                        await REQ_STATS.record_success(REALTOR_DOMAIN)
                        return listings

            return []

        await REQ_STATS.record_success(REALTOR_DOMAIN)

        data = resp.json()
        results = data.get("Results", [])
        for item in results:
            mls = item.get("MlsNumber", "")
            price_raw = item.get("Property", {}).get("Price", "0")
            try:
                price = int(price_raw.replace("$", "").replace(",", "").replace(" ", "").strip())
            except:
                price = 0

            addr_obj = item.get("Property", {}).get("Address", {})
            address_text = addr_obj.get("AddressText", "Unknown Address")

            if price >= 100000:
                listings.append({
                    "id": f"realtor_ca_{mls}",
                    "source": "realtor_ca",
                    "region": name,
                    "url": f"https://www.realtor.ca{item.get('RelativeDetailsURL', '')}",
                    "address": pick_display_address(address_text.replace("Just listed", "").strip() or None),
                    "city": name.split(' (')[0] if ' (' in name else name,
                    "price": price,
                    "bedrooms": item.get("Building", {}).get("Bedrooms", ""),
                    "bathrooms": item.get("Building", {}).get("BathroomTotal", ""),
                    "sqft": _parse_sqft(item.get("Building", {}).get("SizeInterior", "")),
                    "scraped_at": datetime.utcnow().isoformat(),
                })
    except Exception as e:
        logger.error(f"Region {name} scraping failed: {e}")

        # If async_retry raised on repeated 403, try curl_cffi impersonation once.
        if "returned 403" in str(e) and _curl_cffi_available():
            try:
                status, data = await asyncio.to_thread(
                    _realtor_post_via_curl_cffi,
                    headers,
                    {
                        "CultureId": "1",
                        "ApplicationId": "1",
                        "RecordsPerPage": "50",
                        "MaximumResults": "50",
                        "LatitudeMin": coords["LatitudeMin"],
                        "LatitudeMax": coords["LatitudeMax"],
                        "LongitudeMin": coords["LongitudeMin"],
                        "LongitudeMax": coords["LongitudeMax"],
                        "PriceMin": str(min_price),
                        "PriceMax": str(max_price),
                        "TransactionTypeId": "2",
                        "PropertySearchTypeId": "1",
                        "PropertyTypeGroupID": "1",
                        "Version": "7.0",
                        "CurrentPage": "1",
                    },
                )
                if status == 200 and isinstance(data, dict):
                    results = data.get("Results", []) or []
                    for item in results:
                        mls = item.get("MlsNumber", "")
                        price_raw = item.get("Property", {}).get("Price", "0")
                        try:
                            price = int(
                                str(price_raw)
                                .replace("$", "")
                                .replace(",", "")
                                .replace(" ", "")
                                .strip()
                            )
                        except Exception:
                            price = 0

                        addr_obj = item.get("Property", {}).get("Address", {})
                        address_text = addr_obj.get("AddressText", "Unknown Address")
                        if price >= 100000:
                            listings.append(
                                {
                                    "id": f"realtor_ca_{mls}",
                                    "source": "realtor_ca",
                                    "region": name,
                                    "url": f"https://www.realtor.ca{item.get('RelativeDetailsURL', '')}",
                                    "address": pick_display_address(address_text.replace("Just listed", "").strip() or None),
                                    "city": name.split(" (")[0] if " (" in name else name,
                                    "price": price,
                                    "bedrooms": item.get("Building", {}).get("Bedrooms", ""),
                                    "bathrooms": item.get("Building", {}).get("BathroomTotal", ""),
                                    "sqft": _parse_sqft(item.get("Building", {}).get("SizeInterior", "")),
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )
                    if listings:
                        await REQ_STATS.record_success(REALTOR_DOMAIN)
            except Exception as e2:
                logger.debug(f"curl_cffi realtor fallback in except failed: {e2}")
        
    return listings

async def scrape_listing_details(url: str) -> dict:
    """Extract individual listing details using httpx."""
    base_headers = HEADER_GEN.generate(profile="chrome")
    headers = dict(base_headers)
    headers.update(
        {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.realtor.ca",
            "Referer": url,
        }
    )

    @async_retry(domain=REALTOR_DOMAIN)
    async def _post_details(client: httpx.AsyncClient, data: dict) -> httpx.Response:
        return await client.post(
            "https://api2.realtor.ca/Listing.svc/PropertySearch_Post",
            data=data,
            timeout=15,
        )

    try:
        match = re.search(r"/real-estate/(\d+)/", url)
        listing_id = match.group(1) if match else ""

        proxies = _get_httpx_proxies()
        client_kwargs: Dict[str, Any] = {
            "headers": headers,
            "follow_redirects": True,
        }
        if proxies:
            client_kwargs["proxies"] = proxies

        async with httpx.AsyncClient(**client_kwargs) as client:
            await client.get("https://www.realtor.ca/")
            await RATE_LIMITER.acquire(REALTOR_DOMAIN)
            resp = await _post_details(
                client,
                {
                    "CultureId": "1",
                    "ApplicationId": "1",
                    "RecordsPerPage": "1",
                    "MaximumResults": "1",
                    "ListingId": listing_id,
                    "Version": "7.0",
                },
            )
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("Results", [])
                if results:
                    item = results[0]
                    addr = item.get("Property", {}).get("Address", {})
                    price_raw = item.get("Property", {}).get("Price", "")
                    photo_list = item.get("Property", {}).get("Photo", [{}])
                    return {
                        "address": addr.get("AddressText", url),
                        "price": price_raw,
                        "photo": photo_list[0].get("HighResPath", "") if photo_list else "",
                        "url": url
                    }
    except Exception as e:
        logger.error(f"Failed to scrape listing details: {e}")
        
    return {"address": url, "price": "", "photo": "", "url": url}


def _scrape_realtor_browser_sync(area: str) -> List[Dict[str, Any]]:
    """
    Browser-based fallback scraper using DrissionPage.

    When the httpx path is heavily blocked, this uses a real Edge
    instance with hardened fingerprints to scrape listing cards
    directly from the Realtor.ca map UI.
    """
    # Reuse the AREA_URLS mapping from browser_use so we stay consistent.
    url = REALTOR_MAP_URLS.get(area, REALTOR_MAP_URLS.get("gta"))
    if not url:
        return []

    from collections import defaultdict

    listings: List[Dict[str, Any]] = []
    page = None

    try:
        page = create_browser(headless=False)
        logger.info(f"Realtor.ca (browser): navigating to {url}")
        page.get(url, retry=1, interval=1, timeout=20)
        time.sleep(10)  # allow JS map + cards to render

        # Scroll a bit to load more cards
        for _ in range(3):
            try:
                page.scroll.down(500)
                time.sleep(1)
            except Exception:
                break

        # Group all <a href="/real-estate/..."> by their href, then
        # merge price + address texts gathered from separate links.
        link_groups = defaultdict(list)
        all_links = page.eles("tag:a")
        for link in all_links:
            href = link.attr("href") or ""
            if "/real-estate/" not in href:
                continue
            text = (link.text or "").strip()
            if text:
                link_groups[href].append(text)

        logger.info(f"Realtor.ca (browser): found {len(link_groups)} unique listing links")

        for href, texts in link_groups.items():
            try:
                price = 0
                address = ""
                beds = ""
                baths = ""

                for text in texts:
                    # Price link contains $
                    if "$" in text and not price:
                        m = re.search(r"[\$C]*\$([\d,]+)", text)
                        if m:
                            price = int(m.group(1).replace(",", ""))
                    elif looks_like_real_address(text):
                        address = text

                if price <= 0:
                    continue
                display_addr = pick_display_address(address) if address else "Unknown"

                full_url = href if href.startswith("http") else f"https://www.realtor.ca{href}"
                mls = hashlib.md5(full_url.encode()).hexdigest()[:12]

                city = "Toronto"
                if "mississauga" in (display_addr + href).lower():
                    city = "Mississauga"

                listings.append(
                    {
                        "id": f"realtor_ca_{mls}",
                        "source": "realtor_ca",
                        "url": full_url,
                        "address": display_addr,
                        "city": city,
                        "price": price,
                        "bedrooms": beds,
                        "bathrooms": baths,
                        "sqft": "",
                        "lat": None,
                        "lng": None,
                        "scraped_at": datetime.utcnow().isoformat(),
                    }
                )
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Realtor.ca browser scraping failed: {e}")
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass

    logger.info(f"Realtor.ca (browser): scraped {len(listings)} listings")
    return listings


async def scrape_realtor_browser(area: str = "gta") -> List[Dict[str, Any]]:
    """Async wrapper around the sync DrissionPage scraper."""
    return await asyncio.to_thread(_scrape_realtor_browser_sync, area)


async def _scrape_realtor_scrapling(area: str) -> List[Dict[str, Any]]:
    """
    Scrapling v0.3 StealthyFetcher fallback: fetch Realtor.ca map page and parse listing links.
    Same link-group + price/address extraction logic as the DrissionPage fallback.
    """
    from collections import defaultdict

    from scrapling.fetchers import StealthyFetcher

    url = REALTOR_MAP_URLS.get(area, REALTOR_MAP_URLS.get("gta"))
    if not url:
        return []

    listings: List[Dict[str, Any]] = []
    try:
        page = await StealthyFetcher.async_fetch(
            url,
            headless=True,
            timeout=45000,
            wait=8000,
        )
        if page.status != 200:
            return []

        link_groups = defaultdict(list)
        for link in page.css('a[href*="/real-estate/"]'):
            href = (link.attrib.get("href") or "").strip()
            if not href or "/real-estate/" not in href:
                continue
            text = (link.text or "").strip()
            if text:
                link_groups[href].append(text)

        for href, texts in link_groups.items():
            try:
                price = 0
                address = ""
                for text in texts:
                    if "$" in text and not price:
                        m = re.search(r"[\$C]*\$([\d,]+)", text)
                        if m:
                            price = int(m.group(1).replace(",", ""))
                    elif looks_like_real_address(text):
                        address = text
                if price <= 0:
                    continue
                display_addr = pick_display_address(address) if address else "Unknown"
                full_url = href if href.startswith("http") else f"https://www.realtor.ca{href}"
                mls = hashlib.md5(full_url.encode()).hexdigest()[:12]
                city = "Mississauga" if "mississauga" in (display_addr + href).lower() else "Toronto"
                listings.append({
                    "id": f"realtor_ca_{mls}",
                    "source": "realtor_ca",
                    "url": full_url,
                    "address": display_addr,
                    "city": city,
                    "price": price,
                    "bedrooms": "",
                    "bathrooms": "",
                    "sqft": "",
                    "lat": None,
                    "lng": None,
                    "scraped_at": datetime.utcnow().isoformat(),
                })
            except Exception:
                continue
        logger.info(f"Realtor.ca (Scrapling): scraped {len(listings)} listings")
    except Exception as e:
        logger.warning(f"Realtor.ca Scrapling fallback failed: {e}")
    return listings


async def scrape_realtor_ca(area: str = "gta") -> list:
    """Wrapper: httpx first, then Scrapling v0.3 fallback, then DrissionPage fallback."""
    if area == "toronto":
        regions = [
            "Toronto Downtown",
            "Toronto East (Scarborough)",
            "Toronto West (Etobicoke)",
            "Toronto North (North York)",
        ]
    elif area == "mississauga":
        regions = ["Mississauga"]
    else:
        regions = None  # all GTA

    listings = await scrape_listings(regions=regions)
    if not listings and _scrapling_available():
        logger.warning(
            "Realtor.ca httpx returned 0 listings; trying Scrapling v0.3 fallback."
        )
        try:
            listings = await _scrape_realtor_scrapling(area)
        except Exception as e:
            logger.error(f"Realtor.ca Scrapling fallback failed: {e}")
    if not listings:
        logger.warning(
            "Realtor.ca Scrapling returned 0; falling back to DrissionPage browser."
        )
        try:
            browser_listings = await scrape_realtor_browser(area)
            if browser_listings:
                listings = browser_listings
        except Exception as e:
            logger.error(f"Realtor.ca browser fallback failed: {e}")

    if not listings:
        try:
            crawler_listings = await _scrape_realtor_via_crawler(area)
            if crawler_listings:
                listings = crawler_listings
                logger.info(f"Realtor.ca crawler fallback: {len(listings)} listings")
        except Exception as e:
            logger.warning(f"Realtor.ca crawler fallback failed: {e}")

    return listings


async def _scrape_realtor_via_crawler(area: str) -> List[Dict[str, Any]]:
    """Fallback: crawl Realtor.ca map via Cloudflare/Firecrawl and parse listing pages."""
    from .crawler import CrawlRequest, CrawlBackend, crawl_site

    url = REALTOR_MAP_URLS.get(area.lower(), REALTOR_MAP_URLS.get("gta"))
    request = CrawlRequest(
        url=url,
        backend=CrawlBackend.CLOUDFLARE,
        max_depth=1,
        max_pages=20,
        include_patterns=["/real-estate/"],
        format="html",
        timeout_seconds=120,
    )
    result = await crawl_site(request)
    if not result.stats.success or not result.pages:
        return []
    listings = []
    for page in result.pages:
        parsed = _parse_realtor_crawled_page(page)
        if parsed:
            listings.append(parsed)
    return listings


def _parse_realtor_crawled_page(page: "CrawlPage") -> Optional[Dict[str, Any]]:
    """Extract listing dict from a crawled Realtor.ca page (HTML or markdown)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    html = page.html
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    # Realtor.ca listing page: look for address, price, beds/baths
    address_el = soup.select_one(".addressLine1, [data-testid='listing-address'], .listingAddress")
    price_el = soup.select_one(".listingPrice, [data-testid='listing-price'], .price")
    if not address_el or not price_el:
        return None
    address = address_el.get_text(strip=True)
    price_text = price_el.get_text(strip=True)
    price = int("".join(c for c in price_text if c.isdigit())) if price_text else 0
    if price <= 0:
        return None
    beds_el = soup.select_one(".bedrooms, .bed, [data-testid='bedrooms']")
    baths_el = soup.select_one(".bathrooms, .bath, [data-testid='bathrooms']")
    beds = int(beds_el.get_text(strip=True)) if beds_el and beds_el.get_text(strip=True).isdigit() else 0
    baths = int(baths_el.get_text(strip=True)) if baths_el and baths_el.get_text(strip=True).isdigit() else 0
    city = "Mississauga" if "mississauga" in (address + page.url).lower() else "Toronto"
    mls = hashlib.md5(page.url.encode()).hexdigest()[:12]
    return {
        "id": f"realtor_ca_{mls}",
        "source": "realtor_ca",
        "url": page.url,
        "address": address[:300],
        "city": city,
        "price": price,
        "bedrooms": str(beds) if beds else "",
        "bathrooms": str(baths) if baths else "",
        "sqft": "",
        "lat": None,
        "lng": None,
        "scraped_at": datetime.utcnow().isoformat(),
    }
