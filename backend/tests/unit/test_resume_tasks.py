"""Unit tests for Celery resume parsing task."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.resumes.models import ResumeProcessingStatus
from app.modules.resumes.parsers.base import ParsedResumeResult, PreservationCapability
from app.modules.resumes.tasks import _async_process_resume


@pytest.mark.asyncio
async def test_async_process_resume_success() -> None:
    """Verify background task processes resume version and updates to COMPLETED."""
    version_id = uuid.uuid4()
    master_id = uuid.uuid4()

    mock_version = AsyncMock()
    mock_version.id = version_id
    mock_version.master_resume_id = master_id
    mock_version.processing_status = ResumeProcessingStatus.PENDING.value

    mock_master = AsyncMock()
    mock_master.id = master_id
    mock_master.storage_key = "resumes/raw/test.pdf"
    mock_master.mime_type = "application/pdf"
    mock_master.original_filename = "resume.pdf"

    mock_repo = AsyncMock()
    mock_repo.get_version_by_id.return_value = mock_version
    mock_repo.get_resume_by_id.return_value = mock_master

    mock_storage = AsyncMock()
    mock_storage.read.return_value = b"%PDF-1.4 dummy bytes"

    parsed_result = ParsedResumeResult(
        raw_text="Jane Doe\nPython Developer",
        structured_content={"skills": ["python"], "contact": {}},
        template_metadata={"page_count": 1},
        preservation_capability=PreservationCapability.SUPPORTED,
        extraction_warnings=[],
        is_valid=True,
    )

    mock_parser = AsyncMock()
    mock_parser.parse.return_value = parsed_result

    with (
        patch("app.modules.resumes.tasks.MasterResumeRepository", return_value=mock_repo),
        patch("app.modules.resumes.tasks.get_file_storage", return_value=mock_storage),
        patch("app.modules.resumes.tasks.get_parser_for_mime_type", return_value=mock_parser),
        patch("app.modules.resumes.tasks.get_session_factory") as mock_session_factory,
    ):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        result = await _async_process_resume(str(version_id), "task-123")

    assert result["status"] == ResumeProcessingStatus.COMPLETED.value
    assert result["is_valid"] is True
    mock_repo.update_version.assert_awaited()


@pytest.mark.asyncio
async def test_async_process_resume_idempotency() -> None:
    """Verify background task skips processing if version is already COMPLETED."""
    version_id = uuid.uuid4()
    mock_version = AsyncMock()
    mock_version.id = version_id
    mock_version.processing_status = ResumeProcessingStatus.COMPLETED.value

    mock_repo = AsyncMock()
    mock_repo.get_version_by_id.return_value = mock_version

    with (
        patch("app.modules.resumes.tasks.MasterResumeRepository", return_value=mock_repo),
        patch("app.modules.resumes.tasks.get_session_factory") as mock_session_factory,
    ):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        result = await _async_process_resume(str(version_id), "task-dup")

    assert result["status"] == "already_completed"
    mock_repo.update_version.assert_not_called()


@pytest.mark.asyncio
async def test_async_process_resume_not_found() -> None:
    """Verify background task handles non-existent version ID safely."""
    version_id = uuid.uuid4()
    mock_repo = AsyncMock()
    mock_repo.get_version_by_id.return_value = None

    with (
        patch("app.modules.resumes.tasks.MasterResumeRepository", return_value=mock_repo),
        patch("app.modules.resumes.tasks.get_session_factory") as mock_session_factory,
    ):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        result = await _async_process_resume(str(version_id), "task-none")

    assert result["status"] == "not_found"
