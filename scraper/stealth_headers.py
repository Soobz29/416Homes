"""
Stealth header utilities powered by browserforge.

This module centralizes generation of realistic browser headers for all
HTTP-based scrapers. It uses browserforge's HeaderGenerator under the hood
and exposes a small, scraper-friendly API.

Key features
------------
* Chrome / Firefox / Safari style profiles.
* Randomized, realistic User-Agent + Sec-CH headers.
* Randomized Accept-Language from a small locale pool.
* Reasonable Sec-Fetch-* defaults for top-level navigations.
"""

from __future__ import annotations

import logging
import random
from typing import Dict, Optional

from browserforge.headers import HeaderGenerator

logger = logging.getLogger(__name__)


ACCEPT_LANGUAGE_POOL = ["en-US", "en-CA", "en-GB"]


class StealthHeaderGenerator:
    """
    Thin wrapper around browserforge.HeaderGenerator.

    Profiles (for now):
      * \"chrome\"  – Chrome 120-style UA on Windows
      * \"firefox\" – Firefox 121-style UA on Windows
      * \"safari\"  – Safari 17-style UA on macOS
    """

    def __init__(self) -> None:
        # Default to HTTP/2 desktop headers; browser+locale are per-generate.
        self._hg = HeaderGenerator(http_version=2)

    def _choose_profile(self, profile: Optional[str]) -> str:
        if profile in {"chrome", "firefox", "safari"}:
            return profile
        # Mild bias towards Chrome-like headers for maximum compatibility.
        return random.choice(["chrome", "chrome", "firefox", "safari"])

    def _profile_ua(self, profile: str) -> str:
        # Representative UAs for each profile family.
        if profile == "chrome":
            return random.choice(
                [
                    # Chrome 120 on Windows 10
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36",
                    # Chrome 121 on macOS
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36",
                ]
            )
        if profile == "firefox":
            return random.choice(
                [
                    # Firefox 121 Windows
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
                    "Gecko/20100101 Firefox/121.0",
                    # Firefox 121 macOS
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.6; rv:121.0) "
                    "Gecko/20100101 Firefox/121.0",
                ]
            )
        # Safari 17 as a default
        return random.choice(
            [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.2 Safari/605.1.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Safari/605.1.15",
            ]
        )

    def generate(self, profile: Optional[str] = None) -> Dict[str, str]:
        """
        Generate a full header set for a given browser profile.

        Returns a mutable dict so callers can override referer/origin, etc.
        """
        profile = self._choose_profile(profile)
        user_agent = self._profile_ua(profile)
        locale = random.choice(ACCEPT_LANGUAGE_POOL)

        try:
            headers = self._hg.generate(
                user_agent=user_agent,
                locale=locale,
            )
        except Exception as e:  # pragma: no cover - very unlikely
            logger.warning(f"browserforge HeaderGenerator failed, falling back to bare UA: {e}")
            headers = {
                "User-Agent": user_agent,
                "Accept-Language": locale,
            }

        # Ensure UA is present under the expected key.
        headers.setdefault("User-Agent", user_agent)

        # Normalize Accept-Language to prefer chosen locale.
        if "Accept-Language" not in headers:
            headers["Accept-Language"] = f"{locale};q=1.0"

        # Browser-specific quirks.
        ua = headers.get("User-Agent", "")
        if "Chrome" in ua and "Safari" in ua:
            # Chrome: keep sec-ch-ua headers and ensure platform is set.
            headers.setdefault("sec-ch-ua-platform", '"Windows"')
        elif "Firefox" in ua:
            # Firefox does not send Sec-CH-UA headers (yet).
            headers.pop("sec-ch-ua", None)
            headers.pop("sec-ch-ua-mobile", None)
            headers.pop("sec-ch-ua-platform", None)
        elif "Safari" in ua and "Version/" in ua:
            # Safari: no Sec-CH-UA; Accept-Encoding is typically gzip/br.
            headers.pop("sec-ch-ua", None)
            headers.pop("sec-ch-ua-mobile", None)
            headers.pop("sec-ch-ua-platform", None)

        # Ensure realistic Sec-Fetch-* defaults for top-level navigation.
        headers.setdefault("Sec-Fetch-Site", "same-origin")
        headers.setdefault("Sec-Fetch-Mode", "navigate")
        headers.setdefault("Sec-Fetch-Dest", "document")
        headers.setdefault("Sec-Fetch-User", "?1")

        return headers


_GLOBAL_HEADER_GEN: Optional[StealthHeaderGenerator] = None


def get_stealth_header_generator() -> StealthHeaderGenerator:
    """Return a process-wide StealthHeaderGenerator singleton."""
    global _GLOBAL_HEADER_GEN
    if _GLOBAL_HEADER_GEN is None:
        _GLOBAL_HEADER_GEN = StealthHeaderGenerator()
    return _GLOBAL_HEADER_GEN

