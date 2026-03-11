import asyncio
import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List

import httpx

from scraper.rate_limiter import async_retry, get_rate_limiter, get_request_stats
from scraper.stealth_headers import get_stealth_header_generator
from scraper.browser_util import create_browser
from scraper.listing_utils import is_sold_or_inactive, pick_display_address, looks_like_real_address

logger = logging.getLogger(__name__)


def _scrapling_available() -> bool:
    """Return True if Scrapling v0.3 StealthyFetcher is available."""
    try:
        from scrapling.fetchers import StealthyFetcher  # noqa: F401
        return True
    except Exception:
        return False

CONDOS_DOMAIN = "condos.ca"
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


def _condos_api_via_curl_cffi(city: str, per_page: int = 50) -> tuple[int, dict | None]:
    """
    Condos.ca API-first attempt using curl_cffi impersonation.
    Endpoint discovered in inspect_scrapers.py.
    Returns (status_code, json_or_none).
    """
    try:
        from curl_cffi import requests as creq

        proxy = _get_proxy_for_curl_cffi()
        proxies = {"http": proxy, "https": proxy} if proxy else None

        s = creq.Session(impersonate="chrome120")
        # Warm-up to get any cookies
        s.get(
            "https://condos.ca/",
            headers={"User-Agent": HEADER_GEN.generate(profile="chrome").get("User-Agent", "")},
            proxies=proxies,
            timeout=20,
        )
        resp = s.get(
            "https://condos.ca/api/v2/listings",
            params={"city": city, "status": "for-sale", "per_page": per_page},
            headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": f"https://condos.ca/{city}/condos-for-sale",
            },
            proxies=proxies,
            timeout=30,
        )
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, None
    except Exception as e:
        logger.debug(f"curl_cffi condos API failed: {e}")
        return 0, None


def _normalize_condos_api_payload(payload: dict) -> List[Dict[str, Any]]:
    """
    Best-effort normalize Condos.ca API v2 payload to listing dicts.
    The exact keys may vary; we defensively probe common shapes.
    """
    listings: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return listings

    # Common patterns: {"listings": [...]} or {"data": [...]} or {"data": {"listings": [...]}}
    items = payload.get("listings")
    if items is None:
        data = payload.get("data")
        if isinstance(data, dict):
            items = data.get("listings") or data.get("data") or data.get("results")
        else:
            items = data
    if not isinstance(items, list):
        return listings

    for item in items:
        if not isinstance(item, dict):
            continue
        status = item.get("status") or item.get("listing_status") or ""
        if is_sold_or_inactive(status):
            continue
        url = item.get("url") or item.get("permalink") or ""
        if url and url.startswith("/"):
            url = f"https://condos.ca{url}"
        address = pick_display_address(
            item.get("address"),
            item.get("full_address"),
            item.get("display_address"),
        )
        price = item.get("price") or item.get("list_price") or ""
        mls = item.get("mls_number") or item.get("mls") or hashlib.md5((url or address).encode()).hexdigest()[:12]
        region = _detect_region(address)
        city = "Toronto" if region.startswith("Toronto") else region.split(" ")[0]
        listings.append(
            {
                "id": f"condos_ca_{mls}",
                "address": address,
                "price": price,
                "bedrooms": item.get("bedrooms", ""),
                "bathrooms": item.get("bathrooms", ""),
                "url": url or "",
                "photo": "",
                "source": "condos_ca",
                "scraped_at": datetime.utcnow().isoformat(),
                "region": region,
                "city": city,
            }
        )
    return listings

CONDOS_URLS = [
    "https://condos.ca/toronto/condos-for-sale",
    "https://condos.ca/mississauga/condos-for-sale",
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
        "Toronto Downtown": ["downtown", "waterfront", "king west",
                             "queen west", "financial district"],
        "Toronto East (Scarborough)": ["scarborough", "east end"],
        "Toronto West (Etobicoke)": ["etobicoke", "west end"],
        "Toronto North (North York)": ["north york", "willowdale",
                                        "thornhill"],
    }
    for region, keywords in region_keywords.items():
        if any(kw in location for kw in keywords):
            return region
    return "Toronto"

async def _fetch_condos_page(client, url: str) -> list:
    """Scrapes a single Condos.ca page using __REACT_QUERY_STATE__ or sitemap fallback."""
    try:
        # Attempt 1: full browser headers to bypass Cloudflare
        if "toronto" in url:
            referer = "https://condos.ca/toronto/condos-for-sale"
        elif "mississauga" in url:
            referer = "https://condos.ca/mississauga/condos-for-sale"
        else:
            referer = "https://condos.ca/"

        headers = HEADER_GEN.generate(profile="chrome")
        headers.update(
            {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "accept-encoding": "gzip, deflate, br",
                "sec-fetch-site": "same-origin",
                "cache-control": "no-cache",
                "referer": referer,
            }
        )

        @async_retry(domain=CONDOS_DOMAIN)
        async def _do_get() -> httpx.Response:
            await RATE_LIMITER.acquire(CONDOS_DOMAIN)
            return await client.get(url, headers=headers, timeout=20)

        resp = await _do_get()
        
        if resp.status_code == 403:
            logger.warning(f"Condos.ca blocked {url} (403). Trying sitemap fallback.")
            await REQ_STATS.record_block(CONDOS_DOMAIN, resp.status_code)
            return await _scrape_condos_sitemap(client)
        
        if resp.status_code != 200:
            logger.error(f"Condos.ca page {url} failed with status {resp.status_code}")
            return []

        await REQ_STATS.record_success(CONDOS_DOMAIN)
            
        match = re.search(
            r'window\.__REACT_QUERY_STATE__\s*=\s*({.*?});', 
            resp.text, re.DOTALL
        )
        if not match:
            logger.warning(f"No __REACT_QUERY_STATE__ found on {url}")
            return await _scrape_condos_sitemap(client)
        
        data = json.loads(match.group(1))
        queries = data.get("queries", [])
        listings = []
        for query in queries:
            items = (query.get("state", {})
                        .get("data", {})
                        .get("response", {})
                        .get("data", {})
                        .get("data", []))
            if not items:
                continue
            for item in items:
                status = item.get("status") or item.get("listing_status") or ""
                if is_sold_or_inactive(status):
                    continue
                addr = pick_display_address(
                    item.get("address"),
                    item.get("full_address"),
                    item.get("display_address"),
                    item.get("neighbourhood"),
                )
                mls = item.get("mls_number", "")
                base_url = item.get("photo_base_url", "")
                count = item.get("photo_count", 0)
                version = item.get("photo_version", 1)
                photo = f"{base_url}{mls}_1.jpg?width=1920&v={version}" if all([mls, base_url, count]) else ""
                
                region = _detect_region(item.get("neighbourhood") or "")
                city = "Toronto" if region.startswith("Toronto") else region.split(" ")[0]
                listings.append({
                    "id": f"condos_ca_{mls}",
                    "address": addr,
                    "price": item.get("price", item.get("list_price", "")),
                    "bedrooms": item.get("bedrooms", ""),
                    "bathrooms": item.get("bathrooms", ""),
                    "url": f"https://condos.ca{item.get('url', '')}",
                    "photo": photo,
                    "source": "condos_ca",
                    "scraped_at": datetime.utcnow().isoformat(),
                    "region": region,
                    "city": city,
                })
        return listings
    except Exception as e:
        logger.error(f"Error scraping Condos.ca page {url}: {e}")
        return await _scrape_condos_sitemap(client)

async def _scrape_condos_sitemap(client) -> list:
    """Fallback: parse Condos.ca sitemap for listing URLs"""
    try:
        from listing_agent.activity_log import log_activity

        @async_retry(domain=CONDOS_DOMAIN)
        async def _do_get_sitemap() -> httpx.Response:
            await RATE_LIMITER.acquire(CONDOS_DOMAIN)
            headers = HEADER_GEN.generate(profile="chrome")
            headers.update({"accept": "application/xml,text/xml;q=0.9,*/*;q=0.8"})
            return await client.get(
                "https://condos.ca/sitemap-listings.xml",
                headers=headers,
                timeout=15,
            )

        resp = await _do_get_sitemap()
        if resp.status_code != 200:
            return []
            
        urls = re.findall(r'<loc>(https://condos\.ca/[^<]+)</loc>', resp.text)
        toronto_urls = [u for u in urls if 'toronto' in u][:20]
        log_activity("SCAN", f"condos_ca sitemap fallback: {len(toronto_urls)} URLs")
        
        # Return minimal listing stubs from URLs — better than nothing
        return [{"id": f"condos_ca_{u.split('/')[-1]}", 
                 "address": u.split('/')[-1].replace('-', ' ').title(),
                 "url": u, "source": "condos_ca", 
                 "price": "", "photo": "", "region": "Toronto",
                 "scraped_at": datetime.utcnow().isoformat()} 
                for u in toronto_urls]
    except Exception as e:
        logger.error(f"Condos.ca sitemap fallback failed: {e}")
        return []

async def scrape_listings() -> list:
    """Main entry point for Condos.ca scraper."""
    # Hybrid/API-first: try the public JSON API (faster, avoids DOM issues).
    if _curl_cffi_available():
        try:
            api_results: List[Dict[str, Any]] = []
            for city in ("toronto", "mississauga"):
                status, payload = await asyncio.to_thread(_condos_api_via_curl_cffi, city, 50)
                if status == 200 and isinstance(payload, dict):
                    for L in _normalize_condos_api_payload(payload):
                        L["city"] = city.title()
                        api_results.append(L)
            if api_results:
                logger.info(f"Condos.ca (API): scraped {len(api_results)} listings")
                return api_results
        except Exception as e:
            logger.warning(f"Condos.ca API-first failed: {e}")

    proxies = _get_httpx_proxies()
    client_kwargs: Dict[str, Any] = {
        "follow_redirects": True,
    }
    if proxies:
        client_kwargs["proxies"] = proxies

    async with httpx.AsyncClient(**client_kwargs) as client:
        # Warm-up request to set cookies + basic session
        try:
            await RATE_LIMITER.acquire(CONDOS_DOMAIN)
            warmup_headers = HEADER_GEN.generate(profile="chrome")
            await client.get(
                "https://condos.ca/",
                headers=warmup_headers,
                timeout=15,
            )
        except Exception as e:
            logger.warning(f"Condos.ca warm-up failed: {e}")

        tasks = [_fetch_condos_page(client, url) for url in CONDOS_URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    listings: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, list):
            listings.extend(r)
        elif isinstance(r, Exception):
            logger.error(f"Condos.ca task failed: {r}")

    if not listings and _scrapling_available():
        logger.warning(
            "Condos.ca httpx returned 0 listings; trying Scrapling v0.3 fallback."
        )
        try:
            listings = await _scrape_condos_scrapling()
        except Exception as e:
            logger.error(f"Condos.ca Scrapling fallback failed: {e}")
    if not listings:
        logger.warning(
            "Condos.ca Scrapling returned 0; falling back to DrissionPage browser."
        )
        try:
            browser_listings = await scrape_condos_browser()
            if browser_listings:
                listings = browser_listings
        except Exception as e:
            logger.error(f"Condos.ca browser fallback failed: {e}")

    summary = await REQ_STATS.summary(CONDOS_DOMAIN)
    logger.info(f"Condos.ca: scraped {len(listings)} listings. {summary}")
    return listings


def _scrape_condos_browser_sync() -> List[Dict[str, Any]]:
    """
    Browser-based fallback scraper using DrissionPage.

    When the httpx path is blocked, this uses a real Edge instance
    with hardened fingerprints to scrape listing cards directly
    from Condos.ca search result pages.
    """
    from collections import defaultdict

    listings: List[Dict[str, Any]] = []
    page = None

    try:
        page = create_browser(headless=False)

        for url in CONDOS_URLS:
            try:
                logger.info(f"Condos.ca (browser): navigating to {url}")
                page.get(url, retry=1, interval=1, timeout=20)
                time.sleep(8)  # allow React UI to render

                # Scroll to load more cards
                for _ in range(3):
                    try:
                        page.scroll.down(500)
                        time.sleep(1)
                    except Exception:
                        break

                # Group links per unique href, then merge price + address texts.
                link_groups = defaultdict(list)
                all_links = page.eles("tag:a")
                for link in all_links:
                    href = link.attr("href") or ""
                    if "condos.ca" not in href and href.startswith("/"):
                        href = f"https://condos.ca{href}"
                    if "condos.ca" not in href:
                        continue
                    # Heuristic: keep only likely listing detail pages (slug contains a digit).
                    slug = href.rstrip("/").split("/")[-1]
                    if "condos-for-sale" in slug or not re.search(r"\d", slug):
                        continue

                    text = (link.text or "").strip()
                    if text:
                        link_groups[href].append(text)

                logger.info(
                    f"Condos.ca (browser): {url} yielded {len(link_groups)} unique listing links"
                )

                for href, texts in link_groups.items():
                    try:
                        price = 0
                        address = ""

                        for text in texts:
                            # Price link contains $
                            if "$" in text and not price:
                                m = re.search(r"[\$C]*\$([\d,]+)", text)
                                if m:
                                    price = int(m.group(1).replace(",", ""))
                            # Address heuristics: only use text that looks like a real address
                            elif looks_like_real_address(text):
                                address = text

                        lid = hashlib.md5(href.encode()).hexdigest()[:12]
                        if price <= 0:
                            continue
                        if not address or not looks_like_real_address(address):
                            slug = href.rstrip("/").split("/")[-1]
                            address = slug.replace("-", " ").title() if slug else "Unknown"
                        region = _detect_region(address)

                        listings.append(
                            {
                                "id": f"condos_ca_{lid}",
                                "address": address or "Unknown",
                                "price": price,
                                "bedrooms": "",
                                "bathrooms": "",
                                "url": href,
                                "photo": "",
                                "source": "condos_ca",
                                "scraped_at": datetime.utcnow().isoformat(),
                                "region": region,
                            }
                        )
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"Condos.ca browser navigation failed for {url}: {e}")

    except Exception as e:
        logger.error(f"Condos.ca browser scraping failed: {e}")
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass

    logger.info(f"Condos.ca (browser): scraped {len(listings)} listings")
    return listings


async def scrape_condos_browser() -> List[Dict[str, Any]]:
    """Async wrapper around the sync DrissionPage scraper."""
    return await asyncio.to_thread(_scrape_condos_browser_sync)


async def _scrape_condos_scrapling() -> List[Dict[str, Any]]:
    """
    Scrapling v0.3 StealthyFetcher fallback: fetch Condos.ca search pages and parse listing links.
    """
    from collections import defaultdict

    from scrapling.fetchers import StealthyFetcher

    listings: List[Dict[str, Any]] = []
    for url in CONDOS_URLS:
        try:
            page = await StealthyFetcher.async_fetch(
                url,
                headless=True,
                timeout=45000,
                wait=6000,
            )
            if page.status != 200:
                continue

            # Prefer parsing embedded React query state when available (more reliable than link-text heuristics).
            try:
                html = page.html_content or ""
                match = re.search(
                    r"window\.__REACT_QUERY_STATE__\s*=\s*({.*?});",
                    html,
                    re.DOTALL,
                )
                if match:
                    data = json.loads(match.group(1))
                    queries = data.get("queries", [])
                    for query in queries:
                        items = (
                            query.get("state", {})
                            .get("data", {})
                            .get("response", {})
                            .get("data", {})
                            .get("data", [])
                        )
                        if not items:
                            continue
                        for item in items:
                            status = item.get("status") or item.get("listing_status") or ""
                            if is_sold_or_inactive(status):
                                continue
                            mls = item.get("mls_number", "")
                            href = item.get("url", "") or ""
                            full_url = f"https://condos.ca{href}" if href.startswith("/") else href
                            addr = pick_display_address(
                                item.get("address"),
                                item.get("full_address"),
                                item.get("display_address"),
                                item.get("neighbourhood"),
                            )
                            price = item.get("price", item.get("list_price", "")) or ""
                            listings.append(
                                {
                                    "id": f"condos_ca_{mls or hashlib.md5(full_url.encode()).hexdigest()[:12]}",
                                    "address": addr,
                                    "price": price,
                                    "bedrooms": item.get("bedrooms", ""),
                                    "bathrooms": item.get("bathrooms", ""),
                                    "url": full_url,
                                    "photo": "",
                                    "source": "condos_ca",
                                    "scraped_at": datetime.utcnow().isoformat(),
                                    "region": _detect_region(item.get("neighbourhood") or addr),
                                }
                            )
                    if listings:
                        continue
            except Exception:
                pass

            link_groups = defaultdict(list)
            for link in page.css("a"):
                href = (link.attrib.get("href") or "").strip()
                if not href:
                    continue
                if href.startswith("/"):
                    href = f"https://condos.ca{href}"
                if "condos.ca" not in href:
                    continue
                # Skip search/nav URLs; keep listing pages (path with slug)
                if "condos-for-sale" in href and href.rstrip("/").endswith("condos-for-sale"):
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
                    if not address or not looks_like_real_address(address):
                        slug = href.rstrip("/").split("/")[-1]
                        address = slug.replace("-", " ").title() if slug else "Unknown"
                    lid = hashlib.md5(href.encode()).hexdigest()[:12]
                    region = _detect_region(address)
                    listings.append({
                        "id": f"condos_ca_{lid}",
                        "address": address,
                        "price": price,
                        "bedrooms": "",
                        "bathrooms": "",
                        "url": href,
                        "photo": "",
                        "source": "condos_ca",
                        "scraped_at": datetime.utcnow().isoformat(),
                        "region": region,
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Condos.ca Scrapling fetch failed for {url}: {e}")
    if listings:
        logger.info(f"Condos.ca (Scrapling): scraped {len(listings)} listings")
    return listings


# For backward compatibility
async def scrape_condos_ca(area: str = "gta") -> List[Dict[str, Any]]:
    return await scrape_listings()
