"""Async SQLAlchemy session factory and connection lifecycle."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global engine and sessionmaker references
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Return the initialized async database engine."""
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        if settings.app_env == "test":
            _async_engine = create_async_engine(
                settings.database_url,
                echo=settings.debug and not settings.is_production,
                poolclass=NullPool,
            )
        else:
            _async_engine = create_async_engine(
                settings.database_url,
                echo=settings.debug and not settings.is_production,
                poolclass=QueuePool,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_timeout=settings.database_pool_timeout,
                pool_pre_ping=True,
            )
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _async_session_factory


async def init_db() -> None:
    """Initialize database engine connections at application startup."""
    logger.info("Initializing PostgreSQL async database connection pool...")
    get_async_engine()


async def close_db() -> None:
    """Dispose of the database engine and connection pool on shutdown."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        logger.info("Closing PostgreSQL database engine and active connections...")
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding an isolated async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
