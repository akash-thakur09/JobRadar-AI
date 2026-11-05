"""Core domain and infrastructure exception hierarchy."""

from typing import Any


class AppException(Exception):
    """Base application exception for all domain and infrastructure errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: str = "internal-error",
        invalid_params: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.invalid_params = invalid_params or []


class DomainException(AppException):
    """Base exception for business logic and domain rule violations."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_type: str = "domain-error",
        invalid_params: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_type=error_type,
            invalid_params=invalid_params,
        )


class EntityNotFoundError(DomainException):
    """Raised when a requested resource does not exist."""

    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            status_code=404,
            error_type="not-found",
        )


class EntityAlreadyExistsError(DomainException):
    """Raised when creating a resource violates a unique constraint."""

    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' already exists.",
            status_code=409,
            error_type="conflict",
        )


class InfrastructureException(AppException):
    """Base exception for infrastructure and third-party failures."""

    def __init__(
        self,
        message: str,
        status_code: int = 503,
        error_type: str = "infrastructure-unavailable",
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_type=error_type,
        )


class DatabaseUnavailableError(InfrastructureException):
    """Raised when PostgreSQL connection or query fails."""

    def __init__(self, message: str = "Database service is unreachable or unhealthy.") -> None:
        super().__init__(message=message, status_code=503, error_type="database-unavailable")


class RedisUnavailableError(InfrastructureException):
    """Raised when Redis connection or ping fails."""

    def __init__(self, message: str = "Redis service is unreachable or unhealthy.") -> None:
        super().__init__(message=message, status_code=503, error_type="redis-unavailable")
