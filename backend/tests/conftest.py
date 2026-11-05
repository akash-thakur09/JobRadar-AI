"""Shared pytest fixtures and test configuration."""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Enforce test environment before loading application settings
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")
if "DATABASE_URL" not in os.environ:
    from app.core.config import get_settings

    os.environ["DATABASE_URL"] = get_settings().database_url
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_settings_cache() -> None:
    """Clear settings cache before each test run."""
    get_settings.cache_clear()


@pytest.fixture
def app():
    """Create test application instance."""
    return create_app()


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client for API endpoint testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
