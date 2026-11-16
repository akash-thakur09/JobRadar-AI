"""FastAPI endpoints for Pipeline Runs and Orchestration Monitoring."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.schemas import (
    PipelineRunCancelResponse,
    PipelineRunCreateRequest,
    PipelineRunListResponse,
    PipelineRunRead,
)
from app.modules.pipeline.service import PipelineOrchestrationService, get_pipeline_service

router = APIRouter(prefix="/pipeline-runs", tags=["Pipeline Orchestration"])


@router.post(
    "",
    response_model=PipelineRunRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a new pipeline run",
    description=(
        "Initiates an asynchronous pipeline run coordinating job discovery, canonicalization, "
        "matching, tailoring, and notifications. Returns 202 Accepted with PENDING run state."
    ),
    responses={
        202: {"description": "Pipeline run successfully accepted and enqueued."},
        404: {"description": "Candidate profile not found."},
        409: {"description": "An active pipeline run already exists for this candidate."},
        422: {"description": "Validation error in request payload."},
    },
)
async def start_pipeline_run(
    request: PipelineRunCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    service: PipelineOrchestrationService = Depends(get_pipeline_service),
) -> PipelineRunRead:
    """Start and enqueue a new pipeline orchestration run."""
    run = await service.start_pipeline_run(
        session=session,
        candidate_profile_id=request.candidate_profile_id,
        trigger_type=request.trigger_type,
        metadata=request.metadata,
    )
    return await service.get_pipeline_run(session=session, run_id=run.id)


@router.get(
    "",
    response_model=PipelineRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List pipeline runs",
    description="Retrieve paginated pipeline runs with optional candidate, status, and trigger filters.",
)
async def list_pipeline_runs(
    candidate_profile_id: uuid.UUID | None = Query(
        None, description="Filter by candidate profile ID"
    ),
    status_filter: PipelineRunStatusEnum | None = Query(
        None, alias="status", description="Filter by run status"
    ),
    trigger_type: PipelineTriggerTypeEnum | None = Query(
        None, description="Filter by trigger type"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    service: PipelineOrchestrationService = Depends(get_pipeline_service),
) -> PipelineRunListResponse:
    """Fetch paginated pipeline run summaries."""
    return await service.list_pipeline_runs(
        session=session,
        candidate_profile_id=candidate_profile_id,
        status=status_filter,
        trigger_type=trigger_type,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{pipeline_run_id}",
    response_model=PipelineRunRead,
    status_code=status.HTTP_200_OK,
    summary="Get pipeline run details",
    description="Fetch full operational metrics and lifecycle state for a specific pipeline run.",
    responses={
        200: {"description": "Pipeline run details found."},
        404: {"description": "Pipeline run not found."},
        422: {"description": "Invalid UUID format."},
    },
)
async def get_pipeline_run(
    pipeline_run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: PipelineOrchestrationService = Depends(get_pipeline_service),
) -> PipelineRunRead:
    """Fetch complete detail representation of a pipeline run."""
    return await service.get_pipeline_run(session=session, run_id=pipeline_run_id)


@router.post(
    "/{pipeline_run_id}/cancel",
    response_model=PipelineRunCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a pipeline run",
    description="Cancel an active (PENDING or RUNNING) pipeline run.",
    responses={
        200: {"description": "Pipeline run successfully cancelled."},
        404: {"description": "Pipeline run not found."},
        409: {"description": "Run is already in a terminal state."},
    },
)
async def cancel_pipeline_run(
    pipeline_run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: PipelineOrchestrationService = Depends(get_pipeline_service),
) -> PipelineRunCancelResponse:
    """Cancel a non-terminal pipeline run."""
    cancelled = await service.cancel_pipeline_run(
        session=session,
        run_id=pipeline_run_id,
        reason="Cancelled via API request",
    )
    return PipelineRunCancelResponse(
        pipeline_run_id=cancelled.id,
        status=cancelled.status,
        message=f"Pipeline run '{pipeline_run_id}' has been cancelled.",
    )
