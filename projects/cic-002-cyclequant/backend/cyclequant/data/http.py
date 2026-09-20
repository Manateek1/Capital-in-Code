from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from cyclequant.data.base import DataSourceError

RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


async def request(
    client: httpx.AsyncClient,
    source: str,
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    json: Any | None = None,
    retries: int = 3,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = await client.request(method, url, params=params, headers=headers, json=json)
            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response
            retry_after = response.headers.get("Retry-After")
            delay = min(float(retry_after), 5.0) if retry_after else min(0.25 * (2**attempt), 3.0)
            last_error = httpx.HTTPStatusError(
                f"retryable HTTP {response.status_code}",
                request=response.request,
                response=response,
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            last_error = exc
            delay = min(0.25 * (2**attempt), 3.0)
            if isinstance(exc, httpx.HTTPStatusError):
                response = exc.response
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    break
        if attempt < retries:
            await asyncio.sleep(delay)
    raise DataSourceError(source, str(last_error or "request failed"))


async def request_json(
    client: httpx.AsyncClient,
    source: str,
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    json: Any | None = None,
    retries: int = 3,
) -> Any:
    response = await request(
        client,
        source,
        method,
        url,
        params=params,
        headers=headers,
        json=json,
        retries=retries,
    )
    try:
        return response.json()
    except ValueError as exc:
        raise DataSourceError(source, "response was not valid JSON") from exc
