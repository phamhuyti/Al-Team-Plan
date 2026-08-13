"""Permission levels: SAFE (auto), MODERATE (manager), DANGEROUS (user)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"


SAFE_GIT = {"status", "diff", "log", "show", "branch", "rev-parse", "ls-files"}
MODERATE_GIT = {"add", "commit", "checkout", "switch", "restore", "stash", "merge"}
DANGEROUS_GIT = {"push", "reset", "rebase", "clean", "filter-branch"}

DANGEROUS_SHELL = [
    re.compile(r"\bdocker\s+compose\s+down\s+[^\n]*-v\b", re.I),
    re.compile(r"\bdocker\s+compose\s+down\s+[^\n]*--volumes\b", re.I),
    re.compile(r"\brm\s+-[^\n]*r[^\n]*f\b", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\s+if=", re.I),
    re.compile(r"\bdrop\s+(database|table|schema)\b", re.I),
    re.compile(r"\btruncate\b", re.I),
    re.compile(r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;", re.I),
    re.compile(r"\bshutdown\b", re.I),
    re.compile(r"\breboot\b", re.I),
    re.compile(r"\bcurl\b.+\|\s*(sh|bash)\b", re.I),
    re.compile(r"\bgit\s+push\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bkubectl\s+delete\b", re.I),
]

MODERATE_SHELL = [
    re.compile(r"\bpip\s+install\b", re.I),
    re.compile(r"\bnpm\s+install\b", re.I),
    re.compile(r"\bapt(-get)?\s+install\b", re.I),
    re.compile(r"\bdocker\s+build\b", re.I),
    re.compile(r"\bdocker\s+compose\b", re.I),
    re.compile(r"\balembic\s+upgrade\b", re.I),
    re.compile(r"\bchmod\b", re.I),
    re.compile(r"\bchown\b", re.I),
]


def classify_git(args: list[str]) -> RiskLevel:
    if not args:
        return RiskLevel.SAFE
    cmd = args[0].lstrip("-")
    if cmd in DANGEROUS_GIT or "--force" in args or "-f" in args:
        return RiskLevel.DANGEROUS
    if cmd in MODERATE_GIT:
        return RiskLevel.MODERATE
    if cmd in SAFE_GIT:
        return RiskLevel.SAFE
    return RiskLevel.MODERATE


def classify_shell(command: str) -> RiskLevel:
    for pat in DANGEROUS_SHELL:
        if pat.search(command):
            return RiskLevel.DANGEROUS
    for pat in MODERATE_SHELL:
        if pat.search(command):
            return RiskLevel.MODERATE
    return RiskLevel.SAFE


def classify_filesystem(action: str) -> RiskLevel:
    action = action.lower()
    if action in {"read", "list", "search", "stat"}:
        return RiskLevel.SAFE
    if action in {"write", "create", "modify", "mkdir"}:
        return RiskLevel.MODERATE
    if action in {"delete", "rm", "unlink", "rmdir"}:
        return RiskLevel.DANGEROUS
    return RiskLevel.MODERATE


def classify_tool(name: str, arguments: dict[str, Any]) -> RiskLevel:
    if name in {"fs_read", "fs_list", "fs_search", "code_search"}:
        return RiskLevel.SAFE
    if name in {"fs_write", "fs_mkdir"}:
        return RiskLevel.MODERATE
    if name in {"fs_delete"}:
        return RiskLevel.DANGEROUS
    if name == "git":
        return classify_git(list(arguments.get("args") or []))
    if name in {"shell", "terminal"}:
        return classify_shell(str(arguments.get("command") or ""))
    if name == "docker":
        cmd = str(arguments.get("command") or "")
        return classify_shell(f"docker {cmd}")
    return RiskLevel.MODERATE
