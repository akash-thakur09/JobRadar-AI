"""Integration tests for Layer 1 Eligibility and Layer 2 Scoring against live PostgreSQL."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.database.health import check_db_health
from app.database.session import get_session_factory
from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    User,
    WorkplaceTypeEnum,
)
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.matching.service import MatchingService


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(
            f"Live PostgreSQL not reachable ({detail}). Skipping matching DB integration tests."
        )


@pytest.mark.integration
async def test_candidate_job_matching_lifecycle() -> None:
    """Verify Layer 1 Eligibility, Layer 2 Scoring, and Idempotent Upsert on live PostgreSQL."""
    session_factory = get_session_factory()
    service = MatchingService()

    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)

    async with session_factory() as session:
        # 1. Create User and Candidate Profile
        user = User(
            id=uuid.uuid4(),
            email=f"candidate_{suffix}@test.com",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Candidate {suffix}",
            headline="Senior Python Engineer",
            city="San Francisco",
            country="USA",
            total_experience_months=72,
        )
        session.add(profile)
        await session.flush()

        skills = [
            CandidateSkill(
                candidate_profile_id=profile.id,
                skill_name="Python",
                category="programming",
                experience_months=72,
                is_core=True,
            ),
            CandidateSkill(
                candidate_profile_id=profile.id,
                skill_name="FastAPI",
                category="framework",
                experience_months=48,
                is_core=True,
            ),
            CandidateSkill(
                candidate_profile_id=profile.id,
                skill_name="PostgreSQL",
                category="database",
                experience_months=60,
                is_core=True,
            ),
        ]
        session.add_all(skills)

        prefs = CandidatePreference(
            candidate_profile_id=profile.id,
            minimum_relevance_score=Decimal("70.00"),
            preferred_titles=["Python Engineer", "Backend Engineer"],
            preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
            preferred_locations=["San Francisco, CA"],
            preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
            max_job_age_days=14,
        )
        session.add(prefs)

        # 2. Create Job 1: High Match (Remote, Python/FastAPI/Postgres, Full-time)
        job1 = Job(
            id=uuid.uuid4(),
            canonical_company_name=f"TechCorp {suffix}",
            title="Senior Python Backend Engineer",
            canonical_application_url=f"https://techcorp{suffix}.com/jobs/101",
            workplace_type=WorkplaceTypeEnum.REMOTE,
            normalized_location="San Francisco, CA",
            employment_type=EmploymentTypeEnum.FULL_TIME,
            description_text="We need a Senior Python Engineer with experience in FastAPI and PostgreSQL.",
            posted_at=now - timedelta(days=1),
            first_seen_at=now - timedelta(days=1),
            last_seen_at=now,
            dedup_fingerprint_sha256=hashlib.sha256(f"job1_{suffix}".encode()).hexdigest(),
            status=JobStatusEnum.NORMALIZED,
        )

        # 3. Create Job 2: Location Ineligible (Onsite in New York while candidate wants Remote)
        job2 = Job(
            id=uuid.uuid4(),
            canonical_company_name=f"FinanceCorp {suffix}",
            title="Python Developer",
            canonical_application_url=f"https://financecorp{suffix}.com/jobs/202",
            workplace_type=WorkplaceTypeEnum.ONSITE,
            normalized_location="New York, NY",
            employment_type=EmploymentTypeEnum.FULL_TIME,
            description_text="Onsite Python Developer position in NYC headquarters.",
            posted_at=now - timedelta(days=1),
            first_seen_at=now - timedelta(days=1),
            last_seen_at=now,
            dedup_fingerprint_sha256=hashlib.sha256(f"job2_{suffix}".encode()).hexdigest(),
            status=JobStatusEnum.NORMALIZED,
        )

        session.add_all([job1, job2])
        await session.commit()

        cand_id = profile.id
        job1_id = job1.id
        job2_id = job2.id

    # 4. Evaluate Job 1 (Eligible & High Match)
    async with session_factory() as session:
        match1 = await service.evaluate_job_for_candidate(
            session=session,
            job_id=job1_id,
            candidate_profile_id=cand_id,
        )
        await session.commit()

        assert match1.eligibility_status == EligibilityStatusEnum.ELIGIBLE
        assert match1.deterministic_score >= Decimal("70.00")
        assert match1.final_score >= Decimal("70.00")
        assert match1.skill_score == Decimal("40.00")
        assert match1.title_score >= Decimal("10.00")
        assert match1.preference_score == Decimal("15.00")
        assert match1.is_qualified is True
        assert match1.match_explanation_details is not None
        assert "deterministic_breakdown" in match1.match_explanation_details

    # Verify Job 1 lifecycle status remains candidate-independent (NORMALIZED) in database
    async with session_factory() as session:
        saved_job1 = await session.get(Job, job1_id)
        assert saved_job1 is not None
        assert saved_job1.status == JobStatusEnum.NORMALIZED

    # 5. Evaluate Job 2 (Hard Gate Ineligible - Location mismatch)
    async with session_factory() as session:
        match2 = await service.evaluate_job_for_candidate(
            session=session,
            job_id=job2_id,
            candidate_profile_id=cand_id,
        )
        await session.commit()

        assert match2.eligibility_status == EligibilityStatusEnum.INELIGIBLE_LOCATION
        assert match2.deterministic_score == Decimal("0.00")
        assert match2.final_score == Decimal("0.00")
        assert match2.skill_score == Decimal("0.00")
        assert match2.is_qualified is False
        assert "onsite" in match2.match_explanation.lower()

    # Verify Job 2 lifecycle status remains candidate-independent (NORMALIZED) in database
    async with session_factory() as session:
        saved_job2 = await session.get(Job, job2_id)
        assert saved_job2 is not None
        assert saved_job2.status == JobStatusEnum.NORMALIZED

    # 6. Verify Idempotent Upsert & Reprocessing when Candidate changes
    async with session_factory() as session:
        # Candidate changes profile headline to exact match
        cand = await session.get(CandidateProfile, cand_id)
        assert cand is not None
        cand.headline = "Senior Python Backend Engineer"
        await session.commit()

    async with session_factory() as session:
        match1_repeat = await service.evaluate_job_for_candidate(
            session=session,
            job_id=job1_id,
            candidate_profile_id=cand_id,
        )
        await session.commit()

        # Same match row ID updated
        assert match1_repeat.id == match1.id
        # Title score improved to perfect 15.00 due to candidate change
        assert match1_repeat.title_score == Decimal("15.00")

        # Verify only 1 row exists for this candidate-job pair (no duplicates)
        stmt = select(JobMatch).where(
            JobMatch.candidate_profile_id == cand_id,
            JobMatch.job_id == job1_id,
        )
        rows = (await session.execute(stmt)).scalars().all()
        assert len(rows) == 1

    # 7. Verify List and Filter Matches
    async with session_factory() as session:
        # Filter by min_score 70.0
        paginated_high = await service.list_matches(
            session=session,
            candidate_profile_id=cand_id,
            min_score=Decimal("70.00"),
        )
        assert paginated_high.pagination.total_items == 1
        assert paginated_high.items[0].job_id == job1_id

        # Filter by eligibility status ELIGIBLE
        paginated_eligible = await service.list_matches(
            session=session,
            candidate_profile_id=cand_id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        )
        assert paginated_eligible.pagination.total_items == 1

        # Detail fetch
        detail = await service.get_match(session=session, match_id=match1.id)
        assert detail.id == match1.id
        assert detail.company_name == f"TechCorp {suffix}"
        assert detail.job is not None
        assert detail.job.id == job1_id


@pytest.mark.integration
async def test_batch_unmatched_evaluation() -> None:
    """Verify batch evaluation of pending un-matched jobs for a candidate on live DB."""
    session_factory = get_session_factory()
    service = MatchingService()

    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)

    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"batch_cand_{suffix}@test.com",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Batch Candidate {suffix}",
            headline="Full Stack Engineer",
            city="San Francisco",
            country="USA",
            total_experience_months=48,
        )
        session.add(profile)
        await session.flush()

        skills = [
            CandidateSkill(
                candidate_profile_id=profile.id,
                skill_name="Python",
                category="programming",
                experience_months=48,
                is_core=True,
            ),
            CandidateSkill(
                candidate_profile_id=profile.id,
                skill_name="TypeScript",
                category="programming",
                experience_months=36,
                is_core=True,
            ),
        ]
        session.add_all(skills)

        prefs = CandidatePreference(
            candidate_profile_id=profile.id,
            minimum_relevance_score=Decimal("60.00"),
            preferred_titles=["Full Stack Engineer"],
            preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
            preferred_locations=["San Francisco, CA"],
            preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
            max_job_age_days=14,
        )
        session.add(prefs)

        # Create 3 canonical jobs without matches
        jobs = [
            Job(
                id=uuid.uuid4(),
                canonical_company_name=f"BatchCo_{i}_{suffix}",
                title=f"Full Stack Developer {i}",
                canonical_application_url=f"https://batchco{i}_{suffix}.com/jobs/1",
                workplace_type=WorkplaceTypeEnum.REMOTE,
                normalized_location="San Francisco, CA",
                employment_type=EmploymentTypeEnum.FULL_TIME,
                description_text="Full stack position requiring Python and TypeScript.",
                posted_at=now - timedelta(days=1),
                first_seen_at=now - timedelta(days=1),
                last_seen_at=now,
                dedup_fingerprint_sha256=hashlib.sha256(
                    f"batch_job_{i}_{suffix}".encode()
                ).hexdigest(),
                status=JobStatusEnum.NORMALIZED,
            )
            for i in range(3)
        ]
        session.add_all(jobs)
        await session.commit()

        cand_id = profile.id

    async with session_factory() as session:
        evaluated_count = await service.evaluate_pending_job_matches(
            session=session,
            candidate_profile_id=cand_id,
            batch_size=10,
        )
        await session.commit()
        assert evaluated_count >= 3

    # Verify the 3 batch jobs now have matches for this candidate
    batch_job_ids = [j.id for j in jobs]
    async with session_factory() as session:
        stmt = select(JobMatch).where(
            JobMatch.candidate_profile_id == cand_id,
            JobMatch.job_id.in_(batch_job_ids),
        )
        matches = (await session.execute(stmt)).scalars().all()
        assert len(matches) == 3
        for m in matches:
            assert m.eligibility_status == EligibilityStatusEnum.ELIGIBLE
            assert m.deterministic_score >= Decimal("50.00")


@pytest.mark.integration
async def test_multi_candidate_database_isolation() -> None:
    """Verify that multiple candidates evaluating the same Job have isolated JobMatch records and Job.status remains candidate-independent on PostgreSQL."""
    session_factory = get_session_factory()
    service = MatchingService()

    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)

    async with session_factory() as session:
        # 1. Candidate A (Senior Python Engineer)
        user_a = User(
            id=uuid.uuid4(),
            email=f"cand_a_{suffix}@test.com",
            is_active=True,
        )
        session.add(user_a)
        await session.flush()

        profile_a = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user_a.id,
            full_name=f"Candidate A {suffix}",
            headline="Senior Python Engineer",
            city="San Francisco",
            country="USA",
            total_experience_months=72,
        )
        session.add(profile_a)
        await session.flush()

        session.add(
            CandidateSkill(
                candidate_profile_id=profile_a.id,
                skill_name="Python",
                category="programming",
                experience_months=72,
                is_core=True,
            )
        )
        session.add(
            CandidatePreference(
                candidate_profile_id=profile_a.id,
                preferred_titles=["Python Engineer"],
                preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
                preferred_locations=["San Francisco, CA"],
                preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
                max_job_age_days=14,
            )
        )

        # 2. Candidate B (Junior Frontend Developer)
        user_b = User(
            id=uuid.uuid4(),
            email=f"cand_b_{suffix}@test.com",
            is_active=True,
        )
        session.add(user_b)
        await session.flush()

        profile_b = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user_b.id,
            full_name=f"Candidate B {suffix}",
            headline="Junior Frontend Developer",
            city="San Francisco",
            country="USA",
            total_experience_months=12,
        )
        session.add(profile_b)
        await session.flush()

        session.add(
            CandidateSkill(
                candidate_profile_id=profile_b.id,
                skill_name="CSS",
                category="frontend",
                experience_months=12,
                is_core=True,
            )
        )
        session.add(
            CandidatePreference(
                candidate_profile_id=profile_b.id,
                preferred_titles=["Frontend Developer"],
                preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
                preferred_locations=["San Francisco, CA"],
                preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
                max_job_age_days=14,
            )
        )

        # 3. Single Canonical Job X
        job_x = Job(
            id=uuid.uuid4(),
            canonical_company_name=f"SharedCorp_{suffix}",
            title="Senior Python Backend Engineer",
            canonical_application_url=f"https://sharedcorp{suffix}.com/jobs/1",
            workplace_type=WorkplaceTypeEnum.REMOTE,
            normalized_location="San Francisco, CA",
            employment_type=EmploymentTypeEnum.FULL_TIME,
            description_text="Senior Python Backend Engineer with 5 years experience.",
            posted_at=now - timedelta(days=1),
            first_seen_at=now - timedelta(days=1),
            last_seen_at=now,
            dedup_fingerprint_sha256=hashlib.sha256(f"job_x_{suffix}".encode()).hexdigest(),
            status=JobStatusEnum.NORMALIZED,
        )
        session.add(job_x)
        await session.commit()

        cand_a_id = profile_a.id
        cand_b_id = profile_b.id
        job_id = job_x.id

    # Evaluate Candidate A
    async with session_factory() as session:
        match_a = await service.evaluate_job_for_candidate(
            session=session,
            job_id=job_id,
            candidate_profile_id=cand_a_id,
        )
        await session.commit()
        assert match_a.is_qualified is True
        assert match_a.deterministic_score >= Decimal("70.00")

    # Evaluate Candidate B
    async with session_factory() as session:
        match_b = await service.evaluate_job_for_candidate(
            session=session,
            job_id=job_id,
            candidate_profile_id=cand_b_id,
        )
        await session.commit()
        assert match_b.is_qualified is False
        assert match_b.deterministic_score < Decimal("50.00")

    # Verify Database Invariants
    async with session_factory() as session:
        # Invariant 1: Canonical Job.status remains NORMALIZED
        saved_job = await session.get(Job, job_id)
        assert saved_job is not None
        assert saved_job.status == JobStatusEnum.NORMALIZED

        # Invariant 2: Exactly two independent match records exist for this Job
        stmt = select(JobMatch).where(JobMatch.job_id == job_id)
        matches = (await session.execute(stmt)).scalars().all()
        assert len(matches) == 2

        matches_by_cand = {m.candidate_profile_id: m for m in matches}
        assert matches_by_cand[cand_a_id].is_qualified is True
        assert matches_by_cand[cand_b_id].is_qualified is False
        assert matches_by_cand[cand_a_id].id != matches_by_cand[cand_b_id].id
