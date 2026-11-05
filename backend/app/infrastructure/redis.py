"""Async Redis connection lifecycle and client management."""

import asyncio
import logging
from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global connection pool and client references
_redis_pool: ConnectionPool | None = None
_redis_client: Redis | None = None


def get_redis_pool() -> ConnectionPool:
    """Return the global Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


def get_redis() -> Redis:
    """Return the shared asynchronous Redis client."""
    global _redis_client
    if _redis_client is None:
        pool = get_redis_pool()
        _redis_client = Redis(connection_pool=pool)
    return _redis_client


async def init_redis() -> None:
    """Initialize Redis connection pool on startup."""
    logger.info("Initializing Redis connection pool...")
    get_redis()


async def close_redis() -> None:
    """Close Redis client and connection pool on shutdown."""
    global _redis_client, _redis_pool
    if _redis_client is not None:
        logger.info("Closing Redis client...")
        await _redis_client.aclose()
        _redis_client = None

    if _redis_pool is not None:
        logger.info("Disconnecting Redis connection pool...")
        await _redis_pool.disconnect()
        _redis_pool = None


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency for injecting the Redis client."""
    client = get_redis()
    yield client


async def check_redis_health(timeout_seconds: float = 3.0) -> tuple[bool, str]:
    """Verify Redis connectivity via PING command.

    Returns:
        tuple[bool, str]: (is_healthy, status_detail)
    """
    try:
        client = get_redis()
        response = await asyncio.wait_for(client.ping(), timeout=timeout_seconds)
        if response is True:
            return True, "healthy"
        return False, "Unexpected PING response"
    except TimeoutError:
        logger.warning("Redis health check timed out after %s seconds", timeout_seconds)
        return False, "Redis connection timed out"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", type(exc).__name__)
        return False, f"Redis connectivity error ({type(exc).__name__})"
