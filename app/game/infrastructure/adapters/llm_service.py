"""LLM Service Adapter.

GeminiProvider를 Port 인터페이스에 맞춰 래핑합니다.
"""

from app.game.application.ports import LLMServiceInterface
from app.llm.dto.llm_response import LLMResponse
from app.llm.providers.gemini import GeminiProvider
from config.settings import settings


class LLMServiceAdapter(LLMServiceInterface):
    """LLM 서비스 어댑터.
    
    GeminiProvider를 Port 인터페이스에 맞춰 래핑합니다.
    향후 다른 LLM 제공자로 교체 가능합니다.
    """

    def __init__(self, provider: GeminiProvider = None):
        if provider is None:
            self._provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model_name=settings.gemini_model,
            )
        else:
            self._provider = provider

    async def generate_response(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.8,
    ) -> LLMResponse:
        """LLM 응답 생성."""
        return await self._provider.generate_response(
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
        )
