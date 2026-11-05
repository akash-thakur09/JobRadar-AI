"""REST API endpoints for Job Discovery Source Configuration and Execution."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.discovery.schemas import (
    DiscoveryRunResponse,
    DiscoveryTriggerRequest,
    JobSourceCreateRequest,
    JobSourceResponse,
    JobSourceUpdateRequest,
    PaginatedResponse,
    RawJobRecordResponse,
)
from app.modules.discovery.service import DiscoveryService, get_discovery_service

discovery_router = APIRouter(prefix="/discovery", tags=["Discovery"])


# =============================================================================
# Job Source Management
# =============================================================================


@discovery_router.get(
    "/sources",
    response_model=list[JobSourceResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered job sources",
    description="Retrieve all configured job boards, ATS portals, and discovery endpoints.",
)
async def list_job_sources(
    is_enabled: bool | None = Query(default=None, description="Filter by enabled status"),
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> list[JobSourceResponse]:
    return await service.list_sources(session, is_enabled=is_enabled)


@discovery_router.post(
    "/sources",
    response_model=JobSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new job discovery source",
    description="Register a new ATS board or company portal after validating source configuration.",
)
async def create_job_source(
    request: JobSourceCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> JobSourceResponse:
    return await service.create_source(session, request)


@discovery_router.get(
    "/sources/{source_id}",
    response_model=JobSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job source details",
    description="Fetch a single job source configuration and its latest execution metrics.",
)
async def get_job_source(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> JobSourceResponse:
    return await service.get_source(session, source_id)


@discovery_router.patch(
    "/sources/{source_id}",
    response_model=JobSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a job source",
    description="Apply partial updates to polling interval, enabled status, or configuration.",
)
async def update_job_source(
    source_id: uuid.UUID,
    request: JobSourceUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> JobSourceResponse:
    return await service.update_source(session, source_id, request)


@discovery_router.put(
    "/sources/{source_id}",
    response_model=JobSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a job source (PUT alias)",
    description="Update job source configuration and polling parameters.",
)
async def put_job_source(
    source_id: uuid.UUID,
    request: JobSourceUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> JobSourceResponse:
    return await service.update_source(session, source_id, request)


# =============================================================================
# Discovery Triggers & Execution Runs
# =============================================================================


@discovery_router.post(
    "/sources/{source_id}/discover",
    response_model=DiscoveryRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger immediate discovery for a job source",
    description="Queue an immediate asynchronous discovery task for the specified job source.",
)
async def trigger_source_discovery(
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryRunResponse:
    return await service.trigger_discovery_for_source(session, source_id)


@discovery_router.post(
    "/trigger",
    response_model=list[DiscoveryRunResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger discovery run",
    description="Trigger immediate discovery for a specific source or all enabled sources.",
)
async def trigger_discovery(
    request: DiscoveryTriggerRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> list[DiscoveryRunResponse]:
    target_id = request.source_id if request else None
    return await service.trigger_discovery(session, source_id=target_id)


@discovery_router.get(
    "/runs",
    response_model=PaginatedResponse[DiscoveryRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List discovery execution history",
    description="Retrieve paginated history of discovery runs, counts, and status.",
)
async def list_discovery_runs(
    source_id: uuid.UUID | None = Query(default=None, description="Filter by job source UUID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> PaginatedResponse[DiscoveryRunResponse]:
    return await service.list_discovery_runs(
        session, source_id=source_id, page=page, page_size=page_size
    )


@discovery_router.get(
    "/runs/{run_id}",
    response_model=DiscoveryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get discovery run details",
    description="Retrieve details, timings, and error diagnostics for a specific run.",
)
async def get_discovery_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoveryRunResponse:
    return await service.get_discovery_run(session, run_id)


# =============================================================================
# Ingested Raw Job Records
# =============================================================================


@discovery_router.get(
    "/records",
    response_model=PaginatedResponse[RawJobRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="List ingested raw job records",
    description="Inspect raw source payloads and checksums persisted prior to normalization.",
)
async def list_raw_job_records(
    source_id: uuid.UUID | None = Query(default=None, description="Filter by job source UUID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    service: DiscoveryService = Depends(get_discovery_service),
) -> PaginatedResponse[RawJobRecordResponse]:
    return await service.list_raw_job_records(
        session, source_id=source_id, page=page, page_size=page_size
    )
