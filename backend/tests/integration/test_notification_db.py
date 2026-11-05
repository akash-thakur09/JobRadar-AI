"""Integration tests for Email Notification Delivery against live PostgreSQL."""

import hashlib
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.health import check_db_health
from app.database.session import get_session_factory
from app.infrastructure.storage.local import LocalFileStorage
from app.modules.candidate.models import CandidateProfile, User
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.notifications.email.mock_provider import MockEmailProvider
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.models import NotificationDelivery
from app.modules.notifications.service import NotificationService
from app.modules.resumes.models import MasterResume, ResumeVersion
from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum
from app.modules.tailoring.models import TailoredResume


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(f"Live PostgreSQL not reachable ({detail}). Skipping integration test.")


@pytest.mark.integration
async def test_notification_delivery_db_lifecycle(tmp_path) -> None:
    """Verify end-to-end notification delivery execution and DB persistence against live PostgreSQL."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]
    storage = LocalFileStorage(base_dir=str(tmp_path / "storage"))
    mock_email_provider = MockEmailProvider()

    async with session_factory() as session:
        # 1. Create candidate user & profile
        user = User(
            id=uuid.uuid4(),
            email=f"candidate_{suffix}@deliverytest.com",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Delivery Candidate {suffix}",
            headline="Principal Cloud Architect",
            total_experience_months=84,
        )
        session.add(profile)

        # 2. Add canonical job
        job = Job(
            id=uuid.uuid4(),
            canonical_company_name=f"RoboTech_{suffix}",
            title="Senior Infrastructure Architect",
            canonical_application_url=f"https://robotech_{suffix}.com/jobs/99",
            description_text="Leading cloud architecture and Kubernetes orchestration.",
            dedup_fingerprint_sha256=hashlib.sha256(f"job_{suffix}".encode()).hexdigest(),
            status=JobStatusEnum.TAILORED,
        )
        session.add(job)

        # 3. Add JobMatch
        job_match = JobMatch(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_profile_id=profile.id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
            deterministic_score=Decimal("85.00"),
            final_score=Decimal("88.00"),
            skill_score=Decimal("90.00"),
            experience_score=Decimal("85.00"),
            title_score=Decimal("80.00"),
            preference_score=Decimal("85.00"),
            match_explanation="Candidate possesses deep infrastructure expertise.",
        )
        session.add(job_match)

        # 4. Add Master Resume & Version
        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="master.pdf",
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
            structured_content={"skills": ["Python", "Kubernetes"]},
            template_metadata={"preservation_capability": "LIMITED"},
            checksum_sha256=master_resume.checksum_sha256,
            is_valid=True,
            processing_status="COMPLETED",
        )
        session.add(resume_version)
        await session.flush()

        # 5. Add Tailored Resume and store valid PDF
        pdf_bytes = b"%PDF-1.4 test valid PDF content for delivery"
        checksum = hashlib.sha256(pdf_bytes).hexdigest()
        storage_key = f"resumes/tailored/{profile.id}/tailored_{suffix}.pdf"
        await storage.save(storage_key, pdf_bytes, content_type="application/pdf")

        tailored_resume = TailoredResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            resume_version_id=resume_version.id,
            rendering_strategy=RenderingStrategyEnum.PRESERVED,
            generation_status=TailoredResumeStatusEnum.COMPLETED,
            storage_key=storage_key,
            file_name=f"Candidate_{suffix}_Tailored.pdf",
            checksum_sha256=checksum,
            file_size_bytes=len(pdf_bytes),
        )
        session.add(tailored_resume)
        await session.commit()

    # 6. Initialize notification service and execute delivery pipeline
    service = NotificationService(
        storage=storage,
        email_provider=mock_email_provider,
    )

    async with session_factory() as session:
        # A. Create notification delivery record
        delivery = await service.create_or_get_delivery_for_tailored_resume(
            session=session,
            tailored_resume_id=tailored_resume.id,
        )
        await session.commit()

        assert delivery.status == NotificationDeliveryStatusEnum.PENDING
        assert delivery.recipient_email == f"candidate_{suffix}@deliverytest.com"

        # B. Idempotency test: repeating creation returns same record
        delivery_dup = await service.create_or_get_delivery_for_tailored_resume(
            session=session,
            tailored_resume_id=tailored_resume.id,
        )
        assert delivery_dup.id == delivery.id

        # C. Execute delivery pipeline
        delivered = await service.execute_delivery_pipeline(
            session=session,
            delivery_id=delivery.id,
        )
        await session.commit()

        assert delivered.status == NotificationDeliveryStatusEnum.SENT
        assert delivered.sent_at is not None
        assert delivered.provider_message_id is not None
        assert delivered.attempt_count == 1
        assert mock_email_provider.sent_count == 1

        # D. Verify job status updated to NOTIFIED
        reloaded_job = await session.get(Job, job.id)
        assert reloaded_job is not None
        assert reloaded_job.status == JobStatusEnum.NOTIFIED

        # E. Verify SENT terminal state idempotency
        second_run = await service.execute_delivery_pipeline(
            session=session,
            delivery_id=delivery.id,
        )
        assert second_run.status == NotificationDeliveryStatusEnum.SENT
        # Crucial check: email provider was NOT called a second time
        assert mock_email_provider.sent_count == 1


@pytest.mark.integration
async def test_notification_delivery_unique_constraint() -> None:
    """Database unique constraint uq_notification_deliveries_job_recipient prevents duplicate records."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        user = User(id=uuid.uuid4(), email=f"user_{suffix}@uniqtest.com")
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name="Uniq Candidate",
        )
        session.add(profile)

        job = Job(
            id=uuid.uuid4(),
            canonical_company_name="Uniq Corp",
            title="Software Architect",
            canonical_application_url="https://uniqcorp.com/apply",
            description_text="Leading software architecture.",
            dedup_fingerprint_sha256=hashlib.sha256(f"uniq_job_{suffix}".encode()).hexdigest(),
        )
        session.add(job)

        job_match = JobMatch(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_profile_id=profile.id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
            final_score=Decimal("80.00"),
            match_explanation="Fit",
        )
        session.add(job_match)

        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="master.pdf",
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
            structured_content={"skills": ["Python"]},
            template_metadata={"preservation_capability": "LIMITED"},
            checksum_sha256=master_resume.checksum_sha256,
            is_valid=True,
            processing_status="COMPLETED",
        )
        session.add(resume_version)
        await session.flush()

        tailored_resume = TailoredResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            resume_version_id=resume_version.id,
            rendering_strategy=RenderingStrategyEnum.FALLBACK,
            generation_status=TailoredResumeStatusEnum.COMPLETED,
            file_name="Resume.pdf",
            storage_key="key",
        )
        session.add(tailored_resume)
        await session.flush()

        # Insert first notification delivery
        d1 = NotificationDelivery(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            tailored_resume_id=tailored_resume.id,
            recipient_email=f"user_{suffix}@uniqtest.com",
            status=NotificationDeliveryStatusEnum.PENDING,
        )
        session.add(d1)
        await session.commit()

    # Attempt to insert second notification delivery with identical job_id and recipient_email
    async with session_factory() as session:
        d2 = NotificationDelivery(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            tailored_resume_id=tailored_resume.id,
            recipient_email=f"user_{suffix}@uniqtest.com",
            status=NotificationDeliveryStatusEnum.PENDING,
        )
        session.add(d2)

        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()

        assert "uq_notification_deliveries_job_recipient" in str(exc_info.value)


@pytest.mark.integration
async def test_notification_delivery_cascade_deletion() -> None:
    """Deleting a CandidateProfile cascades and cleanly removes associated NotificationDelivery records."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]
    delivery_id = uuid.uuid4()

    async with session_factory() as session:
        user = User(id=uuid.uuid4(), email=f"user_{suffix}@cascadetest.com")
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name="Cascade Candidate",
        )
        session.add(profile)

        job = Job(
            id=uuid.uuid4(),
            canonical_company_name="Cascade Corp",
            title="Architect",
            canonical_application_url="https://cascade.com",
            description_text="Description",
            dedup_fingerprint_sha256=hashlib.sha256(f"cascade_job_{suffix}".encode()).hexdigest(),
        )
        session.add(job)

        job_match = JobMatch(
            id=uuid.uuid4(),
            job_id=job.id,
            candidate_profile_id=profile.id,
            eligibility_status=EligibilityStatusEnum.ELIGIBLE,
            final_score=Decimal("80.00"),
            match_explanation="Fit",
        )
        session.add(job_match)

        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="master.pdf",
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
            structured_content={"skills": ["Python"]},
            template_metadata={"preservation_capability": "LIMITED"},
            checksum_sha256=master_resume.checksum_sha256,
            is_valid=True,
            processing_status="COMPLETED",
        )
        session.add(resume_version)
        await session.flush()

        tailored_resume = TailoredResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            resume_version_id=resume_version.id,
            rendering_strategy=RenderingStrategyEnum.FALLBACK,
            generation_status=TailoredResumeStatusEnum.COMPLETED,
            file_name="Resume.pdf",
            storage_key="key",
        )
        session.add(tailored_resume)
        await session.flush()

        delivery = NotificationDelivery(
            id=delivery_id,
            candidate_profile_id=profile.id,
            job_id=job.id,
            job_match_id=job_match.id,
            tailored_resume_id=tailored_resume.id,
            recipient_email=f"user_{suffix}@cascadetest.com",
            status=NotificationDeliveryStatusEnum.PENDING,
        )
        session.add(delivery)
        await session.commit()

        # Delete user (cascades to profile)
        reloaded_user = await session.get(User, user.id)
        assert reloaded_user is not None
        await session.delete(reloaded_user)
        await session.commit()

    # Query in a fresh database session to verify Postgres level ON DELETE CASCADE
    async with session_factory() as verify_session:
        deleted_delivery_query = await verify_session.execute(
            select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        )
        assert deleted_delivery_query.scalar_one_or_none() is None
