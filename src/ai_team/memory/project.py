"""Project markdown memory: PROJECT.md, RULES.md, DECISIONS.md, TASKS.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_team.paths import templates_dir

AI_DIR = ".ai"
MEMORY_FILES = ("PROJECT.md", "RULES.md", "DECISIONS.md", "TASKS.md")
AGENT_FILES = ("manager", "architect", "researcher", "coder", "reviewer", "redteam")


@dataclass
class DecisionRecord:
    title: str
    decision: str
    reason: str
    alternatives: list[str]
    rejected: list[str]
    risks: list[str]
    consequences: list[str]
    task_key: str = ""
    confidence: float = 0.0


class ProjectMemory:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.ai = self.root / AI_DIR

    def exists(self) -> bool:
        return (self.ai / "PROJECT.md").exists()

    def init_structure(self, name: str, purpose: str = "") -> None:
        template = templates_dir() / "project"
        if template.exists():
            _copy_tree(template, self.root)
        else:
            self._create_minimal()

        self.ai.mkdir(parents=True, exist_ok=True)
        (self.ai / "agents").mkdir(exist_ok=True)
        (self.ai / "discussions").mkdir(exist_ok=True)
        (self.ai / "sessions").mkdir(exist_ok=True)
        (self.root / "src").mkdir(exist_ok=True)
        (self.root / "tests").mkdir(exist_ok=True)
        (self.root / "docs").mkdir(exist_ok=True)

        project_md = self.ai / "PROJECT.md"
        if not project_md.exists() or "PROJECT_NAME" in project_md.read_text(encoding="utf-8"):
            project_md.write_text(
                _project_md(name, purpose),
                encoding="utf-8",
            )
        readme = self.root / "README.md"
        if not readme.exists():
            readme.write_text(f"# {name}\n\n{purpose}\n", encoding="utf-8")

    def _create_minimal(self) -> None:
        self.ai.mkdir(parents=True, exist_ok=True)
        (self.ai / "RULES.md").write_text(_rules_md(), encoding="utf-8")
        (self.ai / "DECISIONS.md").write_text("# Decisions\n\n", encoding="utf-8")
        (self.ai / "TASKS.md").write_text("# Tasks\n\n", encoding="utf-8")
        for agent in AGENT_FILES:
            path = self.ai / "agents" / f"{agent}.md"
            path.parent.mkdir(exist_ok=True)
            if not path.exists():
                path.write_text(f"# {agent}\n\nRole notes for this project.\n", encoding="utf-8")

    def read(self, name: str) -> str:
        path = self.ai / name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write(self, name: str, content: str) -> None:
        path = self.ai / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def append_decision(self, record: DecisionRecord) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        block = [
            f"## {record.title}",
            f"- Date: {stamp}",
            f"- Task: {record.task_key or 'n/a'}",
            f"- Decision: {record.decision}",
            f"- Reason: {record.reason}",
            f"- Confidence: {record.confidence}",
            f"- Alternatives: {'; '.join(record.alternatives) or 'none'}",
            f"- Rejected alternatives: {'; '.join(record.rejected) or 'none'}",
            f"- Risks: {'; '.join(record.risks) or 'none'}",
            f"- Consequences: {'; '.join(record.consequences) or 'none'}",
            "",
        ]
        current = self.read("DECISIONS.md") or "# Decisions\n\n"
        self.write("DECISIONS.md", current.rstrip() + "\n\n" + "\n".join(block))

    def upsert_task(self, task_key: str, title: str, status: str, description: str = "") -> None:
        current = self.read("TASKS.md") or "# Tasks\n\n"
        marker = f"### {task_key}"
        entry = (
            f"### {task_key} — {title}\n"
            f"- Status: `{status}`\n"
            f"- Description: {description or title}\n"
        )
        if marker in current:
            lines = current.splitlines()
            out: list[str] = []
            skipping = False
            for line in lines:
                if line.startswith(marker):
                    skipping = True
                    out.append(entry.rstrip())
                    continue
                if skipping and line.startswith("### "):
                    skipping = False
                    out.append(line)
                    continue
                if skipping:
                    continue
                out.append(line)
            current = "\n".join(out) + "\n"
        else:
            current = current.rstrip() + "\n\n" + entry
        self.write("TASKS.md", current)

    def write_session(self, session_id: str, content: str) -> None:
        path = self.ai / "sessions" / f"{session_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_discussion(self, slug: str, content: str) -> None:
        path = self.ai / "discussions" / f"{slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_tasks(self) -> list[dict[str, str]]:
        text = self.read("TASKS.md")
        tasks: list[dict[str, str]] = []
        current: dict[str, str] | None = None
        for line in text.splitlines():
            if line.startswith("### "):
                if current:
                    tasks.append(current)
                heading = line[4:].strip()
                key, _, title = heading.partition("—")
                current = {
                    "task_key": key.strip(),
                    "title": title.strip(),
                    "status": "pending",
                    "description": "",
                }
            elif current and line.startswith("- Status:"):
                current["status"] = line.split("`", 1)[-1].replace("`", "").strip()
            elif current and line.startswith("- Description:"):
                current["description"] = line.split(":", 1)[-1].strip()
        if current:
            tasks.append(current)
        return tasks


def _copy_tree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dest / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")


def _project_md(name: str, purpose: str) -> str:
    return f"""# {name}

## Purpose

{purpose or "To be defined."}

## Architecture

To be defined by the Architect agent.

## Technology stack

- To be decided.

## Constraints

- Prefer simple, testable designs.
- Do not perform destructive actions without approval.

## Coding conventions

- Follow existing project style.
- Keep changes small and reviewable.

## Operational rules

See `RULES.md`.
"""


def _rules_md() -> str:
    return """# Rules

1. Shared project state in `.ai/` is the source of truth.
2. Agents must follow their contracts.
3. SAFE actions may run automatically.
4. MODERATE actions require Manager approval.
5. DANGEROUS actions require user approval.
6. Record every important decision in `DECISIONS.md`.
7. Do not dump the entire codebase into a prompt.
"""
