"""Reusable HTTP client infrastructure for external API requests."""

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
DEFAULT_LIMITS = httpx.Limits(
    max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0
)
DEFAULT_USER_AGENT = "JobRadarAI/1.0 (+https://jobradar.ai; automated discovery engine)"

_shared_client: httpx.AsyncClient | None = None


def create_http_client(
    timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    limits: httpx.Limits = DEFAULT_LIMITS,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """Create a configured AsyncClient instance for external API communication."""
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
    }
    return httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        headers=headers,
        follow_redirects=follow_redirects,
    )


async def get_shared_http_client() -> httpx.AsyncClient:
    """Provide a singleton async HTTP client for connection reuse across tasks."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = create_http_client()
    return _shared_client


async def close_shared_http_client() -> None:
    """Safely shut down the singleton async HTTP client."""
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None
