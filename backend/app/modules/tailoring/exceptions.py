"""Domain exceptions for the Tailoring domain."""

from typing import Any

from app.core.exceptions import AppException, DomainException


class TailoringError(DomainException):
    """Base exception for tailoring pipeline failures."""

    def __init__(
        self, message: str, status_code: int = 400, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_type="tailoring-error",
            invalid_params=[details] if details else None,
        )


class ClaimValidationError(DomainException):
    """Raised when the LLM generates unsupported factual claims that cannot be reconciled."""

    def __init__(self, message: str, unsupported_claims: list[str] | None = None) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_type="unsupported-claim-error",
            invalid_params=[{"unsupported_claims": unsupported_claims or []}],
        )
        self.unsupported_claims = unsupported_claims or []


class RenderingError(AppException):
    """Raised when PDF compilation or binary integrity verification fails."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_type="pdf-rendering-error",
        )


class EvidenceNotFoundError(DomainException):
    """Raised when required candidate evidence (active resume, profile) is missing."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_type="missing-evidence-error",
        )


class InvalidStateTransitionError(DomainException):
    """Raised when an illegal lifecycle transition is attempted on a TailoredResume."""

    def __init__(self, from_state: str, to_state: str) -> None:
        super().__init__(
            message=f"Illegal state transition from '{from_state}' to '{to_state}'.",
            status_code=409,
            error_type="invalid-state-transition",
        )
