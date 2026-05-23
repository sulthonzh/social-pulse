"""Async HTTP retry utility with exponential backoff and jitter.

Retries transient failures (network errors and specific HTTP status codes)
using non-blocking asyncio.sleep between attempts.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx
import structlog

from src.shared.config import settings

logger = structlog.get_logger(__name__)

_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


async def async_fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    max_retries: int | None = None,
    base_delay: float | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Execute an HTTP request with automatic retry on transient failures.

    Retries on ``httpx.RequestError`` (network-level errors) and on
    ``httpx.HTTPStatusError`` for status codes 429, 502, 503, 504.
    All other HTTP errors are raised immediately without retrying.

    Args:
        client: The httpx async client used to make the request.
        method: HTTP method (e.g. ``"GET"``, ``"POST"``).
        url: Request URL (absolute or relative to client base_url).
        params: Query parameters.
        max_retries: Maximum retry attempts. Falls back to
            ``settings.http_retry_max_retries`` when ``None``.
        base_delay: Base delay in seconds for exponential backoff.
            Falls back to ``settings.http_retry_base_delay`` when ``None``.
        **kwargs: Additional keyword arguments forwarded to
            ``httpx.AsyncClient.request``.

    Returns:
        The successful ``httpx.Response``.

    Raises:
        httpx.HTTPStatusError: On non-retryable HTTP errors, or when
            retries are exhausted on retryable HTTP errors.
        httpx.RequestError: When retries are exhausted on network errors.
    """
    effective_max_retries = (
        max_retries if max_retries is not None else settings.http_retry_max_retries
    )
    effective_base_delay = base_delay if base_delay is not None else settings.http_retry_base_delay

    last_exc: httpx.HTTPError | None = None

    for attempt in range(effective_max_retries + 1):
        try:
            response = await client.request(method, url, params=params, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if (
                exc.response.status_code in _RETRYABLE_STATUS_CODES
                and attempt < effective_max_retries
            ):
                delay = effective_base_delay * (2**attempt) + random.uniform(  # noqa: S311
                    0, effective_base_delay
                )
                logger.warning("http_retry", url=url, attempt=attempt, delay=delay)
                await asyncio.sleep(delay)
                continue
            raise
        except httpx.RequestError as exc:
            last_exc = exc
            if attempt < effective_max_retries:
                delay = effective_base_delay * (2**attempt) + random.uniform(  # noqa: S311
                    0, effective_base_delay
                )
                logger.warning("http_retry", url=url, attempt=attempt, delay=delay)
                await asyncio.sleep(delay)
                continue
            raise

    # Unreachable under normal flow, but satisfies type checkers.
    raise last_exc  # type: ignore[misc]
