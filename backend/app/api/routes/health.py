"""Health and readiness monitoring endpoints."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app import __version__
from app.core.config import get_settings
from app.database.health import check_db_health
from app.infrastructure.redis import check_redis_health

router = APIRouter(prefix="/health", tags=["Health & Monitoring"])


class LivenessResponse(BaseModel):
    """Response model for process liveness check."""

    status: str = Field(default="healthy", description="Application liveness status")
    timestamp: str = Field(description="Current UTC timestamp")
    environment: str = Field(description="Active runtime environment")
    version: str = Field(description="Application version")


class ReadinessResponse(BaseModel):
    """Response model for infrastructure readiness check."""

    status: str = Field(description="Overall platform readiness status")
    timestamp: str = Field(description="Current UTC timestamp")
    components: dict[str, str] = Field(description="Detailed status per dependency")


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Liveness Check",
    description="Confirms that the FastAPI application process is running. Does not verify external infrastructure.",
)
async def check_liveness() -> dict[str, Any]:
    """Return process liveness confirmation."""
    settings = get_settings()
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.app_env,
        "version": __version__,
    }


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "All infrastructure dependencies are healthy and reachable."},
        503: {"description": "One or more infrastructure dependencies are unhealthy."},
    },
    summary="Infrastructure Readiness Check",
    description="Verifies that required dependencies (PostgreSQL and Redis) are reachable.",
)
async def check_readiness(response: Response) -> dict[str, Any]:
    """Verify PostgreSQL and Redis reachability."""
    # Run infrastructure checks concurrently
    db_result, redis_result = await asyncio.gather(
        check_db_health(),
        check_redis_health(),
    )

    db_healthy, db_detail = db_result
    redis_healthy, redis_detail = redis_result

    is_overall_healthy = db_healthy and redis_healthy
    if not is_overall_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_overall_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "components": {
            "database": db_detail,
            "redis": redis_detail,
        },
    }
