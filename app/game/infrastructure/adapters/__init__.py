"""Service Adapters - External service integrations.

LLM, Cache 등 외부 서비스를 Port 인터페이스에 맞춰 래핑합니다.
"""

from .llm_service import LLMServiceAdapter
from .cache_service import CacheServiceAdapter

__all__ = ["LLMServiceAdapter", "CacheServiceAdapter"]
