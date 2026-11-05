"""Registry for platform-specific job normalizers."""

from app.modules.discovery.models import JobSourceTypeEnum
from app.modules.jobs.normalizers.base import BaseJobNormalizer
from app.modules.jobs.normalizers.greenhouse import GreenhouseNormalizer
from app.modules.jobs.normalizers.lever import LeverNormalizer

_NORMALIZERS: dict[JobSourceTypeEnum, BaseJobNormalizer] = {
    JobSourceTypeEnum.GREENHOUSE: GreenhouseNormalizer(),
    JobSourceTypeEnum.LEVER: LeverNormalizer(),
}


def get_normalizer_for_source_type(source_type: JobSourceTypeEnum) -> BaseJobNormalizer:
    """Retrieve normalizer instance registered for the given source type.

    Raises:
        ValueError: If no normalizer is registered for the specified source type.
    """
    normalizer = _NORMALIZERS.get(source_type)
    if not normalizer:
        raise ValueError(f"No job normalizer registered for source type: {source_type}")
    return normalizer
