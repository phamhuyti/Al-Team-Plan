"""Factory: agents never construct provider SDKs directly."""

from __future__ import annotations

from ai_team.config import ProviderName, Settings
from ai_team.models.anthropic import AnthropicProvider
from ai_team.models.base import ModelProvider
from ai_team.models.google import GoogleProvider
from ai_team.models.mock import MockProvider
from ai_team.models.openai import OpenAIProvider
from ai_team.models.openrouter import OpenRouterProvider


def build_provider(
    settings: Settings,
    role: str | None = None,
    *,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> ModelProvider:
    role_name = role or "manager"
    model = model_override or settings.model_for_role(role_name)
    provider: ProviderName = provider_override or settings.provider_for_role(role_name)  # type: ignore[assignment]
    if provider_override:
        provider = settings.effective_provider_name(provider)  # type: ignore[arg-type]
    return _build(provider, model, settings)


def _build(provider: ProviderName, model: str, settings: Settings) -> ModelProvider:
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
