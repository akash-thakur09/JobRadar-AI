"""REST API endpoints for Master Resume management and versioning."""

import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.resumes.schemas import (
    MasterResumeDetailResponse,
    MasterResumeSummary,
    PaginatedResponse,
    ResumeVersionResponse,
    ResumeVersionSummary,
)
from app.modules.resumes.service import ResumeService, get_resume_service

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.get(
    "",
    response_model=PaginatedResponse[MasterResumeSummary],
    status_code=status.HTTP_200_OK,
    summary="List master resumes",
    description="Retrieve paginated list of all uploaded master resumes for the active candidate.",
)
async def list_resumes(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    service: ResumeService = Depends(get_resume_service),
) -> PaginatedResponse[MasterResumeSummary]:
    """List uploaded master resumes with pagination envelope."""
    items, pagination = await service.list_resumes(session, page=page, page_size=page_size)

    summaries = []
    for item in items:
        latest = item.versions[0] if item.versions else None
        summaries.append(
            MasterResumeSummary(
                id=item.id,
                candidate_profile_id=item.candidate_profile_id,
                original_filename=item.original_filename,
                mime_type=item.mime_type,
                file_size_bytes=item.file_size_bytes,
                checksum_sha256=item.checksum_sha256,
                is_active=item.is_active,
                created_at=item.created_at,
                updated_at=item.updated_at,
                latest_version=ResumeVersionSummary.model_validate(latest) if latest else None,
            )
        )

    return PaginatedResponse(items=summaries, pagination=pagination)


@router.post(
    "/upload",
    response_model=MasterResumeDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload master resume",
    description="Upload a new master resume file (PDF or DOCX), validate integrity, and queue structural parsing.",
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume binary file (PDF or DOCX)"),
    session: AsyncSession = Depends(get_db_session),
    service: ResumeService = Depends(get_resume_service),
) -> MasterResumeDetailResponse:
    """Handle resume multipart upload and trigger background parsing."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required for uploaded resume.",
        )

    content = await file.read()
    try:
        resume, version = await service.upload_resume(
            session=session,
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return MasterResumeDetailResponse(
        id=resume.id,
        candidate_profile_id=resume.candidate_profile_id,
        original_filename=resume.original_filename,
        storage_key=resume.storage_key,
        mime_type=resume.mime_type,
        file_size_bytes=resume.file_size_bytes,
        checksum_sha256=resume.checksum_sha256,
        is_active=resume.is_active,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        active_version=ResumeVersionResponse.model_validate(version),
        versions=[ResumeVersionSummary.model_validate(version)],
    )


@router.get(
    "/{resume_id}",
    response_model=MasterResumeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get master resume",
    description="Retrieve metadata, active version, and version history for a specific master resume.",
)
async def get_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: ResumeService = Depends(get_resume_service),
) -> MasterResumeDetailResponse:
    """Fetch complete master resume detail by ID."""
    resume = await service.get_resume(session, resume_id)
    latest_version = resume.versions[0] if resume.versions else None

    return MasterResumeDetailResponse(
        id=resume.id,
        candidate_profile_id=resume.candidate_profile_id,
        original_filename=resume.original_filename,
        storage_key=resume.storage_key,
        mime_type=resume.mime_type,
        file_size_bytes=resume.file_size_bytes,
        checksum_sha256=resume.checksum_sha256,
        is_active=resume.is_active,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        active_version=(
            ResumeVersionResponse.model_validate(latest_version) if latest_version else None
        ),
        versions=[ResumeVersionSummary.model_validate(v) for v in resume.versions],
    )


@router.post(
    "/{resume_id}/activate",
    response_model=MasterResumeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate master resume",
    description="Designate this resume as the active master resume for job matching and tailoring.",
)
async def activate_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: ResumeService = Depends(get_resume_service),
) -> MasterResumeDetailResponse:
    """Set resume as active and deactivate all other resumes for the candidate."""
    resume = await service.activate_resume(session, resume_id)
    latest_version = resume.versions[0] if resume.versions else None

    return MasterResumeDetailResponse(
        id=resume.id,
        candidate_profile_id=resume.candidate_profile_id,
        original_filename=resume.original_filename,
        storage_key=resume.storage_key,
        mime_type=resume.mime_type,
        file_size_bytes=resume.file_size_bytes,
        checksum_sha256=resume.checksum_sha256,
        is_active=resume.is_active,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        active_version=(
            ResumeVersionResponse.model_validate(latest_version) if latest_version else None
        ),
        versions=[ResumeVersionSummary.model_validate(v) for v in resume.versions],
    )


@router.get(
    "/{resume_id}/versions",
    response_model=list[ResumeVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="List resume versions",
    description="List all parsed versions and extraction histories for a master resume.",
)
async def list_resume_versions(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: ResumeService = Depends(get_resume_service),
) -> list[ResumeVersionResponse]:
    """List all versions for a master resume."""
    versions = await service.list_versions(session, resume_id)
    return [ResumeVersionResponse.model_validate(v) for v in versions]


@router.get(
    "/{resume_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download resume binary",
    description="Download the original uploaded resume file binary (PDF or DOCX).",
)
async def download_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: ResumeService = Depends(get_resume_service),
) -> Response:
    """Download the original resume file binary."""
    content_bytes, mime_type, filename = await service.download_resume_file(session, resume_id)
    return Response(
        content=content_bytes,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{resume_id}/content",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get structured resume content",
    description="Retrieve structured JSON content (summary, experience, skills, education) of the active version.",
)
async def get_resume_content(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: ResumeService = Depends(get_resume_service),
) -> dict[str, Any]:
    """Return the parsed structured JSON content for the resume."""
    return await service.get_resume_content(session, resume_id)
