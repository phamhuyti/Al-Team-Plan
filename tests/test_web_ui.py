"""Phase 7 Web UI API surface tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ai_team.api.app import create_app
from ai_team.config import Settings


def test_dashboard_and_tasks_list(project_root, settings: Settings) -> None:
    app = create_app(project_root, settings)
    client = TestClient(app)

    dash = client.get("/dashboard").json()
    assert "cost_usd" in dash
    assert "pending_approvals" in dash
    assert dash["routing_strategy"] in {"balanced", "cost_optimized", "quality"}

    created = client.post("/tasks", json={"title": "UI task"}).json()
    tasks = client.get("/tasks").json()
    assert any(t["task_key"] == created["task_key"] for t in tasks)


def test_routing_preview_endpoint(project_root, settings: Settings) -> None:
    client = TestClient(create_app(project_root, settings))
    preview = client.get("/routing/preview", params={"prompt": "fix typo"}).json()
    assert preview["tier"] == "simple"
    assert "routes" in preview


def test_chat_endpoint(project_root, settings: Settings) -> None:
    client = TestClient(create_app(project_root, settings))
    result = client.post("/chat", json={"mode": "research", "message": "Redis vs RabbitMQ", "yes": True}).json()
    assert result["ok"] is True
    assert result["session_id"] > 0
    assert result["details"].get("web_search")


def test_ui_static_assets(project_root, settings: Settings) -> None:
    client = TestClient(create_app(project_root, settings))
    index = client.get("/")
    assert index.status_code == 200
    assert "AI-Team" in index.text
    css = client.get("/ui/styles.css")
    assert css.status_code == 200
    js = client.get("/ui/app.js")
    assert js.status_code == 200
