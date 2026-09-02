"""Researcher web search tool + MCP registration."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_team.config import Settings
from ai_team.mcp.server import build_registry, handle
from ai_team.orchestration.workflow import TeamRuntime
from ai_team.security.permissions import RiskLevel, classify_tool
from ai_team.tools.web import WebSearchTools, mock_search


def test_web_search_classified_safe() -> None:
    assert classify_tool("web_search", {"query": "redis"}) is RiskLevel.SAFE


def test_mock_backend_returns_hits() -> None:
    web = WebSearchTools(enabled=True, backend="mock")
    hits = web.search("Redis vs RabbitMQ", max_results=2)
    assert len(hits) == 2
    assert hits[0]["url"].startswith("https://")
    evidence = web.format_evidence(hits)
    assert evidence
    assert any("Overview" in line or "Comparison" in line for line in evidence)


def test_off_backend_returns_empty() -> None:
    web = WebSearchTools(enabled=True, backend="off")
    assert web.search("anything") == []
    disabled = WebSearchTools(enabled=False, backend="mock")
    assert disabled.search("anything") == []


def test_custom_fetcher() -> None:
    web = WebSearchTools(fetcher=lambda q, n: [{"title": q, "url": "https://x.test", "snippet": "s"}][:n])
    hits = web.search("auth", max_results=1)
    assert hits == [{"title": "auth", "url": "https://x.test", "snippet": "s"}]


def test_mcp_exposes_web_search(project_root: Path) -> None:
    registry = build_registry(project_root, web_enabled=True, web_backend="mock")
    listed = handle(registry, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert "web_search" in names

    reply = handle(
        registry,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "web_search", "arguments": {"query": "authentication", "max_results": 1}},
        },
    )
    assert reply is not None
    assert "example.com" in reply["result"]["content"][0]["text"]


@pytest.mark.asyncio
async def test_research_uses_web_search(project_root: Path) -> None:
    settings = Settings(
        provider="mock",
        model="mock",
        auto_approve_moderate=True,
        auto_approve_dangerous=True,
        web_search_enabled=True,
        web_search_backend="mock",
    )
    rt = TeamRuntime(project_root, settings=settings, auto_approve=True)
    result = await rt.research("Redis vs RabbitMQ")
    assert result.ok
    assert result.details["web_search"]
    assert result.details["web_search"][0]["url"].startswith("https://")

    # Trace should record the tool call
    replay = rt.replay_session(result.session_id)
    tool_steps = [row for row in replay["timeline"] if row["step"] == "tool_call" and row["actor"] == "researcher"]
    assert tool_steps


def test_mock_search_helper() -> None:
    hits = mock_search("queues", max_results=1)
    assert len(hits) == 1
    assert "queues" in hits[0]["title"].lower() or "queues" in hits[0]["snippet"].lower()
