"""Unit tests for ResumeService business logic."""

import hashlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.modules.candidate.models import CandidateProfile
from app.modules.resumes.models import MasterResume, ResumeVersion
from app.modules.resumes.service import ResumeService


@pytest.fixture
def mock_candidate_profile() -> CandidateProfile:
    """Return mock candidate profile."""
    now = datetime.now(UTC)
    return CandidateProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        full_name="Bruce Wayne",
        total_experience_months=60,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_master_resume(mock_candidate_profile: CandidateProfile) -> MasterResume:
    """Return mock master resume."""
    now = datetime.now(UTC)
    return MasterResume(
        id=uuid.uuid4(),
        candidate_profile_id=mock_candidate_profile.id,
        original_filename="resume.pdf",
        storage_key=f"resumes/raw/{mock_candidate_profile.id}/uuid.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        checksum_sha256="abc123sha256fake",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_upload_resume_success(mock_candidate_profile: CandidateProfile) -> None:
    """Verify upload saves binary to storage and persists resume and version."""
    mock_repo = AsyncMock()
    mock_candidate_service = AsyncMock()
    mock_candidate_service.get_profile.return_value = mock_candidate_profile
    mock_storage = AsyncMock()

    content = b"%PDF-1.4 test valid pdf"
    checksum = hashlib.sha256(content).hexdigest()

    mock_repo.get_resume_by_checksum.return_value = None

    resume_id = uuid.uuid4()
    version_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_resume = MasterResume(
        id=resume_id,
        candidate_profile_id=mock_candidate_profile.id,
        original_filename="cv.pdf",
        storage_key=f"resumes/raw/{mock_candidate_profile.id}/file.pdf",
        mime_type="application/pdf",
        file_size_bytes=len(content),
        checksum_sha256=checksum,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    mock_version = ResumeVersion(
        id=version_id,
        master_resume_id=resume_id,
        version_number=1,
        structured_content={},
        checksum_sha256=checksum,
        is_valid=True,
        processing_status="PENDING",
        created_at=now,
        updated_at=now,
    )

    mock_repo.create_resume.return_value = mock_resume
    mock_repo.create_version.return_value = mock_version

    service = ResumeService(
        repository=mock_repo,
        candidate_service=mock_candidate_service,
        storage=mock_storage,
    )

    session = AsyncMock()
    resume, version = await service.upload_resume(
        session=session,
        filename="cv.pdf",
        content=content,
        content_type="application/pdf",
        sync_parse=False,
    )

    assert resume.id == resume_id
    assert version.id == version_id
    mock_storage.save.assert_awaited_once()
    mock_repo.create_resume.assert_awaited_once()
    mock_repo.create_version.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_resume_duplicate_checksum(
    mock_candidate_profile: CandidateProfile, mock_master_resume: MasterResume
) -> None:
    """Verify duplicate upload with identical SHA256 checksum raises EntityAlreadyExistsError."""
    mock_repo = AsyncMock()
    mock_candidate_service = AsyncMock()
    mock_candidate_service.get_profile.return_value = mock_candidate_profile
    mock_storage = AsyncMock()

    content = b"%PDF-1.4 duplicate test content"
    mock_repo.get_resume_by_checksum.return_value = mock_master_resume

    service = ResumeService(
        repository=mock_repo,
        candidate_service=mock_candidate_service,
        storage=mock_storage,
    )

    session = AsyncMock()
    with pytest.raises(EntityAlreadyExistsError) as exc_info:
        await service.upload_resume(
            session=session,
            filename="cv.pdf",
            content=content,
            content_type="application/pdf",
        )

    assert "identical content" in str(exc_info.value)
    mock_storage.save.assert_not_called()
    mock_repo.create_resume.assert_not_called()


@pytest.mark.asyncio
async def test_list_resumes_pagination(
    mock_candidate_profile: CandidateProfile, mock_master_resume: MasterResume
) -> None:
    """Verify list resumes returns pagination envelope."""
    mock_repo = AsyncMock()
    mock_candidate_service = AsyncMock()
    mock_candidate_service.get_profile.return_value = mock_candidate_profile

    mock_repo.list_resumes.return_value = ([mock_master_resume], 1)

    service = ResumeService(
        repository=mock_repo,
        candidate_service=mock_candidate_service,
        storage=AsyncMock(),
    )

    session = AsyncMock()
    items, pagination = await service.list_resumes(session, page=1, page_size=20)

    assert len(items) == 1
    assert pagination.total_items == 1
    assert pagination.total_pages == 1
    assert pagination.page == 1
    assert pagination.has_next is False


@pytest.mark.asyncio
async def test_get_resume_not_found(mock_candidate_profile: CandidateProfile) -> None:
    """Verify get_resume raises EntityNotFoundError for non-existent resume."""
    mock_repo = AsyncMock()
    mock_candidate_service = AsyncMock()
    mock_candidate_service.get_profile.return_value = mock_candidate_profile
    mock_repo.get_resume_by_id.return_value = None

    service = ResumeService(
        repository=mock_repo,
        candidate_service=mock_candidate_service,
        storage=AsyncMock(),
    )

    session = AsyncMock()
    non_existent_id = uuid.uuid4()
    with pytest.raises(EntityNotFoundError):
        await service.get_resume(session, non_existent_id)


@pytest.mark.asyncio
async def test_activate_resume_success(
    mock_candidate_profile: CandidateProfile, mock_master_resume: MasterResume
) -> None:
    """Verify activate_resume designates the chosen resume as active."""
    mock_repo = AsyncMock()
    mock_candidate_service = AsyncMock()
    mock_candidate_service.get_profile.return_value = mock_candidate_profile
    mock_repo.get_resume_by_id.return_value = mock_master_resume
    mock_repo.activate_resume.return_value = mock_master_resume

    service = ResumeService(
        repository=mock_repo,
        candidate_service=mock_candidate_service,
        storage=AsyncMock(),
    )

    session = AsyncMock()
    activated = await service.activate_resume(session, mock_master_resume.id)

    assert activated == mock_master_resume
    mock_repo.activate_resume.assert_awaited_once_with(session, mock_master_resume)


@pytest.mark.asyncio
async def test_download_resume_file(
    mock_candidate_profile: CandidateProfile, mock_master_resume: MasterResume
) -> None:
    """Verify downloading resume returns stored file binary."""
    mock_repo = AsyncMock()
    mock_candidate_service = AsyncMock()
    mock_candidate_service.get_profile.return_value = mock_candidate_profile
    mock_repo.get_resume_by_id.return_value = mock_master_resume

    mock_storage = AsyncMock()
    file_bytes = b"%PDF-1.4 raw binary file"
    mock_storage.read.return_value = file_bytes

    service = ResumeService(
        repository=mock_repo,
        candidate_service=mock_candidate_service,
        storage=mock_storage,
    )

    session = AsyncMock()
    data, mime, filename = await service.download_resume_file(session, mock_master_resume.id)

    assert data == file_bytes
    assert mime == "application/pdf"
    assert filename == mock_master_resume.original_filename
    mock_storage.read.assert_awaited_once_with(mock_master_resume.storage_key)
