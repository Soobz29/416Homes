"""Firecrawl crawling backend."""

import os
import asyncio
import httpx
from datetime import datetime
import logging
from typing import Dict, Any, List
from .crawler import CrawlRequest, CrawlResult, CrawlPage, CrawlStats

logger = logging.getLogger(__name__)

FIRECRAWL_API_BASE = "https://api.firecrawl.dev/v1"


async def firecrawl_crawl(request: CrawlRequest) -> CrawlResult:
    """
    Crawl using Firecrawl API.

    API Docs: https://docs.firecrawl.dev/api-reference/endpoint/crawl
    """
    start_time = datetime.now()

    api_key = os.getenv("FIRECRAWL_API_KEY")

    if not api_key:
        error_msg = "FIRECRAWL_API_KEY required"
        logger.error(error_msg)
        return _error_result(start_time, error_msg)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
            payload: Dict[str, Any] = {
                "url": request.url,
                "limit": request.max_pages,
                "scrapeOptions": {
                    "formats": [request.format],
                },
            }

            if request.include_patterns:
                payload["includePaths"] = request.include_patterns
            if request.exclude_patterns:
                payload["excludePaths"] = request.exclude_patterns

            logger.info(f"Submitting Firecrawl crawl: {request.url}")
            response = await client.post(
                f"{FIRECRAWL_API_BASE}/crawl",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                error = data.get("error", "Unknown error")
                raise RuntimeError(f"Firecrawl error: {error}")

            crawl_id = data["id"]
            logger.info(f"Firecrawl job created: {crawl_id}")

            max_attempts = request.timeout_seconds // 5
            attempt = 0

            while attempt < max_attempts:
                await asyncio.sleep(5)
                attempt += 1

                status_response = await client.get(
                    f"{FIRECRAWL_API_BASE}/crawl/{crawl_id}",
                    headers=headers,
                )
                status_response.raise_for_status()

                status_data = status_response.json()
                status = status_data.get("status")

                logger.info(f"Firecrawl job {crawl_id} status: {status} (attempt {attempt}/{max_attempts})")

                if status == "completed":
                    pages: List[CrawlPage] = []
                    result_data = status_data.get("data", [])

                    for page_data in result_data:
                        metadata = page_data.get("metadata", {})

                        pages.append(CrawlPage(
                            url=metadata.get("url") or page_data.get("url", ""),
                            title=metadata.get("title"),
                            markdown=page_data.get("markdown"),
                            html=page_data.get("html"),
                            text=page_data.get("text"),
                            links=page_data.get("links", []),
                            metadata=metadata,
                            status_code=metadata.get("statusCode"),
                        ))

                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Firecrawl completed: {len(pages)} pages in {duration:.2f}s")

                    return CrawlResult(
                        pages=pages,
                        stats=CrawlStats(
                            total_pages=len(pages),
                            duration_sec=duration,
                            backend="firecrawl",
                            success=True,
                        ),
                    )

                elif status == "failed":
                    error = status_data.get("error", "Unknown error")
                    raise RuntimeError(f"Firecrawl failed: {error}")

            raise TimeoutError(f"Firecrawl job {crawl_id} timed out")

    except Exception as e:
        logger.exception(f"Firecrawl error: {e}")
        return _error_result(start_time, str(e))


def _error_result(start_time: datetime, error: str) -> CrawlResult:
    """Create error result."""
    duration = (datetime.now() - start_time).total_seconds()
    return CrawlResult(
        pages=[],
        stats=CrawlStats(
            total_pages=0,
            duration_sec=duration,
            backend="firecrawl",
            success=False,
            error=error,
        ),
    )
