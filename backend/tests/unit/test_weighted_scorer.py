"""Unit tests for Layer 2 Deterministic Weighted Scoring Engine."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    WorkplaceTypeEnum,
)
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.weighted_scorer import (
    _compute_token_overlap,
    _compute_trigram_similarity,
    _infer_seniority_tier,
    calculate_deterministic_score,
    score_bonus_factors,
    score_experience,
    score_skills,
    score_title,
    score_workplace,
)


def test_trigram_similarity_and_token_overlap() -> None:
    # Identical strings
    assert _compute_trigram_similarity("Software Engineer", "Software Engineer") == 1.0
    assert _compute_token_overlap("Software Engineer", "Software Engineer") == 1.0

    # Empty strings
    assert _compute_trigram_similarity("", "Backend Engineer") == 0.0
    assert _compute_token_overlap("", "Backend Engineer") == 0.0

    # Java vs JavaScript distinction
    # "Java Developer" vs "JavaScript Developer": tokens are {'java', 'developer'} vs {'javascript', 'developer'}
    # 1 common token out of 2 => token overlap is 0.5
    token_overlap = _compute_token_overlap("Java Developer", "JavaScript Developer")
    assert token_overlap == 0.5


def test_infer_seniority_tier() -> None:
    assert _infer_seniority_tier("Senior Backend Engineer", 12) == "senior"
    assert _infer_seniority_tier("Staff Platform Engineer", 36) == "staff"
    assert _infer_seniority_tier("Junior Python Developer", 48) == "junior"
    assert _infer_seniority_tier("Associate Software Engineer", 12) == "junior"

    # Fallback to experience months when title doesn't specify
    assert _infer_seniority_tier("Software Engineer", 100) == "staff"
    assert _infer_seniority_tier("Software Engineer", 72) == "senior"
    assert _infer_seniority_tier("Software Engineer", 36) == "mid"
    assert _infer_seniority_tier("Software Engineer", 12) == "junior"


def test_score_skills_general() -> None:
    # 100% match: 40 points
    cand = {"python", "fastapi", "postgresql"}
    job_skills = {"python", "fastapi", "postgresql"}
    score, details = score_skills(cand, job_skills)
    assert score == Decimal("40.00")
    assert len(details["matched_skills"]) == 3
    assert len(details["missing_skills"]) == 0

    # 50% match: 20 points
    cand = {"python", "fastapi"}
    job_skills = {"python", "fastapi", "docker", "kubernetes"}
    score, details = score_skills(cand, job_skills)
    assert score == Decimal("20.00")
    assert details["matched_skills"] == ["fastapi", "python"]
    assert details["missing_skills"] == ["docker", "kubernetes"]

    # 0% match: 0 points
    cand = {"ruby", "rails"}
    job_skills = {"python", "fastapi"}
    score, details = score_skills(cand, job_skills)
    assert score == Decimal("0.00")

    # Empty job skills: neutral 20.00 points
    score, details = score_skills(cand, set())
    assert score == Decimal("20.00")
    assert "neutral baseline" in details["note"]


def test_score_skills_required_and_preferred() -> None:
    cand = {"python", "fastapi", "docker"}
    required = {"python", "fastapi"}  # cand has 2/2 -> 30.0 pts
    preferred = {"docker", "kubernetes"}  # cand has 1/2 -> 5.0 pts

    score, details = score_skills(cand, set(), required_skills=required, preferred_skills=preferred)
    assert score == Decimal("35.00")
    assert details["matched_required"] == ["fastapi", "python"]
    assert details["matched_preferred"] == ["docker"]


def test_score_experience() -> None:
    # Exact match: 5 years (60 months) cand, 60 req, same senior tier -> 15 (ratio) + 5 (tier) = 20 pts
    score, details = score_experience(
        candidate_months=60,
        required_months=60,
        candidate_seniority="senior",
        job_seniority="senior",
    )
    assert score == Decimal("20.00")
    assert details["ratio_score"] == 15.0
    assert details["seniority_score"] == 5.0

    # Under-experience: 30 months cand, 60 months req -> 30/60 * 15 = 7.5 pts ratio
    # cand is mid (1), job is senior (2) -> diff 1 -> +3 pts seniority
    score, details = score_experience(
        candidate_months=30,
        required_months=60,
        candidate_seniority="mid",
        job_seniority="senior",
    )
    assert score == Decimal("10.50")
    assert details["ratio_score"] == 7.5
    assert details["seniority_score"] == 3.0

    # Overqualified: 120 months cand, 24 req -> ratio capped at 1.0 * 15 = 15.0 pts
    # cand staff (3), job junior (0) -> diff 3 (>1) -> 0 pts seniority
    score, details = score_experience(
        candidate_months=120,
        required_months=24,
        candidate_seniority="staff",
        job_seniority="junior",
    )
    assert score == Decimal("15.00")
    assert details["ratio_score"] == 15.0
    assert details["seniority_score"] == 0.0

    # Zero required months: candidate has exp -> 15 pts ratio
    score, details = score_experience(
        candidate_months=36,
        required_months=0,
        candidate_seniority="mid",
        job_seniority="mid",
    )
    assert score == Decimal("20.00")


def test_score_title() -> None:
    # Exact title match
    score, details = score_title(
        candidate_headline="Senior Backend Engineer",
        preferred_titles=["Backend Engineer"],
        job_title="Senior Backend Engineer",
    )
    assert score == Decimal("15.00")
    assert details["trigram_similarity"] == 1.0
    assert details["token_overlap"] == 1.0

    # Empty candidate headline and preferred titles
    score, details = score_title(
        candidate_headline="",
        preferred_titles=[],
        job_title="Senior Backend Engineer",
    )
    assert score == Decimal("0.00")


def test_score_workplace() -> None:
    job = Job(
        id=uuid4(),
        title="Backend Engineer",
        canonical_company_name="Acme Corp",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        normalized_location="San Francisco, CA",
        status=JobStatusEnum.NORMALIZED,
    )
    profile = CandidateProfile(
        id=uuid4(),
        user_id=uuid4(),
        full_name="Alice Candidate",
        city="San Francisco",
        country="USA",
    )
    prefs = CandidatePreference(
        candidate_profile_id=profile.id,
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_locations=["San Francisco, CA"],
    )

    # 1. Exact preferred workplace match: 15.00 pts
    score, details = score_workplace(job, profile, prefs)
    assert score == Decimal("15.00")

    # 2. Unknown workplace: 8.00 pts
    job.workplace_type = WorkplaceTypeEnum.UNKNOWN
    score, details = score_workplace(job, profile, prefs)
    assert score == Decimal("8.00")

    # 3. Remote when not in preferred types: 12.00 pts
    prefs.preferred_workplace_types = [WorkplaceTypeEnum.ONSITE]
    job.workplace_type = WorkplaceTypeEnum.REMOTE
    score, details = score_workplace(job, profile, prefs)
    assert score == Decimal("12.00")

    # 4. Hybrid in candidate city: 12.00 pts
    prefs.preferred_workplace_types = [WorkplaceTypeEnum.REMOTE]
    job.workplace_type = WorkplaceTypeEnum.HYBRID
    job.normalized_location = "San Francisco, CA"
    score, details = score_workplace(job, profile, prefs)
    assert score == Decimal("12.00")

    # 5. Hybrid outside candidate city: 6.00 pts
    job.normalized_location = "New York, NY"
    score, details = score_workplace(job, profile, prefs)
    assert score == Decimal("6.00")

    # 6. Onsite in candidate city: 10.00 pts
    job.workplace_type = WorkplaceTypeEnum.ONSITE
    job.normalized_location = "San Francisco, CA"
    score, details = score_workplace(job, profile, prefs)
    assert score == Decimal("10.00")

    # 7. Onsite outside candidate city: 4.00 pts
    job.normalized_location = "Austin, TX"
    score, details = score_workplace(job, profile, prefs)
    assert score == Decimal("4.00")


def test_score_bonus_factors() -> None:
    now = datetime(2026, 11, 5, 12, 0, 0, tzinfo=UTC)
    job = Job(
        id=uuid4(),
        title="Senior Python Engineer",
        employment_type=EmploymentTypeEnum.FULL_TIME,
        posted_at=now - timedelta(days=1),  # fresh <= 3 days
    )
    prefs = CandidatePreference(
        candidate_profile_id=uuid4(),
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        preferred_titles=["Python Engineer"],
    )

    # Full bonus: +4 (employment type) + +3 (title match) + +3 (freshness) = 10.0 pts
    score, details = score_bonus_factors(job, prefs, now)
    assert score == Decimal("10.00")
    assert details["employment_type_bonus"] == 4.0
    assert details["target_title_bonus"] == 3.0
    assert details["freshness_bonus"] == 3.0

    # Expired freshness (> 3 days) and mismatched employment type
    job.posted_at = now - timedelta(days=5)
    job.employment_type = EmploymentTypeEnum.CONTRACT
    score, details = score_bonus_factors(job, prefs, now)
    assert score == Decimal("3.00")  # only title matches
    assert details["employment_type_bonus"] == 0.0
    assert details["freshness_bonus"] == 0.0


def test_calculate_deterministic_score_end_to_end() -> None:
    now = datetime(2026, 11, 5, 12, 0, 0, tzinfo=UTC)
    user_id = uuid4()
    profile = CandidateProfile(
        id=uuid4(),
        user_id=user_id,
        full_name="Bob Engineer",
        headline="Senior Backend Engineer",
        city="San Francisco",
        country="USA",
        total_experience_months=72,
    )
    profile.skills = [
        CandidateSkill(
            id=uuid4(),
            candidate_profile_id=profile.id,
            skill_name="Python",
            is_core=True,
        ),
        CandidateSkill(
            id=uuid4(),
            candidate_profile_id=profile.id,
            skill_name="PostgreSQL",
            is_core=True,
        ),
        CandidateSkill(
            id=uuid4(),
            candidate_profile_id=profile.id,
            skill_name="FastAPI",
            is_core=False,
        ),
    ]

    prefs = CandidatePreference(
        candidate_profile_id=profile.id,
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        preferred_titles=["Senior Backend Engineer"],
        preferred_locations=["San Francisco, CA"],
    )

    job = Job(
        id=uuid4(),
        title="Senior Backend Engineer",
        canonical_company_name="Tech Solutions",
        canonical_application_url="https://techsolutions.com/jobs/123",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        employment_type=EmploymentTypeEnum.FULL_TIME,
        normalized_location="San Francisco, CA",
        description_text="We need a Senior Backend Engineer with 5+ years of experience in Python, FastAPI, and PostgreSQL.",
        posted_at=now - timedelta(days=1),
        status=JobStatusEnum.NORMALIZED,
    )

    job_skills = {"python", "fastapi", "postgresql"}
    breakdown = calculate_deterministic_score(job, profile, prefs, job_skills, now=now)

    assert breakdown.skill_score == Decimal("40.00")
    assert breakdown.experience_score == Decimal("20.00")
    assert breakdown.title_score == Decimal("15.00")
    assert breakdown.preference_score == Decimal("15.00")
    assert breakdown.bonus_score == Decimal("10.00")
    assert breakdown.deterministic_score == Decimal("100.00")
    assert breakdown.final_score == Decimal("100.00")
    assert breakdown.details["total_score"] == 100.0


def test_bonus_and_deterministic_score_strict_boundaries() -> None:
    now = datetime(2026, 11, 5, 12, 0, 0, tzinfo=UTC)

    # 1. Zero bonus case
    old_job = Job(
        id=uuid4(),
        title="Ruby Developer",
        employment_type=EmploymentTypeEnum.CONTRACT,
        posted_at=now - timedelta(days=30),  # very old (> 3 days)
    )
    prefs = CandidatePreference(
        candidate_profile_id=uuid4(),
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],  # mismatch
        preferred_titles=["Python Engineer"],  # mismatch
    )
    zero_bonus, details = score_bonus_factors(old_job, prefs, now)
    assert zero_bonus == Decimal("0.00")
    assert Decimal("0.00") <= zero_bonus <= Decimal("10.00")

    # 2. Maximum bonus case
    fresh_job = Job(
        id=uuid4(),
        title="Python Engineer",
        employment_type=EmploymentTypeEnum.FULL_TIME,
        posted_at=now - timedelta(hours=2),  # fresh
    )
    max_bonus, details = score_bonus_factors(fresh_job, prefs, now)
    assert max_bonus == Decimal("10.00")
    assert Decimal("0.00") <= max_bonus <= Decimal("10.00")

    # 3. Minimum deterministic score boundary (completely empty profile against demanding job)
    empty_profile = CandidateProfile(
        id=uuid4(),
        user_id=uuid4(),
        full_name="Zero Exp",
        headline="",
        city=None,
        country=None,
        total_experience_months=0,
    )
    empty_profile.skills = []
    empty_prefs = CandidatePreference(
        candidate_profile_id=empty_profile.id,
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        preferred_titles=[],
        preferred_locations=[],
    )
    mismatch_job = Job(
        id=uuid4(),
        title="Chief Architect",
        canonical_company_name="Enterprise Corp",
        canonical_application_url="https://enterprise.com/jobs/1",
        workplace_type=WorkplaceTypeEnum.ONSITE,
        normalized_location="Tokyo, Japan",
        employment_type=EmploymentTypeEnum.CONTRACT,
        description_text="Must have 10 years experience in Cobol.",
        posted_at=now - timedelta(days=60),
        status=JobStatusEnum.NORMALIZED,
    )

    breakdown_min = calculate_deterministic_score(
        mismatch_job, empty_profile, empty_prefs, job_skills={"cobol"}, now=now
    )
    assert Decimal("0.00") <= breakdown_min.deterministic_score <= Decimal("100.00")
    assert Decimal("0.00") <= breakdown_min.bonus_score <= Decimal("10.00")
