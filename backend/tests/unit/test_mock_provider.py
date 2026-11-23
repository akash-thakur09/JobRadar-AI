"""Unit tests for MockLLMProvider."""

from decimal import Decimal

import pytest

from app.modules.matching.llm.exceptions import (
    LLMResponseValidationError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.modules.matching.llm.mock_provider import MockLLMProvider
from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    SemanticRecommendationEnum,
)


@pytest.mark.asyncio
async def test_mock_provider_default_generation() -> None:
    """Verify default generation returns a valid SemanticAnalysisResult."""
    provider = MockLLMProvider()

    assert await provider.ping() is True

    result = await provider.generate_structured(
        prompt="Test Prompt",
        response_schema=SemanticAnalysisResult,
        system_prompt="Test System",
    )

    assert isinstance(result, SemanticAnalysisResult)
    assert result.semantic_score == Decimal("84.00")
    assert result.recommendation == SemanticRecommendationEnum.STRONG_MATCH
    assert len(provider.calls) == 1
    assert provider.calls[0]["prompt"] == "Test Prompt"


@pytest.mark.asyncio
async def test_mock_provider_custom_result() -> None:
    """Verify custom canned result is returned properly."""
    custom = SemanticAnalysisResult(
        semantic_score=Decimal("92.00"),
        recommendation=SemanticRecommendationEnum.STRONG_MATCH,
        confidence=0.95,
        reasoning_summary="Custom mock evaluation summary",
    )
    provider = MockLLMProvider(default_result=custom)

    result = await provider.generate_structured(
        prompt="Another prompt",
        response_schema=SemanticAnalysisResult,
    )

    assert result.semantic_score == Decimal("92.00")
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_mock_provider_simulated_failures() -> None:
    """Verify programmed failure simulations work as expected."""
    timeout_provider = MockLLMProvider(simulate_timeout=True)
    with pytest.raises(LLMTimeoutError):
        await timeout_provider.generate_structured("prompt", SemanticAnalysisResult)

    unavail_provider = MockLLMProvider(simulate_unavailable=True)
    with pytest.raises(LLMUnavailableError):
        await unavail_provider.generate_structured("prompt", SemanticAnalysisResult)

    val_provider = MockLLMProvider(simulate_validation_error=True)
    with pytest.raises(LLMResponseValidationError):
        await val_provider.generate_structured("prompt", SemanticAnalysisResult)

    exc_provider = MockLLMProvider(simulate_exception=RuntimeError("Custom error"))
    with pytest.raises(RuntimeError):
        await exc_provider.generate_structured("prompt", SemanticAnalysisResult)
