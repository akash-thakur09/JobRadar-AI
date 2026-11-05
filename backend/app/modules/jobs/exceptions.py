"""Exceptions for canonical jobs and normalization domain."""

import uuid

from app.core.exceptions import DomainException, EntityNotFoundError


class JobNotFoundError(EntityNotFoundError):
    """Raised when a canonical job cannot be located by ID."""

    def __init__(self, job_id: uuid.UUID | str) -> None:
        super().__init__(entity_name="Job", identifier=str(job_id))


class JobSourceRecordNotFoundError(EntityNotFoundError):
    """Raised when a job source record cannot be located by ID."""

    def __init__(self, record_id: uuid.UUID | str) -> None:
        super().__init__(entity_name="JobSourceRecord", identifier=str(record_id))


class JobProcessingError(DomainException):
    """Raised when an unrecoverable failure occurs during job normalization or canonicalization."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=422,
            error_type="job-processing-error",
        )
