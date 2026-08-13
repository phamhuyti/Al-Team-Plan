"""Factory: agents never construct provider SDKs directly."""

from __future__ import annotations

from ai_team.config import Settings
from ai_team.models.anthropic import AnthropicProvider
from ai_team.models.base import ModelProvider
from ai_team.models.google import GoogleProvider
from ai_team.models.mock import MockProvider
from ai_team.models.openai import OpenAIProvider
from ai_team.models.openrouter import OpenRouterProvider


def build_provider(settings: Settings, role: str | None = None) -> ModelProvider:
    model = settings.model_for_role(role or "manager")
    provider = settings.effective_provider()
    if provider == "mock":
        return MockProvider(model=model)
    if provider == "openai":
        return OpenAIProvider(model=model, api_key=settings.openai_api_key)
    if provider == "anthropic":
        return AnthropicProvider(model=model or "claude-sonnet-4-5", api_key=settings.anthropic_api_key)
    if provider == "google":
        return GoogleProvider(model=model or "gemini-2.0-flash", api_key=settings.google_api_key)
    if provider == "openrouter":
        return OpenRouterProvider(model=model, api_key=settings.openrouter_api_key)
    raise ValueError(f"Unknown provider: {provider}")
