"""REST API endpoints for Candidate-Job Matching and Scoring."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.jobs.schemas import PaginatedResponse
from app.modules.matching.models import EligibilityStatusEnum
from app.modules.matching.schemas import (
    JobMatchDetailResponse,
    JobMatchReevaluateResponse,
    JobMatchSummaryResponse,
)
from app.modules.matching.semantic_service import (
    SemanticAnalysisService,
    get_semantic_service,
)
from app.modules.matching.service import MatchingService, get_matching_service

matches_router = APIRouter(prefix="/matches", tags=["Matching & Insights"])


@matches_router.get(
    "",
    response_model=PaginatedResponse[JobMatchSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List evaluated job matches",
    description="Retrieve paginated candidate-job match evaluations sorted by relevance score descending.",
)
async def list_matches(
    min_score: Decimal | None = Query(
        default=None,
        ge=0.0,
        le=100.0,
        description="Filter by minimum final score",
    ),
    eligibility: EligibilityStatusEnum | None = Query(
        default=None,
        description="Filter by eligibility outcome",
    ),
    candidate_profile_id: uuid.UUID | None = Query(
        default=None,
        description="Optional candidate profile identifier (defaults to primary)",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    service: MatchingService = Depends(get_matching_service),
) -> PaginatedResponse[JobMatchSummaryResponse]:
    return await service.list_matches(
        session=session,
        candidate_profile_id=candidate_profile_id,
        min_score=min_score,
        eligibility_status=eligibility,
        page=page,
        page_size=page_size,
    )


@matches_router.get(
    "/{match_id}",
    response_model=JobMatchDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed match explanation and scoring breakdown",
    description="Retrieve transparent line-item mathematical scores and boolean eligibility checks.",
)
async def get_match_detail(
    match_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: MatchingService = Depends(get_matching_service),
) -> JobMatchDetailResponse:
    return await service.get_match(session=session, match_id=match_id)


@matches_router.post(
    "/{job_id}/re-evaluate",
    response_model=JobMatchReevaluateResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-evaluate candidate-job matching",
    description="Re-run Layer 1 eligibility and Layer 2 deterministic scoring against latest candidate profile.",
)
async def reevaluate_job_match(
    job_id: uuid.UUID,
    candidate_profile_id: uuid.UUID | None = Query(
        default=None,
        description="Optional candidate profile identifier (defaults to primary)",
    ),
    session: AsyncSession = Depends(get_db_session),
    service: MatchingService = Depends(get_matching_service),
) -> JobMatchReevaluateResponse:
    match = await service.evaluate_job_for_candidate(
        session=session,
        job_id=job_id,
        candidate_profile_id=candidate_profile_id,
    )
    await session.commit()

    detail = await service.get_match(session=session, match_id=match.id)

    return JobMatchReevaluateResponse(
        job_id=job_id,
        candidate_profile_id=match.candidate_profile_id,
        match=detail,
        message="Successfully evaluated candidate-job match.",
    )


@matches_router.post(
    "/{match_id}/semantic-analysis",
    response_model=JobMatchDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Layer 3 LLM Semantic Analysis",
    description="Evaluate contextual alignment and transferable skills via LLM for a qualified match.",
)
async def trigger_semantic_analysis(
    match_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    matching_service: MatchingService = Depends(get_matching_service),
    semantic_service: SemanticAnalysisService = Depends(get_semantic_service),
) -> JobMatchDetailResponse:
    await semantic_service.evaluate_semantic_match(session=session, match_id=match_id)
    await session.commit()
    return await matching_service.get_match(session=session, match_id=match_id)
