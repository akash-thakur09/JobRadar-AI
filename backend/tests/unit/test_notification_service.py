"""Unit tests for NotificationService orchestration, idempotency, and error handling."""

import hashlib
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.candidate.models import CandidateProfile, User
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.notifications.email.exceptions import EmailTimeoutError
from app.modules.notifications.email.mock_provider import MockEmailProvider
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.exceptions import (
    AttachmentUnavailableError,
    DeliveryMaxRetriesExceededError,
    InvalidStateTransitionError,
)
from app.modules.notifications.models import NotificationDelivery
from app.modules.notifications.service import NotificationService
from app.modules.tailoring.enums import TailoredResumeStatusEnum
from app.modules.tailoring.models import TailoredResume


@pytest.fixture
def mock_storage():
    """Mock FileStorage fixture."""
    storage = MagicMock()
    storage.read = AsyncMock(return_value=b"%PDF-1.4 valid test pdf binary")
    return storage


@pytest.fixture
def sample_delivery_setup() -> tuple[
    CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
]:
    """Fixture returning interconnected domain models."""
    user = User(id=uuid.uuid4(), email="candidate@example.com")
    profile = CandidateProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        full_name="Sarah Connor",
        headline="Senior Systems Engineer",
    )
    profile.user = user

    job = Job(
        id=uuid.uuid4(),
        canonical_company_name="Cyberdyne Systems",
        title="AI Engineer",
        status=JobStatusEnum.TAILORED,
        canonical_application_url="https://cyberdyne.com/jobs/1",
        description_text="Building advanced AI platforms.",
    )

    job_match = JobMatch(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_profile_id=profile.id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        final_score=Decimal("92.00"),
        match_explanation="Exceptional qualification alignment.",
    )

    pdf_content = b"%PDF-1.4 valid test pdf binary"
    checksum = hashlib.sha256(pdf_content).hexdigest()

    tailored_resume = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=profile.id,
        job_id=job.id,
        job_match_id=job_match.id,
        resume_version_id=uuid.uuid4(),
        generation_status=TailoredResumeStatusEnum.COMPLETED,
        storage_key="resumes/tailored/test.pdf",
        file_name="Sarah_Connor_Resume.pdf",
        checksum_sha256=checksum,
    )
    tailored_resume.candidate_profile = profile
    tailored_resume.job = job
    tailored_resume.job_match = job_match

    delivery = NotificationDelivery(
        id=uuid.uuid4(),
        candidate_profile_id=profile.id,
        job_id=job.id,
        job_match_id=job_match.id,
        tailored_resume_id=tailored_resume.id,
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.PENDING,
        attempt_count=0,
        max_attempts=3,
        provider="mock",
    )
    delivery.candidate_profile = profile
    delivery.job = job
    delivery.job_match = job_match
    delivery.tailored_resume = tailored_resume

    return profile, job, job_match, tailored_resume, delivery


@pytest.mark.unit
async def test_create_or_get_delivery_success(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
    mock_storage,
):
    """create_or_get_delivery creates pending notification delivery for completed tailored resume."""
    profile, job, job_match, tailored_resume, _ = sample_delivery_setup

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_job_and_recipient = AsyncMock(return_value=None)
    mock_notif_repo.save = AsyncMock(side_effect=lambda _s, d: d)

    mock_tailor_repo = MagicMock()
    mock_tailor_repo.get_by_id = AsyncMock(return_value=tailored_resume)

    service = NotificationService(
        repository=mock_notif_repo,
        tailoring_repository=mock_tailor_repo,
        storage=mock_storage,
        email_provider=MockEmailProvider(),
    )

    mock_session = AsyncMock()
    delivery = await service.create_or_get_delivery_for_tailored_resume(
        session=mock_session,
        tailored_resume_id=tailored_resume.id,
    )

    assert delivery.status == NotificationDeliveryStatusEnum.PENDING
    assert delivery.job_id == job.id
    assert delivery.recipient_email == "candidate@example.com"
    mock_notif_repo.save.assert_called_once()


@pytest.mark.unit
async def test_create_or_get_delivery_idempotency_returns_existing(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
    mock_storage,
):
    """create_or_get_delivery returns existing record without creating duplicate rows."""
    profile, job, job_match, tailored_resume, existing_delivery = sample_delivery_setup

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_job_and_recipient = AsyncMock(return_value=existing_delivery)
    mock_notif_repo.save = AsyncMock()

    mock_tailor_repo = MagicMock()
    mock_tailor_repo.get_by_id = AsyncMock(return_value=tailored_resume)

    service = NotificationService(
        repository=mock_notif_repo,
        tailoring_repository=mock_tailor_repo,
        storage=mock_storage,
        email_provider=MockEmailProvider(),
    )

    mock_session = AsyncMock()
    delivery = await service.create_or_get_delivery_for_tailored_resume(
        session=mock_session,
        tailored_resume_id=tailored_resume.id,
    )

    assert delivery.id == existing_delivery.id
    mock_notif_repo.save.assert_not_called()


@pytest.mark.unit
async def test_create_or_get_delivery_rejects_incomplete_tailoring(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
    mock_storage,
):
    """create_or_get_delivery raises AttachmentUnavailableError if tailoring is not COMPLETED."""
    profile, job, job_match, tailored_resume, _ = sample_delivery_setup
    tailored_resume.generation_status = TailoredResumeStatusEnum.PROCESSING

    mock_tailor_repo = MagicMock()
    mock_tailor_repo.get_by_id = AsyncMock(return_value=tailored_resume)

    service = NotificationService(
        tailoring_repository=mock_tailor_repo,
        storage=mock_storage,
        email_provider=MockEmailProvider(),
    )

    mock_session = AsyncMock()
    with pytest.raises(AttachmentUnavailableError, match="expected 'COMPLETED'"):
        await service.create_or_get_delivery_for_tailored_resume(
            session=mock_session,
            tailored_resume_id=tailored_resume.id,
        )


@pytest.mark.unit
async def test_execute_delivery_pipeline_success(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
    mock_storage,
):
    """execute_delivery_pipeline retrieves PDF, verifies binary, sends email, and updates job to NOTIFIED."""
    profile, job, job_match, tailored_resume, delivery = sample_delivery_setup

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_id = AsyncMock(return_value=delivery)
    mock_notif_repo.save = AsyncMock(side_effect=lambda _s, d: d)

    mock_provider = MockEmailProvider()

    service = NotificationService(
        repository=mock_notif_repo,
        storage=mock_storage,
        email_provider=mock_provider,
    )

    mock_session = AsyncMock()
    result = await service.execute_delivery_pipeline(
        session=mock_session,
        delivery_id=delivery.id,
    )

    assert result.status == NotificationDeliveryStatusEnum.SENT
    assert result.sent_at is not None
    assert result.provider_message_id is not None
    assert result.attempt_count == 1
    assert job.status == JobStatusEnum.NOTIFIED
    assert mock_provider.sent_count == 1


@pytest.mark.unit
async def test_execute_delivery_pipeline_already_sent_idempotency(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
    mock_storage,
):
    """execute_delivery_pipeline terminates idempotently if status is already SENT."""
    profile, job, job_match, tailored_resume, delivery = sample_delivery_setup
    delivery.status = NotificationDeliveryStatusEnum.SENT
    delivery.provider_message_id = "<existing-msg-id@jobradar.ai>"

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_id = AsyncMock(return_value=delivery)
    mock_notif_repo.save = AsyncMock()

    mock_provider = MockEmailProvider()

    service = NotificationService(
        repository=mock_notif_repo,
        storage=mock_storage,
        email_provider=mock_provider,
    )

    mock_session = AsyncMock()
    result = await service.execute_delivery_pipeline(
        session=mock_session,
        delivery_id=delivery.id,
    )

    assert result.status == NotificationDeliveryStatusEnum.SENT
    assert mock_provider.sent_count == 0
    mock_notif_repo.save.assert_not_called()


@pytest.mark.unit
async def test_execute_delivery_pipeline_corrupt_pdf_fails(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
):
    """execute_delivery_pipeline marks delivery FAILED if storage returns non-PDF bytes."""
    profile, job, job_match, tailored_resume, delivery = sample_delivery_setup

    mock_storage = MagicMock()
    mock_storage.read = AsyncMock(return_value=b"NOT_A_VALID_PDF_HEADER")

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_id = AsyncMock(return_value=delivery)
    mock_notif_repo.save = AsyncMock(side_effect=lambda _s, d: d)

    service = NotificationService(
        repository=mock_notif_repo,
        storage=mock_storage,
        email_provider=MockEmailProvider(),
    )

    mock_session = AsyncMock()
    with pytest.raises(AttachmentUnavailableError, match="magic bytes validation"):
        await service.execute_delivery_pipeline(
            session=mock_session,
            delivery_id=delivery.id,
        )

    assert delivery.status == NotificationDeliveryStatusEnum.FAILED
    assert "magic bytes" in (delivery.last_error or "")


@pytest.mark.unit
async def test_execute_delivery_pipeline_checksum_mismatch_fails(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
    mock_storage,
):
    """execute_delivery_pipeline marks delivery FAILED if calculated SHA-256 does not match DB checksum."""
    profile, job, job_match, tailored_resume, delivery = sample_delivery_setup
    tailored_resume.checksum_sha256 = "expected_different_sha256_hash_value"

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_id = AsyncMock(return_value=delivery)
    mock_notif_repo.save = AsyncMock(side_effect=lambda _s, d: d)

    service = NotificationService(
        repository=mock_notif_repo,
        storage=mock_storage,
        email_provider=MockEmailProvider(),
    )

    mock_session = AsyncMock()
    with pytest.raises(AttachmentUnavailableError, match="checksum mismatch"):
        await service.execute_delivery_pipeline(
            session=mock_session,
            delivery_id=delivery.id,
        )

    assert delivery.status == NotificationDeliveryStatusEnum.FAILED
    assert "checksum mismatch" in (delivery.last_error or "")


@pytest.mark.unit
async def test_execute_delivery_pipeline_transient_failure_re_raises(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
    mock_storage,
):
    """execute_delivery_pipeline records FAILED state and re-raises retryable exceptions."""
    profile, job, job_match, tailored_resume, delivery = sample_delivery_setup

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_id = AsyncMock(return_value=delivery)
    mock_notif_repo.save = AsyncMock(side_effect=lambda _s, d: d)

    timeout_provider = MockEmailProvider(simulate_timeout=True)

    service = NotificationService(
        repository=mock_notif_repo,
        storage=mock_storage,
        email_provider=timeout_provider,
    )

    mock_session = AsyncMock()
    with pytest.raises(EmailTimeoutError):
        await service.execute_delivery_pipeline(
            session=mock_session,
            delivery_id=delivery.id,
        )

    assert delivery.status == NotificationDeliveryStatusEnum.FAILED
    assert delivery.attempt_count == 1
    assert "timeout" in (delivery.last_error or "")


@pytest.mark.unit
async def test_retry_delivery_lifecycle(
    sample_delivery_setup: tuple[
        CandidateProfile, Job, JobMatch, TailoredResume, NotificationDelivery
    ],
):
    """retry_delivery resets FAILED delivery to PENDING, respecting state guards and limits."""
    profile, job, job_match, tailored_resume, delivery = sample_delivery_setup

    mock_notif_repo = MagicMock()
    mock_notif_repo.get_by_id = AsyncMock(return_value=delivery)
    mock_notif_repo.save = AsyncMock(side_effect=lambda _s, d: d)

    service = NotificationService(repository=mock_notif_repo)
    mock_session = AsyncMock()

    # 1. Reject retry if already SENT
    delivery.status = NotificationDeliveryStatusEnum.SENT
    with pytest.raises(InvalidStateTransitionError, match="Cannot retry an already delivered"):
        await service.retry_delivery(mock_session, delivery.id)

    # 2. Reject retry if PROCESSING
    delivery.status = NotificationDeliveryStatusEnum.PROCESSING
    with pytest.raises(InvalidStateTransitionError, match="currently actively being processed"):
        await service.retry_delivery(mock_session, delivery.id)

    # 3. Reject if attempts >= max_attempts without force
    delivery.status = NotificationDeliveryStatusEnum.FAILED
    delivery.attempt_count = 3
    delivery.max_attempts = 3
    with pytest.raises(DeliveryMaxRetriesExceededError):
        await service.retry_delivery(mock_session, delivery.id, force=False)

    # 4. Successful retry when attempt_count < max_attempts
    delivery.attempt_count = 1
    retried = await service.retry_delivery(mock_session, delivery.id, force=False)
    assert retried.status == NotificationDeliveryStatusEnum.PENDING
    assert retried.last_error is None
