"""Integration tests for live PostgreSQL and Redis connectivity."""

import pytest

from app.database.health import check_db_health
from app.infrastructure.redis import check_redis_health


@pytest.mark.integration
async def test_live_postgres_connectivity() -> None:
    """Verify live PostgreSQL connectivity and query execution."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(f"Live PostgreSQL not reachable ({detail}). Ensure docker compose is running.")
    assert is_healthy is True
    assert detail == "healthy"


@pytest.mark.integration
async def test_live_redis_connectivity() -> None:
    """Verify live Redis connectivity via PING."""
    is_healthy, detail = await check_redis_health()
    if not is_healthy:
        pytest.skip(f"Live Redis not reachable ({detail}). Ensure docker compose is running.")
    assert is_healthy is True
    assert detail == "healthy"
