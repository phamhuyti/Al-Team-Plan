"""Filesystem tools scoped to a project workspace."""

from __future__ import annotations

import os
from pathlib import Path


class PathEscapeError(ValueError):
    pass


class FilesystemTools:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    def resolve(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise PathEscapeError(f"Path escapes workspace: {relative}") from exc
        return path

    def read(self, relative: str, max_chars: int = 40_000) -> str:
        path = self.resolve(relative)
        if not path.is_file():
            raise FileNotFoundError(relative)
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + "\n...[truncated]..."
        return text

    def write(self, relative: str, content: str) -> str:
        path = self.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.relative_to(self.root))

    def delete(self, relative: str) -> str:
        path = self.resolve(relative)
        if path.is_dir():
            path.rmdir()
        else:
            path.unlink()
        return relative

    def mkdir(self, relative: str) -> str:
        path = self.resolve(relative)
        path.mkdir(parents=True, exist_ok=True)
        return relative

    def list_dir(self, relative: str = ".", max_entries: int = 200) -> list[str]:
        path = self.resolve(relative)
        entries = []
        for item in sorted(path.iterdir()):
            suffix = "/" if item.is_dir() else ""
            entries.append(str(item.relative_to(self.root)) + suffix)
            if len(entries) >= max_entries:
                break
        return entries

    def search(self, query: str, glob: str = "*", max_hits: int = 40) -> list[dict[str, str]]:
        hits: list[dict[str, str]] = []
        query_l = query.lower()
        skip_dirs = {".git", ".venv", "node_modules", "__pycache__", ".ai"}
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for name in filenames:
                path = Path(dirpath) / name
                rel = str(path.relative_to(self.root))
                if glob != "*" and not path.match(glob):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if query_l not in text.lower() and query_l not in rel.lower():
                    continue
                line_no = 1
                snippet = ""
                for i, line in enumerate(text.splitlines(), start=1):
                    if query_l in line.lower():
                        line_no = i
                        snippet = line.strip()[:240]
                        break
                hits.append({"path": rel, "line": str(line_no), "snippet": snippet})
                if len(hits) >= max_hits:
                    return hits
        return hits
