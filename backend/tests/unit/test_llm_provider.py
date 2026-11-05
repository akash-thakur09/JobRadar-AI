"""Unit tests for OllamaProvider HTTP client and error handling."""

from decimal import Decimal

import httpx
import pytest
import respx

from app.modules.matching.llm.exceptions import (
    LLMProviderError,
    LLMResponseValidationError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.modules.matching.llm.ollama import OllamaProvider
from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    SemanticRecommendationEnum,
)


@pytest.mark.asyncio
async def test_ollama_ping_success() -> None:
    """Verify ping returns True when Ollama version endpoint responds 200."""
    provider = OllamaProvider(base_url="http://mock-ollama:11434")

    with respx.mock(base_url="http://mock-ollama:11434") as respx_mock:
        respx_mock.get("/api/version").respond(200, json={"version": "0.3.12"})
        assert await provider.ping() is True


@pytest.mark.asyncio
async def test_ollama_ping_failure() -> None:
    """Verify ping returns False when Ollama endpoint is down."""
    provider = OllamaProvider(base_url="http://mock-ollama:11434")

    with respx.mock(base_url="http://mock-ollama:11434") as respx_mock:
        respx_mock.get("/api/version").respond(503)
        assert await provider.ping() is False


@pytest.mark.asyncio
async def test_ollama_generate_structured_success() -> None:
    """Verify successful structured generation and schema validation."""
    provider = OllamaProvider(
        base_url="http://mock-ollama:11434",
        model="llama3.1:8b",
        timeout_seconds=5.0,
        max_retries=1,
    )

    valid_response_body = {
        "model": "llama3.1:8b",
        "message": {
            "role": "assistant",
            "content": (
                '{"semantic_score": 86.50, '
                '"recommendation": "STRONG_MATCH", '
                '"confidence": 0.90, '
                '"reasoning_summary": "Excellent technical alignment in backend systems.", '
                '"strengths": [{"claim": "Async architecture", "evidence": "5 years FastAPI", "job_context": "Core API"}], '
                '"gaps": [{"gap": "Kubernetes", "impact": "LOW", "mitigation": "Docker"}], '
                '"transferable_skills": [{"candidate_skill": "docker", "target_technology": "kubernetes", "rationale": "Orchestration"}]}'
            ),
        },
        "done": True,
    }

    with respx.mock(base_url="http://mock-ollama:11434") as respx_mock:
        respx_mock.post("/api/chat").respond(200, json=valid_response_body)

        result = await provider.generate_structured(
            prompt="Evaluate candidate",
            response_schema=SemanticAnalysisResult,
            system_prompt="Act as talent evaluator",
        )

        assert isinstance(result, SemanticAnalysisResult)
        assert result.semantic_score == Decimal("86.50")
        assert result.recommendation == SemanticRecommendationEnum.STRONG_MATCH
        assert result.confidence == 0.90
        assert len(result.strengths) == 1
        assert len(result.transferable_skills) == 1


@pytest.mark.asyncio
async def test_ollama_generate_structured_retries_on_http_error() -> None:
    """Verify retries on 500 server error before raising LLMProviderError."""
    provider = OllamaProvider(
        base_url="http://mock-ollama:11434",
        max_retries=2,
    )

    with respx.mock(base_url="http://mock-ollama:11434") as respx_mock:
        route = respx_mock.post("/api/chat").respond(500, text="Internal Ollama Error")

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_structured(
                prompt="Evaluate candidate",
                response_schema=SemanticAnalysisResult,
            )

        assert "HTTP 500" in str(exc_info.value)
        assert route.call_count == 3  # initial attempt + 2 retries


@pytest.mark.asyncio
async def test_ollama_generate_structured_timeout() -> None:
    """Verify timeout exception wraps into LLMTimeoutError."""
    provider = OllamaProvider(
        base_url="http://mock-ollama:11434",
        timeout_seconds=0.01,
        max_retries=1,
    )

    with respx.mock(base_url="http://mock-ollama:11434") as respx_mock:
        respx_mock.post("/api/chat").mock(side_effect=httpx.TimeoutException("Read timed out"))

        with pytest.raises(LLMTimeoutError):
            await provider.generate_structured(
                prompt="Evaluate candidate",
                response_schema=SemanticAnalysisResult,
            )


@pytest.mark.asyncio
async def test_ollama_generate_structured_connection_failure() -> None:
    """Verify network connection errors raise LLMUnavailableError."""
    provider = OllamaProvider(
        base_url="http://mock-ollama:11434",
        max_retries=1,
    )

    with respx.mock(base_url="http://mock-ollama:11434") as respx_mock:
        respx_mock.post("/api/chat").mock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(LLMUnavailableError):
            await provider.generate_structured(
                prompt="Evaluate candidate",
                response_schema=SemanticAnalysisResult,
            )


@pytest.mark.asyncio
async def test_ollama_generate_structured_invalid_json() -> None:
    """Verify malformed JSON output raises LLMResponseValidationError."""
    provider = OllamaProvider(
        base_url="http://mock-ollama:11434",
        max_retries=0,
    )

    with respx.mock(base_url="http://mock-ollama:11434") as respx_mock:
        respx_mock.post("/api/chat").respond(
            200,
            json={"message": {"content": "Not JSON at all, plain text response"}},
        )

        with pytest.raises(LLMResponseValidationError) as exc_info:
            await provider.generate_structured(
                prompt="Evaluate candidate",
                response_schema=SemanticAnalysisResult,
            )

        assert "Failed to validate LLM response" in str(exc_info.value)
