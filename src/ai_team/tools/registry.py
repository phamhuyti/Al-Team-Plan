"""MCP-style tool registry used by agents. V1: filesystem, git, shell."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ai_team.security.permissions import RiskLevel, classify_tool
from ai_team.tools.docker import DockerTools
from ai_team.tools.filesystem import FilesystemTools
from ai_team.tools.git import GitTools
from ai_team.tools.shell import ShellTools


@dataclass
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., Any]
    schema: dict[str, Any]


class ToolRegistry:
    def __init__(
        self,
        fs: FilesystemTools,
        git: GitTools,
        shell: ShellTools,
        docker: DockerTools | None = None,
    ) -> None:
        self.fs = fs
        self.git = git
        self.shell = shell
        self.docker = docker
        self._tools: dict[str, ToolSpec] = {}
        self._register_v1()

    def _register_v1(self) -> None:
        self.register(
            "fs_read",
            "Read a UTF-8 file relative to the project root.",
            lambda path, max_chars=40000: self.fs.read(path, max_chars=max_chars),
            {"path": "string", "max_chars": "integer"},
        )
        self.register(
            "fs_write",
            "Create or overwrite a UTF-8 file relative to the project root.",
            lambda path, content: self.fs.write(path, content),
            {"path": "string", "content": "string"},
        )
        self.register(
            "fs_list",
            "List files in a directory.",
            lambda path=".": self.fs.list_dir(path),
            {"path": "string"},
        )
        self.register(
            "fs_search",
            "Search file contents and paths for a query.",
            lambda query, glob="*": self.fs.search(query, glob=glob),
            {"query": "string", "glob": "string"},
        )
        self.register(
            "fs_delete",
            "Delete a file or empty directory.",
            lambda path: self.fs.delete(path),
            {"path": "string"},
        )
        self.register(
            "git",
            "Run a git command. args is a list such as ['status'] or ['checkout', '-b', 'ai/TASK-1'].",
            lambda args: self.git.run(list(args)),
            {"args": "array"},
        )
        self.register(
            "shell",
            "Run a non-interactive shell command in the project root.",
            lambda command: self.shell.run(command),
            {"command": "string"},
        )
        if self.docker is not None:
            self.register(
                "docker",
                "Run a docker CLI command.",
                lambda command: self.docker.run(command),
                {"command": "string"},
            )

    def register(self, name: str, description: str, handler: Callable[..., Any], schema: dict[str, Any]) -> None:
        self._tools[name] = ToolSpec(name, description, handler, schema)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": spec.name, "description": spec.description, "inputSchema": spec.schema}
            for spec in self._tools.values()
        ]

    def classify(self, name: str, arguments: dict[str, Any]) -> RiskLevel:
        return classify_tool(name, arguments)

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name].handler(**arguments)
