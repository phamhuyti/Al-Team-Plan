"""Phase 7 Web UI static assets."""

from pathlib import Path


def static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"
