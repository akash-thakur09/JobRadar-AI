"""Unit tests for EvidenceValidator."""

from decimal import Decimal

from app.modules.matching.evidence_validator import EvidenceValidator
from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    SemanticRecommendationEnum,
    SemanticStrength,
    TransferableSkill,
)


def test_evidence_validator_valid_candidate_skills() -> None:
    """Verify legitimate transferable skills pass validation without penalty."""
    validator = EvidenceValidator()

    raw_result = SemanticAnalysisResult(
        semantic_score=Decimal("85.00"),
        recommendation=SemanticRecommendationEnum.STRONG_MATCH,
        confidence=0.90,
        reasoning_summary="Candidate demonstrates strong async backend experience.",
        strengths=[
            SemanticStrength(
                claim="Strong PostgreSQL database design",
                evidence="Verified database schema optimizations",
                job_context="PostgreSQL backend requirement",
            )
        ],
        transferable_skills=[
            TransferableSkill(
                candidate_skill="docker",
                target_technology="kubernetes",
                rationale="Container lifecycle foundation transfers to K8s orchestration",
            )
        ],
    )

    candidate_skills = {"python", "fastapi", "postgresql", "docker"}
    corpus = "Senior Python engineer building microservices with Docker and PostgreSQL."

    validated = validator.validate_semantic_result(raw_result, candidate_skills, corpus)

    assert len(validated.transferable_skills) == 1
    assert validated.transferable_skills[0].candidate_skill == "docker"
    assert len(validated.unsupported_claims) == 0
    assert validated.confidence == 0.90
    assert validated.semantic_score == Decimal("85.00")


def test_evidence_validator_rejects_hallucinated_transferable_skill() -> None:
    """Verify hallucinated candidate skills are removed and flagged."""
    validator = EvidenceValidator()

    raw_result = SemanticAnalysisResult(
        semantic_score=Decimal("80.00"),
        recommendation=SemanticRecommendationEnum.GOOD_MATCH,
        confidence=0.85,
        reasoning_summary="Candidate has broad skill set.",
        transferable_skills=[
            TransferableSkill(
                candidate_skill="rust",  # Hallucinated! Candidate only knows Python
                target_technology="golang",
                rationale="Systems programming transfer",
            )
        ],
    )

    candidate_skills = {"python", "fastapi", "postgresql"}
    corpus = "Python backend developer with FastAPI and SQL experience."

    validated = validator.validate_semantic_result(raw_result, candidate_skills, corpus)

    # Hallucinated transferable skill should be purged
    assert len(validated.transferable_skills) == 0
    assert len(validated.unsupported_claims) == 1
    assert "rust" in validated.unsupported_claims[0].lower()
    # Confidence and score adjusted downwards
    assert validated.confidence < 0.85
    assert validated.semantic_score < Decimal("80.00")


def test_evidence_validator_detects_skill_in_resume_corpus() -> None:
    """Verify skills present in candidate resume text corpus are accepted even if not in candidate_skills set."""
    validator = EvidenceValidator()

    raw_result = SemanticAnalysisResult(
        semantic_score=Decimal("78.00"),
        recommendation=SemanticRecommendationEnum.GOOD_MATCH,
        confidence=0.80,
        reasoning_summary="Candidate has Redis cache experience.",
        transferable_skills=[
            TransferableSkill(
                candidate_skill="redis",
                target_technology="memcached",
                rationale="In-memory cache architecture",
            )
        ],
    )

    candidate_skills = {"python", "fastapi"}  # redis not in profile table
    corpus = "Built low-latency caching layer utilizing Redis and Celery background workers."

    validated = validator.validate_semantic_result(raw_result, candidate_skills, corpus)

    # Redis was found in resume corpus!
    assert len(validated.transferable_skills) == 1
    assert len(validated.unsupported_claims) == 0
