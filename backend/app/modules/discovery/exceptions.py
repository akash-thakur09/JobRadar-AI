"""Domain exception hierarchy for job discovery and adapter execution."""

from typing import Any

from app.core.exceptions import AppException, DomainException


class DiscoveryError(AppException):
    """Base exception for all job discovery pipeline errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 502,
        error_type: str = "discovery-error",
        invalid_params: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_type=error_type,
            invalid_params=invalid_params,
        )


class RetryableDiscoveryError(DiscoveryError):
    """Base exception for transient, retryable external discovery failures."""

    def __init__(
        self,
        message: str,
        status_code: int = 503,
        error_type: str = "transient-discovery-error",
    ) -> None:
        super().__init__(message=message, status_code=status_code, error_type=error_type)


class RateLimitExceededError(RetryableDiscoveryError):
    """Raised when an external ATS responds with HTTP 429 Too Many Requests."""

    def __init__(self, source_name: str, retry_after: int | None = None) -> None:
        msg = f"Rate limit exceeded while querying job source '{source_name}'."
        if retry_after:
            msg += f" Retry after {retry_after}s."
        super().__init__(message=msg, status_code=429, error_type="rate-limit-exceeded")
        self.retry_after = retry_after


class UpstreamServerError(RetryableDiscoveryError):
    """Raised when an external ATS responds with HTTP 5xx Server Error."""

    def __init__(self, source_name: str, status_code: int = 502) -> None:
        super().__init__(
            message=f"Upstream ATS service error from '{source_name}' (HTTP {status_code}).",
            status_code=502,
            error_type="upstream-service-error",
        )


class NetworkTimeoutError(RetryableDiscoveryError):
    """Raised when an HTTP connection or read times out against an external ATS."""

    def __init__(self, source_name: str, timeout_seconds: float) -> None:
        super().__init__(
            message=f"Network timeout ({timeout_seconds}s) connecting to job source '{source_name}'.",
            status_code=504,
            error_type="network-timeout",
        )


class NonRetryableDiscoveryError(DiscoveryError):
    """Base exception for permanent configuration or payload errors that must not be retried."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_type: str = "permanent-discovery-error",
    ) -> None:
        super().__init__(message=message, status_code=status_code, error_type=error_type)


class InvalidSourceConfigError(NonRetryableDiscoveryError, DomainException):
    """Raised when a job source has missing or invalid configuration parameters."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message, status_code=422, error_type="invalid-source-configuration"
        )


class SourceNotFoundError(NonRetryableDiscoveryError):
    """Raised when an upstream ATS returns HTTP 404 (e.g. unknown board token)."""

    def __init__(self, source_name: str, board_id: str) -> None:
        super().__init__(
            message=f"Job board or company '{board_id}' not found on upstream provider for source '{source_name}'.",
            status_code=404,
            error_type="upstream-board-not-found",
        )


class MalformedPayloadError(NonRetryableDiscoveryError):
    """Raised when upstream JSON response is unparseable or violates expected contract."""

    def __init__(self, source_name: str, detail: str) -> None:
        super().__init__(
            message=f"Malformed response payload received from '{source_name}': {detail}",
            status_code=502,
            error_type="malformed-upstream-payload",
        )


class UnsupportedSourceTypeError(NonRetryableDiscoveryError):
    """Raised when an adapter for a source type is not registered or supported."""

    def __init__(self, source_type: str) -> None:
        super().__init__(
            message=f"Job source type '{source_type}' is not supported.",
            status_code=400,
            error_type="unsupported-source-type",
        )
