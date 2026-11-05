"""Unit tests for CandidateEvidenceVault fact extraction and grounding bounds."""

import uuid

import pytest

from app.modules.candidate.models import CandidateProfile, CandidateSkill
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.resumes.models import ResumeVersion
from app.modules.tailoring.evidence import CandidateEvidenceVault, extract_metrics_from_text


@pytest.mark.unit
def test_extract_metrics_from_text():
    """Verify regex extraction of quantitative claims across multiple formats."""
    text = (
        "Improved API throughput by 45% and reduced latency by 120ms. "
        "Managed a $1.5M budget, serving 500k users with 99.9% uptime. "
        "Delivered a 3x speedup across 15 microservices for 1,200 clients."
    )
    metrics = extract_metrics_from_text(text)

    assert "45%" in metrics
    assert "99.9%" in metrics
    assert "120ms" in metrics
    assert "3x" in metrics
    assert "$1.5m" in metrics
    assert "500k users" in metrics
    assert "15 microservices" in metrics
    assert "1,200 clients" in metrics


@pytest.mark.unit
def test_candidate_evidence_vault_construction():
    """Verify evidence vault compiles verifiable knowledge boundary from domain entities."""
    profile_id = uuid.uuid4()
    profile = CandidateProfile(
        id=profile_id,
        user_id=uuid.uuid4(),
        full_name="Jane Doe",
        headline="Principal Distributed Systems Architect",
        current_role="Staff Engineer",
        professional_summary="Architected cloud systems processing 10m requests daily.",
        total_experience_months=96,
        city="San Francisco",
        country="USA",
    )

    skills = [
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile_id,
            skill_name="Python",
            category="Languages",
            experience_months=96,
            is_core=True,
        ),
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=profile_id,
            skill_name="FastAPI",
            category="Frameworks",
            experience_months=48,
            is_core=True,
        ),
    ]

    resume_version = ResumeVersion(
        id=uuid.uuid4(),
        master_resume_id=uuid.uuid4(),
        version_number=1,
        checksum_sha256="abc12345",
        structured_content={
            "skills": ["PostgreSQL", "Docker", "Redis", "Kafka"],
            "experience": [
                {
                    "company": "Stripe",
                    "title": "Senior Software Engineer",
                    "bullet_points": [
                        "Scaled payment ledger system handling 50k requests per second.",
                        "Reduced query latency by 35% via database partitioning.",
                    ],
                }
            ],
            "projects": [
                {
                    "name": "Distributed Lock Manager",
                    "description": "High-availability lock system with 99.99% reliability.",
                    "technologies": ["Python", "Redis", "Etcd"],
                }
            ],
            "education": [
                {
                    "institution": "Stanford University",
                    "degree": "B.S. Computer Science",
                }
            ],
        },
    )

    job = Job(
        id=uuid.uuid4(),
        canonical_company_name="Netflix",
        title="Senior Backend Engineer",
        canonical_application_url="https://jobs.netflix.com/123",
        description_text="Seeking Senior Backend Engineer proficient in Python, Redis, and high-scale APIs.",
        dedup_fingerprint_sha256="deadbeef" * 8,
        status=JobStatusEnum.MATCHED,
    )

    vault = CandidateEvidenceVault.from_entities(profile, skills, resume_version, job)

    # Verify skills
    assert vault.is_skill_supported("Python")
    assert vault.is_skill_supported("fastapi")
    assert vault.is_skill_supported("PostgreSQL")
    assert vault.is_skill_supported("Redis")
    assert vault.is_skill_supported("etcd")
    assert not vault.is_skill_supported("Rust")
    assert not vault.is_skill_supported("GraphQL")

    # Verify employers
    assert vault.is_employer_supported("Stripe")
    assert vault.is_employer_supported("stripe inc")
    assert not vault.is_employer_supported("Google")

    # Verify metrics
    assert vault.is_metric_supported("35%")
    assert vault.is_metric_supported("99.99%")
    assert vault.is_metric_supported("50k requests")
    assert not vault.is_metric_supported("75%")
    assert not vault.is_metric_supported("$5M")

    # Verify context dictionary serialization
    context = vault.to_evidence_context()
    assert context["candidate_profile"]["full_name"] == "Jane Doe"
    assert "python" in context["verified_skills"]
    assert "stripe" in context["known_employers"]
    assert context["target_opportunity"]["company"] == "Netflix"
