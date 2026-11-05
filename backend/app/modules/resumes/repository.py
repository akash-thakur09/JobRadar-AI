"""Data access repository for Master Resumes and Resume Versions."""

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.resumes.models import MasterResume, ResumeVersion


class MasterResumeRepository:
    """Async repository providing persistence and query operations for resumes."""

    async def get_resume_by_checksum(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        checksum_sha256: str,
    ) -> MasterResume | None:
        """Find an existing master resume for candidate by SHA256 checksum."""
        stmt = (
            select(MasterResume)
            .where(
                MasterResume.candidate_profile_id == candidate_profile_id,
                MasterResume.checksum_sha256 == checksum_sha256,
            )
            .options(selectinload(MasterResume.versions))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_resumes(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MasterResume], int]:
        """Fetch paginated list of master resumes and total item count."""
        # Total count query
        count_stmt = (
            select(func.count())
            .select_from(MasterResume)
            .where(MasterResume.candidate_profile_id == candidate_profile_id)
        )
        total_items = (await session.execute(count_stmt)).scalar() or 0

        # Items query
        offset = (page - 1) * page_size
        items_stmt = (
            select(MasterResume)
            .where(MasterResume.candidate_profile_id == candidate_profile_id)
            .order_by(MasterResume.is_active.desc(), MasterResume.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(selectinload(MasterResume.versions))
        )
        result = await session.execute(items_stmt)
        return list(result.scalars().all()), total_items

    async def get_resume_by_id(
        self,
        session: AsyncSession,
        resume_id: uuid.UUID,
        candidate_profile_id: uuid.UUID | None = None,
    ) -> MasterResume | None:
        """Fetch master resume by UUID with version relationships."""
        stmt = (
            select(MasterResume)
            .where(MasterResume.id == resume_id)
            .options(selectinload(MasterResume.versions))
        )
        if candidate_profile_id is not None:
            stmt = stmt.where(MasterResume.candidate_profile_id == candidate_profile_id)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_resume(
        self, session: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> MasterResume | None:
        """Fetch the currently active master resume for a candidate profile."""
        stmt = (
            select(MasterResume)
            .where(
                MasterResume.candidate_profile_id == candidate_profile_id,
                MasterResume.is_active.is_(True),
            )
            .options(selectinload(MasterResume.versions))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_all_resumes(
        self, session: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> None:
        """Mark all existing resumes for a candidate as inactive."""
        stmt = (
            update(MasterResume)
            .where(MasterResume.candidate_profile_id == candidate_profile_id)
            .values(is_active=False)
        )
        await session.execute(stmt)
        await session.flush()

    async def create_resume(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        filename: str,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
        checksum_sha256: str,
        is_active: bool = True,
    ) -> MasterResume:
        """Persist a new master resume, deactivating previous active resumes if active."""
        if is_active:
            await self.deactivate_all_resumes(session, candidate_profile_id)

        resume = MasterResume(
            candidate_profile_id=candidate_profile_id,
            original_filename=filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            is_active=is_active,
        )
        session.add(resume)
        await session.flush()
        await session.refresh(resume)
        return resume

    async def activate_resume(
        self,
        session: AsyncSession,
        resume: MasterResume,
    ) -> MasterResume:
        """Set specified resume as the single active resume for the candidate profile."""
        await self.deactivate_all_resumes(session, resume.candidate_profile_id)
        resume.is_active = True
        await session.flush()
        await session.refresh(resume)
        return resume

    async def create_version(
        self,
        session: AsyncSession,
        master_resume_id: uuid.UUID,
        version_number: int,
        structured_content: dict[str, Any],
        template_metadata: dict[str, Any] | None,
        checksum_sha256: str,
        is_valid: bool = True,
        processing_status: str = "PENDING",
        parsing_error: str | None = None,
    ) -> ResumeVersion:
        """Persist a new parsed resume version."""
        version = ResumeVersion(
            master_resume_id=master_resume_id,
            version_number=version_number,
            structured_content=structured_content,
            template_metadata=template_metadata,
            checksum_sha256=checksum_sha256,
            is_valid=is_valid,
            processing_status=processing_status,
            parsing_error=parsing_error,
        )
        session.add(version)
        await session.flush()
        await session.refresh(version)
        return version

    async def get_version_by_id(
        self, session: AsyncSession, version_id: uuid.UUID
    ) -> ResumeVersion | None:
        """Fetch a specific resume version by UUID."""
        stmt = select(ResumeVersion).where(ResumeVersion.id == version_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_versions_for_resume(
        self, session: AsyncSession, master_resume_id: uuid.UUID
    ) -> list[ResumeVersion]:
        """List all versions for a master resume ordered by version number descending."""
        stmt = (
            select(ResumeVersion)
            .where(ResumeVersion.master_resume_id == master_resume_id)
            .order_by(ResumeVersion.version_number.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_version(
        self,
        session: AsyncSession,
        version: ResumeVersion,
        structured_content: dict[str, Any] | None = None,
        template_metadata: dict[str, Any] | None = None,
        is_valid: bool | None = None,
        processing_status: str | None = None,
        parsing_error: str | None = None,
    ) -> ResumeVersion:
        """Update parsed content and processing status on a version."""
        if structured_content is not None:
            version.structured_content = structured_content
        if template_metadata is not None:
            version.template_metadata = template_metadata
        if is_valid is not None:
            version.is_valid = is_valid
        if processing_status is not None:
            version.processing_status = processing_status
        if parsing_error is not None:
            version.parsing_error = parsing_error

        await session.flush()
        await session.refresh(version)
        return version
