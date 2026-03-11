"""
Shared rate limiting, retry, and request statistics utilities for scrapers.

Features
--------
* DomainRateLimiter
  - Simple token-bucket limiter: 1 request every WINDOW seconds per domain.
* async_retry
  - Async exponential backoff decorator (2s, 5s, 10s).
* RequestStats
  - Tracks successes vs blocked responses (403 / 429) per domain.
* random_jitter
  - Small 0.5–2.0s jitter helper for human‑like delays.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DomainRateLimiter:
    """
    Token-bucket rate limiter keyed by domain.

    Default: 1 request every `window_seconds` per domain with a burst
    capacity of 1. The implementation is deliberately simple and in‑memory,
    which is sufficient for our single‑process scrapers.
    """

    def __init__(self, window_seconds: float = 3.0) -> None:
        self.window_seconds = window_seconds
        self._tokens: Dict[str, float] = {}
        self._last_refill: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str) -> None:
        """
        Wait until a token is available for the given domain.

        This enforces roughly 1 request per `window_seconds` for each domain.
        """
        while True:
            async with self._lock:
                now = time.monotonic()
                last = self._last_refill.get(domain, 0.0)
                tokens = self._tokens.get(domain, 1.0)

                # Refill logic: if enough time has passed, grant one token.
                elapsed = now - last
                if elapsed >= self.window_seconds:
                    tokens = 1.0
                    last = now
                    self._tokens[domain] = tokens
                    self._last_refill[domain] = last

                if tokens >= 1.0:
                    # Consume token and proceed immediately.
                    self._tokens[domain] = tokens - 1.0
                    return

                # No tokens available; compute remaining wait.
                remaining = self.window_seconds - elapsed

            # Sleep outside the lock.
            await asyncio.sleep(max(remaining, 0.0))


class RequestStats:
    """
    Tracks success vs blocked responses per domain.

    This is mainly for logging/observability so we can see how often
    the remote service is returning 403/429 status codes.
    """

    def __init__(self) -> None:
        self._success: Dict[str, int] = {}
        self._blocked: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def record_success(self, domain: str) -> None:
        async with self._lock:
            self._success[domain] = self._success.get(domain, 0) + 1

    async def record_block(self, domain: str, status: int) -> None:
        async with self._lock:
            self._blocked[domain] = self._blocked.get(domain, 0) + 1
            logger.warning(f"{domain} returned blocking status {status}")

    async def summary(self, domain: str) -> str:
        async with self._lock:
            ok = self._success.get(domain, 0)
            blocked = self._blocked.get(domain, 0)
        return f"{domain} — success={ok}, blocked={blocked}"


_GLOBAL_RATE_LIMITER: Optional[DomainRateLimiter] = None
_GLOBAL_STATS: Optional[RequestStats] = None


def get_rate_limiter() -> DomainRateLimiter:
    global _GLOBAL_RATE_LIMITER
    if _GLOBAL_RATE_LIMITER is None:
        window = float(
            # Environment override if needed.
            # Using local import to avoid importing os at module import cost
            __import__("os").environ.get("RATE_LIMIT_WINDOW_SECONDS", "3")
        )
        _GLOBAL_RATE_LIMITER = DomainRateLimiter(window_seconds=window)
    return _GLOBAL_RATE_LIMITER


def get_request_stats() -> RequestStats:
    global _GLOBAL_STATS
    if _GLOBAL_STATS is None:
        _GLOBAL_STATS = RequestStats()
    return _GLOBAL_STATS


def random_jitter(min_seconds: float = 0.5, max_seconds: float = 2.0) -> float:
    """Return a small random jitter value in seconds."""
    return random.uniform(min_seconds, max_seconds)


RETRY_STATUS_CODES = {403, 408, 425, 429, 500, 502, 503, 504}


def async_retry(
    *,
    domain: str,
    max_attempts: int = 3,
    delays: Optional[list[float]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Async exponential backoff decorator for HTTP operations.

    Retries on:
      * httpx.RequestError / network issues
      * Responses with status in RETRY_STATUS_CODES
    """

    if delays is None:
        delays = [2.0, 5.0, 10.0]

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            last_exc: Optional[BaseException] = None

            while attempt < max_attempts:
                try:
                    result = await func(*args, **kwargs)

                    # If this looks like an httpx.Response, inspect status code.
                    if isinstance(result, httpx.Response) and result.status_code in RETRY_STATUS_CODES:
                        attempt += 1
                        last_exc = RuntimeError(
                            f"{domain} returned {result.status_code} on attempt {attempt}"
                        )
                        if attempt >= max_attempts:
                            break
                        delay = delays[min(attempt - 1, len(delays) - 1)]
                        logger.warning(
                            f"[retry] {domain} status {result.status_code}, "
                            f"retrying in {delay:.1f}s (attempt {attempt}/{max_attempts})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    return result

                except (httpx.RequestError, asyncio.TimeoutError) as exc:
                    attempt += 1
                    last_exc = exc
                    if attempt >= max_attempts:
                        break
                    delay = delays[min(attempt - 1, len(delays) - 1)]
                    logger.warning(
                        f"[retry] {domain} network error {exc!r}, "
                        f"retrying in {delay:.1f}s (attempt {attempt}/{max_attempts})"
                    )
                    await asyncio.sleep(delay)

            # Out of attempts
            if last_exc is not None:
                raise last_exc

            # Should not happen, but keeps type checker happy.
            raise RuntimeError(f"[retry] Exhausted retries for {domain} without result")

        return wrapper

    return decorator

