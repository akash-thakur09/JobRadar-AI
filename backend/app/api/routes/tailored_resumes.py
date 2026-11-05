"""REST API endpoints for Tailored Resumes and PDF generation."""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.candidate.service import CandidateService, get_candidate_service
from app.modules.resumes.schemas import PaginatedResponse
from app.modules.tailoring.schemas import (
    TailoredResumeDetailResponse,
    TailoredResumeSummaryResponse,
    TailorResumeRequest,
)
from app.modules.tailoring.service import TailoringService, get_tailoring_service

router = APIRouter(prefix="/tailored-resumes", tags=["Tailored Resumes"])


@router.post(
    "",
    response_model=TailoredResumeSummaryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate resume tailoring",
    description="Enqueue truthful resume tailoring pipeline for a qualified candidate-job match.",
)
async def create_tailored_resume(
    request: TailorResumeRequest,
    session: AsyncSession = Depends(get_db_session),
    service: TailoringService = Depends(get_tailoring_service),
) -> TailoredResumeSummaryResponse:
    """Initiate or retry resume tailoring for a qualified job match."""
    record = await service.request_tailoring(session=session, request=request)
    await session.commit()
    return TailoredResumeSummaryResponse.model_validate(record)


@router.get(
    "/{id}",
    response_model=TailoredResumeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get tailored resume details",
    description="Retrieve generation status, tailored JSON content, and claim validation audit trail.",
)
async def get_tailored_resume(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TailoringService = Depends(get_tailoring_service),
) -> TailoredResumeDetailResponse:
    """Retrieve full details of a tailored resume record."""
    record = await service.get_tailored_resume(session=session, tailored_resume_id=id)
    return TailoredResumeDetailResponse.model_validate(record)


@router.get(
    "/{id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download tailored resume PDF",
    description="Download the compiled ATS-optimized PDF artifact.",
)
async def download_tailored_resume(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: TailoringService = Depends(get_tailoring_service),
) -> Response:
    """Stream or download the compiled PDF binary artifact."""
    pdf_bytes, file_name, mime_type = await service.download_tailored_pdf(
        session=session,
        tailored_resume_id=id,
    )
    return Response(
        content=pdf_bytes,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get(
    "",
    response_model=PaginatedResponse[TailoredResumeSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List tailored resumes",
    description="Retrieve paginated tailored resumes for the candidate.",
)
async def list_tailored_resumes(
    candidate_profile_id: uuid.UUID | None = Query(
        default=None,
        description="Optional candidate profile identifier (defaults to primary)",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    service: TailoringService = Depends(get_tailoring_service),
    candidate_service: CandidateService = Depends(get_candidate_service),
) -> PaginatedResponse[TailoredResumeSummaryResponse]:
    """Retrieve paginated collection of tailored resume summaries."""
    if candidate_profile_id is None:
        profile = await candidate_service.get_profile(session)
        target_profile_id = profile.id
    else:
        target_profile_id = candidate_profile_id

    items, pagination = await service.list_tailored_resumes(
        session=session,
        candidate_profile_id=target_profile_id,
        page=page,
        page_size=page_size,
    )

    summaries = [TailoredResumeSummaryResponse.model_validate(item) for item in items]
    return PaginatedResponse(items=summaries, pagination=pagination)
