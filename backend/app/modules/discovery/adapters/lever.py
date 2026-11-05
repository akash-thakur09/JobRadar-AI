"""Lever public job postings discovery adapter."""

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

COMPANY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
DEFAULT_LEVER_BASE_URL = "https://api.lever.co"


class LeverAdapter(JobSourceAdapter):
    """Adapter for harvesting jobs from Lever public postings API."""

    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.LEVER

    def validate_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate Lever company identifier in configuration dictionary."""
        company_id = (
            (configuration.get("company_id") or configuration.get("site"))
            if configuration
            else None
        )
        if not company_id or not isinstance(company_id, str) or not company_id.strip():
            raise InvalidSourceConfigError(
                "Lever configuration must include a non-empty 'company_id' or 'site' string."
            )

        ident = company_id.strip()
        if not COMPANY_ID_PATTERN.match(ident):
            raise InvalidSourceConfigError(
                f"Invalid Lever company identifier '{ident}'. Must contain only alphanumeric, hyphens, or underscores."
            )

    async def discover_jobs(
        self,
        base_url: str,
        configuration: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> DiscoveryResult:
        """Fetch all public job postings for the configured Lever company identifier."""
        self.validate_configuration(configuration)
        company_id = str(configuration.get("company_id") or configuration.get("site")).strip()

        api_root = base_url.rstrip("/") if base_url and base_url.strip() else DEFAULT_LEVER_BASE_URL
        endpoint = f"{api_root}/v0/postings/{company_id}"

        should_close_client = False
        if client is None:
            client = create_http_client()
            should_close_client = True

        start_time = time.monotonic()
        try:
            response = await client.get(endpoint, params={"mode": "json"})
        except httpx.TimeoutException as exc:
            raise NetworkTimeoutError("Lever", timeout_seconds=30.0) from exc
        except httpx.ConnectError as exc:
            raise RetryableDiscoveryError(
                f"Connection failed to Lever at '{endpoint}': {exc}"
            ) from exc
        except httpx.RequestError as exc:
            raise RetryableDiscoveryError(f"Network request error querying Lever: {exc}") from exc
        finally:
            if should_close_client:
                await client.aclose()

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        # Handle HTTP status codes
        if response.status_code == 404:
            raise SourceNotFoundError("Lever", company_id)

        if response.status_code == 429:
            retry_after_hdr = response.headers.get("Retry-After")
            retry_after = (
                int(retry_after_hdr) if (retry_after_hdr and retry_after_hdr.isdigit()) else None
            )
            raise RateLimitExceededError("Lever", retry_after=retry_after)

        if response.status_code >= 500:
            raise UpstreamServerError("Lever", status_code=response.status_code)

        if response.status_code != 200:
            raise DiscoveryError(
                f"Lever API returned unexpected status code {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        # Parse JSON response
        try:
            payload = response.json()
        except Exception as exc:
            raise MalformedPayloadError(
                "Lever", f"Failed to decode response as JSON: {exc}"
            ) from exc

        # Lever returns top-level array of posting objects
        if not isinstance(payload, list):
            raise MalformedPayloadError(
                "Lever",
                "Response payload is not the expected top-level list of postings.",
            )

        discovered_jobs: list[RawDiscoveredJob] = []
        warnings: list[str] = []

        for item in payload:
            if not isinstance(item, dict):
                warnings.append("Skipped malformed posting entry (not a JSON object).")
                continue

            raw_id = item.get("id")
            if raw_id is None:
                warnings.append("Skipped posting entry missing required 'id' attribute.")
                continue

            external_id = str(raw_id).strip()
            source_url = (
                item.get("hostedUrl")
                or item.get("applyUrl")
                or f"https://jobs.lever.co/{company_id}/{external_id}"
            )
            raw_posted_at = item.get("createdAt")

            discovered_jobs.append(
                RawDiscoveredJob(
                    external_id=external_id,
                    source_url=source_url,
                    raw_payload=item,
                    raw_posted_at=str(raw_posted_at) if raw_posted_at is not None else None,
                )
            )

        return DiscoveryResult(
            source_identifier=company_id,
            source_type=JobSourceTypeEnum.LEVER,
            jobs=discovered_jobs,
            request_metadata={
                "endpoint": endpoint,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "raw_count": len(payload),
            },
            warnings=warnings,
        )
