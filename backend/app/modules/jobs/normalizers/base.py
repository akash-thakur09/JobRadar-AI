"""Abstract base class and contract for source-specific job normalizers."""

from abc import ABC, abstractmethod

from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.jobs.models import JobSourceRecord
from app.modules.jobs.schemas import NormalizedJobDTO


class BaseJobNormalizer(ABC):
    """Abstract normalizer isolating platform-specific mapping logic from canonical storage."""

    @property
    @abstractmethod
    def source_type(self) -> JobSourceTypeEnum:
        """The source platform handled by this normalizer."""
        ...

    @abstractmethod
    def normalize(self, record: JobSourceRecord, source: JobSource) -> NormalizedJobDTO:
        """Extract and normalize source-specific payload into a uniform NormalizedJobDTO.

        Args:
            record: The raw JobSourceRecord containing the unadulterated payload.
            source: The configured JobSource providing company naming and metadata.

        Returns:
            NormalizedJobDTO with sanitized text and standardized enums.
        """
        ...
