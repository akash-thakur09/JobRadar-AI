"""Pragmatic evidence validation layer for LLM semantic analysis."""

import logging
from decimal import Decimal

from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    TransferableSkill,
)
from app.modules.matching.skill_normalizer import (
    extract_skills_from_text,
    normalize_skill_token,
)

logger = logging.getLogger(__name__)


class EvidenceValidator:
    """Validates LLM-generated semantic analysis claims against candidate factual evidence.

    Protects against LLM hallucinations regarding candidate skills, qualifications,
    and transferable capabilities.
    """

    def validate_semantic_result(
        self,
        result: SemanticAnalysisResult,
        candidate_skills: set[str],
        candidate_text_evidence: str,
    ) -> SemanticAnalysisResult:
        """Cross-check LLM analysis claims against candidate profile and resume facts.

        Args:
            result: The raw SemanticAnalysisResult produced by the LLM provider.
            candidate_skills: Set of normalized skills verified on candidate profile.
            candidate_text_evidence: Text corpus of profile headline, summary, and resume content.

        Returns:
            Sanitized and evidence-validated SemanticAnalysisResult.
        """
        lowered_corpus = candidate_text_evidence.lower()
        extracted_from_corpus = extract_skills_from_text(candidate_text_evidence)
        known_skills = set(candidate_skills) | extracted_from_corpus

        validated_transferable: list[TransferableSkill] = []
        unsupported: list[str] = list(result.unsupported_claims)

        # 1. Validate transferable skills
        for ts in result.transferable_skills:
            normalized_candidate_skill = normalize_skill_token(ts.candidate_skill)
            raw_candidate_skill = ts.candidate_skill.strip().lower()

            has_skill_evidence = (
                normalized_candidate_skill in known_skills
                or raw_candidate_skill in lowered_corpus
                or any(
                    part in known_skills
                    for part in raw_candidate_skill.replace("-", " ").split()
                    if len(part) > 2
                )
            )

            if has_skill_evidence:
                validated_transferable.append(ts)
            else:
                msg = (
                    f"Claimed transferable skill '{ts.candidate_skill}' lacks supporting "
                    f"evidence in candidate profile or master resume."
                )
                logger.info(f"Evidence validation rejected transferable skill: {msg}")
                unsupported.append(msg)

        # 2. Check strengths for claims of unverified technical skills
        for strength in result.strengths:
            combined_claim = f"{strength.claim} {strength.evidence}"
            mentioned_skills = extract_skills_from_text(combined_claim)

            # If strength claims specific skills that candidate has zero evidence for
            foreign_skills = mentioned_skills - known_skills
            # Filter out target tech terms if mentioned in job_context
            for foreign_skill in foreign_skills:
                # If foreign skill is not anywhere in candidate corpus and is stated in claim
                if foreign_skill not in lowered_corpus and foreign_skill in strength.claim.lower():
                    # Only flag if it appears as an asserted candidate capability
                    unsupported_msg = (
                        f"Strength claim references '{foreign_skill}' without direct evidence "
                        f"in candidate background."
                    )
                    if unsupported_msg not in unsupported:
                        unsupported.append(unsupported_msg)

        # 3. Apply confidence and score adjustment if hallucinations were detected
        adjusted_confidence = result.confidence
        adjusted_score = result.semantic_score

        if unsupported:
            # Dampen confidence proportionally
            penalty = 0.15 * len(unsupported)
            adjusted_confidence = max(0.10, round(result.confidence - penalty, 2))

            # If transferable skills or claims were fabricated, dampen score proportionally
            # (e.g. 5% per unsupported claim, capped at 30% reduction)
            score_penalty_ratio = Decimal(str(min(0.30, 0.05 * len(unsupported))))
            adjusted_score = (adjusted_score * (Decimal("1.00") - score_penalty_ratio)).quantize(
                Decimal("0.01")
            )

        return SemanticAnalysisResult(
            semantic_score=adjusted_score,
            recommendation=result.recommendation,
            confidence=adjusted_confidence,
            reasoning_summary=result.reasoning_summary,
            strengths=result.strengths,
            gaps=result.gaps,
            transferable_skills=validated_transferable,
            unsupported_claims=unsupported,
        )
