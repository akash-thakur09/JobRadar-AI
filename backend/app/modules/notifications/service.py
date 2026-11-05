"""Domain service orchestrating immediate email notification and reliable delivery."""

import hashlib
import inspect
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.storage.base import FileStorage
from app.infrastructure.storage.local import get_file_storage
from app.modules.candidate.models import CandidateProfile, User
from app.modules.jobs.models import JobStatusEnum
from app.modules.notifications.email.factory import get_email_provider
from app.modules.notifications.email.protocol import EmailProvider
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.exceptions import (
    AttachmentUnavailableError,
    DeliveryMaxRetriesExceededError,
    DeliveryNotFoundError,
    InvalidStateTransitionError,
    NotificationDeliveryFailureError,
    NotificationError,
)
from app.modules.notifications.models import NotificationDelivery
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import (
    NotificationDeliveryListResponse,
    NotificationDeliverySummary,
)
from app.modules.notifications.templates import build_job_notification_email
from app.modules.resumes.schemas import PaginationMetadata
from app.modules.tailoring.enums import TailoredResumeStatusEnum
from app.modules.tailoring.models import TailoredResume
from app.modules.tailoring.repository import TailoringRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Orchestrates notification creation, idempotency enforcement, PDF retrieval, and email dispatch."""

    def __init__(
        self,
        repository: NotificationRepository | None = None,
        tailoring_repository: TailoringRepository | None = None,
        storage: FileStorage | None = None,
        email_provider: EmailProvider | None = None,
    ) -> None:
        self.repository = repository or NotificationRepository()
        self.tailoring_repository = tailoring_repository or TailoringRepository()
        self.storage = storage or get_file_storage()
        self._email_provider = email_provider

    @property
    def email_provider(self) -> EmailProvider:
        """Resolve active email provider."""
        if self._email_provider is not None:
            return self._email_provider
        return get_email_provider()

    async def create_or_get_delivery_for_tailored_resume(
        self,
        session: AsyncSession,
        tailored_resume_id: uuid.UUID,
        recipient_email_override: str | None = None,
    ) -> NotificationDelivery:
        """Create or return existing NotificationDelivery record for a completed tailored resume.

        Enforces database-level idempotency: prevents creating duplicate deliveries
        for the same candidate and job.
        """
        # 1. Fetch tailored resume with relations
        tailored_resume = await self.tailoring_repository.get_by_id(
            session=session,
            tailored_resume_id=tailored_resume_id,
            load_relations=True,
        )
        if tailored_resume is None:
            raise AttachmentUnavailableError(
                tailored_resume_id=tailored_resume_id,
                reason="Tailored resume record does not exist",
            )

        if tailored_resume.generation_status != TailoredResumeStatusEnum.COMPLETED:
            raise AttachmentUnavailableError(
                tailored_resume_id=tailored_resume_id,
                reason=f"Status is '{tailored_resume.generation_status.value}', expected 'COMPLETED'",
            )

        # 2. Resolve recipient email directly (checking in-memory dict first without triggering lazy-load, then SQL)
        if recipient_email_override:
            clean_recipient = recipient_email_override.lower().strip()
        else:
            cand_profile = getattr(tailored_resume, "candidate_profile", None)
            user_in_dict = (
                getattr(cand_profile, "__dict__", {}).get("user") if cand_profile else None
            )
            user_email = getattr(user_in_dict, "email", None) if user_in_dict else None

            if user_email and "@" in str(user_email):
                clean_recipient = str(user_email).lower().strip()
            else:
                stmt = (
                    select(User.email)
                    .join(CandidateProfile, CandidateProfile.user_id == User.id)
                    .where(CandidateProfile.id == tailored_resume.candidate_profile_id)
                )
                email_result = await session.execute(stmt)
                res = email_result.scalar_one_or_none()
                recipient = (await res) if inspect.isawaitable(res) else res

                if not recipient or "@" not in str(recipient):
                    raise NotificationError(
                        f"Candidate profile {tailored_resume.candidate_profile_id} lacks a valid recipient email address."
                    )
                clean_recipient = str(recipient).lower().strip()

        # 3. Check for existing delivery (Idempotency check)
        existing = await self.repository.get_by_job_and_recipient(
            session=session,
            job_id=tailored_resume.job_id,
            recipient_email=clean_recipient,
            load_relations=True,
        )
        if existing is not None:
            logger.info(
                f"NotificationDelivery already exists for job {tailored_resume.job_id} "
                f"and recipient {clean_recipient} (status: {existing.status.value}, ID: {existing.id})"
            )
            return existing

        # 4. Create new pending delivery record
        settings = get_settings()
        delivery = NotificationDelivery(
            candidate_profile_id=tailored_resume.candidate_profile_id,
            job_id=tailored_resume.job_id,
            job_match_id=tailored_resume.job_match_id,
            tailored_resume_id=tailored_resume.id,
            recipient_email=clean_recipient,
            status=NotificationDeliveryStatusEnum.PENDING,
            attempt_count=0,
            max_attempts=settings.email_max_retries,
            provider=settings.email_provider.lower(),
        )
        saved = await self.repository.save(session, delivery)
        logger.info(
            f"Created NotificationDelivery record {saved.id} for job {saved.job_id} and recipient {clean_recipient}"
        )
        return saved

    async def execute_delivery_pipeline(
        self,
        session: AsyncSession,
        delivery_id: uuid.UUID,
    ) -> NotificationDelivery:
        """Drive state machine and deliver email with tailored resume PDF attachment."""
        # 1. Fetch delivery record with all relations loaded
        delivery = await self.repository.get_by_id(
            session=session,
            delivery_id=delivery_id,
            load_relations=True,
        )
        if delivery is None:
            raise DeliveryNotFoundError(delivery_id)

        # 2. Strict terminal state guard: SENT is never resent
        if delivery.status == NotificationDeliveryStatusEnum.SENT:
            logger.info(
                f"NotificationDelivery {delivery_id} is already in SENT status; terminating idempotently."
            )
            return delivery

        # 3. Guard retry limits
        if delivery.attempt_count >= delivery.max_attempts:
            raise DeliveryMaxRetriesExceededError(
                delivery_id=delivery_id,
                attempt_count=delivery.attempt_count,
                max_attempts=delivery.max_attempts,
            )

        # 4. Validate tailored resume attachment state
        tailored_resume: TailoredResume | None = delivery.tailored_resume
        if (
            tailored_resume is None
            or tailored_resume.generation_status != TailoredResumeStatusEnum.COMPLETED
            or not tailored_resume.storage_key
        ):
            err_msg = "Tailored resume artifact is missing or has not completed generation"
            delivery.status = NotificationDeliveryStatusEnum.FAILED
            delivery.failed_at = datetime.now(UTC)
            delivery.last_error = err_msg
            await self.repository.save(session, delivery)
            raise AttachmentUnavailableError(
                tailored_resume_id=delivery.tailored_resume_id,
                reason=err_msg,
            )

        # 5. Retrieve PDF bytes from storage safely
        try:
            pdf_bytes = await self.storage.read(tailored_resume.storage_key)
        except Exception as store_err:
            err_msg = f"Failed to retrieve PDF artifact from storage key '{tailored_resume.storage_key}': {store_err}"
            logger.error(err_msg)
            delivery.status = NotificationDeliveryStatusEnum.FAILED
            delivery.failed_at = datetime.now(UTC)
            delivery.last_error = err_msg
            await self.repository.save(session, delivery)
            raise AttachmentUnavailableError(
                tailored_resume_id=tailored_resume.id,
                reason=err_msg,
            ) from store_err

        # 6. Validate PDF binary structure & checksum
        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
            err_msg = "Retrieved PDF artifact failed magic bytes validation (missing '%PDF-')"
            delivery.status = NotificationDeliveryStatusEnum.FAILED
            delivery.failed_at = datetime.now(UTC)
            delivery.last_error = err_msg
            await self.repository.save(session, delivery)
            raise AttachmentUnavailableError(
                tailored_resume_id=tailored_resume.id,
                reason=err_msg,
            )

        if tailored_resume.checksum_sha256:
            calc_checksum = hashlib.sha256(pdf_bytes).hexdigest()
            if calc_checksum != tailored_resume.checksum_sha256:
                err_msg = (
                    f"PDF artifact checksum mismatch: expected {tailored_resume.checksum_sha256}, "
                    f"got {calc_checksum}"
                )
                logger.error(err_msg)
                delivery.status = NotificationDeliveryStatusEnum.FAILED
                delivery.failed_at = datetime.now(UTC)
                delivery.last_error = err_msg
                await self.repository.save(session, delivery)
                raise AttachmentUnavailableError(
                    tailored_resume_id=tailored_resume.id,
                    reason=err_msg,
                )

        # 7. Transition state to PROCESSING and increment attempt count
        delivery.status = NotificationDeliveryStatusEnum.PROCESSING
        delivery.attempt_count += 1
        await self.repository.save(session, delivery)

        # 8. Build EmailMessage
        email_message = build_job_notification_email(
            candidate_profile=delivery.candidate_profile,
            job=delivery.job,
            job_match=delivery.job_match,
            tailored_resume=tailored_resume,
            pdf_bytes=pdf_bytes,
            recipient_email=delivery.recipient_email,
        )

        # 9. Dispatch via configured email provider
        try:
            result = await self.email_provider.send_email(email_message)

            if result.success:
                delivery.status = NotificationDeliveryStatusEnum.SENT
                delivery.sent_at = datetime.now(UTC)
                delivery.provider_message_id = result.provider_message_id
                delivery.last_error = None

                # Update job status to NOTIFIED
                if delivery.job.status != JobStatusEnum.NOTIFIED:
                    delivery.job.status = JobStatusEnum.NOTIFIED

                saved = await self.repository.save(session, delivery)
                logger.info(
                    f"NotificationDelivery {delivery_id} successfully sent to {delivery.recipient_email} "
                    f"(Message-ID: {result.provider_message_id})"
                )
                return saved
            else:
                delivery.status = NotificationDeliveryStatusEnum.FAILED
                delivery.failed_at = datetime.now(UTC)
                delivery.last_error = result.error or "Provider indicated delivery failure"
                saved = await self.repository.save(session, delivery)
                raise NotificationDeliveryFailureError(
                    delivery_id=delivery_id,
                    reason=delivery.last_error,
                )

        except Exception as exc:
            # Capture error state
            delivery.status = NotificationDeliveryStatusEnum.FAILED
            delivery.failed_at = datetime.now(UTC)
            delivery.last_error = str(exc)
            await self.repository.save(session, delivery)
            logger.warning(
                f"NotificationDelivery {delivery_id} dispatch attempt {delivery.attempt_count} failed: {exc}"
            )
            raise

    async def retry_delivery(
        self,
        session: AsyncSession,
        delivery_id: uuid.UUID,
        force: bool = False,
    ) -> NotificationDelivery:
        """Reset a failed notification delivery to PENDING for re-dispatch."""
        delivery = await self.repository.get_by_id(
            session=session,
            delivery_id=delivery_id,
            load_relations=True,
        )
        if delivery is None:
            raise DeliveryNotFoundError(delivery_id)

        if delivery.status == NotificationDeliveryStatusEnum.SENT:
            raise InvalidStateTransitionError(
                current_status=delivery.status.value,
                target_status=NotificationDeliveryStatusEnum.PENDING.value,
                reason="Cannot retry an already delivered notification.",
            )

        if delivery.status == NotificationDeliveryStatusEnum.PROCESSING:
            raise InvalidStateTransitionError(
                current_status=delivery.status.value,
                target_status=NotificationDeliveryStatusEnum.PENDING.value,
                reason="Notification is currently actively being processed by a worker.",
            )

        if delivery.attempt_count >= delivery.max_attempts and not force:
            raise DeliveryMaxRetriesExceededError(
                delivery_id=delivery_id,
                attempt_count=delivery.attempt_count,
                max_attempts=delivery.max_attempts,
            )

        delivery.status = NotificationDeliveryStatusEnum.PENDING
        delivery.last_error = None
        saved = await self.repository.save(session, delivery)
        logger.info(f"NotificationDelivery {delivery_id} reset to PENDING for retry.")
        return saved

    async def get_delivery(
        self,
        session: AsyncSession,
        delivery_id: uuid.UUID,
    ) -> NotificationDelivery:
        """Fetch notification delivery by ID with related entity attributes."""
        delivery = await self.repository.get_by_id(
            session=session,
            delivery_id=delivery_id,
            load_relations=True,
        )
        if delivery is None:
            raise DeliveryNotFoundError(delivery_id)
        return delivery

    async def list_deliveries(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID | None = None,
        status: NotificationDeliveryStatusEnum | None = None,
        job_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> NotificationDeliveryListResponse:
        """Retrieve paginated delivery records matching filter criteria."""
        items, total_items = await self.repository.list_deliveries(
            session=session,
            candidate_profile_id=candidate_profile_id,
            status=status,
            job_id=job_id,
            page=page,
            page_size=page_size,
        )

        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        pagination = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

        summaries = [NotificationDeliverySummary.model_validate(item) for item in items]
        return NotificationDeliveryListResponse(items=summaries, pagination=pagination)


_notification_service_instance: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Return shared NotificationService singleton."""
    global _notification_service_instance
    if _notification_service_instance is None:
        _notification_service_instance = NotificationService()
    return _notification_service_instance
