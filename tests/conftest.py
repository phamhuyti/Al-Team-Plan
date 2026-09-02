"""Shared fixtures. V1 tests use the mock provider so they do not need API keys."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_team.config import Settings
from ai_team.orchestration.workflow import TeamRuntime, init_project


@pytest.fixture(autouse=True)
def _mock_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_TEAM_PROVIDER", "mock")
    monkeypatch.setenv("AI_TEAM_AUTO_APPROVE_MODERATE", "true")
    monkeypatch.setenv("AI_TEAM_AUTO_APPROVE_DANGEROUS", "true")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        provider="mock",
        model="mock",
        auto_approve_moderate=True,
        auto_approve_dangerous=True,
        web_search_enabled=True,
        web_search_backend="mock",
    )


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    init_project(root, name="demo", purpose="Test project for AI-Team")
    return root


@pytest.fixture
def runtime(project_root: Path, settings: Settings) -> TeamRuntime:
    return TeamRuntime(project_root, settings=settings, auto_approve=True)
