"""Phase 8: task-tier classification and cost-aware model routing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ai_team.config import ProviderName, Settings
from ai_team.models.pricing import estimate_cost_usd, rates_for_model


class TaskTier(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


_COMPLEX_KEYWORDS = (
    "architecture",
    "security",
    "migration",
    "refactor",
    "distributed",
    "kubernetes",
    "postgres",
    "authentication",
    "authorization",
    "performance",
    "scale",
    "multi-tenant",
    "microservice",
)

_SIMPLE_KEYWORDS = (
    "typo",
    "rename",
    "comment",
    "readme",
    "format",
    "lint",
    "bump version",
    "fix test",
    "hello",
    "status",
)


def classify_task(prompt: str) -> TaskTier:
    text = (prompt or "").strip().lower()
    if not text:
        return TaskTier.STANDARD
    if len(text) < 40 and not any(k in text for k in _COMPLEX_KEYWORDS):
        return TaskTier.SIMPLE
    if any(k in text for k in _SIMPLE_KEYWORDS) and len(text) < 120:
        return TaskTier.SIMPLE
    if len(text) > 400 or any(k in text for k in _COMPLEX_KEYWORDS):
        return TaskTier.COMPLEX
    return TaskTier.STANDARD


@dataclass(frozen=True)
class RoutedModel:
    role: str
    provider: ProviderName
    model: str
    tier: TaskTier
    reason: str


class ModelRouter:
    """Pick provider/model per role from routing tiers and session budget."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        raw = (settings.project_config or {}).get("routing") or {}
        self.enabled = settings.resolved_routing_enabled()
        self.strategy = settings.resolved_routing_strategy()
        self.budget_usd = settings.resolved_routing_budget_usd()
        self.tiers: dict[str, dict[str, dict[str, str]]] = {}
        tiers = raw.get("tiers") if isinstance(raw, dict) else {}
        if isinstance(tiers, dict):
            for tier_name, roles in tiers.items():
                if isinstance(roles, dict):
                    self.tiers[str(tier_name).lower()] = {
                        str(role).lower(): dict(cfg)
                        for role, cfg in roles.items()
                        if isinstance(cfg, dict)
                    }

    def effective_tier(self, prompt: str, session_cost_usd: float = 0.0) -> TaskTier:
        tier = classify_task(prompt)
        if not self.enabled:
            return tier
        if self.strategy == "cost_optimized" and self.budget_usd is not None:
            if session_cost_usd >= self.budget_usd:
                return TaskTier.SIMPLE
            if session_cost_usd >= self.budget_usd * 0.7 and tier == TaskTier.COMPLEX:
                return TaskTier.STANDARD
        return tier

    def resolve(self, role: str, tier: TaskTier, session_cost_usd: float = 0.0) -> RoutedModel:
        role_key = role.lower()
        if not self.enabled:
            provider = self.settings.provider_for_role(role_key)
            model = self.settings.model_for_role(role_key)
            return RoutedModel(role=role_key, provider=provider, model=model, tier=tier, reason="routing_disabled")

        tier_cfg = self.tiers.get(tier.value, {})
        role_cfg = tier_cfg.get(role_key, {})
        provider_raw = str(role_cfg.get("provider") or "").lower()
        model_raw = str(role_cfg.get("model") or "").strip()

        if provider_raw in {"mock", "openai", "anthropic", "google", "openrouter"} and model_raw:
            provider: ProviderName = provider_raw  # type: ignore[assignment]
            provider = self.settings.effective_provider_name(provider)
            reason = f"tier:{tier.value}"
            if self.strategy == "quality" and tier == TaskTier.SIMPLE and role_key in {"architect", "coder"}:
                upgraded = self.tiers.get(TaskTier.STANDARD.value, {}).get(role_key, {})
                if upgraded.get("provider") and upgraded.get("model"):
                    provider = self.settings.effective_provider_name(str(upgraded["provider"]).lower())  # type: ignore[arg-type]
                    model_raw = str(upgraded["model"])
                    reason = "quality_upgrade"
            return RoutedModel(role=role_key, provider=provider, model=model_raw, tier=tier, reason=reason)

        provider = self.settings.provider_for_role(role_key)
        model = self.settings.model_for_role(role_key)
        if self.strategy == "cost_optimized":
            model = _cheaper_model(model, tier)
            reason = f"cost_optimized:{tier.value}"
        elif self.strategy == "quality" and tier == TaskTier.COMPLEX:
            model = _premium_model(model)
            reason = f"quality:{tier.value}"
        else:
            reason = f"balanced:{tier.value}"
        return RoutedModel(role=role_key, provider=provider, model=model, tier=tier, reason=reason)

    def estimate_step_cost(self, routed: RoutedModel, tokens_in: int = 2000, tokens_out: int = 800) -> float:
        return estimate_cost_usd(routed.model, tokens_in=tokens_in, tokens_out=tokens_out)

    def routing_snapshot(self, prompt: str, session_cost_usd: float = 0.0) -> dict[str, Any]:
        tier = self.effective_tier(prompt, session_cost_usd)
        roles = ("manager", "architect", "researcher", "coder", "reviewer", "redteam")
        routes = {role: self.resolve(role, tier, session_cost_usd).__dict__ for role in roles}
        return {
            "enabled": self.enabled,
            "strategy": self.strategy,
            "budget_usd": self.budget_usd,
            "session_cost_usd": session_cost_usd,
            "tier": tier.value,
            "routes": routes,
        }


def _cheaper_model(model: str, tier: TaskTier) -> str:
    key = (model or "").lower()
    if tier == TaskTier.SIMPLE:
        if "gpt-4o" in key and "mini" not in key:
            return "gpt-4o-mini"
        if "claude-sonnet" in key:
            return "claude-3-5-haiku"
        if "gemini-2.5-pro" in key or "gemini-1.5-pro" in key:
            return "gemini-2.0-flash"
    if tier == TaskTier.STANDARD and "gpt-4.1" in key and "mini" not in key and "nano" not in key:
        return "gpt-4o-mini"
    return model


def _premium_model(model: str) -> str:
    key = (model or "").lower()
    if "mini" in key or "haiku" in key or "flash" in key:
        if "gpt" in key:
            return "gpt-4o"
        if "claude" in key:
            return "claude-sonnet-4-5"
        if "gemini" in key:
            return "gemini-2.5-pro"
    return model


def compare_model_cost(model_a: str, model_b: str) -> float:
    """Return estimated savings (USD per 1M in + 1M out) for model_a vs model_b."""
    a_in, a_out = rates_for_model(model_a)
    b_in, b_out = rates_for_model(model_b)
    return round((b_in + b_out) - (a_in + a_out), 6)
