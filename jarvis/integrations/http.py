"""
Small async HTTP client for integrations.

Wraps ``httpx`` with sane timeouts and exponential-backoff retries, and returns
parsed JSON. Integrations depend on this thin abstraction (not httpx directly),
so tests can inject a fake client without any network.
"""

from __future__ import annotations

import httpx

from jarvis.utils.exceptions import IntegrationError
from jarvis.utils.retry import retry_async


class HttpError(IntegrationError):
    """An HTTP request failed."""


class HttpClient:
    """Minimal async JSON HTTP client with retries."""

    def __init__(self, timeout: float = 10.0, retry_attempts: int = 3) -> None:
        self._timeout = timeout
        self._attempts = retry_attempts

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        """Perform an HTTP request and return the parsed JSON body."""

        @retry_async(attempts=self._attempts, base_delay=0.5,
                    exceptions=(httpx.HTTPError,))
        async def _do() -> dict:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method, url, params=params, json=json, headers=headers
                )
                response.raise_for_status()
                return response.json() if response.content else {}

        try:
            return await _do()
        except httpx.HTTPError as exc:
            raise HttpError(f"HTTP {method} {url} failed: {exc}") from exc

    async def get_json(self, url: str, *, params: dict | None = None,
                    headers: dict | None = None) -> dict:
        return await self.request_json("GET", url, params=params, headers=headers)

    async def post_json(self, url: str, *, json: dict | None = None,
                        headers: dict | None = None) -> dict:
        return await self.request_json("POST", url, json=json, headers=headers)
