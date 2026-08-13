"""Resolve package, prompt, and template locations."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
REPO_ROOT = SRC_DIR.parent


def _first_existing(*candidates: Path) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def prompts_dir() -> Path:
    return _first_existing(
        REPO_ROOT / "prompts",
        Path("/app/prompts"),
        PACKAGE_DIR / "prompts",
        Path.cwd() / "prompts",
    )


def templates_dir() -> Path:
    return _first_existing(
        REPO_ROOT / "templates",
        Path("/app/templates"),
        PACKAGE_DIR / "templates",
        Path.cwd() / "templates",
    )


def load_prompt(name: str) -> str:
    path = prompts_dir() / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")
