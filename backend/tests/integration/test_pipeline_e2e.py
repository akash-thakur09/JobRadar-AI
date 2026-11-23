"""Controlled End-to-End Integration Test for complete Pipeline Orchestration.

Demonstrates:
PipelineRun Created
  -> Discovery executed (Mock Adapter)
  -> Raw Job persisted
  -> Job Normalized & Canonicalized
  -> Candidate Deterministic Matching (Layer 1 & 2)
  -> LLM Semantic Evaluation (Layer 3 Mock)
  -> Resume Tailoring & ATS PDF Compilation
  -> Immediate Email Notification Dispatch (Mock Provider)
  -> Operational Metrics Aggregated & Status Finalized to COMPLETED
"""

import hashlib
import uuid
from decimal import Decimal
from sqlalchemy import update

import pytest

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
from app.modules.discovery.adapters.base import (
    DiscoveryResult,
    JobSourceAdapter,
    RawDiscoveredJob,
)
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.semantic_service import SemanticAnalysisService
from app.modules.notifications.email.mock_provider import MockEmailProvider
from app.modules.notifications.service import NotificationService
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.service import PipelineOrchestrationService
from app.modules.resumes.models import MasterResume, ResumeVersion
from app.modules.tailoring.service import TailoringService


class MockGreenhouseAdapter(JobSourceAdapter):
    """Controlled mock discovery adapter returning a known job payload."""

    def __init__(self, external_id: str = "gh-e2e-101") -> None:
        self.external_id = external_id

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
            source_identifier="acmecorp",
            source_type=JobSourceTypeEnum.GREENHOUSE,
            jobs=[
                RawDiscoveredJob(
                    external_id=self.external_id,
                    source_url=f"https://acme.greenhouse.io/jobs/{self.external_id}",
                    raw_payload={
                        "id": 101,
                        "title": "Staff Cloud Engineer",
                        "content": "Seeking Staff Cloud Engineer with Python and Kubernetes expertise.",
                        "location": {"name": "Remote"},
                        "updated_at": "2026-11-05T12:00:00Z",
                    },
                )
            ],
        )


@pytest.mark.integration
async def test_full_pipeline_orchestration_e2e(tmp_path) -> None:
    """Execute complete end-to-end pipeline run from discovery through to notification delivery."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]
    storage = LocalFileStorage(base_dir=str(tmp_path / "storage"))
    mock_email_provider = MockEmailProvider()
    mock_llm_provider = MockLLMProvider()

    async with session_factory() as session:
        # 1. Candidate User & Profile
        user = User(
            id=uuid.uuid4(),
            email=f"e2e_{suffix}@jobradar.local",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"E2E Engineer {suffix}",
            headline="Staff Cloud Engineer",
            professional_summary="Expert in distributed cloud architecture, Python, and Kubernetes.",
            total_experience_months=96,
        )
        session.add(profile)
        await session.flush()

        # 2. Candidate Skills & Preferences (aligned with Evidence Vault and Mock LLM)
        skills = [
            CandidateSkill(
                candidate_profile_id=profile.id,
                skill_name=skill_name,
                category="Technical",
                experience_months=96,
                is_core=True,
            )
            for skill_name in ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Kubernetes"]
        ]
        session.add_all(skills)

        pref = CandidatePreference(
            candidate_profile_id=profile.id,
            minimum_relevance_score=Decimal("60.00"),
            preferred_titles=[
                "Staff Cloud Engineer",
                "Senior Software Engineer",
                "Cloud Architect",
            ],
            preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
            preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
            max_job_age_days=30,
        )
        session.add(pref)

        # 3. Master Resume and Valid Version (Evidence Vault Foundation)
        dummy_pdf = b"%PDF-1.4 master resume test bytes"
        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="master.pdf",
            storage_key=f"resumes/raw/{profile.id}/master.pdf",
            mime_type="application/pdf",
            file_size_bytes=len(dummy_pdf),
            checksum_sha256=hashlib.sha256(dummy_pdf).hexdigest(),
            is_active=True,
        )
        session.add(master_resume)
        await session.flush()

        resume_version = ResumeVersion(
            id=uuid.uuid4(),
            master_resume_id=master_resume.id,
            version_number=1,
            structured_content={
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Kubernetes"],
                "experience": [
                    {
                        "title": "Senior Software Engineer",
                        "company": "Acme Corp",
                        "location": "Remote",
                        "start_date": "2021",
                        "end_date": "Present",
                        "bullet_points": [
                            "Architected high-throughput async data ingestion services using FastAPI.",
                            "Optimized database indexing and queries, supporting critical production workloads.",
                        ],
                    }
                ],
                "projects": [
                    {
                        "name": "Cloud Task Orchestrator",
                        "description": "Distributed worker task pipeline with Redis queues.",
                        "technologies": ["Python", "Redis", "Docker"],
                    }
                ],
                "education": [
                    {
                        "institution": "State University",
                        "degree": "Bachelor of Science",
                        "field_of_study": "Computer Science",
                        "graduation_date": "2020",
                    }
                ],
            },
            template_metadata={"preservation_capability": "LIMITED"},
            checksum_sha256=master_resume.checksum_sha256,
            is_valid=True,
            processing_status="COMPLETED",
        )
        session.add(resume_version)

        # Disable existing job sources so pipeline run only processes this test's job source
        await session.execute(update(JobSource).values(is_enabled=False))

        # 4. Configured JobSource
        job_source = JobSource(
            id=uuid.uuid4(),
            name=f"E2E Acme Corp {suffix}",
            source_type="GREENHOUSE",
            base_url="https://boards-api.greenhouse.io/v1/boards/acmecorp",
            configuration={"board_token": "acmecorp"},
            is_enabled=True,
        )
        session.add(job_source)
        await session.commit()

        candidate_id = profile.id

    # 5. Build services with dependency injection
    tailoring_service = TailoringService(
        storage=storage,
        llm_provider=mock_llm_provider,
    )
    notification_service = NotificationService(
        storage=storage,
        email_provider=mock_email_provider,
    )
    semantic_service = SemanticAnalysisService(
        llm_provider=mock_llm_provider,
    )

    orchestration_service = PipelineOrchestrationService(
        semantic_service=semantic_service,
        tailoring_service=tailoring_service,
        notification_service=notification_service,
    )

    # 6. Execute E2E Pipeline
    from unittest.mock import AsyncMock, patch

    with (
        patch(
            "app.modules.pipeline.service.get_adapter_for_source_type",
            return_value=MockGreenhouseAdapter(external_id=f"gh-e2e-{suffix}"),
        ),
        patch("app.modules.pipeline.service.get_redis") as mock_redis,
    ):
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()
        mock_redis.return_value.lock.return_value = mock_lock

        async with session_factory() as session:
            # Create PENDING pipeline run
            run = await orchestration_service.start_pipeline_run(
                session=session,
                candidate_profile_id=candidate_id,
                trigger_type=PipelineTriggerTypeEnum.MANUAL,
            )
            run_id = run.id

        async with session_factory() as session:
            # Execute entire pipeline run
            completed_run = await orchestration_service.execute_pipeline_run(
                session=session,
                run_id=run_id,
                batch_size=10,
            )

            # 7. Assertions
            assert completed_run.status == PipelineRunStatusEnum.COMPLETED
            assert completed_run.jobs_discovered >= 1
            assert completed_run.jobs_created >= 1
            assert completed_run.jobs_normalized >= 1
            assert completed_run.jobs_evaluated >= 1
            assert completed_run.matches_created >= 1
            assert completed_run.matches_qualified >= 1
            assert completed_run.semantic_analyses_completed >= 1
            assert completed_run.resumes_generated >= 1
            assert completed_run.notifications_sent >= 1
            assert completed_run.error_summary is None

            # Verify email notification was actually dispatched with PDF attachment
            assert mock_email_provider.sent_count >= 1
            last_msg = mock_email_provider.sent_messages[0]
            assert last_msg.to == f"e2e_{suffix}@jobradar.local"
            assert "JobRadar AI Alert" in last_msg.html_body
            assert len(last_msg.attachments) == 1
            assert last_msg.attachments[0].content_type == "application/pdf"
            assert len(last_msg.attachments[0].content) > 0
