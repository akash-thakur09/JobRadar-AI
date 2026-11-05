"""Integration tests for Layer 3 LLM Semantic Analysis against live PostgreSQL."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
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
from app.modules.matching.llm.factory import set_llm_provider_override
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    SemanticRecommendationEnum,
    SemanticStrength,
    TransferableSkill,
)
from app.modules.matching.models import EligibilityStatusEnum, JobMatch, SemanticAnalysisStatusEnum
from app.modules.matching.semantic_service import SemanticAnalysisService
from app.modules.matching.service import MatchingService
from app.modules.resumes.models import MasterResume, ResumeProcessingStatus, ResumeVersion


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(f"Live PostgreSQL not reachable ({detail}). Skipping integration test.")


@pytest.fixture(autouse=True)
def setup_mock_llm_provider():
    """Ensure mock LLM provider is active for DB integration tests."""
    canned = SemanticAnalysisResult(
        semantic_score=Decimal("85.00"),
        recommendation=SemanticRecommendationEnum.STRONG_MATCH,
        confidence=0.92,
        reasoning_summary="Candidate demonstrates exceptional backend engineering alignment.",
        strengths=[
            SemanticStrength(
                claim="Async backend architecture",
                evidence="FastAPI and microservices experience",
                job_context="Aligns with core scalable backend needs",
            )
        ],
        transferable_skills=[
            TransferableSkill(
                candidate_skill="docker",
                target_technology="kubernetes",
                rationale="Container lifecycle and orchestration concepts transfer directly",
            )
        ],
    )
    provider = MockLLMProvider(default_result=canned)
    set_llm_provider_override(provider)
    yield
    set_llm_provider_override(None)


@pytest.mark.integration
async def test_semantic_analysis_db_lifecycle(async_client: AsyncClient) -> None:
    """Verify Layer 3 evaluation, database persistence, and API endpoint against live PostgreSQL."""
    session_factory = get_session_factory()
    matching_service = MatchingService()
    semantic_service = SemanticAnalysisService()

    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)

    async with session_factory() as session:
        # 1. Create candidate user & profile
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
            full_name=f"Jane Doe {suffix}",
            headline="Senior Python Backend Developer",
            professional_summary="Architecting resilient distributed systems.",
            city="San Francisco",
            country="United States",
            work_authorization="US Citizen",
            total_experience_months=72,
        )
        session.add(profile)

        # 2. Add Candidate Preferences
        prefs = CandidatePreference(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            preferred_titles=["Senior Python Backend Developer", "Backend Engineer"],
            preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
            preferred_locations=["San Francisco"],
            preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
            max_job_age_days=30,
            minimum_relevance_score=Decimal("70.00"),
        )
        session.add(prefs)

        # 3. Add Verified Skills
        skill_python = CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            skill_name="python",
            category="language",
            experience_months=72,
            is_core=True,
        )
        skill_fastapi = CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            skill_name="fastapi",
            category="framework",
            experience_months=48,
            is_core=True,
        )
        skill_docker = CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            skill_name="docker",
            category="devops",
            experience_months=48,
            is_core=False,
        )
        session.add_all([skill_python, skill_fastapi, skill_docker])

        # 4. Add Master Resume & Structured Resume Version
        master_resume = MasterResume(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            original_filename="resume.pdf",
            storage_key=f"resumes/test_{suffix}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256=hashlib.sha256(b"content").hexdigest(),
            is_active=True,
        )
        session.add(master_resume)
        await session.flush()

        resume_ver = ResumeVersion(
            id=uuid.uuid4(),
            master_resume_id=master_resume.id,
            version_number=1,
            structured_content={
                "skills": ["python", "fastapi", "docker", "postgresql"],
                "work_experience": [
                    {
                        "company": "ScaleInc",
                        "role": "Backend Engineer",
                        "description": "Engineered high throughput APIs with FastAPI and Docker.",
                    }
                ],
            },
            checksum_sha256=master_resume.checksum_sha256,
            processing_status=ResumeProcessingStatus.COMPLETED.value,
        )
        session.add(resume_ver)

        # 5. Create Canonical Job
        job = Job(
            id=uuid.uuid4(),
            canonical_company_name="CloudMatrix",
            title="Senior Python Backend Developer",
            canonical_application_url=f"https://cloudmatrix.com/jobs/{suffix}",
            workplace_type=WorkplaceTypeEnum.REMOTE,
            normalized_location="San Francisco",
            employment_type=EmploymentTypeEnum.FULL_TIME,
            description_text="We need a Senior Python Backend Developer with FastAPI experience. Kubernetes is a plus.",
            posted_at=now - timedelta(days=2),
            first_seen_at=now - timedelta(days=2),
            last_seen_at=now,
            dedup_fingerprint_sha256=hashlib.sha256(f"semantic_job_{suffix}".encode()).hexdigest(),
            status=JobStatusEnum.NORMALIZED,
        )
        session.add(job)
        await session.commit()

        # 6. Run Deterministic Matching (Layers 1 & 2)
        match = await matching_service.evaluate_job_for_candidate(
            session=session,
            job_id=job.id,
            candidate_profile_id=profile.id,
        )
        await session.commit()

        assert match.eligibility_status == EligibilityStatusEnum.ELIGIBLE
        assert match.semantic_analysis_status == SemanticAnalysisStatusEnum.PENDING
        assert match.deterministic_score >= Decimal("50.00")
        det_score = match.deterministic_score
        match_id = match.id

    # 7. Execute Layer 3 Semantic Analysis via Service
    async with session_factory() as session:
        evaluated_match = await semantic_service.evaluate_semantic_match(
            session=session,
            match_id=match_id,
        )
        await session.commit()

        assert evaluated_match.semantic_analysis_status == SemanticAnalysisStatusEnum.COMPLETED
        assert evaluated_match.semantic_score == Decimal("85.00")

        # Hybrid formula check: 0.60 * det + 0.40 * 85.00
        expected_hybrid = (
            Decimal("0.60") * det_score + Decimal("0.40") * Decimal("85.00")
        ).quantize(Decimal("0.01"))
        assert evaluated_match.final_score == expected_hybrid
        assert evaluated_match.match_explanation_details["llm_degraded"] is False
        assert "semantic_evaluation" in evaluated_match.match_explanation_details

    # 8. Test API endpoint GET /api/v1/matches/{id}
    res = await async_client.get(f"/api/v1/matches/{match_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(match_id)
    assert data["semantic_analysis_status"] == "COMPLETED"
    assert Decimal(str(data["semantic_score"])) == Decimal("85.00")
    assert Decimal(str(data["final_score"])) == expected_hybrid
    assert "semantic_evaluation" in data["match_explanation_details"]

    # 9. Test API endpoint POST /api/v1/matches/{id}/semantic-analysis (trigger)
    res_trigger = await async_client.post(f"/api/v1/matches/{match_id}/semantic-analysis")
    assert res_trigger.status_code == 200
    trigger_data = res_trigger.json()
    assert trigger_data["semantic_analysis_status"] == "COMPLETED"

    # 10. Verify DB query indexing on semantic_analysis_status
    async with session_factory() as session:
        stmt = select(JobMatch).where(
            JobMatch.candidate_profile_id == profile.id,
            JobMatch.semantic_analysis_status == SemanticAnalysisStatusEnum.COMPLETED,
        )
        records = list((await session.execute(stmt)).scalars().all())
        assert len(records) == 1
        assert records[0].id == match_id
