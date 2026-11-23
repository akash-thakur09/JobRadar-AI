"""Domain exceptions for notification delivery operations."""

from typing import Any

from app.core.exceptions import DomainException


class NotificationError(DomainException):
    """Base exception for all notification domain errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_type: str = "notification-error",
        invalid_params: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_type=error_type,
            invalid_params=invalid_params,
        )


class DeliveryNotFoundError(NotificationError):
    """Raised when a requested NotificationDelivery record does not exist."""

    def __init__(self, delivery_id: Any) -> None:
        super().__init__(
            message=f"NotificationDelivery with identifier '{delivery_id}' was not found.",
            status_code=404,
            error_type="notification-not-found",
        )


class InvalidStateTransitionError(NotificationError):
    """Raised when an illegal status transition is attempted on a delivery record."""

    def __init__(self, current_status: str, target_status: str, reason: str = "") -> None:
        msg = (
            f"Cannot transition notification delivery from '{current_status}' to '{target_status}'."
        )
        if reason:
            msg += f" {reason}"
        super().__init__(
            message=msg,
            status_code=409,
            error_type="invalid-notification-state-transition",
        )


class DeliveryMaxRetriesExceededError(NotificationError):
    """Raised when a delivery has exceeded its maximum configured retry attempts."""

    def __init__(self, delivery_id: Any, attempt_count: int, max_attempts: int) -> None:
        super().__init__(
            message=(
                f"NotificationDelivery '{delivery_id}' has reached maximum retry attempts "
                f"({attempt_count}/{max_attempts}) and cannot be retried further."
            ),
            status_code=400,
            error_type="notification-retries-exceeded",
        )


class AttachmentUnavailableError(NotificationError):
    """Raised when the tailored resume PDF attachment is missing, corrupt, or incomplete."""

    def __init__(self, tailored_resume_id: Any, reason: str) -> None:
        super().__init__(
            message=(
                f"Tailored resume artifact '{tailored_resume_id}' is unavailable for email attachment: {reason}."
            ),
            status_code=400,
            error_type="notification-attachment-unavailable",
        )


class NotificationDeliveryFailureError(NotificationError):
    """Raised when provider delivery fails definitively."""

    def __init__(self, delivery_id: Any, reason: str) -> None:
        super().__init__(
            message=f"Email delivery for notification '{delivery_id}' failed: {reason}",
            status_code=500,
            error_type="notification-delivery-failed",
        )
