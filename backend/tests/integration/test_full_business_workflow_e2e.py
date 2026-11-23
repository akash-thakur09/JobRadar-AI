"""Comprehensive End-to-End Business Workflow Integration Test.

Validates the complete 13-stage lifecycle for JobRadar AI:
 1. Candidate profile creation & configuration
 2. Master resume upload
 3. Resume parsing & validation
 4. Job discovery through Greenhouse & Lever
 5. Job normalization & duplicate detection
 6. Candidate-specific eligibility evaluation
 7. Deterministic matching & weighted scoring
 8. LLM semantic analysis
 9. Truthful resume tailoring & claim validation
 10. Tailored PDF generation & download
 11. Email notification delivery
 12. Pipeline execution & monitoring
 13. Notification history & retry behavior
"""

import io
import uuid
from decimal import Decimal
import pytest
from reportlab.pdfgen import canvas

from unittest.mock import patch

from app.database.session import get_session_factory
from app.infrastructure.storage.local import LocalFileStorage
from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    User,
    WorkplaceTypeEnum,
)
from app.modules.candidate.service import CandidateService
from app.modules.discovery.adapters.base import (
    DiscoveryResult,
    JobSourceAdapter,
    RawDiscoveredJob,
)
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.discovery.service import DiscoveryService
from app.modules.jobs.models import JobSourceRecord
from app.modules.jobs.service import JobService
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.models import EligibilityStatusEnum, SemanticAnalysisStatusEnum
from app.modules.matching.semantic_service import SemanticAnalysisService
from app.modules.matching.service import MatchingService
from app.modules.notifications.email.mock_provider import MockEmailProvider
from app.modules.notifications.models import (
    NotificationDelivery,
    NotificationDeliveryStatusEnum,
)
from app.modules.notifications.service import NotificationService
from app.modules.pipeline.enums import PipelineRunStatusEnum, PipelineTriggerTypeEnum
from app.modules.pipeline.service import PipelineOrchestrationService
from app.modules.resumes.service import ResumeService
from app.modules.tailoring.enums import TailoredResumeStatusEnum
from app.modules.tailoring.schemas import TailorResumeRequest
from app.modules.tailoring.service import TailoringService


class MockDiscoveryAdapter(JobSourceAdapter):
    """Controlled mock discovery adapter for Stage 12 pipeline run."""

    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.GREENHOUSE

    def validate_configuration(self, configuration: dict) -> None:  # noqa: ARG002
        pass

    async def discover_jobs(
        self,
        base_url: str,  # noqa: ARG002
        configuration: dict,  # noqa: ARG002
    ) -> DiscoveryResult:
        return DiscoveryResult(
            source_identifier="acme",
            source_type=JobSourceTypeEnum.GREENHOUSE,
            jobs=[
                RawDiscoveredJob(
                    external_id="gh-e2e-stage12",
                    source_url="https://acme.greenhouse.io/jobs/gh-e2e-stage12",
                    raw_payload={
                        "id": "gh-stage12-101",
                        "title": "Principal Systems Architect",
                        "content": "Seeking Principal Systems Architect with Python and Kubernetes expertise.",
                        "location": {"name": "Remote"},
                        "updated_at": "2026-11-10T12:00:00Z",
                    },
                )
            ],
        )


def _generate_valid_test_pdf() -> bytes:
    """Generate a valid, parseable PDF binary using ReportLab."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 750, "Alex Mercer")
    c.drawString(50, 730, "Principal Systems Architect")
    c.drawString(50, 700, "Skills: Python, FastAPI, PostgreSQL, Docker, Kubernetes, Redis")
    c.drawString(50, 670, "Experience: Staff Engineer at TechCorp 2020-Present")
    c.drawString(50, 650, "Engineered distributed cloud platforms with Python and FastAPI.")
    c.drawString(50, 620, "Education: BS Computer Science, 2018")
    c.save()
    return buf.getvalue()


@pytest.mark.integration
async def test_complete_13_stage_business_workflow(tmp_path, monkeypatch) -> None:
    """Execute and validate all 13 core business workflow stages in order."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]
    monkeypatch.setenv("NOTIFICATION_RECIPIENT_EMAIL", "qa-recipient@example.test")
    storage = LocalFileStorage(base_dir=str(tmp_path / "storage"))
    mock_email_provider = MockEmailProvider()
    mock_llm_provider = MockLLMProvider()

    candidate_service = CandidateService()
    resume_service = ResumeService(storage=storage, candidate_service=candidate_service)
    discovery_service = DiscoveryService()
    job_service = JobService()
    matching_service = MatchingService()
    semantic_service = SemanticAnalysisService(llm_provider=mock_llm_provider)
    tailoring_service = TailoringService(storage=storage, llm_provider=mock_llm_provider)
    notification_service = NotificationService(storage=storage, email_provider=mock_email_provider)
    pipeline_service = PipelineOrchestrationService(
        candidate_repository=candidate_service.repository,
        discovery_repository=discovery_service.repository,
        job_service=job_service,
        matching_service=matching_service,
        semantic_service=semantic_service,
        tailoring_service=tailoring_service,
        notification_service=notification_service,
    )

    async with session_factory() as session:
        # =====================================================================
        # STAGE 1: Candidate Profile Creation & Configuration
        # =====================================================================
        profile = await candidate_service.get_profile(session)
        profile.full_name = f"Alex Mercer {suffix}"
        profile.headline = "Principal Systems Architect"
        profile.professional_summary = "Over 8 years of experience building distributed systems in Python, FastAPI, and Kubernetes."
        profile.total_experience_months = 96
        profile.work_authorization = "US Citizen"
        profile.city = "San Francisco"
        profile.country = "USA"

        pref = await candidate_service.get_preferences(session)
        pref.minimum_relevance_score = Decimal("60.00")
        pref.preferred_titles = ["Principal Systems Architect", "Staff Cloud Engineer", "Senior Software Engineer"]
        pref.preferred_workplace_types = [WorkplaceTypeEnum.REMOTE, WorkplaceTypeEnum.HYBRID]
        pref.preferred_employment_types = [EmploymentTypeEnum.FULL_TIME]
        pref.max_job_age_days = 30

        existing_skill_names = {s.skill_name for s in profile.skills}
        new_skills = [
            CandidateSkill(
                candidate_profile_id=profile.id,
                skill_name=s,
                category="Technical",
                experience_months=80,
                is_core=True,
            )
            for s in ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis"]
            if s not in existing_skill_names
        ]
        if new_skills:
            session.add_all(new_skills)
        await session.commit()

        assert profile.id is not None
        assert profile.full_name.startswith("Alex Mercer")

        # =====================================================================
        # STAGE 2: Master Resume Upload
        # =====================================================================
        pdf_bytes = _generate_valid_test_pdf()
        resume, version = await resume_service.upload_resume(
            session=session,
            filename=f"alex_mercer_{suffix}.pdf",
            content=pdf_bytes,
            content_type="application/pdf",
            sync_parse=True,
        )
        await resume_service.activate_resume(session, resume.id)
        await session.commit()

        assert resume.id is not None
        assert resume.is_active is True
        assert resume.file_size_bytes == len(pdf_bytes)

        # =====================================================================
        # STAGE 3: Resume Parsing & Validation
        # =====================================================================
        assert version.version_number == 1
        assert version.is_valid is True
        assert version.processing_status == "COMPLETED"

        # Update structured experience for Evidence Vault validation
        version.structured_content = {
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis"],
            "experience": [
                {
                    "title": "Principal Systems Architect",
                    "company": "Acme Corp",
                    "location": "Remote",
                    "start_date": "2020",
                    "end_date": "Present",
                    "bullet_points": [
                        "Architected distributed cloud platform supporting 50M daily events using Python and FastAPI.",
                        "Maintained 99.99% service availability across multi-region Kubernetes clusters.",
                    ],
                }
            ],
            "education": [{"institution": "MIT", "degree": "BS Computer Science", "graduation_date": "2018"}],
        }
        await session.commit()

        # =====================================================================
        # STAGE 4: Job Discovery through Greenhouse & Lever
        # =====================================================================
        gh_source = JobSource(
            id=uuid.uuid4(),
            name=f"gh-acme-{suffix}",
            source_type=JobSourceTypeEnum.GREENHOUSE,
            base_url="https://boards-api.greenhouse.io",
            configuration={"board_token": f"acme_{suffix}"},
            is_enabled=True,
        )
        lever_source = JobSource(
            id=uuid.uuid4(),
            name=f"lever-corp-{suffix}",
            source_type=JobSourceTypeEnum.LEVER,
            base_url="https://api.lever.co",
            configuration={"company_id": f"lever_{suffix}"},
            is_enabled=True,
        )
        session.add_all([gh_source, lever_source])
        await session.commit()

        raw_gh_job = JobSourceRecord(
            id=uuid.uuid4(),
            job_source_id=gh_source.id,
            external_job_id=f"gh-{suffix}-001",
            source_job_url=f"https://acme.greenhouse.io/jobs/gh-{suffix}-001",
            payload_hash_sha256="dummy_hash_gh_123",
            raw_payload={
                "id": "gh-001",
                "title": "Principal Systems Architect",
                "content": "Looking for a Principal Systems Architect with deep Python, FastAPI, and Kubernetes skills.",
                "location": {"name": "Remote"},
                "updated_at": "2026-11-10T10:00:00Z",
            },
        )
        session.add(raw_gh_job)
        await session.commit()

        # =====================================================================
        # STAGE 5: Job Normalization & Duplicate Detection
        # =====================================================================
        canonical_job = await job_service.process_raw_record(session=session, record_id=raw_gh_job.id)
        await session.commit()

        assert canonical_job is not None
        assert canonical_job.workplace_type == WorkplaceTypeEnum.REMOTE

        # Test deduplication: identical payload links to same canonical job
        raw_dup = JobSourceRecord(
            id=uuid.uuid4(),
            job_source_id=gh_source.id,
            external_job_id=f"gh-{suffix}-001-dup",
            source_job_url=f"https://acme.greenhouse.io/jobs/gh-{suffix}-001-dup",
            payload_hash_sha256="dummy_hash_gh_dup_456",
            raw_payload=raw_gh_job.raw_payload,
        )
        session.add(raw_dup)
        await session.commit()
        dup_job = await job_service.process_raw_record(session=session, record_id=raw_dup.id)
        await session.commit()
        assert dup_job is not None
        assert dup_job.id == canonical_job.id

        # =====================================================================
        # STAGE 6 & 7: Candidate Eligibility Evaluation & Deterministic Matching
        # =====================================================================
        job_match = await matching_service.evaluate_job_for_candidate(
            session=session,
            job_id=canonical_job.id,
            candidate_profile_id=profile.id,
        )
        await session.commit()

        assert job_match is not None
        assert job_match.eligibility_status == EligibilityStatusEnum.ELIGIBLE
        assert job_match.deterministic_score >= Decimal("50.00")

        # =====================================================================
        # STAGE 8: LLM Semantic Analysis
        # =====================================================================
        analyzed_match = await semantic_service.evaluate_semantic_match(
            session=session,
            match_id=job_match.id,
        )
        await session.commit()

        assert analyzed_match.semantic_score is not None
        assert analyzed_match.semantic_score >= Decimal("70.00")
        assert analyzed_match.semantic_analysis_status == SemanticAnalysisStatusEnum.COMPLETED

        # =====================================================================
        # STAGE 9: Truthful Resume Tailoring & Claim Validation
        # =====================================================================
        tailor_req = TailorResumeRequest(
            job_match_id=job_match.id,
            resume_version_id=version.id,
        )
        tailored_record = await tailoring_service.request_tailoring(session=session, request=tailor_req)
        await session.commit()

        executed_tailoring = await tailoring_service.execute_tailoring_pipeline(
            session=session,
            tailored_resume_id=tailored_record.id,
        )
        await session.commit()

        assert executed_tailoring.generation_status == TailoredResumeStatusEnum.COMPLETED
        assert executed_tailoring.validation_metadata.get("is_valid") is True

        # =====================================================================
        # STAGE 10: Tailored PDF Generation & Download
        # =====================================================================
        compiled_pdf_bytes, pdf_name, mime_type = await tailoring_service.download_tailored_pdf(
            session=session,
            tailored_resume_id=executed_tailoring.id,
        )
        assert len(compiled_pdf_bytes) > 0
        assert compiled_pdf_bytes.startswith(b"%PDF-")
        assert mime_type == "application/pdf"
        assert pdf_name.endswith(".pdf")

        # =====================================================================
        # STAGE 11: Email Notification Delivery
        # =====================================================================
        delivery = await notification_service.create_or_get_delivery_for_tailored_resume(
            session=session,
            tailored_resume_id=executed_tailoring.id,
        )
        await session.commit()

        assert delivery.status == NotificationDeliveryStatusEnum.PENDING

        sent_delivery = await notification_service.execute_delivery_pipeline(
            session=session,
            delivery_id=delivery.id,
        )
        await session.commit()

        assert sent_delivery.status == NotificationDeliveryStatusEnum.SENT
        assert sent_delivery.provider_message_id is not None
        assert sent_delivery.sent_at is not None

        # =====================================================================
        # STAGE 12: Pipeline Execution & Monitoring
        # =====================================================================
        from unittest.mock import AsyncMock

        # Clear any stale active runs for this candidate
        stale_run = await pipeline_service.repository.get_active_run_for_candidate(session, profile.id)
        if stale_run is not None:
            stale_run.status = PipelineRunStatusEnum.CANCELLED
            await session.commit()

        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()

        with (
            patch(
                "app.modules.pipeline.service.get_adapter_for_source_type",
                return_value=MockDiscoveryAdapter(),
            ),
            patch("app.modules.pipeline.service.get_redis") as mock_redis,
            patch("app.modules.pipeline.tasks.execute_pipeline_run_task.delay"),
        ):
            mock_redis.return_value.lock.return_value = mock_lock

            pipeline_run = await pipeline_service.start_pipeline_run(
                session=session,
                candidate_profile_id=profile.id,
                trigger_type=PipelineTriggerTypeEnum.MANUAL,
            )
            assert pipeline_run.status == PipelineRunStatusEnum.PENDING

            completed_run = await pipeline_service.execute_pipeline_run(
                session=session,
                run_id=pipeline_run.id,
                batch_size=1,
            )
            await session.commit()

        assert completed_run.status in (PipelineRunStatusEnum.COMPLETED, PipelineRunStatusEnum.PARTIALLY_COMPLETED)
        assert completed_run.completed_at is not None

        # =====================================================================
        # STAGE 13: Notification History & Retry Behavior
        # =====================================================================
        delivery_res = await notification_service.list_deliveries(
            session=session,
            candidate_profile_id=profile.id,
            page=1,
            page_size=10,
        )
        assert len(delivery_res.items) >= 1
        assert delivery_res.pagination.total_items >= 1

        # Simulate a failed delivery and test retry behavior
        failed_delivery = NotificationDelivery(
            candidate_profile_id=profile.id,
            job_id=canonical_job.id,
            job_match_id=job_match.id,
            tailored_resume_id=executed_tailoring.id,
            recipient_email=f"failed_{suffix}@jobradar.local",
            status=NotificationDeliveryStatusEnum.FAILED,
            attempt_count=3,
            max_attempts=3,
            last_error="Simulated network transmission drop",
        )
        session.add(failed_delivery)
        await session.commit()

        # Retry with force=True should reset status to PENDING
        retried = await notification_service.retry_delivery(
            session=session,
            delivery_id=failed_delivery.id,
            force=True,
        )
        await session.commit()

        assert retried.status == NotificationDeliveryStatusEnum.PENDING
        assert retried.attempt_count == 3  # kept for audit, but re-queued
