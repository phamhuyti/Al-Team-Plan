"""Minimal MCP stdio server exposing filesystem, git, and shell tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ai_team.tools.docker import DockerTools
from ai_team.tools.filesystem import FilesystemTools
from ai_team.tools.git import GitTools
from ai_team.tools.registry import ToolRegistry
from ai_team.tools.shell import ShellTools


def build_registry(root: Path) -> ToolRegistry:
    return ToolRegistry(
        fs=FilesystemTools(root),
        git=GitTools(root),
        shell=ShellTools(root),
        docker=DockerTools(root),
    )


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(registry: ToolRegistry, message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "ai-team-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        tools = []
        for spec in registry.list_tools():
            properties = {key: {"type": value} for key, value in spec["inputSchema"].items()}
            tools.append(
                {
                    "name": spec["name"],
                    "description": spec["description"],
                    "inputSchema": {"type": "object", "properties": properties},
                }
            )
        return _result(request_id, {"tools": tools})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            output = registry.call(name, arguments)
        except Exception as exc:  # noqa: BLE001 — MCP must return tool errors
            return _result(
                request_id,
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            )
        text = output if isinstance(output, str) else json.dumps(output, default=str)
        return _result(request_id, {"content": [{"type": "text", "text": text}]})
    if request_id is None:
        return None
    return _error(request_id, -32601, f"Unknown method: {method}")


def serve_stdio(root: Path | None = None) -> None:
    registry = build_registry(Path(root or ".").resolve())
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(registry, message)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
