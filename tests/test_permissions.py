from ai_team.security.permissions import RiskLevel, classify_filesystem, classify_git, classify_shell, classify_tool


def test_safe_reads() -> None:
    assert classify_filesystem("read") is RiskLevel.SAFE
    assert classify_git(["status"]) is RiskLevel.SAFE
    assert classify_shell("python -m pytest -q") is RiskLevel.SAFE
    assert classify_tool("fs_search", {"query": "auth"}) is RiskLevel.SAFE


def test_moderate_writes_and_installs() -> None:
    assert classify_filesystem("write") is RiskLevel.MODERATE
    assert classify_git(["commit", "-m", "msg"]) is RiskLevel.MODERATE
    assert classify_shell("pip install fastapi") is RiskLevel.MODERATE


def test_dangerous_push_and_volumes() -> None:
    assert classify_git(["push", "origin", "main"]) is RiskLevel.DANGEROUS
    assert classify_shell("docker compose down -v") is RiskLevel.DANGEROUS
    assert classify_shell("rm -rf /data") is RiskLevel.DANGEROUS
    assert classify_tool("fs_delete", {"path": "src/app.py"}) is RiskLevel.DANGEROUS
    assert classify_git(["reset", "--hard"]) is RiskLevel.DANGEROUS
