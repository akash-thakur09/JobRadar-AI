"""Unit tests for MatchingService orchestrating Layer 1 and Layer 2 matching."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import EntityNotFoundError
from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    WorkplaceTypeEnum,
)
from app.modules.candidate.repository import CandidateRepository
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.jobs.repository import JobRepository
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.matching.repository import MatchingRepository
from app.modules.matching.service import MatchingService


@pytest.fixture
def mock_matching_repo() -> AsyncMock:
    return AsyncMock(spec=MatchingRepository)


@pytest.fixture
def mock_candidate_repo() -> AsyncMock:
    return AsyncMock(spec=CandidateRepository)


@pytest.fixture
def mock_job_repo() -> AsyncMock:
    return AsyncMock(spec=JobRepository)


@pytest.fixture
def matching_service(
    mock_matching_repo: AsyncMock,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
) -> MatchingService:
    return MatchingService(
        repository=mock_matching_repo,
        candidate_repo=mock_candidate_repo,
        job_repo=mock_job_repo,
    )


def _make_candidate(
    profile_id: uuid.UUID | None = None,
) -> tuple[CandidateProfile, CandidatePreference]:
    pid = profile_id or uuid.uuid4()
    now = datetime.now(UTC)
    profile = CandidateProfile(
        id=pid,
        user_id=uuid.uuid4(),
        full_name="Alice Candidate",
        headline="Senior Python Engineer",
        city="San Francisco",
        country="USA",
        total_experience_months=60,
        created_at=now,
        updated_at=now,
    )
    profile.skills = [
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=pid,
            skill_name="Python",
            is_core=True,
        ),
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=pid,
            skill_name="FastAPI",
            is_core=True,
        ),
    ]

    prefs = CandidatePreference(
        candidate_profile_id=pid,
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        preferred_titles=["Python Engineer"],
        preferred_locations=["San Francisco, CA"],
        max_job_age_days=14,
        created_at=now,
        updated_at=now,
    )
    return profile, prefs


def _make_job(
    job_id: uuid.UUID | None = None,
    title: str = "Senior Python Engineer",
    workplace_type: WorkplaceTypeEnum = WorkplaceTypeEnum.REMOTE,
    location: str = "San Francisco, CA",
    description: str = "Looking for a Python and FastAPI engineer with 4 years experience.",
    posted_days_ago: int = 1,
) -> Job:
    jid = job_id or uuid.uuid4()
    now = datetime.now(UTC)
    return Job(
        id=jid,
        canonical_company_name="Acme Tech",
        title=title,
        canonical_application_url=f"https://acme.com/jobs/{jid}",
        workplace_type=workplace_type,
        normalized_location=location,
        employment_type=EmploymentTypeEnum.FULL_TIME,
        description_text=description,
        posted_at=now - timedelta(days=posted_days_ago),
        first_seen_at=now - timedelta(days=posted_days_ago),
        last_seen_at=now,
        created_at=now,
        updated_at=now,
        status=JobStatusEnum.NORMALIZED,
    )


@pytest.mark.asyncio
async def test_evaluate_job_candidate_not_found(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    missing_id = uuid.uuid4()
    mock_candidate_repo.get_profile.return_value = None

    with pytest.raises(EntityNotFoundError):
        await matching_service.evaluate_job_for_candidate(
            session=session,
            job_id=uuid.uuid4(),
            candidate_profile_id=missing_id,
        )


@pytest.mark.asyncio
async def test_evaluate_job_not_found(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    profile, prefs = _make_candidate()
    mock_candidate_repo.get_or_create_default_profile.return_value = profile
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs
    mock_job_repo.get_job_by_id.return_value = None

    with pytest.raises(EntityNotFoundError):
        await matching_service.evaluate_job_for_candidate(
            session=session,
            job_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_evaluate_job_layer1_ineligible(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
    mock_matching_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    profile, prefs = _make_candidate()
    # Candidate only wants REMOTE, job is ONSITE in New York
    job = _make_job(
        workplace_type=WorkplaceTypeEnum.ONSITE,
        location="New York, NY",
    )

    mock_candidate_repo.get_or_create_default_profile.return_value = profile
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs
    mock_job_repo.get_job_by_id.return_value = job

    # Mock upsert to return a JobMatch
    created_match = JobMatch(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_profile_id=profile.id,
        eligibility_status=EligibilityStatusEnum.INELIGIBLE_LOCATION,
        deterministic_score=Decimal("0.00"),
        final_score=Decimal("0.00"),
    )
    mock_matching_repo.upsert_match.return_value = created_match

    result = await matching_service.evaluate_job_for_candidate(
        session=session,
        job_id=job.id,
    )

    # Job lifecycle status remains candidate-independent (NORMALIZED)
    assert job.status == JobStatusEnum.NORMALIZED
    assert result.eligibility_status == EligibilityStatusEnum.INELIGIBLE_LOCATION
    assert result.deterministic_score == Decimal("0.00")
    assert result.is_qualified is False

    # Verify upsert payload
    mock_matching_repo.upsert_match.assert_called_once()
    payload = mock_matching_repo.upsert_match.call_args[0][1]
    assert payload["eligibility_status"] == EligibilityStatusEnum.INELIGIBLE_LOCATION
    assert payload["deterministic_score"] == Decimal("0.00")
    assert payload["final_score"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_evaluate_job_layer2_matched_qualifies(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
    mock_matching_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    profile, prefs = _make_candidate()
    job = _make_job(
        title="Senior Python Engineer",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        location="San Francisco, CA",
        description="Looking for Senior Python Engineer with FastAPI skills.",
    )

    mock_candidate_repo.get_or_create_default_profile.return_value = profile
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs
    mock_job_repo.get_job_by_id.return_value = job

    # Mock upsert_match
    def fake_upsert(_session, data):
        m = JobMatch(
            id=uuid.uuid4(),
            job_id=data["job_id"],
            candidate_profile_id=data["candidate_profile_id"],
            eligibility_status=data["eligibility_status"],
            deterministic_score=data["deterministic_score"],
            final_score=data["final_score"],
            skill_score=data["skill_score"],
            experience_score=data["experience_score"],
            title_score=data["title_score"],
            preference_score=data["preference_score"],
            match_explanation=data["match_explanation"],
            match_explanation_details=data["match_explanation_details"],
        )
        return m

    mock_matching_repo.upsert_match.side_effect = fake_upsert

    result = await matching_service.evaluate_job_for_candidate(
        session=session,
        job_id=job.id,
    )

    # Job lifecycle status remains candidate-independent (NORMALIZED)
    assert job.status == JobStatusEnum.NORMALIZED
    assert result.eligibility_status == EligibilityStatusEnum.ELIGIBLE
    assert result.deterministic_score >= Decimal("50.00")
    assert result.final_score >= Decimal("50.00")
    assert result.is_qualified is True
    assert "Eligible position" in result.match_explanation


@pytest.mark.asyncio
async def test_evaluate_job_layer2_rejected_below_threshold(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
    mock_matching_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    profile, prefs = _make_candidate()
    # Candidate has Python/FastAPI, but job is for a Frontend UI Engineer with React & Vue & CSS
    # Meets experience (5 years required, candidate has 5 years)
    job = _make_job(
        title="Frontend UI Engineer",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        location="San Francisco, CA",
        description="Looking for Frontend UI Engineer with 5 years experience in React, Vue, CSS.",
    )

    mock_candidate_repo.get_or_create_default_profile.return_value = profile
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs
    mock_job_repo.get_job_by_id.return_value = job

    def fake_upsert(_session, data):
        return JobMatch(
            id=uuid.uuid4(),
            job_id=data["job_id"],
            candidate_profile_id=data["candidate_profile_id"],
            eligibility_status=data["eligibility_status"],
            deterministic_score=data["deterministic_score"],
            final_score=data["final_score"],
            match_explanation=data["match_explanation"],
        )

    mock_matching_repo.upsert_match.side_effect = fake_upsert

    result = await matching_service.evaluate_job_for_candidate(
        session=session,
        job_id=job.id,
    )

    # Job lifecycle status remains candidate-independent (NORMALIZED)
    assert job.status == JobStatusEnum.NORMALIZED
    assert result.eligibility_status == EligibilityStatusEnum.ELIGIBLE
    assert result.deterministic_score < Decimal("50.00")
    assert result.is_qualified is False
    assert "below qualification threshold" in result.match_explanation


@pytest.mark.asyncio
async def test_evaluate_pending_job_matches(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
    mock_matching_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    profile, prefs = _make_candidate()
    mock_candidate_repo.get_or_create_default_profile.return_value = profile
    mock_candidate_repo.get_profile.return_value = profile
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs

    job1 = _make_job(title="Python Developer")
    job2 = _make_job(title="FastAPI Engineer")
    mock_matching_repo.get_unmatched_jobs_for_candidate.return_value = [job1, job2]
    mock_job_repo.get_job_by_id.side_effect = [job1, job2]

    count = await matching_service.evaluate_pending_job_matches(session=session)
    assert count == 2


@pytest.mark.asyncio
async def test_get_match_found_and_not_found(
    matching_service: MatchingService,
    mock_matching_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    match_id = uuid.uuid4()
    now = datetime.now(UTC)

    # Not found case
    mock_matching_repo.get_match_by_id.return_value = None
    with pytest.raises(EntityNotFoundError):
        await matching_service.get_match(session, match_id)

    # Found case
    job = _make_job()
    found_match = JobMatch(
        id=match_id,
        job_id=job.id,
        candidate_profile_id=uuid.uuid4(),
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        deterministic_score=Decimal("85.00"),
        final_score=Decimal("85.00"),
        skill_score=Decimal("40.00"),
        experience_score=Decimal("20.00"),
        title_score=Decimal("15.00"),
        preference_score=Decimal("10.00"),
        match_explanation="Great match",
        match_explanation_details={},
        created_at=now,
        updated_at=now,
        job=job,
    )
    mock_matching_repo.get_match_by_id.return_value = found_match

    resp = await matching_service.get_match(session, match_id)
    assert resp.id == match_id
    assert resp.deterministic_score == Decimal("85.00")
    assert resp.job_title == job.title


@pytest.mark.asyncio
async def test_list_matches(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_matching_repo: AsyncMock,
) -> None:
    session = AsyncMock()
    profile, prefs = _make_candidate()
    mock_candidate_repo.get_or_create_default_profile.return_value = profile
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs

    now = datetime.now(UTC)
    job = _make_job()
    m1 = JobMatch(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_profile_id=profile.id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        deterministic_score=Decimal("90.00"),
        final_score=Decimal("90.00"),
        skill_score=Decimal("40.00"),
        experience_score=Decimal("20.00"),
        title_score=Decimal("15.00"),
        preference_score=Decimal("15.00"),
        match_explanation="Match 1",
        match_explanation_details={},
        created_at=now,
        updated_at=now,
        job=job,
    )
    mock_matching_repo.list_matches.return_value = ([m1], 1)

    result = await matching_service.list_matches(
        session=session,
        min_score=Decimal("70.00"),
        page=1,
        page_size=10,
    )

    assert result.pagination.total_items == 1
    assert result.pagination.total_pages == 1
    assert len(result.items) == 1
    assert result.items[0].deterministic_score == Decimal("90.00")


@pytest.mark.asyncio
async def test_multi_candidate_independence_same_job(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
    mock_matching_repo: AsyncMock,
) -> None:
    """Verify that multiple candidates evaluating the same Job receive independent match results without mutating Job.status."""
    session = AsyncMock()

    # Single canonical job
    canonical_job = _make_job(
        title="Senior Python Backend Engineer",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        location="San Francisco, CA",
        description="We need an expert Python & FastAPI engineer with 5 years experience.",
    )
    mock_job_repo.get_job_by_id.return_value = canonical_job

    # Candidate A: Highly qualified Senior Python Engineer
    cand_a_id = uuid.uuid4()
    profile_a, prefs_a = _make_candidate(cand_a_id)
    profile_a.headline = "Senior Python Backend Engineer"

    # Candidate B: Junior Frontend Developer (unqualified for this Python backend role)
    cand_b_id = uuid.uuid4()
    profile_b = CandidateProfile(
        id=cand_b_id,
        user_id=uuid.uuid4(),
        full_name="Bob Junior",
        headline="Junior Frontend Developer",
        city="San Francisco",
        country="USA",
        total_experience_months=12,
    )
    profile_b.skills = [
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=cand_b_id,
            skill_name="Vue.js",
            is_core=True,
        )
    ]
    prefs_b = CandidatePreference(
        candidate_profile_id=cand_b_id,
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        preferred_titles=["Frontend Developer"],
        preferred_locations=["San Francisco, CA"],
        max_job_age_days=14,
    )

    def fake_upsert(_session, data):
        return JobMatch(
            id=uuid.uuid4(),
            job_id=data["job_id"],
            candidate_profile_id=data["candidate_profile_id"],
            eligibility_status=data["eligibility_status"],
            deterministic_score=data["deterministic_score"],
            final_score=data["final_score"],
            skill_score=data["skill_score"],
            experience_score=data["experience_score"],
            title_score=data["title_score"],
            preference_score=data["preference_score"],
            match_explanation=data["match_explanation"],
            match_explanation_details=data["match_explanation_details"],
        )

    mock_matching_repo.upsert_match.side_effect = fake_upsert

    # 1. Evaluate Candidate A
    mock_candidate_repo.get_profile.return_value = profile_a
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs_a
    match_a = await matching_service.evaluate_job_for_candidate(
        session=session,
        job_id=canonical_job.id,
        candidate_profile_id=cand_a_id,
    )

    # 2. Evaluate Candidate B
    mock_candidate_repo.get_profile.return_value = profile_b
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs_b
    match_b = await matching_service.evaluate_job_for_candidate(
        session=session,
        job_id=canonical_job.id,
        candidate_profile_id=cand_b_id,
    )

    # Invariant 1: Canonical Job.status remains candidate-independent (NORMALIZED)
    assert canonical_job.status == JobStatusEnum.NORMALIZED

    # Invariant 2: Candidate A qualifies with high score
    assert match_a.candidate_profile_id == cand_a_id
    assert match_a.is_qualified is True
    assert match_a.deterministic_score >= Decimal("70.00")

    # Invariant 3: Candidate B is rejected with low score, but does NOT alter Candidate A's match
    assert match_b.candidate_profile_id == cand_b_id
    assert match_b.is_qualified is False
    assert match_b.deterministic_score < Decimal("50.00")

    # Invariant 4: Candidate A and B match records are distinct
    assert match_a.id != match_b.id
    assert match_a.deterministic_score != match_b.deterministic_score


@pytest.mark.asyncio
async def test_missing_skills_scoring_only_not_eligibility_failure(
    matching_service: MatchingService,
    mock_candidate_repo: AsyncMock,
    mock_job_repo: AsyncMock,
    mock_matching_repo: AsyncMock,
) -> None:
    """Verify missing skills reduce Layer 2 score to 0 pts without causing a Layer 1 hard gate failure."""
    session = AsyncMock()
    profile, prefs = _make_candidate()
    profile.total_experience_months = 48
    profile.headline = "System Administrator"
    prefs.preferred_titles = ["System Administrator"]
    profile.skills = [
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            skill_name="Linux",
            is_core=True,
        )
    ]

    # Job text requires Python and FastAPI (which candidate lacks completely), with 3 years experience requirement
    job = _make_job(
        title="Python Backend Engineer",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        location="San Francisco, CA",
        description="We require 3 years of Python, FastAPI, and PostgreSQL.",
    )

    mock_candidate_repo.get_or_create_default_profile.return_value = profile
    mock_candidate_repo.get_preferences_by_profile_id.return_value = prefs
    mock_job_repo.get_job_by_id.return_value = job

    def fake_upsert(_session, data):
        return JobMatch(
            id=uuid.uuid4(),
            job_id=data["job_id"],
            candidate_profile_id=data["candidate_profile_id"],
            eligibility_status=data["eligibility_status"],
            deterministic_score=data["deterministic_score"],
            final_score=data["final_score"],
            skill_score=data["skill_score"],
            experience_score=data["experience_score"],
            title_score=data["title_score"],
            preference_score=data["preference_score"],
            match_explanation=data["match_explanation"],
            match_explanation_details=data["match_explanation_details"],
        )

    mock_matching_repo.upsert_match.side_effect = fake_upsert

    result = await matching_service.evaluate_job_for_candidate(
        session=session,
        job_id=job.id,
    )

    # Invariant: Layer 1 is ELIGIBLE (not INELIGIBLE_MANDATORY_SKILL)
    assert result.eligibility_status == EligibilityStatusEnum.ELIGIBLE
    # Invariant: Skills score is penalized in Layer 2 (0 pts)
    assert result.skill_score == Decimal("0.00")
    # Invariant: Canonical Job.status remains NORMALIZED
    assert job.status == JobStatusEnum.NORMALIZED
    # Invariant: Because score is below threshold, candidate is marked not qualified
    assert result.is_qualified is False
