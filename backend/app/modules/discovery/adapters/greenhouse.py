"""Greenhouse public job board discovery adapter."""

import re
import time
from typing import Any

import httpx

from app.infrastructure.http_client import create_http_client
from app.modules.discovery.adapters.base import DiscoveryResult, JobSourceAdapter, RawDiscoveredJob
from app.modules.discovery.exceptions import (
    DiscoveryError,
    InvalidSourceConfigError,
    MalformedPayloadError,
    NetworkTimeoutError,
    RateLimitExceededError,
    RetryableDiscoveryError,
    SourceNotFoundError,
    UpstreamServerError,
)
from app.modules.discovery.models import JobSourceTypeEnum

BOARD_TOKEN_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
DEFAULT_GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io"


class GreenhouseAdapter(JobSourceAdapter):
    """Adapter for harvesting jobs from Greenhouse public board APIs."""

    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.GREENHOUSE

    def validate_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate Greenhouse board token in configuration dictionary."""
        board_token = configuration.get("board_token") if configuration else None
        if not board_token or not isinstance(board_token, str) or not board_token.strip():
            raise InvalidSourceConfigError(
                "Greenhouse configuration must include a non-empty 'board_token' string."
            )

        token = board_token.strip()
        if not BOARD_TOKEN_PATTERN.match(token):
            raise InvalidSourceConfigError(
                f"Invalid Greenhouse board_token '{token}'. Must contain only alphanumeric, hyphens, or underscores."
            )

    async def discover_jobs(
        self,
        base_url: str,
        configuration: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> DiscoveryResult:
        """Fetch all public job postings for the configured Greenhouse board token."""
        self.validate_configuration(configuration)
        board_token = str(configuration["board_token"]).strip()

        api_root = (
            base_url.rstrip("/") if base_url and base_url.strip() else DEFAULT_GREENHOUSE_BASE_URL
        )
        endpoint = f"{api_root}/v1/boards/{board_token}/jobs"

        should_close_client = False
        if client is None:
            client = create_http_client()
            should_close_client = True

        start_time = time.monotonic()
        try:
            response = await client.get(endpoint, params={"content": "true"})
        except httpx.TimeoutException as exc:
            raise NetworkTimeoutError("Greenhouse", timeout_seconds=30.0) from exc
        except httpx.ConnectError as exc:
            raise RetryableDiscoveryError(
                f"Connection failed to Greenhouse at '{endpoint}': {exc}"
            ) from exc
        except httpx.RequestError as exc:
            raise RetryableDiscoveryError(
                f"Network request error querying Greenhouse: {exc}"
            ) from exc
        finally:
            if should_close_client:
                await client.aclose()

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        # Handle HTTP status codes
        if response.status_code == 404:
            raise SourceNotFoundError("Greenhouse", board_token)

        if response.status_code == 429:
            retry_after_hdr = response.headers.get("Retry-After")
            retry_after = (
                int(retry_after_hdr) if (retry_after_hdr and retry_after_hdr.isdigit()) else None
            )
            raise RateLimitExceededError("Greenhouse", retry_after=retry_after)

        if response.status_code >= 500:
            raise UpstreamServerError("Greenhouse", status_code=response.status_code)

        if response.status_code != 200:
            raise DiscoveryError(
                f"Greenhouse API returned unexpected status code {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        # Parse JSON response
        try:
            payload = response.json()
        except Exception as exc:
            raise MalformedPayloadError(
                "Greenhouse", f"Failed to decode response as JSON: {exc}"
            ) from exc

        if (
            not isinstance(payload, dict)
            or "jobs" not in payload
            or not isinstance(payload["jobs"], list)
        ):
            raise MalformedPayloadError(
                "Greenhouse",
                "Response payload is missing the expected root 'jobs' list attribute.",
            )

        raw_jobs_list = payload["jobs"]
        discovered_jobs: list[RawDiscoveredJob] = []
        warnings: list[str] = []

        for item in raw_jobs_list:
            if not isinstance(item, dict):
                warnings.append("Skipped malformed job entry (not a JSON object).")
                continue

            raw_id = item.get("id")
            if raw_id is None:
                warnings.append("Skipped job entry missing required 'id' attribute.")
                continue

            external_id = str(raw_id).strip()
            source_url = (
                item.get("absolute_url")
                or f"https://boards.greenhouse.io/{board_token}/jobs/{external_id}"
            )
            raw_posted_at = item.get("updated_at")

            discovered_jobs.append(
                RawDiscoveredJob(
                    external_id=external_id,
                    source_url=source_url,
                    raw_payload=item,
                    raw_posted_at=str(raw_posted_at) if raw_posted_at else None,
                )
            )

        return DiscoveryResult(
            source_identifier=board_token,
            source_type=JobSourceTypeEnum.GREENHOUSE,
            jobs=discovered_jobs,
            request_metadata={
                "endpoint": endpoint,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "raw_count": len(raw_jobs_list),
            },
            warnings=warnings,
        )
