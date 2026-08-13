"""Non-interactive shell with timeout. Destructive commands are classified elsewhere."""

from __future__ import annotations

import subprocess
from pathlib import Path


class ShellError(RuntimeError):
    pass


class ShellTools:
    def __init__(self, root: Path, timeout: int = 120) -> None:
        self.root = Path(root).resolve()
        self.timeout = timeout

    def run(self, command: str, timeout: int | None = None) -> str:
        try:
            result = subprocess.run(
                command,
                cwd=self.root,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ShellError(f"Command timed out: {command}") from exc
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            raise ShellError(output.strip() or f"exit {result.returncode}")
        return output.strip()
