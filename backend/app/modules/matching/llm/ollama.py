"""Ollama HTTP provider implementation for local LLM inference."""

import asyncio
import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.modules.matching.llm.exceptions import (
    LLMProviderError,
    LLMResponseValidationError,
    LLMTimeoutError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaProvider:
    """Ollama HTTP client supporting structured JSON generation and schema validation."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        temperature: float = 0.1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature

    async def ping(self) -> bool:
        """Check if Ollama service is reachable and responsive."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/version")
                return response.status_code == 200
        except Exception:
            return False

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        system_prompt: str | None = None,
    ) -> T:
        """Call Ollama /api/chat with format='json', retrying on transient errors.

        Args:
            prompt: User context and instructions.
            response_schema: Target Pydantic model class.
            system_prompt: Optional instructions constraining model behavior.

        Returns:
            Validated instance of response_schema.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Append JSON schema definition to prompt context to guide Ollama
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        instruction_suffix = (
            f"\nYou MUST respond with a single, valid JSON object strictly adhering "
            f"to the following JSON Schema:\n{schema_json}\n"
            f"Do not include any surrounding markdown fences or additional commentary."
        )
        messages[-1]["content"] += instruction_suffix

        payload = {
            "model": self.model,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )

                if response.status_code != 200:
                    raise LLMProviderError(
                        f"Ollama returned HTTP {response.status_code}: {response.text}",
                        details={"status_code": str(response.status_code), "body": response.text},
                    )

                body = response.json()
                raw_content = body.get("message", {}).get("content", "")
                if not raw_content:
                    raise LLMResponseValidationError(
                        "Ollama returned empty response message content",
                        raw_response=response.text,
                    )

                # Parse JSON and validate against schema
                try:
                    data = json.loads(raw_content)
                    return response_schema.model_validate(data)
                except (json.JSONDecodeError, ValidationError) as val_err:
                    logger.warning(
                        f"Ollama structured validation error (attempt {attempt + 1}): {val_err}"
                    )
                    raise LLMResponseValidationError(
                        f"Failed to validate LLM response against {response_schema.__name__}: {val_err}",
                        raw_response=raw_content,
                    ) from val_err

            except (httpx.ConnectError, httpx.NetworkError) as net_err:
                last_error = LLMUnavailableError(
                    f"Ollama service unavailable at {self.base_url}: {net_err}"
                )
                logger.warning(f"Ollama connection error (attempt {attempt + 1}): {net_err}")
            except httpx.TimeoutException as time_err:
                last_error = LLMTimeoutError(
                    f"Ollama request timed out after {self.timeout_seconds}s"
                )
                logger.warning(f"Ollama timeout (attempt {attempt + 1}): {time_err}")
            except LLMResponseValidationError as val_err:
                last_error = val_err
            except LLMProviderError as prov_err:
                last_error = prov_err
            except Exception as unk_err:
                last_error = LLMProviderError(f"Unexpected Ollama provider error: {unk_err}")
                logger.warning(f"Unexpected Ollama error (attempt {attempt + 1}): {unk_err}")

            if attempt < self.max_retries:
                backoff = 0.5 * (2**attempt)
                await asyncio.sleep(backoff)

        assert last_error is not None
        raise last_error
