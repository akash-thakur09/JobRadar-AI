"""Unit tests for asynchronous Celery tailoring tasks."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.tailoring.enums import TailoredResumeStatusEnum
from app.modules.tailoring.models import TailoredResume
from app.modules.tailoring.tasks import _async_generate_tailored_resume


@pytest.mark.unit
async def test_tailoring_task_invalid_uuid():
    """Passing an invalid UUID string aborts with status FAILED without database query."""
    mock_task = MagicMock()
    result = await _async_generate_tailored_resume(mock_task, "not-a-valid-uuid")

    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_tailored_resume_uuid"


@pytest.mark.unit
async def test_tailoring_task_already_completed_idempotency():
    """If record is already COMPLETED, worker returns ALREADY_COMPLETED without executing pipeline."""
    mock_task = MagicMock()
    resume_id = uuid.uuid4()

    mock_record = TailoredResume(
        id=resume_id,
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=uuid.uuid4(),
        resume_version_id=uuid.uuid4(),
        generation_status=TailoredResumeStatusEnum.COMPLETED,
        storage_key="resumes/tailored/test.pdf",
    )

    mock_service = MagicMock()
    mock_service.repository.get_by_id = AsyncMock(return_value=mock_record)

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    with patch("app.modules.tailoring.tasks.get_tailoring_service", return_value=mock_service):
        with patch(
            "app.modules.tailoring.tasks.get_session_factory", return_value=mock_session_factory
        ):
            result = await _async_generate_tailored_resume(mock_task, str(resume_id))

    assert result["status"] == "ALREADY_COMPLETED"
    assert result["tailored_resume_id"] == str(resume_id)
    mock_service.execute_tailoring_pipeline.assert_not_called()
