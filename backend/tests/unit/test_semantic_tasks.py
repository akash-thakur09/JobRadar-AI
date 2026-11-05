"""Unit tests for semantic matching Celery tasks."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.matching.models import EligibilityStatusEnum, JobMatch, SemanticAnalysisStatusEnum
from app.modules.matching.tasks import (
    _async_evaluate_job_matching,
    _async_evaluate_semantic_matching,
)


@pytest.mark.asyncio
async def test_semantic_task_invalid_uuid() -> None:
    """Verify task returns FAILED for invalid match UUID."""
    mock_task = MagicMock()
    result = await _async_evaluate_semantic_matching(mock_task, "not-a-valid-uuid")
    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_match_uuid"


@pytest.mark.asyncio
async def test_semantic_task_already_completed_idempotency() -> None:
    """Verify idempotency: already completed match skips LLM evaluation."""
    match_id = uuid.uuid4()
    completed_match = MagicMock(spec=JobMatch)
    completed_match.semantic_analysis_status = SemanticAnalysisStatusEnum.COMPLETED
    completed_match.final_score = Decimal("82.50")

    mock_repo = MagicMock()
    mock_repo.get_match_by_id = AsyncMock(return_value=completed_match)

    mock_service = MagicMock()
    mock_service.repository = mock_repo

    mock_redis = MagicMock()
    mock_lock = AsyncMock()
    mock_lock.acquire = AsyncMock(return_value=True)
    mock_lock.release = AsyncMock()
    mock_redis.lock.return_value = mock_lock

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with (
        patch("app.modules.matching.tasks.get_redis", return_value=mock_redis),
        patch("app.modules.matching.tasks.get_semantic_service", return_value=mock_service),
        patch("app.modules.matching.tasks.get_session_factory", return_value=mock_session_factory),
    ):
        mock_task = MagicMock()
        result = await _async_evaluate_semantic_matching(mock_task, str(match_id))

        assert result["status"] == "ALREADY_COMPLETED"
        assert result["final_score"] == 82.50
        mock_service.evaluate_semantic_match.assert_not_called()


@pytest.mark.asyncio
async def test_job_matching_dispatches_semantic_task_when_qualified() -> None:
    """Verify evaluate_job_matching_task dispatches semantic task when match qualifies."""
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    match_id = uuid.uuid4()

    mock_match = MagicMock(spec=JobMatch)
    mock_match.id = match_id
    mock_match.job_id = job_id
    mock_match.candidate_profile_id = candidate_id
    mock_match.eligibility_status = EligibilityStatusEnum.ELIGIBLE
    mock_match.deterministic_score = Decimal("75.00")
    mock_match.final_score = Decimal("75.00")
    mock_match.is_qualified = True

    mock_matching_service = MagicMock()
    mock_matching_service.evaluate_job_for_candidate = AsyncMock(return_value=mock_match)

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with (
        patch(
            "app.modules.matching.tasks.get_matching_service", return_value=mock_matching_service
        ),
        patch("app.modules.matching.tasks.get_session_factory", return_value=mock_session_factory),
        patch("app.modules.matching.tasks.evaluate_semantic_matching_task.delay") as mock_delay,
    ):
        mock_task = MagicMock()
        result = await _async_evaluate_job_matching(mock_task, str(job_id), str(candidate_id))

        assert result["status"] == "SUCCESS"
        assert result["semantic_dispatched"] is True
        mock_delay.assert_called_once_with(str(match_id))


@pytest.mark.asyncio
async def test_job_matching_does_not_dispatch_when_not_qualified() -> None:
    """Verify evaluate_job_matching_task skips semantic task dispatch when match score < 50."""
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    match_id = uuid.uuid4()

    mock_match = MagicMock(spec=JobMatch)
    mock_match.id = match_id
    mock_match.job_id = job_id
    mock_match.candidate_profile_id = candidate_id
    mock_match.eligibility_status = EligibilityStatusEnum.ELIGIBLE
    mock_match.deterministic_score = Decimal("40.00")
    mock_match.final_score = Decimal("40.00")
    mock_match.is_qualified = False

    mock_matching_service = MagicMock()
    mock_matching_service.evaluate_job_for_candidate = AsyncMock(return_value=mock_match)

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with (
        patch(
            "app.modules.matching.tasks.get_matching_service", return_value=mock_matching_service
        ),
        patch("app.modules.matching.tasks.get_session_factory", return_value=mock_session_factory),
        patch("app.modules.matching.tasks.evaluate_semantic_matching_task.delay") as mock_delay,
    ):
        mock_task = MagicMock()
        result = await _async_evaluate_job_matching(mock_task, str(job_id), str(candidate_id))

        assert result["status"] == "SUCCESS"
        assert result["semantic_dispatched"] is False
        mock_delay.assert_not_called()
