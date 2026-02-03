"""LLM DTO - Pydantic models for LLM module."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class TokenUsage(BaseModel):
    """Token usage statistics for an LLM response."""

    model_config = ConfigDict(frozen=True)

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    """Standard response from any LLM provider."""

    model_config = ConfigDict(frozen=True)

    content: str
    model: str
    usage: Optional[TokenUsage] = None
    finish_reason: Optional[str] = None
