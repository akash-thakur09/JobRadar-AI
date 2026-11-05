"""Domain service orchestrating candidate-job matching and scoring."""

import logging
import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    EmploymentTypeEnum,
    WorkplaceTypeEnum,
)
from app.modules.candidate.repository import CandidateRepository
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobSummaryResponse, PaginatedResponse, PaginationMetadata
from app.modules.matching.eligibility import evaluate_eligibility
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.matching.repository import MatchingRepository
from app.modules.matching.schemas import (
    JobMatchDetailResponse,
    JobMatchSummaryResponse,
)
from app.modules.matching.skill_normalizer import extract_skills_from_text
from app.modules.matching.weighted_scorer import calculate_deterministic_score

logger = logging.getLogger(__name__)

QUALIFICATION_SCORE_THRESHOLD = Decimal("50.00")


class MatchingService:
    """Service orchestrating Layer 1 eligibility and Layer 2 deterministic scoring."""

    def __init__(
        self,
        repository: MatchingRepository | None = None,
        candidate_repo: CandidateRepository | None = None,
        job_repo: JobRepository | None = None,
    ) -> None:
        self.repository = repository or MatchingRepository()
        self.candidate_repo = candidate_repo or CandidateRepository()
        self.job_repo = job_repo or JobRepository()

    async def _resolve_candidate_profile(
        self, session: AsyncSession, candidate_profile_id: uuid.UUID | None
    ) -> tuple[CandidateProfile, CandidatePreference]:
        """Fetch candidate profile and preferences, defaulting to primary profile if omitted."""
        if candidate_profile_id is not None:
            profile = await self.candidate_repo.get_profile(session, candidate_profile_id)
            if profile is None:
                raise EntityNotFoundError("CandidateProfile", candidate_profile_id)
            pref = await self.candidate_repo.get_preferences_by_profile_id(session, profile.id)
        else:
            profile = await self.candidate_repo.get_or_create_default_profile(session)
            pref = await self.candidate_repo.get_preferences_by_profile_id(session, profile.id)

        if pref is None:
            # Fallback default preferences if absent
            pref = CandidatePreference(
                candidate_profile_id=profile.id,
                minimum_relevance_score=Decimal("70.00"),
                preferred_titles=[],
                preferred_workplace_types=[
                    WorkplaceTypeEnum.REMOTE,
                    WorkplaceTypeEnum.HYBRID,
                ],
                preferred_locations=[],
                preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
                max_job_age_days=14,
            )

        return profile, pref

    async def evaluate_job_for_candidate(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        candidate_profile_id: uuid.UUID | None = None,
    ) -> JobMatch:
        """Evaluate Layer 1 Eligibility and Layer 2 Scoring for a single candidate-job pair.

        Guarantees:
        - Layer 1 hard failure stops qualification immediately (score remains 0.00).
        - Layer 2 weighted scoring executed only for eligible opportunities.
        - Persists structured explainability breakdown.
        - Idempotently creates or updates the JobMatch record.
        """
        profile, pref = await self._resolve_candidate_profile(session, candidate_profile_id)

        job = await self.job_repo.get_job_by_id(session, job_id, load_sources=False)
        if job is None:
            raise EntityNotFoundError("Job", job_id)

        now = datetime.now(UTC)

        # 1. Extract canonical skills from JD
        combined_text = f"{job.title}\n{job.description_text}"
        job_skills = extract_skills_from_text(combined_text)

        # 2. Layer 1: Deterministic Eligibility Evaluation
        elig_result = evaluate_eligibility(
            job=job,
            profile=profile,
            prefs=pref,
            job_skills=job_skills,
            now=now,
        )

        if not elig_result.is_eligible:
            # Hard boolean failure: cannot qualify or score (canonical job lifecycle remains independent)
            match_data: dict[str, Any] = {
                "job_id": job.id,
                "candidate_profile_id": profile.id,
                "eligibility_status": elig_result.status,
                "deterministic_score": Decimal("0.00"),
                "semantic_score": None,
                "final_score": Decimal("0.00"),
                "skill_score": Decimal("0.00"),
                "experience_score": Decimal("0.00"),
                "title_score": Decimal("0.00"),
                "preference_score": Decimal("0.00"),
                "match_explanation": elig_result.explanation,
                "match_explanation_details": {
                    "is_qualified": False,
                    "qualification_status": "ELIGIBILITY_FAILED",
                    "eligibility": elig_result.to_dict(),
                },
            }
            logger.info(
                "Candidate failed Layer 1 eligibility for job",
                extra={
                    "job_id": str(job.id),
                    "candidate_id": str(profile.id),
                    "eligibility_status": elig_result.status.value,
                    "reason": elig_result.explanation,
                },
            )
            return await self.repository.upsert_match(session, match_data)

        # 3. Layer 2: Deterministic Weighted Scoring
        score_breakdown = calculate_deterministic_score(
            job=job,
            profile=profile,
            prefs=pref,
            job_skills=job_skills,
            now=now,
        )

        det_score = score_breakdown.deterministic_score

        # Determine qualification threshold (TD-005 Section 4.1: >= 50.00 qualifies)
        threshold = QUALIFICATION_SCORE_THRESHOLD
        is_qualified = det_score >= threshold
        qualification_status = "QUALIFIED" if is_qualified else "REJECTED"

        if is_qualified:
            matched_skills_list = score_breakdown.details["skills"].get("matched_skills", [])
            explanation = (
                f"Eligible position. Deterministic relevance score: {det_score}/100. "
                f"Matched skills: {matched_skills_list}."
            )
        else:
            explanation = f"Eligible but below qualification threshold (score: {det_score}/100 < {threshold})."

        match_data = {
            "job_id": job.id,
            "candidate_profile_id": profile.id,
            "eligibility_status": EligibilityStatusEnum.ELIGIBLE,
            "deterministic_score": det_score,
            "semantic_score": None,
            "final_score": score_breakdown.final_score,
            "skill_score": score_breakdown.skill_score,
            "experience_score": score_breakdown.experience_score,
            "title_score": score_breakdown.title_score,
            "preference_score": score_breakdown.preference_score,
            "match_explanation": explanation,
            "match_explanation_details": {
                "is_qualified": is_qualified,
                "qualification_status": qualification_status,
                "eligibility": elig_result.to_dict(),
                "deterministic_breakdown": score_breakdown.details,
            },
        }

        match_obj = await self.repository.upsert_match(session, match_data)

        logger.info(
            "Completed candidate-job match evaluation",
            extra={
                "job_id": str(job.id),
                "candidate_id": str(profile.id),
                "deterministic_score": float(det_score),
                "qualification_status": qualification_status,
            },
        )
        return match_obj

    async def evaluate_pending_job_matches(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID | None = None,
        batch_size: int = 100,
    ) -> int:
        """Batch evaluate all un-matched canonical jobs for a candidate."""
        profile, _ = await self._resolve_candidate_profile(session, candidate_profile_id)

        unmatched_jobs = await self.repository.get_unmatched_jobs_for_candidate(
            session=session, candidate_profile_id=profile.id, limit=batch_size
        )

        evaluated_count = 0
        for job in unmatched_jobs:
            try:
                await self.evaluate_job_for_candidate(
                    session=session,
                    job_id=job.id,
                    candidate_profile_id=profile.id,
                )
                evaluated_count += 1
            except Exception as exc:
                logger.warning(f"Skipping match evaluation for job {job.id} due to error: {exc}")
                continue

        return evaluated_count

    async def get_match(self, session: AsyncSession, match_id: uuid.UUID) -> JobMatchDetailResponse:
        """Fetch detailed match record with score breakdown and provenance."""
        match = await self.repository.get_match_by_id(session, match_id, load_job=True)
        if match is None:
            raise EntityNotFoundError("JobMatch", match_id)

        job_summary = JobSummaryResponse.model_validate(match.job) if match.job else None

        return JobMatchDetailResponse(
            id=match.id,
            job_id=match.job_id,
            candidate_profile_id=match.candidate_profile_id,
            eligibility_status=match.eligibility_status,
            deterministic_score=match.deterministic_score,
            semantic_score=match.semantic_score,
            final_score=match.final_score,
            skill_score=match.skill_score,
            experience_score=match.experience_score,
            title_score=match.title_score,
            preference_score=match.preference_score,
            match_explanation=match.match_explanation,
            match_explanation_details=match.match_explanation_details,
            is_qualified=match.is_qualified,
            created_at=match.created_at,
            updated_at=match.updated_at,
            job_title=match.job.title if match.job else None,
            company_name=match.job.canonical_company_name if match.job else None,
            workplace_type=match.job.workplace_type if match.job else None,
            normalized_location=match.job.normalized_location if match.job else None,
            job=job_summary,
        )

    async def list_matches(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID | None = None,
        min_score: Decimal | None = None,
        eligibility_status: EligibilityStatusEnum | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[JobMatchSummaryResponse]:
        """Fetch paginated matches for a candidate sorted by final score descending."""
        profile, _ = await self._resolve_candidate_profile(session, candidate_profile_id)

        matches, total_items = await self.repository.list_matches(
            session=session,
            candidate_profile_id=profile.id,
            min_score=min_score,
            eligibility_status=eligibility_status,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

        items: list[JobMatchSummaryResponse] = []
        for m in matches:
            items.append(
                JobMatchSummaryResponse(
                    id=m.id,
                    job_id=m.job_id,
                    candidate_profile_id=m.candidate_profile_id,
                    eligibility_status=m.eligibility_status,
                    deterministic_score=m.deterministic_score,
                    semantic_score=m.semantic_score,
                    final_score=m.final_score,
                    skill_score=m.skill_score,
                    experience_score=m.experience_score,
                    title_score=m.title_score,
                    preference_score=m.preference_score,
                    match_explanation=m.match_explanation,
                    is_qualified=m.is_qualified,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                    job_title=m.job.title if m.job else None,
                    company_name=m.job.canonical_company_name if m.job else None,
                    workplace_type=m.job.workplace_type if m.job else None,
                    normalized_location=m.job.normalized_location if m.job else None,
                )
            )

        return PaginatedResponse[JobMatchSummaryResponse](
            items=items,
            pagination=PaginationMetadata(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1 and total_pages > 0,
            ),
        )


def get_matching_service() -> MatchingService:
    """Dependency provider for MatchingService."""
    return MatchingService()
