"""Permitted Company Career Page discovery adapter extension point."""

from typing import Any

import httpx

from app.modules.discovery.adapters.base import DiscoveryResult, JobSourceAdapter
from app.modules.discovery.exceptions import InvalidSourceConfigError
from app.modules.discovery.models import JobSourceTypeEnum


class CareerPageAdapter(JobSourceAdapter):
    """Extension point adapter for controlled harvesting from permitted company career pages.

    Strictly honors boundaries: unrestricted web crawling is prohibited.
    Career page discovery operates only on verified, permitted company endpoints.
    """

    @property
    def source_type(self) -> JobSourceTypeEnum:
        return JobSourceTypeEnum.CAREER_PAGE

    def validate_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate career page configuration."""
        if not configuration:
            raise InvalidSourceConfigError(
                "Configuration dictionary cannot be empty for Career Page source."
            )

        if not configuration.get("permitted"):
            raise InvalidSourceConfigError(
                "Career page harvesting requires explicit compliance verification: 'permitted' must be true."
            )

    async def discover_jobs(
        self,
        base_url: str,
        configuration: dict[str, Any],
        _client: httpx.AsyncClient | None = None,
    ) -> DiscoveryResult:
        """Execute career page harvesting under controlled constraints."""
        self.validate_configuration(configuration)

        return DiscoveryResult(
            source_identifier=base_url,
            source_type=JobSourceTypeEnum.CAREER_PAGE,
            jobs=[],
            warnings=[
                "Permitted company career page adapter extension point registered. "
                "Targeted extraction rules activate when permitted domain schemas are approved."
            ],
        )
