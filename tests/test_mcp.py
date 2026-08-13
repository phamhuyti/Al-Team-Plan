from pathlib import Path

from ai_team.mcp.server import build_registry, handle
from ai_team.tools.git import GitTools


def test_mcp_list_and_read(project_root: Path) -> None:
    registry = build_registry(project_root)
    listed = handle(registry, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert {"fs_read", "fs_write", "git", "shell"} <= names

    reply = handle(
        registry,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "fs_read", "arguments": {"path": ".ai/PROJECT.md"}},
        },
    )
    assert reply is not None
    assert "Purpose" in reply["result"]["content"][0]["text"]


def test_git_branch_convention(project_root: Path) -> None:
    git = GitTools(project_root)
    git.ensure_identity()
    git.create_branch("ai/task-001-authentication")
    assert git.current_branch() == "ai/task-001-authentication"
