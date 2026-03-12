"""Unified crawling interface for Firecrawl and Cloudflare Browser Rendering."""

import os
import logging
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)


class CrawlBackend(str, Enum):
    """Supported crawling backends."""
    FIRECRAWL = "firecrawl"
    CLOUDFLARE = "cloudflare"


class CrawlRequest(BaseModel):
    """Request for crawling a website."""
    url: str
    backend: CrawlBackend = CrawlBackend.CLOUDFLARE
    max_depth: int = 2
    max_pages: int = 50
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    format: Literal["markdown", "json", "html"] = "markdown"
    timeout_seconds: int = 300


class CrawlPage(BaseModel):
    """Single page result from crawl."""
    url: str
    title: Optional[str] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    text: Optional[str] = None
    links: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None


class CrawlStats(BaseModel):
    """Statistics about the crawl."""
    total_pages: int
    duration_sec: float
    backend: str
    success: bool
    error: Optional[str] = None


class CrawlResult(BaseModel):
    """Complete result from a crawl operation."""
    pages: List[CrawlPage]
    stats: CrawlStats


async def crawl_site(request: CrawlRequest) -> CrawlResult:
    """
    Crawl a website using specified backend.

    Args:
        request: Crawl configuration

    Returns:
        CrawlResult with pages and stats

    Raises:
        ValueError: If backend is not supported
        RuntimeError: If crawl fails
    """
    logger.info(f"Starting crawl: {request.url} with backend {request.backend}")

    if request.backend == CrawlBackend.CLOUDFLARE:
        from .crawler_cloudflare import cloudflare_crawl
        return await cloudflare_crawl(request)
    elif request.backend == CrawlBackend.FIRECRAWL:
        from .crawler_firecrawl import firecrawl_crawl
        return await firecrawl_crawl(request)
    else:
        raise ValueError(f"Unsupported backend: {request.backend}")


def get_default_backend() -> CrawlBackend:
    """Get default crawling backend from environment."""
    default = os.getenv("DEFAULT_CRAWL_BACKEND", "cloudflare")
    try:
        return CrawlBackend(default.lower())
    except ValueError:
        logger.warning(f"Invalid DEFAULT_CRAWL_BACKEND: {default}, using cloudflare")
        return CrawlBackend.CLOUDFLARE
