"""Runtime configuration. OpenAI is the V1 default; other providers are pluggable."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["mock", "openai", "anthropic", "google", "openrouter"]

DEFAULT_AGENT_ROLES = (
    "manager",
    "architect",
    "researcher",
    "coder",
    "reviewer",
    "redteam",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AI_TEAM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: ProviderName = "openai"
    model: str = "gpt-4o"

    manager_model: str | None = None
    architect_model: str | None = None
    researcher_model: str | None = None
    coder_model: str | None = None
    reviewer_model: str | None = None
    redteam_model: str | None = None

    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("openai_api_key", "OPENAI_API_KEY", "AI_TEAM_OPENAI_API_KEY"),
    )
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("anthropic_api_key", "ANTHROPIC_API_KEY", "AI_TEAM_ANTHROPIC_API_KEY"),
    )
    google_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("google_api_key", "GOOGLE_API_KEY", "AI_TEAM_GOOGLE_API_KEY"),
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("openrouter_api_key", "OPENROUTER_API_KEY", "AI_TEAM_OPENROUTER_API_KEY"),
    )

    database_url: str = "sqlite:///./.ai/ai-team.db"
    projects_root: Path = Path("./projects")

    auto_approve_moderate: bool = False
    auto_approve_dangerous: bool = False

    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    max_context_chars: int = 80_000
    debate_rounds: int = 2
    max_review_loops: int = 2

    def model_for_role(self, role: str) -> str:
        override = getattr(self, f"{role}_model", None)
        return override or self.model

    def effective_provider(self) -> ProviderName:
        if self.provider == "openai" and not (self.openai_api_key or _env("OPENAI_API_KEY")):
            return "mock"
        return self.provider


def _env(name: str) -> str:
    import os

    return os.environ.get(name, "")


def load_settings() -> Settings:
    import os

    # Allow unprefixed provider keys commonly used by SDKs.
    data: dict[str, str] = {}
    if os.environ.get("OPENAI_API_KEY"):
        data["openai_api_key"] = os.environ["OPENAI_API_KEY"]
    if os.environ.get("ANTHROPIC_API_KEY"):
        data["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]
    if os.environ.get("GOOGLE_API_KEY"):
        data["google_api_key"] = os.environ["GOOGLE_API_KEY"]
    if os.environ.get("OPENROUTER_API_KEY"):
        data["openrouter_api_key"] = os.environ["OPENROUTER_API_KEY"]
    return Settings(**data)
