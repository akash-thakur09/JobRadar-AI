"""Unit tests for email templates and message formatting."""

import uuid
from decimal import Decimal

import pytest

from app.modules.candidate.models import CandidateProfile, WorkplaceTypeEnum
from app.modules.jobs.models import Job
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.notifications.templates import build_job_notification_email
from app.modules.tailoring.models import TailoredResume


@pytest.fixture
def sample_entities() -> tuple[CandidateProfile, Job, JobMatch, TailoredResume]:
    """Fixture providing populated domain entities for template rendering."""
    profile = CandidateProfile(
        id=uuid.uuid4(),
        full_name="Alex Mercer <script>",
        headline="Principal Distributed Systems Architect",
    )
    job = Job(
        id=uuid.uuid4(),
        canonical_company_name="Acme Robotics & AI",
        title="Staff Backend Engineer",
        normalized_location="San Francisco, CA",
        workplace_type=WorkplaceTypeEnum.HYBRID,
        canonical_application_url="https://acme.careers/jobs/123?utm=jobradar",
        description_text="Leading backend architecture for autonomous systems.",
    )
    job_match = JobMatch(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_profile_id=profile.id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        final_score=Decimal("88.50"),
        match_explanation="Candidate possesses 8+ years distributed backend experience matching all core criteria.",
        match_explanation_details={"recommendation": "STRONG_MATCH"},
    )
    tailored_resume = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=profile.id,
        job_id=job.id,
        job_match_id=job_match.id,
        resume_version_id=uuid.uuid4(),
        file_name="Alex_Mercer_Acme_Robotics_Resume.pdf",
        storage_key="resumes/tailored/test.pdf",
    )
    return profile, job, job_match, tailored_resume


@pytest.mark.unit
def test_build_job_notification_email(
    sample_entities: tuple[CandidateProfile, Job, JobMatch, TailoredResume],
):
    """Email template formats validated job info, match metrics, and PDF attachment safely."""
    profile, job, job_match, tailored_resume = sample_entities
    pdf_bytes = b"%PDF-1.4 binary stream test resume"

    message = build_job_notification_email(
        candidate_profile=profile,
        job=job,
        job_match=job_match,
        tailored_resume=tailored_resume,
        pdf_bytes=pdf_bytes,
        recipient_email="alex.mercer@example.com",
    )

    # 1. Recipient and Subject
    assert message.to == "alex.mercer@example.com"
    assert "Staff Backend Engineer" in message.subject
    assert "Acme Robotics & AI" in message.subject
    assert "89%" in message.subject or "88%" in message.subject

    # 2. Plain Text Body
    assert "Staff Backend Engineer at Acme Robotics & AI" in message.text_body
    assert "San Francisco, CA (HYBRID)" in message.text_body
    assert "https://acme.careers/jobs/123?utm=jobradar" in message.text_body
    assert "Candidate possesses 8+ years" in message.text_body
    assert "Alex_Mercer_Acme_Robotics_Resume.pdf" in message.text_body

    # 3. HTML Body & XSS Escaping
    assert "&lt;script&gt;" in message.html_body
    assert "<script>" not in message.html_body
    assert "Acme Robotics &amp; AI" in message.html_body
    assert "Recommendation: STRONG MATCH" in message.html_body

    # 4. Attachment
    assert len(message.attachments) == 1
    att = message.attachments[0]
    assert att.filename == "Alex_Mercer_Acme_Robotics_Resume.pdf"
    assert att.content == pdf_bytes
    assert att.content_type == "application/pdf"

