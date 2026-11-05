"""Mock LLM Provider for unit and integration testing without local LLM dependency."""

from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel

from app.modules.matching.llm.exceptions import (
    LLMResponseValidationError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.modules.matching.llm.schemas import (
    SemanticAnalysisResult,
    SemanticRecommendationEnum,
    SemanticRisk,
    SemanticStrength,
    TransferableSkill,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider:
    """Configurable mock LLM provider simulating success, failure, timeouts, and edge cases."""

    def __init__(
        self,
        default_result: BaseModel | None = None,
        simulate_timeout: bool = False,
        simulate_unavailable: bool = False,
        simulate_validation_error: bool = False,
        simulate_exception: Exception | None = None,
        is_healthy: bool = True,
    ) -> None:
        self.default_result = default_result
        self.simulate_timeout = simulate_timeout
        self.simulate_unavailable = simulate_unavailable
        self.simulate_validation_error = simulate_validation_error
        self.simulate_exception = simulate_exception
        self.is_healthy = is_healthy
        self.calls: list[dict[str, Any]] = []

    async def ping(self) -> bool:
        """Return simulated reachability state."""
        return self.is_healthy

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        """Simulate structured generation or programmed failure mode."""
        self.calls.append(
            {
                "prompt": prompt,
                "response_schema": response_schema,
                "system_prompt": system_prompt,
            }
        )

        if self.simulate_timeout:
            raise LLMTimeoutError("Simulated Ollama request timeout after 30.0s")

        if self.simulate_unavailable:
            raise LLMUnavailableError("Simulated Ollama service unavailable")

        if self.simulate_validation_error:
            raise LLMResponseValidationError(
                "Simulated JSON schema mismatch or corrupted JSON",
                raw_response="{not: valid json",
            )

        if self.simulate_exception:
            raise self.simulate_exception

        if self.default_result is not None:
            if isinstance(self.default_result, response_schema):
                return self.default_result
            # Try validating dict if provided
            if isinstance(self.default_result, dict):
                return response_schema.model_validate(self.default_result)

        # Default synthetic SemanticAnalysisResult if target matches
        if issubclass(response_schema, SemanticAnalysisResult):
            default_semantic = SemanticAnalysisResult(
                semantic_score=Decimal("84.00"),
                recommendation=SemanticRecommendationEnum.STRONG_MATCH,
                confidence=0.88,
                reasoning_summary=(
                    "Candidate shows strong alignment with async backend and database layers, "
                    "with demonstrated transferable experience in distributed systems."
                ),
                strengths=[
                    SemanticStrength(
                        claim="Async backend architecture experience",
                        evidence="5+ years building FastAPI and microservices",
                        job_context="Aligns directly with core backend scale requirements",
                    ),
                    SemanticStrength(
                        claim="PostgreSQL optimization",
                        evidence="Verified SQL & database indexing skills",
                        job_context="Aligns with data model ownership",
                    ),
                ],
                gaps=[
                    SemanticRisk(
                        gap="Kubernetes production cluster management",
                        impact="MEDIUM",
                        mitigation="Demonstrated Docker Compose containerization foundation",
                    )
                ],
                transferable_skills=[
                    TransferableSkill(
                        candidate_skill="docker",
                        target_technology="kubernetes",
                        rationale="Container lifecycle and orchestration concepts directly translate",
                    )
                ],
            )
            return default_semantic  # type: ignore[return-value]

        # Generic dummy model instantiation
        return response_schema.model_validate({})
