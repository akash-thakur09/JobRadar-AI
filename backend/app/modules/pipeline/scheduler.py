"""Standalone and distributed scheduler architecture for periodic pipeline orchestration."""

import asyncio
import logging
import signal
from datetime import UTC, datetime
from typing import Any

from app.core.runtime_settings import get_runtime_settings
from app.infrastructure.redis import get_redis
from app.modules.pipeline.tasks import schedule_candidate_pipeline_runs_task

logger = logging.getLogger(__name__)
SCHEDULER_LEADER_LOCK = "lock:pipeline_scheduler:leader"


class StandalonePipelineScheduler:
    """Safe, single-leader periodic scheduler preventing multi-worker execution collisions.

    Features:
    - Distributed Leader Election via Redis lock ('lock:pipeline_scheduler:leader').
    - Only the active leader triggers candidate scheduling passes.
    - Graceful degradation if Redis is unavailable in local dev.
    - Clean signal handling for SIGINT and SIGTERM.
    """

    def __init__(self, check_interval_seconds: float = 60.0) -> None:
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._redis_client = None

    @property
    def is_enabled(self) -> bool:
        """Return True if automated scheduling is enabled in configuration."""
        return get_runtime_settings().pipeline_scheduler_enabled

    async def run(self) -> None:
        """Start the periodic scheduling loop until stopped."""
        self._running = True
        logger.info(
            f"StandalonePipelineScheduler started (enabled={self.is_enabled}, interval={self.check_interval_seconds}s)"
        )

        while self._running:
            try:
                if self.is_enabled:
                    await self._execute_tick()
                else:
                    logger.debug("Scheduler tick: scheduling disabled via settings.")
            except Exception as tick_err:
                logger.error(f"Error during scheduler tick: {tick_err}", exc_info=True)

            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

        logger.info("StandalonePipelineScheduler stopped gracefully.")

    async def _execute_tick(self) -> dict[str, Any]:
        """Execute one scheduler tick with single-leader election."""
        redis = get_redis()
        lock_ttl = max(self.check_interval_seconds * 2, 60.0)

        lock = None
        is_leader = False

        try:
            lock = redis.lock(SCHEDULER_LEADER_LOCK, timeout=lock_ttl, blocking_timeout=2.0)
            is_leader = await lock.acquire()
        except Exception as redis_exc:
            logger.warning(
                f"Redis leader election error: {redis_exc}; assuming local single-node leadership."
            )
            is_leader = True

        if not is_leader:
            logger.debug("Scheduler standby: another instance holds leader lock.")
            return {"status": "STANDBY"}

        try:
            logger.info("Scheduler leader: initiating candidate discovery schedule check.")
            # Trigger Celery periodic task asynchronously
            schedule_candidate_pipeline_runs_task.delay()
            return {"status": "TRIGGERED", "timestamp": datetime.now(UTC).isoformat()}
        finally:
            if lock is not None and is_leader:
                try:
                    await lock.release()
                except Exception:
                    pass

    def stop(self) -> None:
        """Signal the scheduler to terminate."""
        self._running = False


async def run_scheduler_daemon() -> None:
    """Entry point for running the scheduler process from the command line."""
    scheduler = StandalonePipelineScheduler()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, scheduler.stop)
        except NotImplementedError:
            # Signal handlers not implemented on Windows event loop for add_signal_handler
            pass

    await scheduler.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_scheduler_daemon())
