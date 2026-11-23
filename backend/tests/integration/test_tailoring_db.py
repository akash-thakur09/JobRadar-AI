"""Integration tests for Resume Tailoring and PDF generation against live PostgreSQL."""

import hashlib
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.health import check_db_health
from app.database.session import get_session_factory
from app.modules.candidate.models import CandidateProfile, CandidateSkill, User
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.resumes.models import MasterResume, ResumeVersion
from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum
from app.modules.tailoring.models import TailoredResume
from app.modules.tailoring.repository import TailoringRepository
from app.modules.tailoring.schemas import TailorResumeRequest
from app.modules.tailoring.service import TailoringService


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(f"Live PostgreSQL not reachable ({detail}). Skipping integration test.")


@pytest.mark.integration
async def test_tailored_resume_db_lifecycle() -> None:
    """Verify end-to-end tailoring pipeline execution and DB persistence against live PostgreSQL."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        # 1. Create candidate user & profile
        user = User(
            id=uuid.uuid4(),
            email=f"candidate_{suffix}@tailortest.com",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Taylor Candidate {suffix}",
            headline="Senior Backend Architect",
            professional_summary="Senior developer with deep Python and database expertise.",
            total_experience_months=72,
        )
        session.add(profile)

        # 2. Add Candidate Skills
        skill1 = CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            skill_name="Python",
            category="Languages",
            experience_months=72,
            is_core=True,
        )
        skill2 = CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            skill_name="PostgreSQL",
            category="Databases",
            experience_months=60,
            is_core=True,
        )
        session.add_all([skill1, skill2])

        # 3. Create Master Resume & Parsed Resume Version
        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="master_resume.pdf",
            storage_key=f"resumes/raw/{profile.id}/master.pdf",
            mime_type="application/pdf",
            file_size_bytes=4096,
            checksum_sha256=hashlib.sha256(suffix.encode()).hexdigest(),
            is_active=True,
        )
        session.add(master_resume)
        await session.flush()

        resume_version = ResumeVersion(
            id=uuid.uuid4(),
            master_resume_id=master_resume.id,
            version_number=1,
            structured_content={
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
                "experience": [
                    {
                        "company": "Acme Corp",
                        "title": "Senior Software Engineer",
                        "bullet_points": [
                            "Architected high-throughput async data ingestion services using FastAPI.",
                            "Optimized database indexing and queries, supporting critical production workloads.",
                        ],
                    }
                ],
            },
            template_metadata={"preservation_capability": "LIMITED"},
            checksum_sha256=master_resume.checksum_sha256,
            is_valid=True,
            processing_status="COMPLETED",
        )
        session.add(resume_version)

        # 4. Create Canonical Job
        job = Job(
            id=uuid.uuid4(),
            canonical_company_name="Cloudscale Inc",
            title="Senior Backend Engineer",
            canonical_application_url=f"https://cloudscale.test/jobs/{suffix}",
            description_text="Seeking Senior Backend Engineer proficient in Python, FastAPI, and PostgreSQL.",
            dedup_fingerprint_sha256=hashlib.sha256(f"job_{suffix}".encode()).hexdigest(),
            status=JobStatusEnum.MATCHED,
        )
        session.add(job)
        await session.flush()

        # 5. Create Qualified JobMatch (score >= 50 and ELIGIBLE)
        job_match = JobMatch(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_profile_id=profile.id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
            deterministic_score=Decimal("82.00"),
            final_score=Decimal("82.00"),
            match_explanation="Eligible and high matching score.",
        )
        session.add(job_match)
        await session.commit()

    # 6. Execute Tailoring Request & Pipeline
    service = TailoringService()

    async with session_factory() as session:
        req = TailorResumeRequest(job_match_id=job_match.id)
        tailored_record = await service.request_tailoring(session, req)
        await session.commit()

        assert tailored_record.generation_status == TailoredResumeStatusEnum.PENDING
        assert tailored_record.job_id == job.id
        assert tailored_record.resume_version_id == resume_version.id

    async with session_factory() as session:
        # Execute pipeline
        completed_record = await service.execute_tailoring_pipeline(session, tailored_record.id)
        await session.commit()

        assert completed_record.generation_status == TailoredResumeStatusEnum.COMPLETED
        assert completed_record.file_name is not None
        assert completed_record.file_size_bytes is not None
        assert completed_record.file_size_bytes > 500
        assert completed_record.checksum_sha256 is not None
        assert completed_record.completed_at is not None
        assert completed_record.tailored_content != {}
        assert completed_record.validation_metadata != {}
        assert completed_record.rendering_strategy == RenderingStrategyEnum.FALLBACK
        assert completed_record.validation_metadata.get("fallback_reason") is not None
        assert "LIMITED" in completed_record.validation_metadata["fallback_reason"]

    # 7. Verify Queries
    async with session_factory() as session:
        repo = TailoringRepository()
        by_id = await repo.get_by_id(session, tailored_record.id)
        assert by_id is not None
        assert by_id.candidate_profile.full_name == profile.full_name

        by_job_ver = await repo.get_by_job_and_version(session, job.id, resume_version.id)
        assert by_job_ver is not None
        assert by_job_ver.id == tailored_record.id

        items, total_count = await repo.list_for_candidate(session, profile.id)
        assert total_count == 1
        assert items[0].id == tailored_record.id


@pytest.mark.integration
async def test_tailored_resume_db_preservation_strategy() -> None:
    """Verify live PostgreSQL persistence when preservation capability is SUPPORTED."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        user = User(id=uuid.uuid4(), email=f"pres_{suffix}@test.com")
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Preserved Candidate {suffix}",
            headline="Lead Architect",
            professional_summary="Architect with 10 years experience in Python and PostgreSQL.",
            total_experience_months=120,
        )
        session.add(profile)

        skill = CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            skill_name="Python",
            category="Languages",
            is_core=True,
        )
        session.add(skill)

        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="master.pdf",
            storage_key=f"resumes/raw/{profile.id}/m.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048,
            checksum_sha256=hashlib.sha256(f"pres_{suffix}".encode()).hexdigest(),
        )
        session.add(master_resume)
        await session.flush()

        # template_metadata indicates SUPPORTED preservation
        resume_version = ResumeVersion(
            id=uuid.uuid4(),
            master_resume_id=master_resume.id,
            version_number=1,
            structured_content={
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "experience": [
                    {
                        "company": "Acme Corp",
                        "title": "Lead Architect",
                        "bullet_points": ["Engineered distributed core services."],
                    }
                ],
            },
            template_metadata={
                "preservation_capability": "SUPPORTED",
                "fonts": ["Georgia-Bold", "Georgia", "Times-Roman"],
                "page_count": 1,
            },
            checksum_sha256=master_resume.checksum_sha256,
            is_valid=True,
            processing_status="COMPLETED",
        )
        session.add(resume_version)

        job = Job(
            id=uuid.uuid4(),
            canonical_company_name="Apex Corp",
            title="Lead Backend Architect",
            canonical_application_url=f"https://apex.test/jobs/{suffix}",
            description_text="Seeking Lead Architect proficient in Python.",
            dedup_fingerprint_sha256=hashlib.sha256(f"pres_j_{suffix}".encode()).hexdigest(),
            status=JobStatusEnum.MATCHED,
        )
        session.add(job)
        await session.flush()

        job_match = JobMatch(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_profile_id=profile.id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
            deterministic_score=Decimal("85.00"),
            final_score=Decimal("85.00"),
            match_explanation="Eligible match.",
        )
        session.add(job_match)
        await session.commit()

        job_match_id = job_match.id

    service = TailoringService()
    async with session_factory() as session:
        record = await service.request_tailoring(
            session=session,
            request=TailorResumeRequest(job_match_id=job_match_id),
        )
        await session.commit()
        record_id = record.id

    async with session_factory() as session:
        completed = await service.execute_tailoring_pipeline(session, record_id)
        await session.commit()

        # Verify strategy is genuinely PRESERVED in database
        assert completed.rendering_strategy == RenderingStrategyEnum.PRESERVED
        assert completed.generation_status == TailoredResumeStatusEnum.COMPLETED
        assert completed.validation_metadata.get("fallback_reason") is None
        assert completed.validation_metadata.get("actual_strategy") == "PRESERVED"
        assert completed.checksum_sha256 is not None
        assert completed.file_size_bytes is not None and completed.file_size_bytes > 500


@pytest.mark.integration
async def test_tailored_resume_db_unique_constraint() -> None:
    """Attempting to persist duplicate records for same (job_id, resume_version_id) raises IntegrityError."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        user = User(id=uuid.uuid4(), email=f"unique_{suffix}@test.com")
        session.add(user)
        await session.flush()

        profile = CandidateProfile(id=uuid.uuid4(), user_id=user.id, full_name=f"Unique {suffix}")
        session.add(profile)

        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="res.pdf",
            storage_key="k",
            mime_type="application/pdf",
            file_size_bytes=100,
            checksum_sha256=hashlib.sha256(f"m_{suffix}".encode()).hexdigest(),
        )
        session.add(master_resume)
        await session.flush()

        version = ResumeVersion(
            id=uuid.uuid4(),
            master_resume_id=master_resume.id,
            version_number=1,
            checksum_sha256=master_resume.checksum_sha256,
        )
        session.add(version)

        job = Job(
            id=uuid.uuid4(),
            canonical_company_name="Corp",
            title="Dev",
            canonical_application_url="http://app",
            description_text="Desc",
            dedup_fingerprint_sha256=hashlib.sha256(f"j_{suffix}".encode()).hexdigest(),
        )
        session.add(job)
        await session.flush()

        job_match = JobMatch(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_profile_id=profile.id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
            deterministic_score=Decimal("80.00"),
            match_explanation="Ok",
        )
        session.add(job_match)

        rec1 = TailoredResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            resume_version_id=version.id,
            generation_status=TailoredResumeStatusEnum.PENDING,
        )
        session.add(rec1)
        await session.commit()

    async with session_factory() as session:
        rec2 = TailoredResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            resume_version_id=version.id,
            generation_status=TailoredResumeStatusEnum.PENDING,
        )
        session.add(rec2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.integration
async def test_tailored_resume_db_cascade_deletion() -> None:
    """Deleting CandidateProfile cascades and deletes associated TailoredResume records."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        user = User(id=uuid.uuid4(), email=f"cascade_{suffix}@test.com")
        session.add(user)
        await session.flush()

        profile = CandidateProfile(id=uuid.uuid4(), user_id=user.id, full_name=f"Cascade {suffix}")
        session.add(profile)

        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="res.pdf",
            storage_key="k",
            mime_type="application/pdf",
            file_size_bytes=100,
            checksum_sha256=hashlib.sha256(f"cas_{suffix}".encode()).hexdigest(),
        )
        session.add(master_resume)
        await session.flush()

        version = ResumeVersion(
            id=uuid.uuid4(),
            master_resume_id=master_resume.id,
            version_number=1,
            checksum_sha256=master_resume.checksum_sha256,
        )
        session.add(version)

        job = Job(
            id=uuid.uuid4(),
            canonical_company_name="Corp",
            title="Dev",
            canonical_application_url="http://app",
            description_text="Desc",
            dedup_fingerprint_sha256=hashlib.sha256(f"cas_j_{suffix}".encode()).hexdigest(),
        )
        session.add(job)
        await session.flush()

        job_match = JobMatch(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_profile_id=profile.id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
            deterministic_score=Decimal("80.00"),
            match_explanation="Ok",
        )
        session.add(job_match)

        tailored_resume = TailoredResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            resume_version_id=version.id,
            generation_status=TailoredResumeStatusEnum.PENDING,
        )
        session.add(tailored_resume)
        await session.commit()

        tailored_id = tailored_resume.id
        profile_id = profile.id

    # Delete CandidateProfile
    async with session_factory() as session:
        prof = await session.get(CandidateProfile, profile_id)
        assert prof is not None
        await session.delete(prof)
        await session.commit()

    # Verify TailoredResume was cascade-deleted
    async with session_factory() as session:
        res = await session.execute(select(TailoredResume).where(TailoredResume.id == tailored_id))
        assert res.scalar_one_or_none() is None
