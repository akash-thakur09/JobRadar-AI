"""Domain service orchestrating Job Sources and Discovery executions."""

import logging
import math
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainException, EntityAlreadyExistsError, EntityNotFoundError
from app.modules.discovery.adapters.registry import get_adapter_for_source_type
from app.modules.discovery.models import DiscoveryRun, DiscoveryRunStatusEnum, JobSource
from app.modules.discovery.repository import DiscoveryRepository
from app.modules.discovery.schemas import (
    DiscoveryRunResponse,
    DiscoveryRunSummary,
    JobSourceCreateRequest,
    JobSourceResponse,
    JobSourceUpdateRequest,
    PaginatedResponse,
    PaginationMetadata,
    RawJobRecordResponse,
)
from app.modules.discovery.tasks import discover_source_jobs_task

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service handling job source configuration, validation, and discovery dispatch."""

    def __init__(self, repository: DiscoveryRepository | None = None) -> None:
        self.repository = repository or DiscoveryRepository()

    # =========================================================================
    # Job Source Management
    # =========================================================================

    async def create_source(
        self, session: AsyncSession, request: JobSourceCreateRequest
    ) -> JobSourceResponse:
        """Register a new job source after validating adapter parameters and unique constraints."""
        # 1. Check name uniqueness
        existing = await self.repository.get_source_by_name(session, request.name)
        if existing is not None:
            raise EntityAlreadyExistsError("JobSource", request.name)

        # 2. Validate configuration against source adapter
        adapter = get_adapter_for_source_type(request.source_type)
        adapter.validate_configuration(request.configuration)

        # 3. Persist record
        source_data = request.model_dump()
        source = await self.repository.create_source(session, source_data)
        await session.commit()

        logger.info(f"Registered new job source '{source.name}' ({source.id}).")
        return self._to_source_response(source)

    async def get_source(self, session: AsyncSession, source_id: uuid.UUID) -> JobSourceResponse:
        """Fetch a job source by primary key with its latest execution run."""
        source = await self.repository.get_source_by_id(session, source_id)
        if source is None:
            raise EntityNotFoundError("JobSource", source_id)

        latest_run = await self.repository.get_latest_run_for_source(session, source.id)
        return self._to_source_response(source, latest_run)

    async def list_sources(
        self, session: AsyncSession, is_enabled: bool | None = None
    ) -> list[JobSourceResponse]:
        """List all registered job sources."""
        sources = await self.repository.list_sources(session, is_enabled=is_enabled)
        responses: list[JobSourceResponse] = []
        for src in sources:
            latest_run = await self.repository.get_latest_run_for_source(session, src.id)
            responses.append(self._to_source_response(src, latest_run))
        return responses

    async def update_source(
        self,
        session: AsyncSession,
        source_id: uuid.UUID,
        request: JobSourceUpdateRequest,
    ) -> JobSourceResponse:
        """Apply partial updates to a job source after validating parameters."""
        source = await self.repository.get_source_by_id(session, source_id)
        if source is None:
            raise EntityNotFoundError("JobSource", source_id)

        update_data = request.model_dump(exclude_unset=True)

        # Name collision check
        if "name" in update_data and update_data["name"] != source.name:
            existing = await self.repository.get_source_by_name(session, update_data["name"])
            if existing is not None and existing.id != source.id:
                raise EntityAlreadyExistsError("JobSource", update_data["name"])

        # Configuration validation
        if "configuration" in update_data and update_data["configuration"] is not None:
            adapter = get_adapter_for_source_type(source.source_type)
            adapter.validate_configuration(update_data["configuration"])

        updated_source = await self.repository.update_source(session, source, update_data)
        await session.commit()

        latest_run = await self.repository.get_latest_run_for_source(session, updated_source.id)
        return self._to_source_response(updated_source, latest_run)

    # =========================================================================
    # Discovery Triggers & Execution History
    # =========================================================================

    async def trigger_discovery_for_source(
        self, session: AsyncSession, source_id: uuid.UUID
    ) -> DiscoveryRunResponse:
        """Trigger an immediate asynchronous discovery run for a specific job source."""
        source = await self.repository.get_source_by_id(session, source_id)
        if source is None:
            raise EntityNotFoundError("JobSource", source_id)

        if not source.is_enabled:
            raise DomainException(
                f"Job source '{source.name}' is currently disabled. Enable the source before triggering discovery.",
                status_code=400,
                error_type="source-disabled",
            )

        # Validate adapter configuration before queuing
        adapter = get_adapter_for_source_type(source.source_type)
        adapter.validate_configuration(source.configuration)

        run = await self.repository.create_discovery_run(
            session=session,
            job_source_id=source.id,
            status=DiscoveryRunStatusEnum.PENDING,
        )
        await session.commit()

        # Enqueue background Celery task
        discover_source_jobs_task.delay(str(source.id))
        logger.info(
            f"Dispatched background discovery task for source '{source.name}' (run {run.id})."
        )

        return DiscoveryRunResponse.model_validate(run)

    async def trigger_discovery(
        self, session: AsyncSession, source_id: uuid.UUID | None = None
    ) -> list[DiscoveryRunResponse]:
        """Trigger discovery for a single source or all enabled sources."""
        if source_id is not None:
            run_resp = await self.trigger_discovery_for_source(session, source_id)
            return [run_resp]

        enabled_sources = await self.repository.list_sources(session, is_enabled=True)
        if not enabled_sources:
            return []

        runs: list[DiscoveryRunResponse] = []
        for src in enabled_sources:
            try:
                run_resp = await self.trigger_discovery_for_source(session, src.id)
                runs.append(run_resp)
            except Exception as exc:
                logger.error(f"Failed to dispatch discovery for source '{src.name}': {exc}")

        return runs

    async def list_discovery_runs(
        self,
        session: AsyncSession,
        source_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[DiscoveryRunResponse]:
        """Fetch paginated discovery runs."""
        runs, total_items = await self.repository.list_discovery_runs(
            session=session,
            job_source_id=source_id,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

        return PaginatedResponse[DiscoveryRunResponse](
            items=[DiscoveryRunResponse.model_validate(r) for r in runs],
            pagination=PaginationMetadata(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    async def get_discovery_run(
        self, session: AsyncSession, run_id: uuid.UUID
    ) -> DiscoveryRunResponse:
        """Fetch single discovery run details."""
        run = await self.repository.get_discovery_run_by_id(session, run_id)
        if run is None:
            raise EntityNotFoundError("DiscoveryRun", run_id)
        return DiscoveryRunResponse.model_validate(run)

    async def list_raw_job_records(
        self,
        session: AsyncSession,
        source_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[RawJobRecordResponse]:
        """Fetch paginated raw job ingestion records."""
        records, total_items = await self.repository.list_job_source_records(
            session=session,
            job_source_id=source_id,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

        return PaginatedResponse[RawJobRecordResponse](
            items=[RawJobRecordResponse.model_validate(r) for r in records],
            pagination=PaginationMetadata(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _to_source_response(
        self, source: JobSource, latest_run: DiscoveryRun | None = None
    ) -> JobSourceResponse:
        """Convert JobSource model and optional run to DTO."""
        run_summary = None
        if latest_run is not None:
            run_summary = DiscoveryRunSummary.model_validate(latest_run)

        return JobSourceResponse(
            id=source.id,
            name=source.name,
            source_type=source.source_type,
            base_url=source.base_url,
            is_enabled=source.is_enabled,
            polling_interval_minutes=source.polling_interval_minutes,
            configuration=source.configuration,
            created_at=source.created_at,
            updated_at=source.updated_at,
            latest_run=run_summary,
        )


def get_discovery_service() -> DiscoveryService:
    """Dependency provider for DiscoveryService."""
    return DiscoveryService()
