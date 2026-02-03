"""Gemini LLM Provider implementation.

Uses Google's new genai SDK to interact with Gemini models.
"""

from google import genai
from google.genai import types
from google.genai.errors import ClientError
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.common.exception import TooManyRequests
from app.llm.providers.base import LLMProvider
from app.llm.dto.llm_response import LLMResponse, TokenUsage


class GeminiProvider(LLMProvider):
    """Gemini LLM provider using Google genai SDK.

    Supports Gemini 2.0 Flash and other Gemini models.
    Includes automatic retry logic for transient API errors.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
    ):
        """Initialize Gemini provider.

        Args:
            api_key: Google AI API key.
            model_name: Gemini model to use.
        """
        self._client = genai.Client(api_key=api_key)
        self.model_name = model_name
        masked_key = api_key[:5] + "*" * 5 if api_key else "None"
        import logging
        logger = logging.getLogger("uvicorn")
        logger.info(f"DEBUG: GeminiProvider initialized with API Key: {masked_key}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_not_exception_type((ValueError, TooManyRequests)),
    )
    async def generate_response(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.8,
    ) -> LLMResponse:
        """Generate a response using Gemini.

        Args:
            system_prompt: The system prompt for game master context.
            messages: Conversation history as list of dicts.
            temperature: Creativity level (0.0 - 1.0).

        Returns:
            LLMResponse with generated content.

        Raises:
            ValueError: If messages list is empty.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        # Build conversation contents
        contents = self._build_contents(system_prompt, messages)

        # Call Gemini API using new SDK
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=system_prompt,
                ),
            )
        except ClientError as e:
            import logging
            logger = logging.getLogger("uvicorn")
            logger.warning(f"DEBUG: Gemini ClientError: {e}")
            
            # Check for 429 Too Many Requests or quota exhaustion
            if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                raise TooManyRequests(message="Gemini API Quota Exceeded. Please try again later.")
            raise e
        except Exception as e:
            import logging
            logger = logging.getLogger("uvicorn")
            logger.error(f"DEBUG: Gemini API Error: {e}", exc_info=True)
            raise e

        # Extract usage if available
        usage = None
        if response.usage_metadata:
            usage = TokenUsage(
                prompt_tokens=response.usage_metadata.prompt_token_count or 0,
                completion_tokens=response.usage_metadata.candidates_token_count or 0,
                total_tokens=response.usage_metadata.total_token_count or 0,
            )

        # Extract finish_reason (handle both string and enum)
        finish_reason = None
        if response.candidates and response.candidates[0].finish_reason:
            fr = response.candidates[0].finish_reason
            finish_reason = fr.name if hasattr(fr, "name") else str(fr)

        return LLMResponse(
            content=response.text or "",
            model=self.model_name,
            usage=usage,
            finish_reason=finish_reason,
        )

    def _build_contents(
        self, system_prompt: str, messages: list[dict]
    ) -> list[types.Content]:
        """Build Gemini-compatible content list.

        Args:
            system_prompt: System instruction.
            messages: User/assistant message history.

        Returns:
            List of Content objects for Gemini API.
        """
        contents = []

        # Conversation messages
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])],
            ))

        return contents
