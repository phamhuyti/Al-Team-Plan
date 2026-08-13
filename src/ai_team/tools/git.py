"""Git checkpoint tools. Push/reset --hard are dangerous."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


class GitTools:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    def run(self, args: list[str], check: bool = True) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if check and result.returncode != 0:
            raise GitError(output.strip() or f"git {' '.join(args)} failed")
        return output.strip()

    def is_repo(self) -> bool:
        return (self.root / ".git").exists()

    def init(self) -> str:
        if self.is_repo():
            return "already a git repository"
        return self.run(["init"])

    def status(self) -> str:
        return self.run(["status", "--porcelain=v1"])

    def diff(self) -> str:
        return self.run(["diff"]) + "\n" + self.run(["diff", "--cached"])

    def current_branch(self) -> str:
        return self.run(["rev-parse", "--abbrev-ref", "HEAD"], check=False) or "main"

    def create_branch(self, name: str) -> str:
        existing = self.run(["branch", "--list", name], check=False)
        if existing.strip():
            self.run(["checkout", name])
            return f"checked out existing {name}"
        self.run(["checkout", "-b", name])
        return f"created {name}"

    def add(self, paths: list[str] | None = None) -> str:
        return self.run(["add", *(paths or ["."])])

    def commit(self, message: str) -> str:
        self.run(["add", "-A"])
        status = self.status()
        if not status:
            return "nothing to commit"
        return self.run(["commit", "-m", message])

    def log(self, n: int = 5) -> str:
        return self.run(["log", f"-{n}", "--oneline"], check=False)

    def ensure_identity(self) -> None:
        name = self.run(["config", "user.name"], check=False)
        email = self.run(["config", "user.email"], check=False)
        if not name:
            self.run(["config", "user.name", "AI-Team"])
        if not email:
            self.run(["config", "user.email", "ai-team@local"])
