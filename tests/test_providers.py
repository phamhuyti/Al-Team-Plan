"""V1 hardening: optional provider HTTP adapters (mocked, no live keys)."""

from __future__ import annotations

import json

import httpx
import pytest

from ai_team.agents.contracts import ManagerPlan
from ai_team.models.anthropic import AnthropicProvider
from ai_team.models.base import ChatMessage
from ai_team.models.google import GoogleProvider
from ai_team.models.openrouter import OpenRouterProvider


def _manager_plan_json() -> str:
    return json.dumps(
        {
            "understanding": "Add auth",
            "tasks": ["design", "implement"],
            "chosen_agents": ["architect", "coder"],
            "questions": [],
            "risks": [],
            "next_action": "plan",
        }
    )


def _patch_async_client(monkeypatch: pytest.MonkeyPatch, module: str, transport: httpx.MockTransport) -> None:
    real_client = httpx.AsyncClient

    def factory(**kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_client(**kwargs)

    monkeypatch.setattr(f"{module}.httpx.AsyncClient", factory)


@pytest.mark.asyncio
async def test_anthropic_provider_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "sk-ant-test"
        return httpx.Response(
            200,
            json={
                "id": "msg_1",
                "model": "claude-sonnet-4-5",
                "content": [{"type": "text", "text": _manager_plan_json()}],
                "usage": {"input_tokens": 120, "output_tokens": 80},
            },
        )

    transport = httpx.MockTransport(handler)
    provider = AnthropicProvider(model="claude-sonnet-4-5", api_key="sk-ant-test")
    _patch_async_client(monkeypatch, "ai_team.models.anthropic", transport)
    result = await provider.generate(
        [ChatMessage(role="user", content="Plan auth")],
        response_schema=ManagerPlan,
    )
    assert isinstance(result.parsed, ManagerPlan)
    assert result.tokens_in == 120
    assert result.tokens_out == 80


@pytest.mark.asyncio
async def test_google_provider_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "key=google-test" in str(request.url)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": _manager_plan_json()}]}}],
                "usageMetadata": {"promptTokenCount": 90, "candidatesTokenCount": 70},
            },
        )

    transport = httpx.MockTransport(handler)
    provider = GoogleProvider(model="gemini-2.0-flash", api_key="google-test")
    _patch_async_client(monkeypatch, "ai_team.models.google", transport)
    result = await provider.generate(
        [ChatMessage(role="user", content="Plan auth")],
        response_schema=ManagerPlan,
    )
    assert isinstance(result.parsed, ManagerPlan)
    assert result.tokens_in == 90


@pytest.mark.asyncio
async def test_openrouter_provider_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer or-test"
        return httpx.Response(
            200,
            json={
                "id": "or_1",
                "model": "anthropic/claude-sonnet-4-5",
                "choices": [{"message": {"content": _manager_plan_json()}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 60},
            },
        )

    transport = httpx.MockTransport(handler)
    provider = OpenRouterProvider(model="anthropic/claude-sonnet-4-5", api_key="or-test")
    _patch_async_client(monkeypatch, "ai_team.models.openrouter", transport)
    result = await provider.generate(
        [ChatMessage(role="user", content="Plan auth")],
        response_schema=ManagerPlan,
    )
    assert isinstance(result.parsed, ManagerPlan)
    assert result.tokens_out == 60
