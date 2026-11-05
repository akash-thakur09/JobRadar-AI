"""REST API endpoints for Canonical Jobs and Processing Operations."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.jobs.models import JobStatusEnum
from app.modules.jobs.schemas import (
    JobDetailResponse,
    JobProcessPendingResponse,
    JobSourceRecordResponse,
    JobSummaryResponse,
    PaginatedResponse,
)
from app.modules.jobs.service import JobService, get_job_service

jobs_router = APIRouter(prefix="/jobs", tags=["Canonical Jobs"])


@jobs_router.get(
    "",
    response_model=PaginatedResponse[JobSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List canonical jobs",
    description="Retrieve paginated canonical job opportunities with optional filtering and search.",
)
async def list_jobs(
    search: str | None = Query(default=None, description="Search company name or position title"),
    status: JobStatusEnum | None = Query(
        default=None, description="Filter by canonical job status"
    ),
    workplace_type: WorkplaceTypeEnum | None = Query(
        default=None, description="Filter by workplace type"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    session: AsyncSession = Depends(get_db_session),
    service: JobService = Depends(get_job_service),
) -> PaginatedResponse[JobSummaryResponse]:
    return await service.list_jobs(
        session=session,
        search=search,
        status=status,
        workplace_type=workplace_type,
        page=page,
        page_size=page_size,
    )


@jobs_router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get canonical job details",
    description="Retrieve detailed canonical job record including clean description text and discovery source provenance.",
)
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: JobService = Depends(get_job_service),
) -> JobDetailResponse:
    return await service.get_job(session=session, job_id=job_id)


@jobs_router.get(
    "/{job_id}/sources",
    response_model=list[JobSourceRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="Get linked source records for a job",
    description="List all raw discovered upstream postings and audit history linked to a canonical job.",
)
async def get_job_sources(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: JobService = Depends(get_job_service),
) -> list[JobSourceRecordResponse]:
    return await service.get_job_sources(session=session, job_id=job_id)


@jobs_router.post(
    "/process-pending",
    response_model=JobProcessPendingResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger processing of pending raw job postings",
    description="Process uncanonicalized raw source records into deduplicated canonical jobs.",
)
async def process_pending_jobs(
    batch_size: int = Query(
        default=100, ge=1, le=500, description="Maximum number of records to process"
    ),
    session: AsyncSession = Depends(get_db_session),
    service: JobService = Depends(get_job_service),
) -> JobProcessPendingResponse:
    processed_count = await service.process_pending_records(session=session, batch_size=batch_size)
    return JobProcessPendingResponse(
        queued_count=processed_count,
        processed_count=processed_count,
        message=f"Successfully processed {processed_count} pending job source records.",
    )
