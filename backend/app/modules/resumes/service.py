"""Business logic service for Master Resumes and Versioning."""

import hashlib
import math
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.infrastructure.storage.base import FileStorage
from app.infrastructure.storage.local import get_file_storage
from app.modules.candidate.service import CandidateService, get_candidate_service
from app.modules.resumes.models import MasterResume, ResumeProcessingStatus, ResumeVersion
from app.modules.resumes.parsers.registry import get_parser_for_mime_type
from app.modules.resumes.repository import MasterResumeRepository
from app.modules.resumes.schemas import (
    PaginationMetadata,
    validate_resume_file,
)


class ResumeService:
    """Service orchestrating resume upload, storage, parsing dispatch, and activation."""

    def __init__(
        self,
        repository: MasterResumeRepository | None = None,
        candidate_service: CandidateService | None = None,
        storage: FileStorage | None = None,
    ) -> None:
        self.repository = repository or MasterResumeRepository()
        self.candidate_service = candidate_service or get_candidate_service()
        self.storage = storage or get_file_storage()

    async def upload_resume(
        self,
        session: AsyncSession,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        sync_parse: bool = False,
    ) -> tuple[MasterResume, ResumeVersion]:
        """Validate, store, and create database records for an uploaded resume.

        Args:
            session: Active database session.
            filename: Original client filename.
            content: Raw file binary bytes.
            content_type: Optional client-provided MIME content type.
            sync_parse: Whether to perform synchronous parsing (e.g. for testing or light load).

        Returns:
            Tuple of (MasterResume, Initial ResumeVersion).
        """
        # 1. Binary & format validation
        canonical_mime = validate_resume_file(filename, content, content_type)

        # 2. Checksum calculation
        checksum_sha256 = hashlib.sha256(content).hexdigest()

        # 3. Retrieve active candidate profile
        profile = await self.candidate_service.get_profile(session)

        # 4. Check for duplicate upload
        existing = await self.repository.get_resume_by_checksum(
            session=session,
            candidate_profile_id=profile.id,
            checksum_sha256=checksum_sha256,
        )
        if existing is not None:
            raise EntityAlreadyExistsError(
                entity_name="MasterResume",
                identifier=f"A resume with identical content (SHA256: {checksum_sha256[:12]}...) already exists.",
            )

        # 5. Generate secure internal storage key
        safe_ext = Path(filename).suffix.lower()
        storage_key = f"resumes/raw/{profile.id}/{uuid.uuid4()}{safe_ext}"

        # 6. Store file binary
        await self.storage.save(storage_key, content, content_type=canonical_mime)

        # 7. Create MasterResume record (active by default)
        resume = await self.repository.create_resume(
            session=session,
            candidate_profile_id=profile.id,
            filename=filename.strip(),
            storage_key=storage_key,
            mime_type=canonical_mime,
            file_size_bytes=len(content),
            checksum_sha256=checksum_sha256,
            is_active=True,
        )

        # 8. Create initial ResumeVersion
        version = await self.repository.create_version(
            session=session,
            master_resume_id=resume.id,
            version_number=1,
            structured_content={},
            template_metadata=None,
            checksum_sha256=checksum_sha256,
            is_valid=True,
            processing_status=ResumeProcessingStatus.PENDING.value,
        )

        # 9. Parsing execution
        if sync_parse:
            # Inline extraction
            try:
                parser = get_parser_for_mime_type(canonical_mime, filename)
                result = await parser.parse(content, filename)
                new_status = (
                    ResumeProcessingStatus.COMPLETED.value
                    if result.is_valid
                    else ResumeProcessingStatus.FAILED.value
                )
                error_msg = "; ".join(result.extraction_warnings) if not result.is_valid else None
                version = await self.repository.update_version(
                    session=session,
                    version=version,
                    structured_content=result.structured_content,
                    template_metadata=result.template_metadata,
                    is_valid=result.is_valid,
                    processing_status=new_status,
                    parsing_error=error_msg,
                )
            except Exception as exc:
                version = await self.repository.update_version(
                    session=session,
                    version=version,
                    is_valid=False,
                    processing_status=ResumeProcessingStatus.FAILED.value,
                    parsing_error=str(exc),
                )
        else:
            # Dispatch background task to Celery
            try:
                from app.modules.resumes.tasks import process_resume_task

                process_resume_task.apply_async(args=[str(version.id)], queue="processing")
            except Exception:
                # If celery broker is offline in local dev without queue, fallback gracefully
                pass

        return resume, version

    async def list_resumes(
        self,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MasterResume], PaginationMetadata]:
        """Fetch paginated master resumes with metadata."""
        profile = await self.candidate_service.get_profile(session)
        items, total_items = await self.repository.list_resumes(
            session=session,
            candidate_profile_id=profile.id,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
        pagination = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
        return items, pagination

    async def get_resume(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
    ) -> MasterResume:
        """Fetch a specific master resume for the active candidate."""
        profile = await self.candidate_service.get_profile(session)
        resume = await self.repository.get_resume_by_id(
            session=session,
            resume_id=resume_id,
            candidate_profile_id=profile.id,
        )
        if resume is None:
            raise EntityNotFoundError(entity_name="MasterResume", identifier=str(resume_id))

        return resume

    async def activate_resume(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
    ) -> MasterResume:
        """Set a master resume as the single active resume for the candidate."""
        resume = await self.get_resume(session, resume_id)
        return await self.repository.activate_resume(session, resume)

    async def list_versions(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
    ) -> list[ResumeVersion]:
        """List all parsed versions for a given master resume."""
        resume = await self.get_resume(session, resume_id)
        return await self.repository.list_versions_for_resume(session, resume.id)

    async def download_resume_file(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        """Read and return raw file binary, content type, and filename."""
        resume = await self.get_resume(session, resume_id)
        content_bytes = await self.storage.read(resume.storage_key)
        return content_bytes, resume.mime_type, resume.original_filename

    async def get_resume_content(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Retrieve structured parsed content from the latest version of a resume."""
        versions = await self.list_versions(session, resume_id)
        if not versions:
            return {}

        latest = versions[0]
        return latest.structured_content


_resume_service = ResumeService()


def get_resume_service() -> ResumeService:
    """FastAPI dependency for accessing the resume domain service."""
    return _resume_service
