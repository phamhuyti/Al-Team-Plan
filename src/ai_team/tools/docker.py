"""Docker CLI wrapper. Volume-destructive commands are DANGEROUS."""

from __future__ import annotations

from pathlib import Path

from ai_team.tools.shell import ShellTools


class DockerTools:
    def __init__(self, root: Path) -> None:
        self.shell = ShellTools(root)

    def run(self, command: str) -> str:
        if not command.startswith("docker"):
            command = f"docker {command}"
        return self.shell.run(command)
