"""Domain service orchestrating truthful resume tailoring and PDF generation."""

import logging
import math
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import EntityNotFoundError
from app.infrastructure.storage.base import FileStorage
from app.infrastructure.storage.local import get_file_storage
from app.modules.jobs.models import JobStatusEnum
from app.modules.matching.llm.factory import get_llm_provider
from app.modules.matching.llm.protocol import LLMProvider
from app.modules.matching.repository import MatchingRepository
from app.modules.resumes.repository import MasterResumeRepository
from app.modules.resumes.schemas import PaginationMetadata
from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum
from app.modules.tailoring.evidence import CandidateEvidenceVault
from app.modules.tailoring.exceptions import (
    EvidenceNotFoundError,
    RenderingError,
    TailoringError,
)
from app.modules.tailoring.models import TailoredResume
from app.modules.tailoring.prompt import build_tailoring_prompt
from app.modules.tailoring.renderer import ResumeRenderer
from app.modules.tailoring.repository import TailoringRepository
from app.modules.tailoring.schemas import (
    TailoredResumeContent,
    TailorResumeRequest,
)
from app.modules.tailoring.validator import ClaimValidator

logger = logging.getLogger(__name__)


class TailoringService:
    """Service orchestrating candidate evidence retrieval, LLM tailoring, claim validation, and PDF compilation."""

    def __init__(
        self,
        repository: TailoringRepository | None = None,
        matching_repository: MatchingRepository | None = None,
        resume_repository: MasterResumeRepository | None = None,
        renderer: ResumeRenderer | None = None,
        storage: FileStorage | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.repository = repository or TailoringRepository()
        self.matching_repository = matching_repository or MatchingRepository()
        self.resume_repository = resume_repository or MasterResumeRepository()
        self.renderer = renderer or ResumeRenderer()
        self.storage = storage or get_file_storage()
        self._llm_provider = llm_provider

    @property
    def llm_provider(self) -> LLMProvider:
        """Obtain the configured LLM provider instance."""
        if self._llm_provider is not None:
            return self._llm_provider
        return get_llm_provider()

    async def request_tailoring(
        self,
        session: AsyncSession,
        request: TailorResumeRequest,
    ) -> TailoredResume:
        """Initiate or re-run resume tailoring for a qualified JobMatch.

        Args:
            session: Active database session.
            request: Tailoring parameters including job match ID.

        Returns:
            TailoredResume entity in PENDING or existing status.

        Raises:
            EntityNotFoundError: If JobMatch or ResumeVersion does not exist.
            TailoringError: If JobMatch is not qualified.
            EvidenceNotFoundError: If candidate lacks active master resume version.
        """
        # 1. Fetch JobMatch with related entities
        job_match = await self.matching_repository.get_match_with_relations(
            session=session,
            match_id=request.job_match_id,
        )
        if job_match is None:
            raise EntityNotFoundError(
                entity_name="JobMatch",
                identifier=str(request.job_match_id),
            )

        # 2. Verify eligibility / qualification threshold
        if not job_match.is_qualified:
            raise TailoringError(
                f"JobMatch '{request.job_match_id}' is not qualified for resume tailoring "
                f"(eligibility: {job_match.eligibility_status.value}, deterministic_score: {job_match.deterministic_score})."
            )

        candidate_profile = job_match.candidate_profile

        # 3. Resolve target ResumeVersion
        if request.resume_version_id is not None:
            resume_version = await self.resume_repository.get_version_by_id(
                session=session,
                version_id=request.resume_version_id,
            )
            if resume_version is None:
                raise EntityNotFoundError(
                    entity_name="ResumeVersion",
                    identifier=str(request.resume_version_id),
                )
        else:
            active_master = await self.matching_repository.get_active_resume_for_candidate(
                session=session,
                candidate_profile_id=candidate_profile.id,
            )
            if active_master is None or not active_master.versions:
                raise EvidenceNotFoundError(
                    f"Candidate profile '{candidate_profile.id}' has no active master resume with parsed versions."
                )
            resume_version = active_master.versions[0]

        # 4. Check existing tailored resume for idempotency
        existing = await self.repository.get_by_job_and_version(
            session=session,
            job_id=job_match.job_id,
            resume_version_id=resume_version.id,
        )

        if existing is not None and not request.force_regenerate:
            # If already generated or in progress, return without duplicating work
            if existing.generation_status in (
                TailoredResumeStatusEnum.COMPLETED,
                TailoredResumeStatusEnum.PENDING,
                TailoredResumeStatusEnum.PROCESSING,
                TailoredResumeStatusEnum.VALIDATING,
                TailoredResumeStatusEnum.RENDERING,
            ):
                return existing

        if existing is not None and (
            request.force_regenerate
            or existing.generation_status == TailoredResumeStatusEnum.FAILED
        ):
            # Reset state for retry
            existing.generation_status = TailoredResumeStatusEnum.PENDING
            existing.validation_error = None
            existing.generation_attempts += 1
            record = await self.repository.save(session, existing)
        else:
            # Create fresh record (attempting original template preservation by default)
            record = await self.repository.create(
                session=session,
                candidate_profile_id=candidate_profile.id,
                job_id=job_match.job_id,
                job_match_id=job_match.id,
                resume_version_id=resume_version.id,
                rendering_strategy=RenderingStrategyEnum.PRESERVED,
                generation_status=TailoredResumeStatusEnum.PENDING,
            )

        # 5. Dispatch async Celery background task
        try:
            from app.modules.tailoring.tasks import generate_tailored_resume_task

            generate_tailored_resume_task.apply_async(
                args=[str(record.id)],
                queue="tailoring",
            )
        except Exception as exc:
            logger.warning(
                f"Unable to dispatch Celery tailoring task for record {record.id}: {exc}. "
                "Pipeline may be triggered synchronously or in worker."
            )

        return record

    async def execute_tailoring_pipeline(
        self,
        session: AsyncSession,
        tailored_resume_id: uuid.UUID,
    ) -> TailoredResume:
        """Drive full tailoring pipeline: evidence vault, LLM call, claim validation, PDF rendering, and persistence.

        Args:
            session: Active database session.
            tailored_resume_id: Primary key of TailoredResume to process.

        Returns:
            Updated TailoredResume entity.
        """
        record = await self.repository.get_by_id(
            session=session,
            tailored_resume_id=tailored_resume_id,
            load_relations=True,
        )
        if record is None:
            raise EntityNotFoundError(
                entity_name="TailoredResume",
                identifier=str(tailored_resume_id),
            )

        if record.generation_status == TailoredResumeStatusEnum.COMPLETED:
            logger.info(
                f"TailoredResume '{tailored_resume_id}' already completed; skipping pipeline."
            )
            return record

        settings = get_settings()
        max_attempts = settings.tailoring_max_regeneration_attempts

        # 1. Transition to PROCESSING
        record.generation_status = TailoredResumeStatusEnum.PROCESSING
        record = await self.repository.save(session, record)

        # 2. Compile Candidate Evidence Vault
        vault = CandidateEvidenceVault.from_entities(
            candidate_profile=record.candidate_profile,
            skills=record.candidate_profile.skills,
            resume_version=record.resume_version,
            job=record.job,
        )

        system_prompt, user_prompt = build_tailoring_prompt(vault, record.job)

        validated_content: TailoredResumeContent | None = None
        last_report = None
        current_attempt = 1

        # 3. LLM Generation and Claim Validation Loop
        while current_attempt <= max_attempts:
            try:
                record.generation_attempts = current_attempt
                logger.info(
                    f"Tailoring generation attempt {current_attempt}/{max_attempts} for record {record.id}"
                )

                # Generate structured content from LLM
                content = await self.llm_provider.generate_structured(
                    prompt=user_prompt,
                    response_schema=TailoredResumeContent,
                    system_prompt=system_prompt,
                )

                # Transition to VALIDATING
                record.generation_status = TailoredResumeStatusEnum.VALIDATING
                await self.repository.save(session, record)

                # Run claim validation and repair
                validator = ClaimValidator(vault)
                repaired_content, report = validator.validate_and_repair(content)
                last_report = report

                if report.is_valid:
                    validated_content = repaired_content
                    logger.info(
                        f"Resume tailoring passed claim validation on attempt {current_attempt}. "
                        f"Repaired claims: {len(report.repaired_claims)}"
                    )
                    break
                else:
                    logger.warning(
                        f"Attempt {current_attempt} failed claim validation: {report.violations_detected}"
                    )
                    current_attempt += 1

            except Exception as exc:
                logger.warning(
                    f"Error during LLM generation attempt {current_attempt} for record {record.id}: {exc}"
                )
                current_attempt += 1

        # Handle failure after maximum attempts
        if validated_content is None or last_report is None or not last_report.is_valid:
            error_reason = (
                "; ".join(last_report.violations_detected)
                if last_report and last_report.violations_detected
                else "Claim validation failed after maximum regeneration attempts."
            )
            record.generation_status = TailoredResumeStatusEnum.FAILED
            record.validation_error = error_reason
            record.validation_metadata = last_report.model_dump() if last_report else {}
            return await self.repository.save(session, record)

        # 4. PDF Rendering
        record.generation_status = TailoredResumeStatusEnum.RENDERING
        await self.repository.save(session, record)

        # Determine rendering strategy (attempt PRESERVED unless FALLBACK explicitly requested)
        template_meta = record.resume_version.template_metadata or {}
        requested_strategy = record.rendering_strategy or RenderingStrategyEnum.PRESERVED

        try:
            pdf_bytes, actual_strategy, fallback_reason = self.renderer.render(
                content=validated_content,
                candidate_profile=record.candidate_profile,
                strategy=requested_strategy,
                template_metadata=template_meta,
            )

            # Validate PDF binary
            pdf_validation = self.renderer.validate_pdf_binary(pdf_bytes)
        except RenderingError as rend_err:
            logger.error(f"Rendering error for record {record.id}: {rend_err}")
            record.generation_status = TailoredResumeStatusEnum.FAILED
            record.validation_error = f"PDF Rendering failed: {rend_err}"
            return await self.repository.save(session, record)

        # 5. File Storage and Metadata Persistence
        safe_company = re.sub(r"[^\w\-]", "_", record.job.canonical_company_name.strip())
        safe_title = re.sub(r"[^\w\-]", "_", record.job.title.strip())
        safe_name = re.sub(r"[^\w\-]", "_", record.candidate_profile.full_name.strip())
        file_name = f"{safe_name}_{safe_company}_{safe_title}_Resume.pdf"
        storage_key = f"resumes/tailored/{record.candidate_profile_id}/{record.id}.pdf"

        await self.storage.save(storage_key, pdf_bytes, content_type="application/pdf")

        # 6. Finalize record
        record.generation_status = TailoredResumeStatusEnum.COMPLETED
        record.rendering_strategy = actual_strategy
        record.tailored_content = validated_content.model_dump()
        record.validation_metadata = {
            **last_report.model_dump(),
            "pdf_validation": pdf_validation,
            "requested_strategy": requested_strategy.value if requested_strategy else "PRESERVED",
            "actual_strategy": actual_strategy.value,
            "fallback_reason": fallback_reason,
        }
        record.storage_key = storage_key
        record.file_name = file_name
        record.file_size_bytes = len(pdf_bytes)
        record.checksum_sha256 = pdf_validation["checksum_sha256"]
        record.validation_error = None
        record.completed_at = datetime.now(UTC)

        # Update Job status to TAILORED if appropriate
        if record.job.status in (JobStatusEnum.MATCHED, JobStatusEnum.TAILORING):
            record.job.status = JobStatusEnum.TAILORED

        saved = await self.repository.save(session, record)
        logger.info(f"Successfully tailored resume {record.id} for job {record.job_id}")
        return saved

    async def get_tailored_resume(
        self,
        session: AsyncSession,
        tailored_resume_id: uuid.UUID,
    ) -> TailoredResume:
        """Fetch a specific tailored resume by ID."""
        record = await self.repository.get_by_id(
            session=session,
            tailored_resume_id=tailored_resume_id,
            load_relations=True,
        )
        if record is None:
            raise EntityNotFoundError(
                entity_name="TailoredResume",
                identifier=str(tailored_resume_id),
            )
        return record

    async def list_tailored_resumes(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TailoredResume], PaginationMetadata]:
        """Fetch paginated tailored resumes for a candidate."""
        items, total_count = await self.repository.list_for_candidate(
            session=session,
            candidate_profile_id=candidate_profile_id,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0
        pagination = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
        return items, pagination

    async def download_tailored_pdf(
        self,
        session: AsyncSession,
        tailored_resume_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        """Download raw PDF bytes for a completed tailored resume.

        Returns:
            Tuple of (pdf_bytes, file_name, mime_type).

        Raises:
            EntityNotFoundError: If record is not found.
            TailoringError: If record generation is not yet completed or storage file missing.
        """
        record = await self.get_tailored_resume(session, tailored_resume_id)

        if record.generation_status != TailoredResumeStatusEnum.COMPLETED:
            raise TailoringError(
                f"Tailored resume '{tailored_resume_id}' is not ready for download "
                f"(current status: {record.generation_status.value})."
            )

        if not record.storage_key:
            raise TailoringError(
                f"Tailored resume '{tailored_resume_id}' has no associated storage file."
            )

        try:
            pdf_bytes = await self.storage.read(record.storage_key)
        except Exception as exc:
            raise TailoringError(f"Failed to read file from storage: {exc}") from exc

        file_name = record.file_name or f"Resume_{record.id}.pdf"
        return pdf_bytes, file_name, record.mime_type


_tailoring_service = TailoringService()


def get_tailoring_service() -> TailoringService:
    """FastAPI dependency for accessing TailoringService singleton."""
    return _tailoring_service
