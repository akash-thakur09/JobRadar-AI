"""Job Source Adapters package."""

from app.modules.discovery.adapters.base import DiscoveryResult, JobSourceAdapter, RawDiscoveredJob
from app.modules.discovery.adapters.career_page import CareerPageAdapter
from app.modules.discovery.adapters.greenhouse import GreenhouseAdapter
from app.modules.discovery.adapters.lever import LeverAdapter
from app.modules.discovery.adapters.registry import get_adapter_for_source_type

__all__ = [
    "JobSourceAdapter",
    "RawDiscoveredJob",
    "DiscoveryResult",
    "GreenhouseAdapter",
    "LeverAdapter",
    "CareerPageAdapter",
    "get_adapter_for_source_type",
]
