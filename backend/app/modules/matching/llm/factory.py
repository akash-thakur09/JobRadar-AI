"""Factory for instantiating LLM provider implementations."""

from app.core.config import get_settings
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.llm.ollama import OllamaProvider
from app.modules.matching.llm.protocol import LLMProvider

_override_provider: LLMProvider | None = None


def set_llm_provider_override(provider: LLMProvider | None) -> None:
    """Set or clear a global test provider override."""
    global _override_provider
    _override_provider = provider


def get_llm_provider() -> LLMProvider:
    """Obtain the configured LLM provider instance based on application settings."""
    if _override_provider is not None:
        return _override_provider

    settings = get_settings()
    if settings.llm_provider.lower() == "mock" or settings.is_testing:
        return MockLLMProvider()

    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
    )
