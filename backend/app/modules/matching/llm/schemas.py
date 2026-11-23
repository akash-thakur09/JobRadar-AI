"""Structured Pydantic schemas for LLM Semantic Analysis output."""

from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SemanticRecommendationEnum(StrEnum):
    """Holistic candidate match recommendation category."""

    STRONG_MATCH = "STRONG_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    BORDERLINE = "BORDERLINE"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class SemanticStrength(BaseModel):
    """Specific candidate strength validated against job requirements."""

    claim: str = Field(description="Key candidate strength or capability aligned with role")
    evidence: str = Field(
        default="",
        description="Factual citation or demonstration from candidate background",
    )
    job_context: str = Field(
        default="",
        description="Explanation of why this strength is relevant to the JD",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_from_raw(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {
                "claim": data.strip(),
                "evidence": "Candidate verified background",
                "job_context": "Core job requirement",
            }
        return data


class SemanticRisk(BaseModel):
    """Potential risk or missing requirement where candidate lacks direct evidence."""

    gap: str = Field(description="Missing requirement, technology, or domain knowledge")
    impact: str = Field(
        default="MEDIUM",
        description="Assessed severity impact: LOW, MEDIUM, or HIGH",
    )
    mitigation: str | None = Field(
        default=None,
        description="Candidate factor or transferable foundation that softens the gap",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_from_raw(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {
                "gap": data.strip(),
                "impact": "MEDIUM",
                "mitigation": None,
            }
        return data


class TransferableSkill(BaseModel):
    """Demonstrated candidate skill that substitutes for a missing JD technology."""

    candidate_skill: str = Field(description="Demonstrated skill candidate possesses")
    target_technology: str = Field(description="JD requirement or technology it substitutes for")
    rationale: str = Field(
        default="",
        description="Technical justification for why the skill transfers",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_from_raw(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {
                "candidate_skill": data.strip(),
                "target_technology": "Target tech stack",
                "rationale": "Transferable architectural concepts",
            }
        return data


class SemanticAnalysisResult(BaseModel):
    """Validated structured output produced by Layer 3 LLM Semantic Analysis."""

    semantic_score: Decimal = Field(
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Holistic contextual alignment score from 0.00 to 100.00",
    )
    recommendation: SemanticRecommendationEnum = Field(
        description="Qualitative match recommendation classification"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence based on JD clarity and candidate detail",
    )
    reasoning_summary: str = Field(
        max_length=600,
        description="Executive summary explaining contextual fit and nuances",
    )
    strengths: list[SemanticStrength] = Field(
        default_factory=list,
        description="Candidate strengths matching core responsibilities",
    )
    gaps: list[SemanticRisk] = Field(
        default_factory=list,
        description="Identified candidate gaps or unverified requirements",
    )
    transferable_skills: list[TransferableSkill] = Field(
        default_factory=list,
        description="Demonstrated skills that bridge target JD technologies",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims filtered or flagged during evidence verification",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_score_and_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Support alias 'semantic_relevance_score' from prompt/design doc
        if "semantic_relevance_score" in data and "semantic_score" not in data:
            data["semantic_score"] = data["semantic_relevance_score"]

        # Support alias 'matching_strengths'
        if "matching_strengths" in data and "strengths" not in data:
            data["strengths"] = data["matching_strengths"]

        # Support alias 'matching_gaps'
        if "matching_gaps" in data and "gaps" not in data:
            data["gaps"] = data["matching_gaps"]

        # Ensure score is rounded Decimal
        raw_score = data.get("semantic_score", 0)
        try:
            dec = Decimal(str(raw_score)).quantize(Decimal("0.01"))
            if dec < Decimal("0.00"):
                dec = Decimal("0.00")
            elif dec > Decimal("100.00"):
                dec = Decimal("100.00")
            data["semantic_score"] = dec
        except Exception:
            data["semantic_score"] = Decimal("0.00")

        return data
