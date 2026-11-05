"""Domain exceptions for LLM Provider interactions."""


class LLMProviderError(Exception):
    """Base exception for all LLM provider failures."""

    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LLMTimeoutError(LLMProviderError):
    """Raised when the LLM service exceeds configured timeout limits."""


class LLMUnavailableError(LLMProviderError):
    """Raised when the LLM service is unreachable or offline."""


class LLMResponseValidationError(LLMProviderError):
    """Raised when the LLM returns unparseable or schema-invalid responses."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response
