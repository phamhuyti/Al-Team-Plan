"""Task-scoped context. Never dump the whole codebase into a prompt."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ai_team.memory.project import ProjectMemory
from ai_team.tools.filesystem import FilesystemTools
from ai_team.tools.git import GitTools

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "have",
    "will", "should", "could", "about", "please", "them", "they", "then", "than",
}


@dataclass
class ContextBundle:
    task: str
    project_md: str = ""
    rules_md: str = ""
    decisions_md: str = ""
    tasks_md: str = ""
    files: list[tuple[str, str]] = field(default_factory=list)
    git_diff: str = ""
    tests: list[tuple[str, str]] = field(default_factory=list)
    discussions: str = ""

    def render(self, budget: int = 80_000) -> str:
        parts = [
            "# Task\n" + self.task,
            "# PROJECT.md\n" + self.project_md,
            "# RULES.md\n" + self.rules_md,
            "# DECISIONS.md\n" + _tail(self.decisions_md, 8_000),
            "# TASKS.md\n" + _tail(self.tasks_md, 6_000),
        ]
        if self.git_diff.strip():
            parts.append("# Git diff\n" + _tail(self.git_diff, 8_000))
        if self.discussions.strip():
            parts.append("# Recent discussions\n" + _tail(self.discussions, 4_000))
        for path, content in self.files:
            parts.append(f"# File {path}\n{content}")
        for path, content in self.tests:
            parts.append(f"# Test {path}\n{content}")
        rendered = "\n\n".join(part for part in parts if part.strip())
        if len(rendered) > budget:
            return rendered[:budget] + "\n...[context truncated]..."
        return rendered


class ContextEngine:
    def __init__(self, root: Path, memory: ProjectMemory, max_chars: int = 80_000) -> None:
        self.root = Path(root).resolve()
        self.memory = memory
        self.fs = FilesystemTools(self.root)
        self.git = GitTools(self.root)
        self.max_chars = max_chars

    def build(self, task: str) -> ContextBundle:
        keywords = _keywords(task)
        files = self._relevant_files(keywords, prefer="src")
        tests = self._relevant_files(keywords, prefer="tests")
        diff = ""
        if self.git.is_repo():
            try:
                diff = self.git.diff()
            except Exception:  # noqa: BLE001
                diff = ""
        discussions = self._recent_discussions()
        return ContextBundle(
            task=task,
            project_md=self.memory.read("PROJECT.md"),
            rules_md=self.memory.read("RULES.md"),
            decisions_md=self.memory.read("DECISIONS.md"),
            tasks_md=self.memory.read("TASKS.md"),
            files=files,
            tests=tests,
            git_diff=diff,
            discussions=discussions,
        )

    def _relevant_files(self, keywords: list[str], prefer: str, limit: int = 8) -> list[tuple[str, str]]:
        ranked: list[tuple[int, Path]] = []
        base = self.root / prefer
        if not base.exists():
            base = self.root
        skip = {".git", ".venv", "node_modules", "__pycache__", ".ai"}
        for path in base.rglob("*"):
            if not path.is_file() or any(part in skip for part in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".md", ".ts", ".js", ".yml", ".yaml", ".toml", ".txt", ".json"}:
                continue
            rel = str(path.relative_to(self.root)).lower()
            score = 0
            for word in keywords:
                if word in rel:
                    score += 5
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            lower = text.lower()
            for word in keywords:
                score += lower.count(word)
            if score:
                ranked.append((score, path))
        ranked.sort(key=lambda item: item[0], reverse=True)
        out: list[tuple[str, str]] = []
        for _, path in ranked[:limit]:
            rel = str(path.relative_to(self.root))
            try:
                content = self.fs.read(rel, max_chars=6_000)
            except OSError:
                continue
            out.append((rel, content))
        return out

    def _recent_discussions(self, limit: int = 3) -> str:
        folder = self.memory.ai / "discussions"
        if not folder.exists():
            return ""
        files = sorted(folder.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        chunks = []
        for path in files[:limit]:
            chunks.append(f"## {path.name}\n{path.read_text(encoding='utf-8')[:2000]}")
        return "\n\n".join(chunks)


def _keywords(task: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_-]{3,}", task.lower())
    seen: list[str] = []
    for word in words:
        if word in STOPWORDS or word in seen:
            continue
        seen.append(word)
    return seen[:12]


def _tail(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    return text[-n:]
