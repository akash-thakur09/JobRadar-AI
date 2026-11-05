"""Registry and dynamic factory for Job Source Adapters."""

from app.modules.discovery.adapters.base import JobSourceAdapter
from app.modules.discovery.adapters.career_page import CareerPageAdapter
from app.modules.discovery.adapters.greenhouse import GreenhouseAdapter
from app.modules.discovery.adapters.lever import LeverAdapter
from app.modules.discovery.exceptions import UnsupportedSourceTypeError
from app.modules.discovery.models import JobSourceTypeEnum

_ADAPTER_REGISTRY: dict[JobSourceTypeEnum, type[JobSourceAdapter]] = {
    JobSourceTypeEnum.GREENHOUSE: GreenhouseAdapter,
    JobSourceTypeEnum.LEVER: LeverAdapter,
    JobSourceTypeEnum.CAREER_PAGE: CareerPageAdapter,
}


def get_adapter_for_source_type(source_type: JobSourceTypeEnum | str) -> JobSourceAdapter:
    """Resolve and instantiate the registered adapter for the given source type."""
    try:
        resolved_type = (
            source_type
            if isinstance(source_type, JobSourceTypeEnum)
            else JobSourceTypeEnum(str(source_type).upper())
        )
    except ValueError as exc:
        raise UnsupportedSourceTypeError(str(source_type)) from exc

    adapter_cls = _ADAPTER_REGISTRY.get(resolved_type)
    if adapter_cls is None:
        raise UnsupportedSourceTypeError(str(source_type))

    return adapter_cls()
