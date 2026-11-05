"""Base interface and DTO contracts for Job Discovery Source Adapters."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.modules.discovery.models import JobSourceTypeEnum


class RawDiscoveredJob(BaseModel):
    """Raw unnormalized job artifact extracted verbatim from an upstream ATS."""

    model_config = ConfigDict(extra="ignore")

    external_id: str = Field(description="Upstream ATS job identifier")
    source_url: str = Field(description="Direct URL to the job listing")
    raw_payload: dict[str, Any] = Field(description="Complete raw JSON payload from source")
    raw_posted_at: str | None = Field(
        default=None, description="Original unparsed date string from source"
    )
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DiscoveryResult(BaseModel):
    """Aggregate result bundle produced by an adapter discovery run."""

    model_config = ConfigDict(extra="ignore")

    source_identifier: str = Field(description="Board token, company ID, or unique source identity")
    source_type: JobSourceTypeEnum = Field(description="Platform type identifier")
    jobs: list[RawDiscoveredJob] = Field(default_factory=list, description="Extracted raw jobs")
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic HTTP headers or timing"
    )
    warnings: list[str] = Field(default_factory=list, description="Non-fatal notices or anomalies")


class JobSourceAdapter(ABC):
    """Abstract contract for platform-specific job discovery adapters."""

    @property
    @abstractmethod
    def source_type(self) -> JobSourceTypeEnum:
        """The platform type handled by this adapter."""
        ...

    @abstractmethod
    def validate_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate source-specific parameters.

        Raises:
            InvalidSourceConfigError: If required keys are missing or malformed.
        """
        ...

    @abstractmethod
    async def discover_jobs(
        self,
        base_url: str,
        configuration: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> DiscoveryResult:
        """Execute discovery against external public job board.

        Returns:
            DiscoveryResult containing raw discovered jobs.

        Raises:
            RateLimitExceededError: On HTTP 429.
            UpstreamServerError: On HTTP 5xx.
            NetworkTimeoutError: On request timeout.
            SourceNotFoundError: On HTTP 404.
            MalformedPayloadError: On invalid response structure.
        """
        ...
