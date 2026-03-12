"""Cloudflare Browser Rendering crawling backend."""

import os
import asyncio
import httpx
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List
from .crawler import CrawlRequest, CrawlResult, CrawlPage, CrawlStats

logger = logging.getLogger(__name__)

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


async def cloudflare_crawl(request: CrawlRequest) -> CrawlResult:
    """
    Crawl using Cloudflare Browser Rendering.

    API Docs: https://developers.cloudflare.com/browser-rendering/platform/crawl/
    """
    start_time = datetime.now()

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not account_id or not api_token:
        error_msg = "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN required"
        logger.error(error_msg)
        return _error_result(start_time, error_msg)

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
            crawl_url = f"{CLOUDFLARE_API_BASE}/accounts/{account_id}/browser-rendering/crawl"

            payload: Dict[str, Any] = {
                "url": request.url,
                "depth": request.max_depth,
                "pageLimit": request.max_pages,
                "formats": [request.format],
            }

            if request.include_patterns:
                payload["includePatterns"] = request.include_patterns
            if request.exclude_patterns:
                payload["excludePatterns"] = request.exclude_patterns

            logger.info(f"Submitting Cloudflare crawl: {request.url}")
            response = await client.post(crawl_url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                errors = data.get("errors", [])
                error_msg = f"Cloudflare API error: {errors}"
                logger.error(error_msg)
                return _error_result(start_time, error_msg)

            job_id = data["result"]["id"]
            logger.info(f"Cloudflare crawl job created: {job_id}")

            status_url = f"{crawl_url}/{job_id}"
            max_attempts = request.timeout_seconds // 5
            attempt = 0

            while attempt < max_attempts:
                await asyncio.sleep(5)
                attempt += 1

                status_response = await client.get(status_url, headers=headers)
                status_response.raise_for_status()

                status_data = status_response.json()
                if not status_data.get("success"):
                    errors = status_data.get("errors", [])
                    raise RuntimeError(f"Status check failed: {errors}")

                result = status_data["result"]
                status = result.get("status")
                logger.info(f"Crawl job {job_id} status: {status} (attempt {attempt}/{max_attempts})")

                if status == "completed":
                    pages: List[CrawlPage] = []
                    records = result.get("records", [])

                    for record in records:
                        metadata = record.get("metadata", {})

                        pages.append(CrawlPage(
                            url=record.get("url", ""),
                            title=metadata.get("title"),
                            markdown=record.get("markdown"),
                            html=record.get("html"),
                            text=record.get("text"),
                            links=record.get("links", []),
                            metadata=metadata,
                            status_code=metadata.get("status"),
                        ))

                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Cloudflare crawl completed: {len(pages)} pages in {duration:.2f}s")

                    return CrawlResult(
                        pages=pages,
                        stats=CrawlStats(
                            total_pages=len(pages),
                            duration_sec=duration,
                            backend="cloudflare",
                            success=True,
                        ),
                    )

                elif status == "failed":
                    error = result.get("error", "Unknown error")
                    raise RuntimeError(f"Cloudflare crawl failed: {error}")

            raise TimeoutError(f"Crawl job {job_id} timed out after {attempt * 5}s")

    except Exception as e:
        logger.exception(f"Cloudflare crawl error: {e}")
        return _error_result(start_time, str(e))


def _error_result(start_time: datetime, error: str) -> CrawlResult:
    """Create error result."""
    duration = (datetime.now() - start_time).total_seconds()
    return CrawlResult(
        pages=[],
        stats=CrawlStats(
            total_pages=0,
            duration_sec=duration,
            backend="cloudflare",
            success=False,
            error=error,
        ),
    )
