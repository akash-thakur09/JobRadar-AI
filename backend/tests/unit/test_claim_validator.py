"""Unit tests for ClaimValidator factual truth enforcement and repair mechanisms."""

import pytest

from app.modules.tailoring.evidence import CandidateEvidenceVault
from app.modules.tailoring.schemas import (
    TailoredEducationItem,
    TailoredExperienceItem,
    TailoredProjectItem,
    TailoredResumeContent,
)
from app.modules.tailoring.validator import ClaimValidator


@pytest.fixture
def sample_evidence_vault() -> CandidateEvidenceVault:
    """Fixture providing a mock evidence vault with strict factual boundaries."""
    return CandidateEvidenceVault(
        candidate_profile_id="cand-123",
        full_name="Bob Builder",
        headline="Senior Systems Engineer",
        professional_summary="Engineer with 6 years experience in Python and PostgreSQL.",
        total_experience_months=72,
        skills={"python", "fastapi", "postgresql", "docker", "redis"},
        employers={"acme corp", "initech"},
        titles={"senior systems engineer", "software engineer"},
        metrics={"30%", "100k users", "2x"},
        raw_experiences=[
            {
                "company": "Acme Corp",
                "title": "Senior Systems Engineer",
                "bullet_points": ["Improved throughput by 30% for 100k users."],
            }
        ],
        raw_projects=[],
        raw_education=[],
        job_title="Lead Backend Engineer",
        job_company="Hooli",
        job_description="Seeking backend engineer with Python and Redis expertise.",
    )


@pytest.mark.unit
def test_claim_validator_accepts_truthful_content(sample_evidence_vault: CandidateEvidenceVault):
    """Truthful content matching evidence passes validation cleanly with is_valid=True."""
    content = TailoredResumeContent(
        headline="Lead Backend Engineer",
        professional_summary="Experienced Python and Redis specialist with 6 years experience.",
        skills=["Python", "FastAPI", "Redis", "Docker"],
        experience=[
            TailoredExperienceItem(
                company="Acme Corp",
                title="Senior Systems Engineer",
                bullet_points=["Architected async pipelines, achieving a 2x throughput speedup."],
            )
        ],
        projects=[
            TailoredProjectItem(
                name="Cache Layer",
                description="Distributed cache implementation using Redis.",
                technologies=["Python", "Redis"],
            )
        ],
        education=[
            TailoredEducationItem(
                institution="Tech University",
                degree="B.S. in Computer Science",
            )
        ],
    )

    validator = ClaimValidator(sample_evidence_vault)
    repaired, report = validator.validate_and_repair(content)

    assert report.is_valid is True
    assert len(report.violations_detected) == 0
    assert "Python" in report.supported_skills
    assert "Redis" in report.supported_skills


@pytest.mark.unit
def test_claim_validator_prunes_unsupported_skills(sample_evidence_vault: CandidateEvidenceVault):
    """Unsupported technical skills not found in evidence are pruned from skills and projects."""
    content = TailoredResumeContent(
        headline="Senior Systems Engineer",
        professional_summary="Python engineer.",
        skills=["Python", "Rust", "Golang", "PostgreSQL"],  # Rust and Golang not in vault
        experience=[
            TailoredExperienceItem(
                company="Acme Corp",
                title="Senior Systems Engineer",
                bullet_points=["Scaled core services."],
            )
        ],
        projects=[
            TailoredProjectItem(
                name="Kubernetes Pipeline",
                description="CI/CD tool.",
                technologies=["Python", "Kubernetes"],  # Kubernetes not in vault
            )
        ],
        education=[],
    )

    validator = ClaimValidator(sample_evidence_vault)
    repaired, report = validator.validate_and_repair(content)

    assert report.is_valid is True
    assert "Rust" in report.unsupported_skills
    assert "Golang" in report.unsupported_skills
    # Skills pruned from final content
    assert "Rust" not in repaired.skills
    assert "Golang" not in repaired.skills
    assert "Python" in repaired.skills
    assert "PostgreSQL" in repaired.skills
    # Project technology pruned
    assert "Kubernetes" not in repaired.projects[0].technologies
    assert "Python" in repaired.projects[0].technologies
    assert any("Pruned unverified skill: 'Rust'" in r for r in report.repaired_claims)


@pytest.mark.unit
def test_claim_validator_sanitizes_hallucinated_metrics(
    sample_evidence_vault: CandidateEvidenceVault,
):
    """Hallucinated metrics in bullet points are detected and sanitized into qualitative statements."""
    content = TailoredResumeContent(
        headline="Senior Systems Engineer",
        professional_summary="Summary.",
        skills=["Python", "PostgreSQL"],
        experience=[
            TailoredExperienceItem(
                company="Acme Corp",
                title="Senior Systems Engineer",
                bullet_points=[
                    # 75% is NOT in evidence (only 30%, 100k users, 2x are)
                    "Optimized database indexing, cutting latency by 75% across the cluster.",
                ],
            )
        ],
        projects=[],
        education=[],
    )

    validator = ClaimValidator(sample_evidence_vault)
    repaired, report = validator.validate_and_repair(content)

    assert report.is_valid is True
    assert "75%" in report.unsupported_metrics
    # Bullet sanitized to eliminate the hallucinated 75% metric
    sanitized_bullet = repaired.experience[0].bullet_points[0]
    assert "75%" not in sanitized_bullet
    assert "significantly" in sanitized_bullet
    assert any("Sanitized hallucinated metric '75%'" in r for r in report.repaired_claims)


@pytest.mark.unit
def test_claim_validator_rejects_unverified_employer(sample_evidence_vault: CandidateEvidenceVault):
    """Hallucinated employers not in evidence fail validation with is_valid=False."""
    content = TailoredResumeContent(
        headline="Senior Systems Engineer",
        professional_summary="Summary.",
        skills=["Python"],
        experience=[
            TailoredExperienceItem(
                company="Google Inc",  # Google is NOT in candidate evidence (only Acme Corp and Initech)
                title="Staff Engineer",
                bullet_points=["Built search infrastructure."],
            )
        ],
        projects=[],
        education=[],
    )

    validator = ClaimValidator(sample_evidence_vault)
    repaired, report = validator.validate_and_repair(content)

    assert report.is_valid is False
    assert len(report.violations_detected) > 0
    assert any("Google Inc" in v for v in report.violations_detected)


@pytest.mark.unit
def test_claim_validator_sanitizes_metrics_in_summary_and_headline(
    sample_evidence_vault: CandidateEvidenceVault,
):
    """Hallucinated metrics in summary or headline are sanitized and recorded in repaired_claims."""
    content = TailoredResumeContent(
        headline="Senior Systems Engineer delivering 50% faster deployments",
        professional_summary="Backend leader with 6 years experience who drove a $10M revenue boost.",
        skills=["Python", "PostgreSQL"],
        experience=[
            TailoredExperienceItem(
                company="Acme Corp",
                title="Senior Systems Engineer",
                bullet_points=["Maintained systems."],
            )
        ],
        projects=[],
        education=[],
    )

    validator = ClaimValidator(sample_evidence_vault)
    repaired, report = validator.validate_and_repair(content)

    assert report.is_valid is True
    assert "50%" in report.unsupported_metrics
    assert "$10m" in report.unsupported_metrics
    # $10M sanitized to significantly in summary
    assert "$10m" not in repaired.professional_summary.lower()
    assert "significantly" in repaired.professional_summary
    # 50% stripped from headline
    assert "50%" not in repaired.headline
