"""V1 hardening: project config.yaml, provider/role, cost, approval API."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from ai_team.api.app import create_app
from ai_team.config import Settings, apply_project_config, load_project_config
from ai_team.models.factory import build_provider
from ai_team.models.mock import MockProvider
from ai_team.models.openai import OpenAIProvider
from ai_team.models.pricing import estimate_cost_usd, rates_for_model
from ai_team.orchestration.workflow import TeamRuntime
from ai_team.security.approvals import ApprovalPending
from ai_team.security.permissions import RiskLevel


def test_rates_and_cost_estimate() -> None:
    assert rates_for_model("mock") == (0.0, 0.0)
    assert rates_for_model("gpt-4o") == (2.50, 10.00)
    assert rates_for_model("openrouter/anthropic/claude-sonnet-4-5") == (3.00, 15.00)
    cost = estimate_cost_usd("gpt-4o", tokens_in=1_000_000, tokens_out=1_000_000)
    assert cost == pytest.approx(12.5)


def test_load_project_config_yaml(project_root: Path) -> None:
    cfg_path = project_root / ".ai" / "config.yaml"
    assert cfg_path.exists()
    raw = load_project_config(project_root)
    assert "agents" in raw
    assert raw["agents"]["coder"]["provider"] == "openai"


def test_apply_project_config_sets_provider_and_model(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AI_TEAM_AUTO_APPROVE_MODERATE", raising=False)
    monkeypatch.delenv("AI_TEAM_AUTO_APPROVE_DANGEROUS", raising=False)
    cfg_path = project_root / ".ai" / "config.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "agents": {
                    "manager": {"provider": "openai", "model": "gpt-4o-mini"},
                    "coder": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
                    "architect": {"provider": "openai", "model": "gpt-4o"},
                    "researcher": {"provider": "openai", "model": "gpt-4o"},
                    "reviewer": {"provider": "openai", "model": "gpt-4o"},
                    "redteam": {"provider": "openai", "model": "gpt-4o"},
                },
                "permissions": {"auto_approve_moderate": True, "auto_approve_dangerous": False},
                "git": {"branch_prefix": "team/", "auto_commit": True, "auto_push": False},
            }
        ),
        encoding="utf-8",
    )
    base = Settings(provider="mock", model="mock", openai_api_key="sk-test", anthropic_api_key="sk-ant")
    merged = apply_project_config(base, project_root)
    assert merged.coder_provider == "anthropic"
    assert merged.coder_model == "claude-sonnet-4-5"
    assert merged.manager_model == "gpt-4o-mini"
    assert merged.git_branch_prefix == "team/"
    assert merged.auto_approve_moderate is True
    assert merged.provider_for_role("coder") == "anthropic"
    assert merged.model_for_role("coder") == "claude-sonnet-4-5"


def test_env_role_override_beats_yaml(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = project_root / ".ai" / "config.yaml"
    cfg_path.write_text(
        yaml.safe_dump({"agents": {"coder": {"provider": "anthropic", "model": "claude-sonnet-4-5"}}}),
        encoding="utf-8",
    )
    base = Settings(
        provider="mock",
        model="mock",
        coder_model="gpt-4o-mini",
        coder_provider="openai",
        openai_api_key="sk-test",
    )
    merged = apply_project_config(base, project_root)
    assert merged.coder_model == "gpt-4o-mini"
    assert merged.coder_provider == "openai"


def test_build_provider_per_role(project_root: Path) -> None:
    cfg_path = project_root / ".ai" / "config.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "agents": {
                    "manager": {"provider": "openai", "model": "gpt-4o"},
                    "coder": {"provider": "openai", "model": "gpt-4o-mini"},
                }
            }
        ),
        encoding="utf-8",
    )
    settings = apply_project_config(
        Settings(provider="openai", model="gpt-4o", openai_api_key="sk-test"),
        project_root,
    )
    manager = build_provider(settings, "manager")
    coder = build_provider(settings, "coder")
    assert isinstance(manager, OpenAIProvider)
    assert isinstance(coder, OpenAIProvider)
    assert manager.model == "gpt-4o"
    assert coder.model == "gpt-4o-mini"


def test_runtime_reads_config_and_records_cost(project_root: Path) -> None:
    cfg_path = project_root / ".ai" / "config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    data["agents"]["coder"] = {"provider": "mock", "model": "gpt-4o"}
    data["agents"]["manager"] = {"provider": "mock", "model": "gpt-4o"}
    data["git"]["branch_prefix"] = "feat/"
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    settings = Settings(provider="mock", model="mock", auto_approve_moderate=True, auto_approve_dangerous=True)
    rt = TeamRuntime(project_root, settings=settings, auto_approve=True)
    agents = {row["role"]: row for row in rt.list_agents()}
    assert agents["coder"]["model"] == "gpt-4o"
    assert agents["coder"]["provider"] == "mock"
    assert rt.settings.git_branch_prefix == "feat/"


@pytest.mark.asyncio
async def test_plan_emits_nonzero_cost_for_priced_model(project_root: Path) -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4o",
        auto_approve_moderate=True,
        auto_approve_dangerous=True,
    )
    rt = TeamRuntime(project_root, settings=settings, auto_approve=True)
    planned = await rt.plan("Add authentication")
    assert planned.ok
    cost = rt.session_cost(planned.session_id)
    assert cost["tokens_in"] > 0
    assert cost["cost_usd"] > 0


def test_approval_gate_defer_and_resolve(project_root: Path, settings: Settings) -> None:
    rt = TeamRuntime(project_root, settings=settings, auto_approve=False, defer_approvals=True)
    with pytest.raises(ApprovalPending) as pending:
        rt.gate.require("rm -rf /tmp/demo-danger", RiskLevel.DANGEROUS, requested_by="coder")
    approval_id = pending.value.approval.id
    assert pending.value.approval.status == "pending"

    resolved = rt.resolve_approval(approval_id, approved=True, reason="ok for test")
    assert resolved["status"] == "approved"

    # Retry consumes the API approval once.
    again = rt.gate.require("rm -rf /tmp/demo-danger", RiskLevel.DANGEROUS, requested_by="coder")
    assert again.status == "approved"
    assert again.decided_by.startswith("reuse:")


def test_api_approvals_and_cost_endpoints(project_root: Path) -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4o",
        auto_approve_moderate=True,
        auto_approve_dangerous=True,
    )
    app = create_app(project_root, settings)
    client = TestClient(app)

    # Seed a pending approval via gate
    rt = TeamRuntime(project_root, settings=settings, auto_approve=False, defer_approvals=True)
    with pytest.raises(ApprovalPending) as pending:
        rt.gate.require("git push origin main", RiskLevel.DANGEROUS, requested_by="coder")
    approval_id = pending.value.approval.id

    listed = client.get("/approvals", params={"status": "pending"}).json()
    assert any(row["id"] == approval_id for row in listed)

    decided = client.post(f"/approvals/{approval_id}", json={"approved": True, "reason": "ship it"}).json()
    assert decided["status"] == "approved"
    assert decided["decided_by"] == "api"

    got = client.get(f"/approvals/{approval_id}").json()
    assert got["status"] == "approved"

    # Plan via API then check cost endpoint
    created = client.post("/tasks", json={"title": "Add authentication"}).json()
    run = client.post(
        f"/tasks/{created['task_key']}/run",
        json={"command": "plan", "prompt": "Add authentication", "yes": True},
    ).json()
    assert run["ok"] is True
    cost = client.get(f"/sessions/{run['session_id']}/cost").json()
    assert cost["cost_usd"] > 0
    traces = client.get(f"/sessions/{run['session_id']}/traces").json()
    assert any(row.get("cost_usd", 0) for row in traces if row["step"] == "agent_response")


def test_mock_provider_still_builds_without_keys() -> None:
    settings = Settings(provider="openai", model="gpt-4o", openai_api_key="")
    provider = build_provider(settings, "manager")
    assert isinstance(provider, MockProvider)
