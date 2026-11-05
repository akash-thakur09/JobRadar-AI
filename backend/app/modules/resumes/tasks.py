"""Celery background tasks for resume parsing and extraction."""

import asyncio
import logging
import uuid
from typing import Any

from app.database.session import get_session_factory
from app.infrastructure.storage.local import get_file_storage
from app.modules.resumes.models import ResumeProcessingStatus
from app.modules.resumes.parsers.registry import get_parser_for_mime_type
from app.modules.resumes.repository import MasterResumeRepository
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.modules.resumes.tasks.process_resume_task", bind=True)
def process_resume_task(self: Any, version_id_str: str) -> dict[str, Any]:
    """Background task to extract text and structure from uploaded resume binary."""
    task_id = getattr(getattr(self, "request", None), "id", "local-exec")
    logger.info("Starting resume parsing task: version_id=%s (task_id=%s)", version_id_str, task_id)
    return asyncio.run(_async_process_resume(version_id_str, str(task_id)))


async def _async_process_resume(version_id_str: str, task_id: str) -> dict[str, Any]:
    """Execute asynchronous parsing within an isolated database session."""
    version_id = uuid.UUID(version_id_str)
    session_factory = get_session_factory()
    repo = MasterResumeRepository()
    storage = get_file_storage()

    async with session_factory() as session:
        version = await repo.get_version_by_id(session, version_id)
        if version is None:
            logger.error("ResumeVersion %s not found for task %s", version_id, task_id)
            return {"status": "not_found", "version_id": str(version_id)}

        # Strict idempotency check: exit early if already completed
        if version.processing_status == ResumeProcessingStatus.COMPLETED.value:
            logger.info("ResumeVersion %s already processed; skipping task.", version_id)
            return {"status": "already_completed", "version_id": str(version_id)}

        master_resume = await repo.get_resume_by_id(session, version.master_resume_id)
        if master_resume is None:
            logger.error("Parent MasterResume not found for version %s", version_id)
            return {"status": "parent_not_found"}

        # Mark as PROCESSING
        await repo.update_version(
            session=session,
            version=version,
            processing_status=ResumeProcessingStatus.PROCESSING.value,
        )
        await session.commit()

        # Read binary from storage
        try:
            content_bytes = await storage.read(master_resume.storage_key)
        except Exception as exc:
            logger.error("Failed to read storage key %s: %s", master_resume.storage_key, exc)
            await repo.update_version(
                session=session,
                version=version,
                is_valid=False,
                processing_status=ResumeProcessingStatus.FAILED.value,
                parsing_error=f"Storage read error: {exc}",
            )
            await session.commit()
            return {"status": "storage_failed", "error": str(exc)}

        # Select parser and execute
        try:
            parser = get_parser_for_mime_type(
                master_resume.mime_type, master_resume.original_filename
            )
            result = await parser.parse(content_bytes, master_resume.original_filename)

            new_status = (
                ResumeProcessingStatus.COMPLETED.value
                if result.is_valid
                else ResumeProcessingStatus.FAILED.value
            )
            error_msg = "; ".join(result.extraction_warnings) if not result.is_valid else None

            await repo.update_version(
                session=session,
                version=version,
                structured_content=result.structured_content,
                template_metadata=result.template_metadata,
                is_valid=result.is_valid,
                processing_status=new_status,
                parsing_error=error_msg,
            )
            await session.commit()

            logger.info(
                "Successfully parsed resume version %s (status=%s, sections=%s)",
                version_id,
                new_status,
                list(result.structured_content.keys()),
            )
            return {
                "status": new_status,
                "version_id": str(version_id),
                "is_valid": result.is_valid,
                "warnings": result.extraction_warnings,
            }
        except Exception as exc:
            logger.exception("Unexpected exception during resume parsing: %s", exc)
            await repo.update_version(
                session=session,
                version=version,
                is_valid=False,
                processing_status=ResumeProcessingStatus.FAILED.value,
                parsing_error=f"Parser execution error: {exc}",
            )
            await session.commit()
            return {"status": "failed", "error": str(exc)}
