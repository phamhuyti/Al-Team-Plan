from pathlib import Path

from ai_team.memory.project import DecisionRecord, ProjectMemory


def test_init_and_decision_and_tasks(project_root: Path) -> None:
    memory = ProjectMemory(project_root)
    assert memory.exists()
    memory.upsert_task("TASK-001", "Auth", "planned", "Add authentication")
    memory.append_decision(
        DecisionRecord(
            title="Use sessions",
            decision="Cookie sessions for V1",
            reason="Simplest option",
            alternatives=["JWT"],
            rejected=["JWT"],
            risks=["CSRF"],
            consequences=["Need CSRF token"],
            task_key="TASK-001",
            confidence=0.8,
        )
    )
    tasks = memory.list_tasks()
    assert tasks[0]["task_key"] == "TASK-001"
    assert "Cookie sessions" in memory.read("DECISIONS.md")
    assert (project_root / ".ai" / "agents" / "manager.md").exists()
