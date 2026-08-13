from typer.testing import CliRunner

from ai_team.main import app


def test_cli_init_and_status(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(tmp_path / "app"), "--name", "demo", "--purpose", "demo app"])
    assert result.exit_code == 0, result.output
    status = runner.invoke(app, ["status", "--project", str(tmp_path / "app")])
    assert status.exit_code == 0, status.output
    assert "manager" in status.output
