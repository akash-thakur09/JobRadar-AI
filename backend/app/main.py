"""FastAPI application factory, lifespan management, and global middleware."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.middleware import CorrelationIdMiddleware
from app.api.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import close_db, init_db
from app.infrastructure.redis import close_redis, init_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager handling startup and shutdown events."""
    settings = get_settings()

    # 1. Startup: Initialize logging
    configure_logging(
        log_level=settings.log_level,
        is_production=settings.is_production,
        environment=settings.app_env,
    )
    logger.info(
        "Starting %s [version=%s, env=%s, debug=%s]",
        settings.app_name,
        __version__,
        settings.app_env,
        settings.debug,
    )

    # 2. Startup: Initialize connection pools
    try:
        await init_db()
        await init_redis()
        logger.info("Core infrastructure pools initialized successfully.")
    except Exception as exc:
        logger.warning(
            "Non-fatal infrastructure initialization warning: %s. Application will continue starting.",
            exc,
        )

    yield

    # 3. Shutdown: Clean up connection pools
    logger.info("Initiating graceful shutdown...")
    await close_redis()
    await close_db()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered Job Intelligence Platform Backend API",
        version=__version__,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Register CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Correlation ID Middleware
    app.add_middleware(CorrelationIdMiddleware)

    # Register centralized RFC 7807 exception handlers
    register_exception_handlers(app)

    # Register API v1 master router
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        """Redirect root requests to the interactive API documentation."""
        return RedirectResponse(url="/docs")

    return app


# Application singleton
app = create_app()
