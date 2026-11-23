"""Unit tests for TailoringService domain logic and pipeline execution."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.candidate.models import CandidateProfile, CandidateSkill, WorkplaceTypeEnum
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.resumes.models import MasterResume, ResumeVersion
from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum
from app.modules.tailoring.exceptions import EvidenceNotFoundError, TailoringError
from app.modules.tailoring.models import TailoredResume
from app.modules.tailoring.schemas import (
    TailoredExperienceItem,
    TailoredResumeContent,
    TailorResumeRequest,
)
from app.modules.tailoring.service import TailoringService


@pytest.fixture
def mock_storage() -> MagicMock:
    """Mock file storage."""
    storage = MagicMock()
    storage.save = AsyncMock(return_value="resumes/tailored/test.pdf")
    storage.read = AsyncMock(return_value=b"%PDF-1.4 dummy valid pdf content " + b" " * 150)
    return storage


@pytest.fixture
def sample_entities():
    """Build mock candidate, resume, job, and qualified match."""
    profile_id = uuid.uuid4()
    profile = CandidateProfile(
        id=profile_id,
        user_id=uuid.uuid4(),
        full_name="Alice Smith",
        headline="Senior Backend Engineer",
        professional_summary="Backend developer with Python skills.",
        total_experience_months=60,
    )
    skill = CandidateSkill(
        id=uuid.uuid4(),
        candidate_profile_id=profile_id,
        skill_name="Python",
        category="Languages",
        is_core=True,
    )
    profile.skills = [skill]

    master_resume = MasterResume(
        id=uuid.uuid4(),
        candidate_profile_id=profile_id,
        original_filename="resume.pdf",
        storage_key="resumes/raw/1.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        checksum_sha256="123456",
        is_active=True,
    )
    resume_version = ResumeVersion(
        id=uuid.uuid4(),
        master_resume_id=master_resume.id,
        version_number=1,
        checksum_sha256="123456",
        structured_content={
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience": [
                {
                    "company": "Acme Corp",
                    "title": "Backend Engineer",
                    "bullet_points": ["Built APIs."],
                }
            ],
        },
    )
    master_resume.versions = [resume_version]

    job = Job(
        id=uuid.uuid4(),
        canonical_company_name="Tech Corp",
        title="Backend Software Engineer",
        canonical_application_url="https://tech.corp/jobs/1",
        description_text="Python engineer needed.",
        dedup_fingerprint_sha256="abc" * 21 + "a",
        status=JobStatusEnum.MATCHED,
        workplace_type=WorkplaceTypeEnum.REMOTE,
    )

    qualified_match = JobMatch(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_profile_id=profile_id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        deterministic_score=Decimal("75.00"),
        final_score=Decimal("75.00"),
        match_explanation="Strong match",
    )
    qualified_match.candidate_profile = profile
    qualified_match.job = job

    return {
        "profile": profile,
        "resume_version": resume_version,
        "master_resume": master_resume,
        "job": job,
        "match": qualified_match,
    }


@pytest.mark.unit
async def test_request_tailoring_qualified_match(sample_entities, mock_storage):
    """Requesting tailoring for a qualified match creates TailoredResume in PENDING status."""
    match = sample_entities["match"]
    version = sample_entities["resume_version"]

    mock_matching_repo = MagicMock()
    mock_matching_repo.get_match_with_relations = AsyncMock(return_value=match)
    mock_matching_repo.get_active_resume_for_candidate = AsyncMock(
        return_value=sample_entities["master_resume"]
    )

    mock_tailoring_repo = MagicMock()
    mock_tailoring_repo.get_by_job_and_version = AsyncMock(return_value=None)
    created_record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=match.candidate_profile_id,
        job_id=match.job_id,
        job_match_id=match.id,
        resume_version_id=version.id,
        generation_status=TailoredResumeStatusEnum.PENDING,
    )
    mock_tailoring_repo.create = AsyncMock(return_value=created_record)

    service = TailoringService(
        repository=mock_tailoring_repo,
        matching_repository=mock_matching_repo,
        storage=mock_storage,
    )

    session = AsyncMock()
    req = TailorResumeRequest(job_match_id=match.id)
    result = await service.request_tailoring(session, req)

    assert result.generation_status == TailoredResumeStatusEnum.PENDING
    mock_tailoring_repo.create.assert_called_once()


@pytest.mark.unit
async def test_request_tailoring_unqualified_match_raises_tailoring_error(
    sample_entities, mock_storage
):
    """Requesting tailoring for an unqualified match raises TailoringError."""
    match = sample_entities["match"]
    match.eligibility_status = EligibilityStatusEnum.INELIGIBLE_EXPERIENCE
    match.deterministic_score = Decimal("30.00")

    mock_matching_repo = MagicMock()
    mock_matching_repo.get_match_with_relations = AsyncMock(return_value=match)

    service = TailoringService(
        matching_repository=mock_matching_repo,
        storage=mock_storage,
    )

    session = AsyncMock()
    req = TailorResumeRequest(job_match_id=match.id)
    with pytest.raises(TailoringError, match="not qualified for resume tailoring"):
        await service.request_tailoring(session, req)


@pytest.mark.unit
async def test_request_tailoring_missing_resume_raises_evidence_not_found(
    sample_entities, mock_storage
):
    """Requesting tailoring when candidate has no active resume version raises EvidenceNotFoundError."""
    match = sample_entities["match"]

    mock_matching_repo = MagicMock()
    mock_matching_repo.get_match_with_relations = AsyncMock(return_value=match)
    mock_matching_repo.get_active_resume_for_candidate = AsyncMock(return_value=None)

    service = TailoringService(
        matching_repository=mock_matching_repo,
        storage=mock_storage,
    )

    session = AsyncMock()
    req = TailorResumeRequest(job_match_id=match.id)
    with pytest.raises(EvidenceNotFoundError, match="no active master resume"):
        await service.request_tailoring(session, req)


@pytest.mark.unit
async def test_request_tailoring_idempotency_returns_existing(sample_entities, mock_storage):
    """If a tailored resume already exists and force_regenerate is False, return existing record."""
    match = sample_entities["match"]
    version = sample_entities["resume_version"]

    mock_matching_repo = MagicMock()
    mock_matching_repo.get_match_with_relations = AsyncMock(return_value=match)
    mock_matching_repo.get_active_resume_for_candidate = AsyncMock(
        return_value=sample_entities["master_resume"]
    )

    existing_record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=match.candidate_profile_id,
        job_id=match.job_id,
        job_match_id=match.id,
        resume_version_id=version.id,
        generation_status=TailoredResumeStatusEnum.COMPLETED,
    )
    mock_tailoring_repo = MagicMock()
    mock_tailoring_repo.get_by_job_and_version = AsyncMock(return_value=existing_record)

    service = TailoringService(
        repository=mock_tailoring_repo,
        matching_repository=mock_matching_repo,
        storage=mock_storage,
    )

    session = AsyncMock()
    req = TailorResumeRequest(job_match_id=match.id, force_regenerate=False)
    result = await service.request_tailoring(session, req)

    assert result.id == existing_record.id
    mock_tailoring_repo.create.assert_not_called()


@pytest.mark.unit
async def test_execute_tailoring_pipeline_success(sample_entities, mock_storage):
    """Full execution of tailoring pipeline completes with validated content, PDF, and checksum."""
    match = sample_entities["match"]
    version = sample_entities["resume_version"]

    record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=match.candidate_profile_id,
        job_id=match.job_id,
        job_match_id=match.id,
        resume_version_id=version.id,
        generation_status=TailoredResumeStatusEnum.PENDING,
    )
    record.candidate_profile = sample_entities["profile"]
    record.job = sample_entities["job"]
    record.job_match = match
    record.resume_version = version

    mock_tailoring_repo = MagicMock()
    mock_tailoring_repo.get_by_id = AsyncMock(return_value=record)
    mock_tailoring_repo.save = AsyncMock(side_effect=lambda _session, r: r)

    mock_llm = MockLLMProvider()

    service = TailoringService(
        repository=mock_tailoring_repo,
        storage=mock_storage,
        llm_provider=mock_llm,
    )

    session = AsyncMock()
    result = await service.execute_tailoring_pipeline(session, record.id)

    assert result.generation_status == TailoredResumeStatusEnum.COMPLETED
    assert result.file_name is not None
    assert result.checksum_sha256 is not None
    assert result.storage_key is not None
    assert result.validation_error is None
    assert result.job.status == JobStatusEnum.TAILORED
    assert result.rendering_strategy == RenderingStrategyEnum.FALLBACK
    assert "fallback_reason" in result.validation_metadata


@pytest.mark.unit
async def test_execute_tailoring_pipeline_preservation_success(sample_entities, mock_storage):
    """When template metadata supports preservation, pipeline renders with PRESERVED strategy."""
    match = sample_entities["match"]
    version = sample_entities["resume_version"]
    version.template_metadata = {
        "preservation_capability": "SUPPORTED",
        "fonts": ["Georgia-Bold", "Georgia", "Times-Roman"],
        "page_count": 1,
    }

    record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=match.candidate_profile_id,
        job_id=match.job_id,
        job_match_id=match.id,
        resume_version_id=version.id,
        generation_status=TailoredResumeStatusEnum.PENDING,
    )
    record.candidate_profile = sample_entities["profile"]
    record.job = sample_entities["job"]
    record.job_match = match
    record.resume_version = version

    mock_tailoring_repo = MagicMock()
    mock_tailoring_repo.get_by_id = AsyncMock(return_value=record)
    mock_tailoring_repo.save = AsyncMock(side_effect=lambda _session, r: r)

    mock_llm = MockLLMProvider()

    service = TailoringService(
        repository=mock_tailoring_repo,
        storage=mock_storage,
        llm_provider=mock_llm,
    )

    session = AsyncMock()
    result = await service.execute_tailoring_pipeline(session, record.id)

    assert result.generation_status == TailoredResumeStatusEnum.COMPLETED
    assert result.rendering_strategy == RenderingStrategyEnum.PRESERVED
    assert result.validation_metadata.get("actual_strategy") == "PRESERVED"
    assert result.validation_metadata.get("fallback_reason") is None


@pytest.mark.unit
async def test_execute_tailoring_pipeline_validated_content_reaches_renderer(
    sample_entities, mock_storage
):
    """Verify that repaired/validated content (not raw hallucinated LLM output) reaches renderer."""
    match = sample_entities["match"]
    version = sample_entities["resume_version"]

    record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=match.candidate_profile_id,
        job_id=match.job_id,
        job_match_id=match.id,
        resume_version_id=version.id,
        generation_status=TailoredResumeStatusEnum.PENDING,
    )
    record.candidate_profile = sample_entities["profile"]
    record.job = sample_entities["job"]
    record.job_match = match
    record.resume_version = version

    mock_tailoring_repo = MagicMock()
    mock_tailoring_repo.get_by_id = AsyncMock(return_value=record)
    mock_tailoring_repo.save = AsyncMock(side_effect=lambda _session, r: r)

    # LLM outputs an unverified skill (COBOL) and an unverified metric (88%)
    raw_llm_content = TailoredResumeContent(
        headline="Senior Backend Engineer",
        professional_summary="Summary.",
        skills=["Python", "COBOL"],  # COBOL is unverified
        experience=[
            TailoredExperienceItem(
                company="Acme Corp",
                title="Backend Engineer",
                bullet_points=["Sped up queries by 88%."],  # 88% is unverified
            )
        ],
    )
    mock_llm = MockLLMProvider(default_result=raw_llm_content)

    mock_renderer = MagicMock()
    mock_renderer.render.return_value = (
        b"%PDF-1.4 dummy",
        RenderingStrategyEnum.FALLBACK,
        "Fallback selected",
    )
    mock_renderer.validate_pdf_binary.return_value = {
        "is_valid": True,
        "page_count": 1,
        "checksum_sha256": "dummychecksum" * 4,
    }

    service = TailoringService(
        repository=mock_tailoring_repo,
        storage=mock_storage,
        llm_provider=mock_llm,
        renderer=mock_renderer,
    )

    session = AsyncMock()
    await service.execute_tailoring_pipeline(session, record.id)

    # Check what content was passed to mock_renderer.render
    rendered_content = mock_renderer.render.call_args[1]["content"]
    assert "COBOL" not in rendered_content.skills
    assert "Python" in rendered_content.skills
    assert "88%" not in rendered_content.experience[0].bullet_points[0]
    assert "significantly" in rendered_content.experience[0].bullet_points[0]


@pytest.mark.unit
async def test_execute_tailoring_pipeline_bounded_failure_on_persistent_hallucination(
    sample_entities, mock_storage
):
    """Pipeline fails gracefully after max regeneration attempts if LLM persistently hallucinates employers."""
    match = sample_entities["match"]
    version = sample_entities["resume_version"]

    record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=match.candidate_profile_id,
        job_id=match.job_id,
        job_match_id=match.id,
        resume_version_id=version.id,
        generation_status=TailoredResumeStatusEnum.PENDING,
    )
    record.candidate_profile = sample_entities["profile"]
    record.job = sample_entities["job"]
    record.job_match = match
    record.resume_version = version

    mock_tailoring_repo = MagicMock()
    mock_tailoring_repo.get_by_id = AsyncMock(return_value=record)
    mock_tailoring_repo.save = AsyncMock(side_effect=lambda _session, r: r)

    # Program mock LLM to return hallucinated employer not in candidate evidence
    hallucinated_content = TailoredResumeContent(
        headline="Senior Engineer",
        professional_summary="Summary.",
        skills=["Python"],
        experience=[
            TailoredExperienceItem(
                company="Untraceable Fake Company LLC",
                title="CTO",
                bullet_points=["Invented metrics and companies."],
            )
        ],
    )
    mock_llm = MockLLMProvider(default_result=hallucinated_content)

    service = TailoringService(
        repository=mock_tailoring_repo,
        storage=mock_storage,
        llm_provider=mock_llm,
    )

    session = AsyncMock()
    result = await service.execute_tailoring_pipeline(session, record.id)

    assert result.generation_status == TailoredResumeStatusEnum.FAILED
    assert result.validation_error is not None
    assert "Untraceable Fake Company LLC" in result.validation_error


@pytest.mark.unit
async def test_download_tailored_pdf(sample_entities, mock_storage):
    """Downloading tailored PDF returns bytes and filename for completed records, errors if not ready."""
    record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=sample_entities["profile"].id,
        job_id=sample_entities["job"].id,
        job_match_id=sample_entities["match"].id,
        resume_version_id=sample_entities["resume_version"].id,
        generation_status=TailoredResumeStatusEnum.COMPLETED,
        storage_key="resumes/tailored/test.pdf",
        file_name="Alice_Smith_TechCorp_Resume.pdf",
        mime_type="application/pdf",
    )

    mock_tailoring_repo = MagicMock()
    mock_tailoring_repo.get_by_id = AsyncMock(return_value=record)

    service = TailoringService(
        repository=mock_tailoring_repo,
        storage=mock_storage,
    )

    session = AsyncMock()
    pdf_bytes, filename, mime = await service.download_tailored_pdf(session, record.id)

    assert pdf_bytes.startswith(b"%PDF-")
    assert filename == "Alice_Smith_TechCorp_Resume.pdf"
    assert mime == "application/pdf"

    # If status is PENDING, download raises TailoringError
    record.generation_status = TailoredResumeStatusEnum.PENDING
    with pytest.raises(TailoringError, match="not ready for download"):
        await service.download_tailored_pdf(session, record.id)
