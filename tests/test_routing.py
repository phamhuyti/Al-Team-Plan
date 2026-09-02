"""Phase 8 routing and cost optimization tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ai_team.config import Settings, apply_project_config
from ai_team.models.routing import ModelRouter, TaskTier, classify_task, compare_model_cost
from ai_team.orchestration.workflow import TeamRuntime


def test_classify_task_tiers() -> None:
    assert classify_task("fix typo in readme") == TaskTier.SIMPLE
    assert classify_task("Add authentication with OAuth2 and session security hardening") == TaskTier.COMPLEX
    assert classify_task("Add a health check endpoint with metrics export and alert hooks") == TaskTier.STANDARD


def test_routing_disabled_uses_settings() -> None:
    settings = Settings(provider="mock", model="gpt-4o", coder_model="gpt-4o-mini")
    router = ModelRouter(settings)
    routed = router.resolve("coder", TaskTier.SIMPLE)
    assert routed.provider == "mock"
    assert routed.model == "gpt-4o-mini"
    assert routed.reason == "routing_disabled"


def test_routing_tier_from_yaml(project_root: Path) -> None:
    cfg_path = project_root / ".ai" / "config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    data["routing"] = {
        "enabled": True,
        "strategy": "balanced",
        "tiers": {
            "simple": {"coder": {"provider": "mock", "model": "gpt-4o-mini"}},
            "complex": {"coder": {"provider": "mock", "model": "gpt-4o"}},
        },
    }
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    settings = apply_project_config(Settings(provider="mock", model="mock"), project_root)
    router = ModelRouter(settings)
    simple = router.resolve("coder", TaskTier.SIMPLE)
    complex_ = router.resolve("coder", TaskTier.COMPLEX)
    assert simple.model == "gpt-4o-mini"
    assert complex_.model == "gpt-4o"


def test_cost_optimized_downgrades_on_budget() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4o",
        routing_enabled=True,
        routing_strategy="cost_optimized",
        routing_budget_usd=1.0,
        project_config={
            "routing": {
                "enabled": True,
                "strategy": "cost_optimized",
                "budget_usd_per_session": 1.0,
            }
        },
    )
    router = ModelRouter(settings)
    tier = router.effective_tier("Design distributed authentication", session_cost_usd=1.2)
    assert tier == TaskTier.SIMPLE


def test_compare_model_cost() -> None:
    assert compare_model_cost("gpt-4o-mini", "gpt-4o") > 0


@pytest.mark.asyncio
async def test_plan_records_routing_trace(project_root: Path) -> None:
    cfg_path = project_root / ".ai" / "config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    data["routing"] = {"enabled": True, "strategy": "balanced"}
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    settings = Settings(
        provider="mock",
        model="gpt-4o",
        auto_approve_moderate=True,
        auto_approve_dangerous=True,
    )
    rt = TeamRuntime(project_root, settings=settings, auto_approve=True)
    result = await rt.plan("Add authentication")
    assert result.ok
    assert "routing" in result.details
    replay = rt.replay_session(result.session_id)
    steps = {row["step"] for row in replay["timeline"]}
    assert "routing" in steps
