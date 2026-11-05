"""Database health check utility."""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


async def check_db_health(
    session: AsyncSession | None = None,
    timeout_seconds: float = 3.0,
) -> tuple[bool, str]:
    """Verify PostgreSQL connectivity and query execution.

    Returns:
        tuple[bool, str]: (is_healthy, status_detail)
    """
    try:

        async def _ping(sess: AsyncSession) -> None:
            await sess.execute(text("SELECT 1;"))

        if session is not None:
            await asyncio.wait_for(_ping(session), timeout=timeout_seconds)
        else:
            session_factory = get_session_factory()
            async with session_factory() as temp_session:
                await asyncio.wait_for(_ping(temp_session), timeout=timeout_seconds)

        return True, "healthy"
    except TimeoutError:
        logger.warning("Database health check timed out after %s seconds", timeout_seconds)
        return False, "Database query timed out"
    except Exception as exc:
        logger.warning("Database health check failed: %s", type(exc).__name__)
        # Sanitize message to ensure no connection strings or credentials leak
        return False, f"Database connectivity error ({type(exc).__name__})"
