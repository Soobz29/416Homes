"""Extract ordered listing photo URLs from zon HTML (Zoocasa expcloud CDN)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_EXP_CLOUD_RE = re.compile(
    r"https://images\.expcloud\.com/[^\s\"\'<>)]+",
    re.IGNORECASE,
)


def extract_expcloud_photo_urls_from_html(html: str, max_urls: int = 15) -> List[str]:
    """
    Pull images.expcloud.com URLs in first-seen gallery order.

    For each logical photo (base path without w=/h=), keep the largest w= variant
    seen while preserving the order of first encounter in the document.
    Do not re-sort different photos by width — that scrambles MLS gallery order.
    """
    if not html:
        return []

    urls: List[str] = []

    all_urls = _EXP_CLOUD_RE.findall(html)
    url_bases: Dict[str, Dict[str, Any]] = {}
    for url in all_urls:
        normalized = (
            url.replace("\\/", "/").replace("&amp;", "&").rstrip("',")
        )
        base = re.sub(r"[?&]w=\d+", "", normalized)
        base = re.sub(r"[?&]h=\d+", "", base)
        width_match = re.search(r"[?&]w=(\d+)", normalized)
        width = int(width_match.group(1)) if width_match else 0
        if base not in url_bases or width > url_bases.get(base, {}).get("width", 0):
            url_bases[base] = {"url": normalized, "width": width}

    urls = [info["url"] for info in url_bases.values()]
    logger.info("Extracted %d unique photos from regex scan", len(urls))

    if len(urls) < 3:
        photo_patterns = [
            r'"photos"\s*:\s*\[(.*?)\]',
            r'"images"\s*:\s*\[(.*?)\]',
            r"photoUrls\s*[:=]\s*\[(.*?)\]",
            r'"media"\s*:\s*{[^}]*"photos"\s*:\s*\[(.*?)\]',
        ]
        for p in photo_patterns:
            for match in re.findall(p, html, re.DOTALL):
                photo_urls = re.findall(
                    r"https://images\.expcloud\.com/[^\"\'<>]+",
                    match,
                )
                urls.extend(photo_urls)
        logger.info("After script extraction: %d total photos", len(urls))

    if len(urls) < 3 and "<" in html:
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for img in soup.find_all("img"):
                srcset = img.get("srcset", "")
                if "images.expcloud.com" in srcset:
                    for part in srcset.split(","):
                        srcset_url = part.strip().split()[0]
                        if srcset_url.startswith("http"):
                            urls.append(srcset_url)
                src = img.get("src", "")
                if "images.expcloud.com" in src and src.startswith("http"):
                    urls.append(src)
            logger.info("After BeautifulSoup: %d total photos", len(urls))
        except Exception as e:
            logger.warning("BeautifulSoup parsing failed: %s", e)

    seen = set()
    clean_urls: List[str] = []
    for u in urls:
        if not u or u in seen:
            continue
        if u.lower().endswith(".svg"):
            continue
        if re.search(r"[?&]w=([0-9]{1,2})(?:&|$)", u):
            continue
        seen.add(u)
        clean_urls.append(u)

    logger.info("Final count: %d high-res photos from listing (gallery order)", len(clean_urls))
    return clean_urls[:max_urls]
