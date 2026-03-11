"""Internal API client for Telegram bot (and other workers) to call the 416Homes API."""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class APIClient:
    """Client for calling 416Homes API (listings, health)."""

    def __init__(self):
        self.base_url = (os.getenv("API_BASE_URL") or "http://localhost:8000").strip().rstrip("/")
        self.timeout = 30.0

    async def get_listings(
        self,
        city: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        bedrooms: Optional[str] = None,
        bathrooms: Optional[str] = None,
        property_types: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get listings from the API.

        Returns:
            {
                "listings": [...],
                "total": int,
                "scan_time": str | None,
                "error": str | None  (only on failure)
            }
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if city:
            params["city"] = city
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if bedrooms is not None:
            params["bedrooms"] = bedrooms
        if bathrooms is not None:
            params["bathrooms"] = bathrooms
        if property_types is not None:
            params["property_types"] = property_types

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/listings"
                logger.info("Fetching listings from API: %s params=%s", url, params)
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            # Support both shapes: object with listings/total/scan_time or raw array (legacy)
            if isinstance(data, list):
                return {
                    "listings": data,
                    "total": len(data),
                    "scan_time": None,
                }
            return {
                "listings": data.get("listings", []),
                "total": data.get("total", len(data.get("listings", []))),
                "scan_time": data.get("scan_time"),
            }
        except httpx.HTTPError as e:
            logger.error("API request failed: %s", e)
            return {
                "listings": [],
                "total": 0,
                "scan_time": None,
                "error": str(e),
            }
        except Exception as e:
            logger.exception("Unexpected error calling API: %s", e)
            return {
                "listings": [],
                "total": 0,
                "scan_time": None,
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check if the API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/health")
                return response.status_code == 200
        except Exception:
            return False
