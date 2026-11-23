"""Unit tests for Layer 1 Deterministic Eligibility Engine."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    EmploymentTypeEnum,
    WorkplaceTypeEnum,
)
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.eligibility import (
    check_experience_threshold,
    check_job_freshness,
    check_location,
    check_mandatory_skills,
    check_work_authorization,
    check_workplace_type,
    evaluate_eligibility,
    extract_required_experience_months,
)
from app.modules.matching.models import EligibilityStatusEnum


def _make_dummy_job(
    title: str = "Senior Backend Engineer",
    description: str = "Build APIs using Python and PostgreSQL.",
    workplace: WorkplaceTypeEnum = WorkplaceTypeEnum.REMOTE,
    location: str | None = "San Francisco, CA",
    posted_at: datetime | None = None,
    first_seen_at: datetime | None = None,
) -> Job:
    now = datetime.now(UTC)
    job = Job(
        id=uuid.uuid4(),
        canonical_company_name="Acme Corp",
        title=title,
        canonical_application_url="https://acme.com/jobs/1",
        workplace_type=workplace,
        normalized_location=location,
        employment_type=EmploymentTypeEnum.FULL_TIME,
        description_text=description,
        posted_at=posted_at or now,
        first_seen_at=first_seen_at or now,
        last_seen_at=now,
        dedup_fingerprint_sha256="abcd" * 16,
        status=JobStatusEnum.DISCOVERED,
    )
    return job


def _make_dummy_candidate(
    total_experience_months: int = 48,
    city: str = "Seattle",
    country: str = "USA",
    work_authorization: str = "US Citizen",
    preferred_workplaces: list[WorkplaceTypeEnum] | None = None,
    preferred_locations: list[str] | None = None,
    max_job_age_days: int = 14,
) -> tuple[CandidateProfile, CandidatePreference]:
    profile_id = uuid.uuid4()
    profile = CandidateProfile(
        id=profile_id,
        user_id=uuid.uuid4(),
        full_name="Alex Developer",
        headline="Senior Backend Engineer",
        total_experience_months=total_experience_months,
        city=city,
        country=country,
        work_authorization=work_authorization,
    )
    prefs = CandidatePreference(
        id=uuid.uuid4(),
        candidate_profile_id=profile_id,
        minimum_relevance_score=Decimal("70.00"),
        preferred_titles=["Backend Engineer", "Software Engineer"],
        preferred_workplace_types=preferred_workplaces
        or [WorkplaceTypeEnum.REMOTE, WorkplaceTypeEnum.HYBRID],
        preferred_locations=preferred_locations or ["Seattle", "Remote"],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        max_job_age_days=max_job_age_days,
    )
    return profile, prefs


def test_check_job_freshness_fresh_and_stale() -> None:
    now = datetime(2026, 11, 5, 12, 0, 0, tzinfo=UTC)
    _, prefs = _make_dummy_candidate(max_job_age_days=14)

    # 1. Fresh job posted 3 days ago
    fresh_job = _make_dummy_job(posted_at=now - timedelta(days=3))
    res_fresh = check_job_freshness(fresh_job, prefs, now)
    assert res_fresh.passed
    assert res_fresh.status == EligibilityStatusEnum.ELIGIBLE

    # 2. Stale job posted 20 days ago (max is 14)
    stale_job = _make_dummy_job(posted_at=now - timedelta(days=20))
    res_stale = check_job_freshness(stale_job, prefs, now)
    assert not res_stale.passed
    assert res_stale.status == EligibilityStatusEnum.INELIGIBLE_EXPERIENCE
    assert "exceeds maximum allowed age" in res_stale.reason


def test_check_workplace_type_compatibility() -> None:
    _, prefs = _make_dummy_candidate(preferred_workplaces=[WorkplaceTypeEnum.REMOTE])

    # Remote job passes
    remote_job = _make_dummy_job(workplace=WorkplaceTypeEnum.REMOTE)
    assert check_workplace_type(remote_job, prefs).passed

    # Onsite job fails hard
    onsite_job = _make_dummy_job(workplace=WorkplaceTypeEnum.ONSITE)
    res_onsite = check_workplace_type(onsite_job, prefs)
    assert not res_onsite.passed
    assert res_onsite.status == EligibilityStatusEnum.INELIGIBLE_LOCATION

    # Unknown workplace passes with note
    unknown_job = _make_dummy_job(workplace=WorkplaceTypeEnum.UNKNOWN)
    assert check_workplace_type(unknown_job, prefs).passed


def test_check_location_filtering() -> None:
    profile, prefs = _make_dummy_candidate(
        city="Seattle",
        preferred_workplaces=[WorkplaceTypeEnum.HYBRID, WorkplaceTypeEnum.ONSITE],
        preferred_locations=["Seattle, WA", "Portland, OR"],
    )

    # Remote job always satisfies location check
    remote_job = _make_dummy_job(workplace=WorkplaceTypeEnum.REMOTE, location="New York, NY")
    assert check_location(remote_job, profile, prefs).passed

    # Onsite in allowed location passes
    onsite_match = _make_dummy_job(workplace=WorkplaceTypeEnum.ONSITE, location="Seattle, WA")
    assert check_location(onsite_match, profile, prefs).passed

    # Onsite in disallowed location fails
    onsite_mismatch = _make_dummy_job(workplace=WorkplaceTypeEnum.ONSITE, location="Austin, TX")
    res = check_location(onsite_mismatch, profile, prefs)
    assert not res.passed
    assert res.status == EligibilityStatusEnum.INELIGIBLE_LOCATION


def test_check_experience_threshold_with_grace_buffer() -> None:
    # 1. Job requires 3 years (36 months)
    job = _make_dummy_job(description="Requires 3+ years of experience in distributed systems.")
    months_req, _ = extract_required_experience_months(job)
    assert months_req == 36

    # Candidate with 48 months (> 36) -> passes directly
    prof_experienced, _ = _make_dummy_candidate(total_experience_months=48)
    res1 = check_experience_threshold(job, prof_experienced, tolerance_buffer_months=12)
    assert res1.passed
    assert "meets required" in res1.reason

    # Candidate with 28 months (< 36, but 28 + 12 = 40 >= 36) -> passes within grace buffer
    prof_grace, _ = _make_dummy_candidate(total_experience_months=28)
    res2 = check_experience_threshold(job, prof_grace, tolerance_buffer_months=12)
    assert res2.passed
    assert "within the 12-month grace buffer" in res2.reason

    # Candidate with 18 months (< 36, and 18 + 12 = 30 < 36) -> fails hard
    prof_under, _ = _make_dummy_candidate(total_experience_months=18)
    res3 = check_experience_threshold(job, prof_under, tolerance_buffer_months=12)
    assert not res3.passed
    assert res3.status == EligibilityStatusEnum.INELIGIBLE_EXPERIENCE
    assert "below minimum requirement" in res3.reason


def test_check_work_authorization() -> None:
    # 1. Job with strict visa restriction
    restricted_job = _make_dummy_job(
        description="Must be a US Citizen. No visa sponsorship will be provided."
    )

    # US Citizen passes
    prof_citizen, _ = _make_dummy_candidate(work_authorization="US Citizen")
    assert check_work_authorization(restricted_job, prof_citizen).passed

    # Candidate requiring sponsorship fails
    prof_sponsor, _ = _make_dummy_candidate(work_authorization="Need Sponsorship / H1B")
    res_sponsor = check_work_authorization(restricted_job, prof_sponsor)
    assert not res_sponsor.passed
    assert res_sponsor.status == EligibilityStatusEnum.INELIGIBLE_WORK_AUTH

    # Unrestricted job passes for everyone
    open_job = _make_dummy_job(description="Great perks, competitive compensation.")
    assert check_work_authorization(open_job, prof_sponsor).passed


def test_check_mandatory_skills() -> None:
    job = _make_dummy_job()
    job_skills = {"python", "fastapi", "postgresql"}

    # Candidate requires python -> passes
    assert check_mandatory_skills(job, {"python"}, job_skills).passed

    # Candidate requires rust -> fails
    res_missing = check_mandatory_skills(job, {"python", "rust"}, job_skills)
    assert not res_missing.passed
    assert res_missing.status == EligibilityStatusEnum.INELIGIBLE_MANDATORY_SKILL
    assert "rust" in res_missing.reason


def test_evaluate_eligibility_aggregate() -> None:
    now = datetime(2026, 11, 5, 12, 0, 0, tzinfo=UTC)
    profile, prefs = _make_dummy_candidate(
        total_experience_months=60,
        preferred_workplaces=[WorkplaceTypeEnum.REMOTE],
    )

    # Job passes all gates
    qualifying_job = _make_dummy_job(
        workplace=WorkplaceTypeEnum.REMOTE,
        posted_at=now - timedelta(days=2),
        description="Requires 4+ years experience with Python.",
    )
    result = evaluate_eligibility(
        qualifying_job,
        profile,
        prefs,
        job_skills={"python", "postgresql"},
        now=now,
    )
    assert result.is_eligible
    assert result.status == EligibilityStatusEnum.ELIGIBLE
    assert len(result.failed_checks) == 0

    # Job fails workplace gate
    ineligible_job = _make_dummy_job(
        workplace=WorkplaceTypeEnum.ONSITE,
        posted_at=now - timedelta(days=2),
    )
    bad_result = evaluate_eligibility(
        ineligible_job,
        profile,
        prefs,
        job_skills={"python"},
        now=now,
    )
    assert not bad_result.is_eligible
    assert bad_result.status == EligibilityStatusEnum.INELIGIBLE_LOCATION
    assert "workplace" in bad_result.failed_checks
