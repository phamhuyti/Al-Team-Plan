"""Runtime configuration. OpenAI is the V1 default; other providers are pluggable.

Precedence (highest wins):
1. Explicit Settings fields (tests / constructor)
2. Role-specific env (`AI_TEAM_CODER_MODEL`, `AI_TEAM_CODER_PROVIDER`)
3. Project `.ai/config.yaml` agents / permissions / git
4. Global env (`AI_TEAM_PROVIDER`, `AI_TEAM_MODEL`)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
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

    manager_provider: ProviderName | None = None
    architect_provider: ProviderName | None = None
    researcher_provider: ProviderName | None = None
    coder_provider: ProviderName | None = None
    reviewer_provider: ProviderName | None = None
    redteam_provider: ProviderName | None = None

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

    git_branch_prefix: str = "ai/"
    git_auto_commit: bool = True
    git_auto_push: bool = False

    # Raw project config snapshot (not from env).
    project_config: dict[str, Any] = Field(default_factory=dict)

    def model_for_role(self, role: str) -> str:
        override = getattr(self, f"{role}_model", None)
        return override or self.model

    def provider_for_role(self, role: str) -> ProviderName:
        override = getattr(self, f"{role}_provider", None)
        named: ProviderName = override or self.provider
        return self.effective_provider_name(named)

    def effective_provider(self) -> ProviderName:
        return self.effective_provider_name(self.provider)

    def effective_provider_name(self, provider: ProviderName) -> ProviderName:
        if provider == "openai" and not (self.openai_api_key or _env("OPENAI_API_KEY")):
            return "mock"
        return provider


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


def load_project_config(root: Path) -> dict[str, Any]:
    path = Path(root).resolve() / ".ai" / "config.yaml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def apply_project_config(settings: Settings, root: Path) -> Settings:
    """Overlay `.ai/config.yaml` onto settings.

    Role-specific Settings fields already set (e.g. via env `AI_TEAM_CODER_MODEL`)
    keep priority and are not overwritten by the YAML file.
    """
    raw = load_project_config(root)
    if not raw:
        return settings.model_copy(update={"project_config": {}})

    updates: dict[str, Any] = {"project_config": raw}
    agents = raw.get("agents") or {}
    if isinstance(agents, dict):
        for role in DEFAULT_AGENT_ROLES:
            cfg = agents.get(role)
            if not isinstance(cfg, dict):
                continue
            model_key = f"{role}_model"
            provider_key = f"{role}_provider"
            if cfg.get("model") and getattr(settings, model_key) is None:
                updates[model_key] = str(cfg["model"])
            if cfg.get("provider") and getattr(settings, provider_key) is None:
                provider = str(cfg["provider"]).lower()
                if provider in {"mock", "openai", "anthropic", "google", "openrouter"}:
                    updates[provider_key] = provider

    permissions = raw.get("permissions") or {}
    if isinstance(permissions, dict):
        # Only overlay when still at defaults so explicit env wins.
        if "auto_approve_moderate" in permissions and not _env_set("AI_TEAM_AUTO_APPROVE_MODERATE"):
            updates["auto_approve_moderate"] = bool(permissions["auto_approve_moderate"])
        if "auto_approve_dangerous" in permissions and not _env_set("AI_TEAM_AUTO_APPROVE_DANGEROUS"):
            updates["auto_approve_dangerous"] = bool(permissions["auto_approve_dangerous"])

    git = raw.get("git") or {}
    if isinstance(git, dict):
        if git.get("branch_prefix"):
            updates["git_branch_prefix"] = str(git["branch_prefix"])
        if "auto_commit" in git:
            updates["git_auto_commit"] = bool(git["auto_commit"])
        if "auto_push" in git:
            updates["git_auto_push"] = bool(git["auto_push"])

    return settings.model_copy(update=updates)


def _env_set(name: str) -> bool:
    import os

    return name in os.environ
