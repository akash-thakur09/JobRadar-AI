"""Protocol definition for structured LLM providers."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    """Protocol interface defining operations required for LLM semantic analysis."""

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        """Generate structured Pydantic model response adhering strictly to response_schema.

        Args:
            prompt: User context and instruction prompt.
            response_schema: Target Pydantic model class for output validation.
            system_prompt: Optional system prompt setting behavioral constraints.

        Returns:
            Validated Pydantic instance of response_schema.

        Raises:
            LLMTimeoutError: If the call times out.
            LLMUnavailableError: If the service is unreachable.
            LLMResponseValidationError: If JSON output is invalid or fails schema validation.
            LLMProviderError: For any other unhandled provider error.
        """
        ...

    async def ping(self) -> bool:
        """Check health and reachability of the LLM provider backend."""
        ...
