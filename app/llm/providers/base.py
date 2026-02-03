"""Base classes for LLM providers.

All LLM providers (Gemini, OpenAI, Claude) should inherit from LLMProvider.
"""

from abc import ABC, abstractmethod

from app.llm.dto.llm_response import LLMResponse


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement the generate_response method.
    This enables easy swapping between different LLM backends.
    """

    @abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.8,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            system_prompt: The system prompt to set context.
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0.0 - 1.0).

        Returns:
            LLMResponse with generated content and metadata.

        Raises:
            ValueError: If messages is empty.
        """
        pass
