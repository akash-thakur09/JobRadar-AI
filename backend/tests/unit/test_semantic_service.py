"""Unit tests for SemanticAnalysisService orchestration and hybrid scoring."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import EntityNotFoundError
from app.modules.candidate.models import (
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    WorkplaceTypeEnum,
)
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    SemanticRecommendationEnum,
    SemanticStrength,
    TransferableSkill,
)
from app.modules.matching.models import EligibilityStatusEnum, JobMatch, SemanticAnalysisStatusEnum
from app.modules.matching.repository import MatchingRepository
from app.modules.matching.semantic_service import SemanticAnalysisService


def create_mock_candidate_and_job() -> tuple[CandidateProfile, Job, JobMatch]:
    """Helper creating mock candidate, job, and match instances for unit testing."""
    profile_id = uuid.uuid4()
    job_id = uuid.uuid4()
    match_id = uuid.uuid4()

    candidate = CandidateProfile(
        id=profile_id,
        user_id=uuid.uuid4(),
        full_name="Jane Doe",
        headline="Staff Backend Architect",
        professional_summary="Experienced distributed systems engineer.",
        total_experience_months=72,
    )
    candidate.skills = [
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile_id,
            skill_name="python",
            category="language",
            experience_months=72,
            is_core=True,
        ),
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile_id,
            skill_name="fastapi",
            category="framework",
            experience_months=48,
            is_core=True,
        ),
    ]

    job = Job(
        id=job_id,
        canonical_company_name="TechCorp",
        title="Senior Python Backend Engineer",
        canonical_application_url="https://techcorp.com/jobs/123",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        employment_type=EmploymentTypeEnum.FULL_TIME,
        description_text="Looking for a Python and FastAPI engineer with container experience.",
        status=JobStatusEnum.NORMALIZED,
    )

    match = JobMatch(
        id=match_id,
        job_id=job_id,
        candidate_profile_id=profile_id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        semantic_analysis_status=SemanticAnalysisStatusEnum.PENDING,
        deterministic_score=Decimal("70.00"),
        final_score=Decimal("70.00"),
        skill_score=Decimal("28.00"),
        experience_score=Decimal("20.00"),
        title_score=Decimal("12.00"),
        preference_score=Decimal("10.00"),
        match_explanation="Initial deterministic score: 70.00/100.00.",
        match_explanation_details={
            "deterministic_breakdown": {
                "skills": {
                    "matched_required": ["python", "fastapi"],
                    "missing_required": ["docker"],
                }
            }
        },
    )
    match.candidate_profile = candidate
    match.job = job

    return candidate, job, match


@pytest.mark.asyncio
async def test_semantic_service_skips_ineligible_match() -> None:
    """Verify ineligible match is skipped and final score is preserved."""
    _, _, match = create_mock_candidate_and_job()
    match.eligibility_status = EligibilityStatusEnum.INELIGIBLE_LOCATION

    repo_mock = MagicMock(spec=MatchingRepository)
    repo_mock.get_match_with_relations = AsyncMock(return_value=match)

    service = SemanticAnalysisService(repository=repo_mock)
    session_mock = AsyncMock()

    result_match = await service.evaluate_semantic_match(session_mock, match.id)

    assert result_match.semantic_analysis_status == SemanticAnalysisStatusEnum.SKIPPED
    assert result_match.semantic_score is None
    assert result_match.final_score == Decimal("70.00")


@pytest.mark.asyncio
async def test_semantic_service_skips_score_below_threshold() -> None:
    """Verify match with deterministic score < 50.00 is skipped."""
    _, _, match = create_mock_candidate_and_job()
    match.deterministic_score = Decimal("45.00")
    match.final_score = Decimal("45.00")

    repo_mock = MagicMock(spec=MatchingRepository)
    repo_mock.get_match_with_relations = AsyncMock(return_value=match)

    service = SemanticAnalysisService(repository=repo_mock)
    session_mock = AsyncMock()

    result_match = await service.evaluate_semantic_match(session_mock, match.id)

    assert result_match.semantic_analysis_status == SemanticAnalysisStatusEnum.SKIPPED
    assert result_match.semantic_score is None
    assert result_match.final_score == Decimal("45.00")


@pytest.mark.asyncio
async def test_semantic_service_hybrid_score_calculation() -> None:
    """Verify hybrid formula: 0.60 * Deterministic + 0.40 * Semantic."""
    _, _, match = create_mock_candidate_and_job()
    match.deterministic_score = Decimal("70.00")

    canned_semantic = SemanticAnalysisResult(
        semantic_score=Decimal("85.00"),
        recommendation=SemanticRecommendationEnum.STRONG_MATCH,
        confidence=0.92,
        reasoning_summary="Candidate has strong architecture alignment.",
        strengths=[
            SemanticStrength(
                claim="FastAPI architecture",
                evidence="4 years FastAPI",
                job_context="Backend API scale",
            )
        ],
        transferable_skills=[
            TransferableSkill(
                candidate_skill="python",
                target_technology="docker",
                rationale="Scripting and environment isolation",
            )
        ],
    )

    mock_llm = MockLLMProvider(default_result=canned_semantic)
    repo_mock = MagicMock(spec=MatchingRepository)
    repo_mock.get_match_with_relations = AsyncMock(return_value=match)
    repo_mock.get_active_resume_for_candidate = AsyncMock(return_value=None)

    service = SemanticAnalysisService(repository=repo_mock, llm_provider=mock_llm)
    session_mock = AsyncMock()

    result_match = await service.evaluate_semantic_match(session_mock, match.id)

    # Expected: 0.60 * 70.00 + 0.40 * 85.00 = 42.00 + 34.00 = 76.00
    assert result_match.semantic_analysis_status == SemanticAnalysisStatusEnum.COMPLETED
    assert result_match.semantic_score == Decimal("85.00")
    assert result_match.final_score == Decimal("76.00")
    assert result_match.match_explanation_details["llm_degraded"] is False
    assert "semantic_evaluation" in result_match.match_explanation_details
    assert "STRONG MATCH" in result_match.match_explanation


@pytest.mark.asyncio
async def test_semantic_service_graceful_degradation_on_timeout() -> None:
    """Verify timeout falls back to deterministic score without crashing pipeline."""
    _, _, match = create_mock_candidate_and_job()
    match.deterministic_score = Decimal("68.50")
    match.final_score = Decimal("68.50")

    timeout_llm = MockLLMProvider(simulate_timeout=True)
    repo_mock = MagicMock(spec=MatchingRepository)
    repo_mock.get_match_with_relations = AsyncMock(return_value=match)
    repo_mock.get_active_resume_for_candidate = AsyncMock(return_value=None)

    service = SemanticAnalysisService(repository=repo_mock, llm_provider=timeout_llm)
    session_mock = AsyncMock()

    result_match = await service.evaluate_semantic_match(session_mock, match.id)

    assert result_match.semantic_analysis_status == SemanticAnalysisStatusEnum.FAILED
    assert result_match.semantic_score is None
    assert result_match.final_score == Decimal("68.50")  # Preserved!
    assert result_match.match_explanation_details["llm_degraded"] is True
    assert "timeout" in result_match.match_explanation_details["llm_error"].lower()


@pytest.mark.asyncio
async def test_semantic_service_graceful_degradation_on_unavailable() -> None:
    """Verify unreachable LLM service triggers fallback cleanly."""
    _, _, match = create_mock_candidate_and_job()
    match.deterministic_score = Decimal("72.00")

    unavail_llm = MockLLMProvider(simulate_unavailable=True)
    repo_mock = MagicMock(spec=MatchingRepository)
    repo_mock.get_match_with_relations = AsyncMock(return_value=match)
    repo_mock.get_active_resume_for_candidate = AsyncMock(return_value=None)

    service = SemanticAnalysisService(repository=repo_mock, llm_provider=unavail_llm)
    session_mock = AsyncMock()

    result_match = await service.evaluate_semantic_match(session_mock, match.id)

    assert result_match.semantic_analysis_status == SemanticAnalysisStatusEnum.FAILED
    assert result_match.semantic_score is None
    assert result_match.final_score == Decimal("72.00")
    assert result_match.match_explanation_details["llm_degraded"] is True


@pytest.mark.asyncio
async def test_semantic_service_not_found_raises_entity_not_found() -> None:
    """Verify EntityNotFoundError is raised when match_id does not exist."""
    missing_id = uuid.uuid4()
    repo_mock = MagicMock(spec=MatchingRepository)
    repo_mock.get_match_with_relations = AsyncMock(return_value=None)

    service = SemanticAnalysisService(repository=repo_mock)
    session_mock = AsyncMock()

    with pytest.raises(EntityNotFoundError) as exc_info:
        await service.evaluate_semantic_match(session_mock, missing_id)

    assert "JobMatch" in str(exc_info.value)
    assert str(missing_id) in str(exc_info.value)
