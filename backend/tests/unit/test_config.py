"""Unit tests for configuration management."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, _parse_cors_origins


@pytest.mark.unit
def test_default_settings() -> None:
    """Verify default settings configuration."""
    settings = Settings()
    assert settings.app_name == "JobRadar AI"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.port == 8000
    assert "postgresql+asyncpg://" in settings.database_url
    assert "redis://" in settings.redis_url


@pytest.mark.unit
def test_environment_helpers() -> None:
    """Verify is_production and is_testing properties."""
    dev_settings = Settings(app_env="development")
    assert not dev_settings.is_production
    assert not dev_settings.is_testing

    prod_settings = Settings(app_env="production")
    assert prod_settings.is_production
    assert not prod_settings.is_testing

    test_settings = Settings(app_env="test")
    assert not test_settings.is_production
    assert test_settings.is_testing


@pytest.mark.unit
def test_cors_origins_parsing() -> None:
    """Verify parsing of CORS origins in string and JSON list formats."""
    # List format
    res1 = _parse_cors_origins(["http://localhost:3000", "http://localhost:8000"])
    assert res1 == ["http://localhost:3000", "http://localhost:8000"]

    # Comma-separated string format
    res2 = _parse_cors_origins("http://example.com, https://app.example.com")
    assert res2 == ["http://example.com", "https://app.example.com"]

    # JSON array string format
    res3 = _parse_cors_origins('["https://jobradar.ai", "http://localhost:5173"]')
    assert res3 == ["https://jobradar.ai", "http://localhost:5173"]


@pytest.mark.unit
def test_invalid_app_env() -> None:
    """Verify that an invalid app_env raises a validation error."""
    with pytest.raises(ValidationError):
        Settings(app_env="invalid_environment")  # type: ignore[arg-type]
