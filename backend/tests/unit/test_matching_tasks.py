"""Unit tests for Matching Celery background tasks."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.matching.tasks import (
    _async_evaluate_job_matching,
    _async_evaluate_pending_matches,
    evaluate_job_matching_task,
    evaluate_pending_job_matches_task,
)


def test_task_registrations() -> None:
    assert (
        evaluate_job_matching_task.name == "app.modules.matching.tasks.evaluate_job_matching_task"
    )
    assert evaluate_job_matching_task.queue == "processing"
    assert (
        evaluate_pending_job_matches_task.name
        == "app.modules.matching.tasks.evaluate_pending_job_matches_task"
    )
    assert evaluate_pending_job_matches_task.queue == "processing"


@pytest.mark.asyncio
async def test_async_evaluate_job_matching_success() -> None:
    task = MagicMock()
    job_id = uuid.uuid4()
    cand_id = uuid.uuid4()
    match_id = uuid.uuid4()

    mock_match = MagicMock(spec=JobMatch)
    mock_match.id = match_id
    mock_match.job_id = job_id
    mock_match.candidate_profile_id = cand_id
    mock_match.eligibility_status = EligibilityStatusEnum.ELIGIBLE
    mock_match.deterministic_score = Decimal("85.50")
    mock_match.final_score = Decimal("85.50")

    mock_service = AsyncMock()
    mock_service.evaluate_job_for_candidate.return_value = mock_match

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.modules.matching.tasks.get_matching_service", return_value=mock_service),
        patch("app.modules.matching.tasks.get_session_factory", return_value=mock_session_factory),
    ):
        result = await _async_evaluate_job_matching(task, str(job_id), str(cand_id))

    assert result["status"] == "SUCCESS"
    assert result["match_id"] == str(match_id)
    assert result["job_id"] == str(job_id)
    assert result["candidate_profile_id"] == str(cand_id)
    assert result["eligibility_status"] == "ELIGIBLE"
    assert result["deterministic_score"] == 85.5
    assert result["final_score"] == 85.5
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_evaluate_job_matching_invalid_job_uuid() -> None:
    task = MagicMock()
    result = await _async_evaluate_job_matching(task, "not-a-valid-uuid", None)
    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_job_uuid"


@pytest.mark.asyncio
async def test_async_evaluate_job_matching_invalid_candidate_uuid() -> None:
    task = MagicMock()
    result = await _async_evaluate_job_matching(task, str(uuid.uuid4()), "not-a-candidate-uuid")
    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_candidate_uuid"


@pytest.mark.asyncio
async def test_async_evaluate_job_matching_retry_on_exception() -> None:
    task = MagicMock()
    task.request.retries = 1
    task.retry.side_effect = Retry("Task retry simulation")

    mock_service = AsyncMock()
    mock_service.evaluate_job_for_candidate.side_effect = RuntimeError("Database connection lost")

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.modules.matching.tasks.get_matching_service", return_value=mock_service),
        patch("app.modules.matching.tasks.get_session_factory", return_value=mock_session_factory),
        pytest.raises(Retry),
    ):
        await _async_evaluate_job_matching(task, str(uuid.uuid4()), None)

    task.retry.assert_called_once()


@pytest.mark.asyncio
async def test_async_evaluate_pending_matches_success() -> None:
    mock_service = AsyncMock()
    mock_service.evaluate_pending_job_matches.return_value = 5

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.modules.matching.tasks.get_matching_service", return_value=mock_service),
        patch("app.modules.matching.tasks.get_session_factory", return_value=mock_session_factory),
    ):
        result = await _async_evaluate_pending_matches(batch_size=50, candidate_profile_id_str=None)

    assert result["status"] == "SUCCESS"
    assert result["evaluated_count"] == 5
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_evaluate_pending_matches_invalid_uuid() -> None:
    result = await _async_evaluate_pending_matches(
        batch_size=50, candidate_profile_id_str="invalid-profile-uuid"
    )
    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_candidate_uuid"
