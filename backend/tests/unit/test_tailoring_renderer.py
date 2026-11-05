"""Unit tests for ResumeRenderer PDF generation and binary validation."""

from unittest.mock import patch

import pytest

from app.modules.candidate.models import CandidateProfile
from app.modules.tailoring.enums import RenderingStrategyEnum
from app.modules.tailoring.exceptions import RenderingError
from app.modules.tailoring.renderer import ResumeRenderer
from app.modules.tailoring.schemas import (
    TailoredEducationItem,
    TailoredExperienceItem,
    TailoredProjectItem,
    TailoredResumeContent,
)


@pytest.fixture
def sample_profile() -> CandidateProfile:
    """Fixture providing candidate profile."""
    return CandidateProfile(
        full_name="Sarah Connor",
        headline="Senior AI Systems Engineer",
        city="Los Angeles",
        country="USA",
    )


@pytest.fixture
def sample_content() -> TailoredResumeContent:
    """Fixture providing tailored resume content."""
    return TailoredResumeContent(
        headline="Senior AI Systems Engineer",
        professional_summary=(
            "Accomplished systems engineer with 8+ years developing scalable architectures, "
            "asynchronous pipelines, and distributed databases."
        ),
        skills=["Python", "PyTorch", "PostgreSQL", "Docker", "FastAPI"],
        experience=[
            TailoredExperienceItem(
                company="Cyberdyne Systems",
                title="AI Systems Engineer",
                location="Los Angeles, CA",
                start_date="2020",
                end_date="Present",
                bullet_points=[
                    "Engineered neural network inference pipelines with sub-50ms latency.",
                    "Managed PostgreSQL database clusters with high availability.",
                ],
            )
        ],
        projects=[
            TailoredProjectItem(
                name="Defense Network Orchestrator",
                description="Resilient message dispatch platform.",
                technologies=["Python", "FastAPI"],
                link="https://github.com/cyberdyne/dno",
            )
        ],
        education=[
            TailoredEducationItem(
                institution="MIT",
                degree="Master of Science",
                field_of_study="Artificial Intelligence",
                graduation_date="2019",
            )
        ],
    )


@pytest.mark.unit
def test_resume_renderer_standardized_pdf(
    sample_content: TailoredResumeContent, sample_profile: CandidateProfile
):
    """Strategy B: ResumeRenderer generates valid ATS single-column PDF with extractable text."""
    renderer = ResumeRenderer()
    pdf_bytes, strategy, fallback_reason = renderer.render(
        content=sample_content,
        candidate_profile=sample_profile,
        strategy=RenderingStrategyEnum.FALLBACK,
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-")
    assert strategy == RenderingStrategyEnum.FALLBACK
    assert fallback_reason is not None
    assert "Standardized ATS" in fallback_reason

    # Structural and text extraction validation
    validation = renderer.validate_pdf_binary(pdf_bytes)
    assert validation["is_valid"] is True
    assert validation["page_count"] >= 1
    assert "Sarah Connor" in validation["text_sample"]
    assert len(validation["checksum_sha256"]) == 64


@pytest.mark.unit
def test_resume_renderer_preservation_strategy_success(
    sample_content: TailoredResumeContent, sample_profile: CandidateProfile
):
    """Strategy A: Successfully preserves template typography and styling when capability is SUPPORTED."""
    renderer = ResumeRenderer()
    template_meta = {
        "preservation_capability": "SUPPORTED",
        "fonts": ["Georgia-Bold", "Georgia", "Times-Roman"],
        "page_count": 1,
    }

    pdf_bytes, strategy, fallback_reason = renderer.render(
        content=sample_content,
        candidate_profile=sample_profile,
        strategy=RenderingStrategyEnum.PRESERVED,
        template_metadata=template_meta,
    )

    assert strategy == RenderingStrategyEnum.PRESERVED
    assert fallback_reason is None
    assert pdf_bytes.startswith(b"%PDF-")

    validation = renderer.validate_pdf_binary(pdf_bytes)
    assert validation["is_valid"] is True
    assert "Sarah Connor" in validation["text_sample"]


@pytest.mark.unit
def test_resume_renderer_preservation_strategy_fallback_on_unsupported(
    sample_content: TailoredResumeContent, sample_profile: CandidateProfile
):
    """When template metadata indicates LIMITED or UNSUPPORTED, renderer transparently falls back."""
    renderer = ResumeRenderer()
    template_meta = {"preservation_capability": "LIMITED", "fonts": []}

    pdf_bytes, strategy, fallback_reason = renderer.render(
        content=sample_content,
        candidate_profile=sample_profile,
        strategy=RenderingStrategyEnum.PRESERVED,
        template_metadata=template_meta,
    )

    assert strategy == RenderingStrategyEnum.FALLBACK
    assert fallback_reason is not None
    assert "LIMITED" in fallback_reason
    assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.unit
def test_resume_renderer_preservation_failure_recovers_to_fallback(
    sample_content: TailoredResumeContent, sample_profile: CandidateProfile
):
    """If Strategy A compilation encounters an unexpected exception, it gracefully recovers to Strategy B."""
    renderer = ResumeRenderer()
    template_meta = {"preservation_capability": "SUPPORTED", "fonts": ["CustomCorruptedFont"]}

    # Simulate compilation error in _render_preserved
    with patch.object(
        renderer, "_render_preserved", side_effect=ValueError("Corrupted font metrics")
    ):
        pdf_bytes, strategy, fallback_reason = renderer.render(
            content=sample_content,
            candidate_profile=sample_profile,
            strategy=RenderingStrategyEnum.PRESERVED,
            template_metadata=template_meta,
        )

    assert strategy == RenderingStrategyEnum.FALLBACK
    assert fallback_reason is not None
    assert "Preservation rendering failed during compilation" in fallback_reason
    assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.unit
def test_resume_renderer_validated_content_reaches_pdf(
    sample_content: TailoredResumeContent, sample_profile: CandidateProfile
):
    """Verify that validated content reaches the compiled PDF binary and is readable."""
    import io

    import pdfplumber

    renderer = ResumeRenderer()
    pdf_bytes, _, _ = renderer.render(
        content=sample_content,
        candidate_profile=sample_profile,
        strategy=RenderingStrategyEnum.FALLBACK,
    )

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = "".join(p.extract_text() or "" for p in pdf.pages)
        assert "Cyberdyne Systems" in full_text
        assert "Sarah Connor" in full_text


@pytest.mark.unit
def test_resume_renderer_validate_rejects_corrupted_pdf():
    """Validating non-PDF or truncated bytes raises RenderingError."""
    renderer = ResumeRenderer()

    # Truncated or empty
    with pytest.raises(RenderingError, match="empty or below minimum"):
        renderer.validate_pdf_binary(b"")

    with pytest.raises(RenderingError, match="missing valid '%PDF-'"):
        renderer.validate_pdf_binary(b"NOT_A_PDF_FILE_HEADER" + b" " * 200)
