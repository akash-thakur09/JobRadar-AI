"""Run Celery coroutines with resources owned by the task's event loop."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from app.database.session import close_db
from app.infrastructure.redis import close_redis

logger = logging.getLogger(__name__)


def run_async_task[Result](task: Coroutine[Any, Any, Result]) -> Result:
    async def execute() -> Result:
        try:
            return await task
        finally:
            for close in (close_redis, close_db):
                try:
                    await close()
                except Exception:
                    logger.exception("Failed to close worker resource %s", close.__name__)

    return asyncio.run(execute())
