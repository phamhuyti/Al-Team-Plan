"""V1 success path: plan → debate/red team → coder → tests → review → commit."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_team.memory.database import TraceEvent
from ai_team.orchestration.workflow import TeamRuntime
from ai_team.tools.git import GitTools


@pytest.mark.asyncio
async def test_plan_and_implement_with_audit(runtime: TeamRuntime, project_root: Path) -> None:
    planned = await runtime.plan("Add authentication")
    assert planned.ok
    assert planned.task_key.startswith("TASK-")
    assert planned.details["redteam"]["should_block"] is False
    assert runtime.list_decisions()

    implemented = await runtime.implement(planned.task_key)
    assert implemented.ok, implemented.summary
    assert (project_root / "src" / "auth.py").exists()
    assert (project_root / "tests" / "test_auth.py").exists()
    assert "ping" in (project_root / "src" / "auth.py").read_text(encoding="utf-8")

    git = GitTools(project_root)
    log = git.log(5)
    assert planned.task_key.lower() in log.lower() or planned.task_key in log or "authentication" in log.lower()

    with runtime.db.session() as session:
        events = (
            session.query(TraceEvent)
            .filter(TraceEvent.session_id == implemented.session_id)
            .all()
        )
    steps = {event.step for event in events}
    assert "task" in steps
    assert "agent_response" in steps
    assert "decision" in steps


@pytest.mark.asyncio
async def test_ask_and_debate(runtime: TeamRuntime) -> None:
    asked = await runtime.ask("Thiết kế authentication")
    assert asked.ok
    debated = await runtime.debate("Redis hay RabbitMQ?")
    assert debated.ok
    assert debated.details["verdict"] is not None
