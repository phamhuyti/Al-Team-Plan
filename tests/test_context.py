from pathlib import Path

from ai_team.context.engine import ContextEngine
from ai_team.memory.project import ProjectMemory


def test_context_includes_project_memory_not_everything(project_root: Path) -> None:
    src = project_root / "src" / "auth.py"
    src.write_text("def login():\n    return True\n", encoding="utf-8")
    noise = project_root / "src" / "unrelated.py"
    noise.write_text("print('hello')\n", encoding="utf-8")

    engine = ContextEngine(project_root, ProjectMemory(project_root))
    bundle = engine.build("Fix authentication login flow")
    rendered = bundle.render()

    assert "PROJECT.md" in rendered
    assert "auth.py" in rendered
    assert bundle.project_md
    assert len(rendered) < 80_000
