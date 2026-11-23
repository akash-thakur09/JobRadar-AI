"""LLM Provider abstraction and structured semantic output schemas."""

from app.modules.matching.llm.exceptions import (
    LLMProviderError,
    LLMResponseValidationError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.modules.matching.llm.factory import get_llm_provider, set_llm_provider_override
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.llm.ollama import OllamaProvider
from app.modules.matching.llm.protocol import LLMProvider
from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    SemanticRecommendationEnum,
    SemanticRisk,
    SemanticStrength,
    TransferableSkill,
)

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "LLMResponseValidationError",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "MockLLMProvider",
    "OllamaProvider",
    "SemanticAnalysisResult",
    "SemanticRecommendationEnum",
    "SemanticRisk",
    "SemanticStrength",
    "TransferableSkill",
    "get_llm_provider",
    "set_llm_provider_override",
]
