"""Unit tests for health and readiness endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_liveness_endpoint(async_client: AsyncClient) -> None:
    """Verify that /health/live returns 200 without touching infrastructure."""
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "test"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.unit
async def test_readiness_endpoint_all_healthy(async_client: AsyncClient) -> None:
    """Verify that /health/ready returns 200 when all components are healthy."""
    with (
        patch("app.api.routes.health.check_db_health", new_callable=AsyncMock) as mock_db,
        patch("app.api.routes.health.check_redis_health", new_callable=AsyncMock) as mock_redis,
    ):
        mock_db.return_value = (True, "healthy")
        mock_redis.return_value = (True, "healthy")

        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["components"]["database"] == "healthy"
        assert data["components"]["redis"] == "healthy"


@pytest.mark.unit
async def test_readiness_endpoint_db_unhealthy(async_client: AsyncClient) -> None:
    """Verify that /health/ready returns 503 when the database fails."""
    with (
        patch("app.api.routes.health.check_db_health", new_callable=AsyncMock) as mock_db,
        patch("app.api.routes.health.check_redis_health", new_callable=AsyncMock) as mock_redis,
    ):
        mock_db.return_value = (False, "Database connectivity error")
        mock_redis.return_value = (True, "healthy")

        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "connectivity error" in data["components"]["database"]
        assert data["components"]["redis"] == "healthy"


@pytest.mark.unit
async def test_readiness_endpoint_redis_unhealthy(async_client: AsyncClient) -> None:
    """Verify that /health/ready returns 503 when Redis fails."""
    with (
        patch("app.api.routes.health.check_db_health", new_callable=AsyncMock) as mock_db,
        patch("app.api.routes.health.check_redis_health", new_callable=AsyncMock) as mock_redis,
    ):
        mock_db.return_value = (True, "healthy")
        mock_redis.return_value = (False, "Redis connection timed out")

        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["database"] == "healthy"
        assert "timed out" in data["components"]["redis"]
