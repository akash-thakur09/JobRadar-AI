"""Service orchestrating Layer 3 LLM Semantic Analysis and hybrid scoring."""

import logging
import uuid
from decimal import Decimal
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.modules.matching.evidence_validator import EvidenceValidator
from app.modules.matching.llm.factory import get_llm_provider
from app.modules.matching.llm.protocol import LLMProvider
from app.modules.matching.llm.schemas import SemanticAnalysisResult
from app.modules.matching.models import EligibilityStatusEnum, JobMatch, SemanticAnalysisStatusEnum
from app.modules.matching.prompt import (
    SEMANTIC_ANALYSIS_SYSTEM_PROMPT,
    build_candidate_context,
    build_candidate_text_corpus,
    build_job_context,
    build_semantic_analysis_prompt,
)
from app.modules.matching.repository import MatchingRepository

logger = logging.getLogger(__name__)


class SemanticAnalysisService:
    """Orchestrates LLM semantic alignment evaluation, evidence validation, and hybrid scoring."""

    def __init__(
        self,
        repository: MatchingRepository | None = None,
        llm_provider: LLMProvider | None = None,
        evidence_validator: EvidenceValidator | None = None,
    ) -> None:
        self.repository = repository or MatchingRepository()
        self._llm_provider = llm_provider
        self.evidence_validator = evidence_validator or EvidenceValidator()

    @property
    def llm_provider(self) -> LLMProvider:
        """Resolve LLM provider lazily to reflect dynamic test overrides."""
        if self._llm_provider is not None:
            return self._llm_provider
        return get_llm_provider()

    async def evaluate_semantic_match(
        self,
        session: AsyncSession,
        match_id: uuid.UUID,
    ) -> JobMatch:
        """Evaluate Layer 3 LLM Semantic Analysis for a qualified job match.

        Enforces:
        - Layer 1 hard eligibility gate (disqualified jobs skipped).
        - Layer 2 score threshold (deterministic score < 50.00 skipped).
        - Evidence verification against candidate profile & master resume facts.
        - Hybrid final score: 0.60 * Deterministic + 0.40 * Semantic.
        - Graceful degradation: preserves deterministic score on LLM errors.

        Args:
            session: Active SQLAlchemy database session.
            match_id: Primary key of the JobMatch to evaluate.

        Returns:
            Updated JobMatch instance with semantic score, status, and breakdown.
        """
        match = await self.repository.get_match_with_relations(session, match_id)
        if not match:
            raise EntityNotFoundError("JobMatch", match_id)

        # 1. Gate: Candidate must be eligible
        if match.eligibility_status != EligibilityStatusEnum.ELIGIBLE:
            logger.info(
                f"Skipping Layer 3 semantic analysis for match {match.id}: "
                f"candidate is ineligible ({match.eligibility_status.value})"
            )
            match.semantic_analysis_status = SemanticAnalysisStatusEnum.SKIPPED
            await session.flush()
            return match

        # 2. Gate: Deterministic score threshold >= 50.00
        if match.deterministic_score < Decimal("50.00"):
            logger.info(
                f"Skipping Layer 3 semantic analysis for match {match.id}: "
                f"deterministic score ({match.deterministic_score}) < 50.00"
            )
            match.semantic_analysis_status = SemanticAnalysisStatusEnum.SKIPPED
            await session.flush()
            return match

        # 3. Transition to PROCESSING state
        match.semantic_analysis_status = SemanticAnalysisStatusEnum.PROCESSING
        await session.flush()

        candidate_profile = match.candidate_profile
        job = match.job

        # Fetch active master resume and versions
        active_resume = await self.repository.get_active_resume_for_candidate(
            session=session,
            candidate_profile_id=candidate_profile.id,
        )

        # 4. Context preparation & Prompt building
        candidate_skills = list(candidate_profile.skills)
        candidate_context = build_candidate_context(
            profile=candidate_profile,
            skills=candidate_skills,
            active_resume=active_resume,
        )
        candidate_corpus = build_candidate_text_corpus(
            profile=candidate_profile,
            skills=candidate_skills,
            active_resume=active_resume,
        )
        job_context = build_job_context(
            job=job,
            deterministic_details=match.match_explanation_details,
        )
        prompt = build_semantic_analysis_prompt(candidate_context, job_context)

        # 5. LLM Provider invocation with graceful fallback
        try:
            raw_semantic_result = await self.llm_provider.generate_structured(
                prompt=prompt,
                response_schema=SemanticAnalysisResult,
                system_prompt=SEMANTIC_ANALYSIS_SYSTEM_PROMPT,
            )
        except Exception as exc:
            logger.warning(
                f"Layer 3 LLM Semantic Analysis failed for match {match.id}: {exc}. "
                f"Degrading gracefully to deterministic score."
            )
            match.semantic_analysis_status = SemanticAnalysisStatusEnum.FAILED
            match.semantic_score = None
            match.final_score = match.deterministic_score

            details = dict(match.match_explanation_details)
            details["llm_degraded"] = True
            details["llm_error"] = str(exc)
            match.match_explanation_details = details
            await session.flush()
            return match

        # 6. Pragmatic Evidence Validation
        candidate_skills_set = {s.skill_name for s in candidate_skills}
        validated_result = self.evidence_validator.validate_semantic_result(
            result=raw_semantic_result,
            candidate_skills=candidate_skills_set,
            candidate_text_evidence=candidate_corpus,
        )

        # 7. Hybrid Final Score Calculation (60% Deterministic + 40% Semantic)
        d_score = match.deterministic_score
        s_score = validated_result.semantic_score
        final_score = (Decimal("0.60") * d_score + Decimal("0.40") * s_score).quantize(
            Decimal("0.01")
        )

        # 8. Persist outcomes
        match.semantic_score = s_score
        match.final_score = final_score
        match.semantic_analysis_status = SemanticAnalysisStatusEnum.COMPLETED

        details = dict(match.match_explanation_details)
        details["semantic_evaluation"] = validated_result.model_dump(mode="json")
        details["llm_degraded"] = False
        details["final_score"] = float(final_score)
        match.match_explanation_details = details

        rec_label = validated_result.recommendation.value.replace("_", " ")
        match.match_explanation = (
            f"Evaluated as {rec_label} with Final Hybrid Score {final_score}/100.00 "
            f"(Deterministic: {d_score}, Semantic: {s_score}). {validated_result.reasoning_summary}"
        )

        await session.flush()
        return match


@lru_cache
def get_semantic_service() -> SemanticAnalysisService:
    """Return cached singleton instance of SemanticAnalysisService."""
    return SemanticAnalysisService()
