"""Unit tests for exception handling, middleware, and RFC 7807 error formatting."""

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.exceptions import AppException, EntityNotFoundError
from app.main import create_app


class DummyPayload(BaseModel):
    required_name: str


@pytest.fixture
def error_test_app():
    """Create test app with custom routes to trigger exceptions."""
    app = create_app()
    test_router = APIRouter()

    @test_router.post("/trigger-validation-error")
    async def trigger_val_error(body: DummyPayload) -> dict[str, str]:
        return {"name": body.required_name}

    @test_router.get("/trigger-app-exception")
    async def trigger_app_exc() -> None:
        raise AppException("Custom app failure", status_code=400, error_type="custom-failure")

    @test_router.get("/trigger-not-found")
    async def trigger_not_found() -> None:
        raise EntityNotFoundError("Job", "job-123")

    @test_router.get("/trigger-server-error")
    async def trigger_server_error() -> None:
        raise RuntimeError("Unexpected boom!")

    app.include_router(test_router)
    return app


@pytest.mark.unit
async def test_root_redirect(async_client: AsyncClient) -> None:
    """Verify that root / redirects to /docs."""
    response = await async_client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


@pytest.mark.unit
async def test_correlation_id_middleware(async_client: AsyncClient) -> None:
    """Verify that X-Correlation-ID is propagated in headers."""
    response = await async_client.get(
        "/api/v1/health/live",
        headers={"X-Correlation-ID": "custom-trace-id-777"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "custom-trace-id-777"


@pytest.mark.unit
async def test_app_exception_handling(error_test_app) -> None:
    """Verify that AppException returns RFC 7807 payload."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/trigger-app-exception")
        assert response.status_code == 400
        assert response.headers["content-type"] == "application/problem+json"
        data = response.json()
        assert data["title"] == "Custom Failure"
        assert data["detail"] == "Custom app failure"
        assert "correlation_id" in data


@pytest.mark.unit
async def test_not_found_exception_handling(error_test_app) -> None:
    """Verify that EntityNotFoundError returns 404 RFC 7807 payload."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/trigger-not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == 404
        assert "Job with identifier 'job-123' was not found" in data["detail"]


@pytest.mark.unit
async def test_validation_exception_handling(error_test_app) -> None:
    """Verify that validation errors return 422 RFC 7807 payload with invalid_params."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/trigger-validation-error", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["title"] == "Validation Error"
        assert data["status"] == 422
        assert "invalid_params" in data
        assert len(data["invalid_params"]) > 0


@pytest.mark.unit
async def test_unhandled_exception_handling(error_test_app) -> None:
    """Verify that unhandled server exceptions return safe 500 RFC 7807 payload."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/trigger-server-error")
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == 500
        assert data["title"] == "Internal Server Error"
        assert "correlation_id" in data
        assert "Unexpected boom" not in data["detail"]  # Doesn't leak internal traces
