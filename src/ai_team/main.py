"""CLI: init, ask, research, debate, plan, implement, review, status, serve, mcp."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ai_team import __version__
from ai_team.config import load_settings
from ai_team.orchestration.workflow import TeamRuntime, init_project

app = typer.Typer(name="ai-team", help="Multi-agent AI development team", no_args_is_help=True)
console = Console()


def _root(project: Optional[Path]) -> Path:
    return (project or Path.cwd()).resolve()


def _runtime(project: Optional[Path], yes: bool = False) -> TeamRuntime:
    settings = load_settings()
    return TeamRuntime(_root(project), settings=settings, auto_approve=yes)


@app.callback()
def _version_callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    if version:
        console.print(f"ai-team {__version__}")
        raise typer.Exit()


@app.command("init")
def init_cmd(
    path: Path = typer.Argument(Path("."), help="Project directory"),
    name: Optional[str] = typer.Option(None, "--name", help="Project name"),
    purpose: str = typer.Option("", "--purpose", help="Project purpose"),
) -> None:
    """Create .ai/ shared memory and a git repository."""
    memory = init_project(path, name=name, purpose=purpose)
    console.print(f"Initialized AI-Team project at {memory.root}")
    console.print(f"Shared memory: {memory.ai}")


@app.command("ask")
def ask_cmd(
    prompt: str = typer.Argument(..., help="Question or request"),
    project: Optional[Path] = typer.Option(None, "--project", "-p"),
    yes: bool = typer.Option(False, "--yes", help="Auto-approve moderate/dangerous actions"),
) -> None:
    """Ask the Manager to coordinate a design/research answer."""
    runtime = _runtime(project, yes)
    result = asyncio.run(runtime.ask(prompt))
    _print_result(result)


@app.command("research")
def research_cmd(
    topic: str = typer.Argument(...),
    project: Optional[Path] = typer.Option(None, "--project", "-p"),
) -> None:
    """Run the Researcher agent."""
    runtime = _runtime(project)
    result = asyncio.run(runtime.research(topic))
    _print_result(result)


@app.command("debate")
def debate_cmd(
    question: str = typer.Argument(...),
    project: Optional[Path] = typer.Option(None, "--project", "-p"),
) -> None:
    """Force a multi-agent debate and Judge decision."""
    runtime = _runtime(project)
    result = asyncio.run(runtime.debate(question, force=True))
    _print_result(result)


@app.command("plan")
def plan_cmd(
    request: str = typer.Argument(...),
    project: Optional[Path] = typer.Option(None, "--project", "-p"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    """Create a task and run Manager → Architect → Researcher → Red Team → Decision."""
    runtime = _runtime(project, yes)
    result = asyncio.run(runtime.plan(request))
    console.print(f"[bold]{result.task_key}[/bold] {result.summary}")
    _print_result(result)


@app.command("implement")
def implement_cmd(
    task_key: str = typer.Argument(..., help="Task id such as TASK-001"),
    project: Optional[Path] = typer.Option(None, "--project", "-p"),
    yes: bool = typer.Option(False, "--yes", help="Auto-approve moderate/dangerous actions"),
) -> None:
    """Coder → tests → Reviewer → Red Team → Manager approval → git commit."""
    runtime = _runtime(project, yes)
    result = asyncio.run(runtime.implement(task_key))
    _print_result(result)


@app.command("review")
def review_cmd(
    task_key: str = typer.Argument(...),
    project: Optional[Path] = typer.Option(None, "--project", "-p"),
) -> None:
    """Reviewer + Red Team pass over a task."""
    runtime = _runtime(project)
    result = asyncio.run(runtime.review_task(task_key))
    _print_result(result)


@app.command("status")
def status_cmd(project: Optional[Path] = typer.Option(None, "--project", "-p")) -> None:
    """Show tasks, agents, and recent sessions."""
    runtime = _runtime(project)
    table = Table(title="Tasks")
    table.add_column("Key")
    table.add_column("Status")
    table.add_column("Title")
    for task in runtime.list_tasks():
        table.add_row(task["task_key"], task["status"], task["title"])
    console.print(table)

    agents = Table(title="Agents")
    agents.add_column("Role")
    agents.add_column("Provider")
    agents.add_column("Model")
    for agent in runtime.list_agents():
        agents.add_row(agent["role"], agent["provider"], agent["model"])
    console.print(agents)

    sessions = Table(title="Sessions")
    sessions.add_column("ID")
    sessions.add_column("Kind")
    sessions.add_column("Status")
    for session in runtime.list_sessions()[:10]:
        sessions.add_row(str(session["id"]), session["kind"], session["status"])
    console.print(sessions)


@app.command("serve")
def serve_cmd(
    host: Optional[str] = typer.Option(None),
    port: Optional[int] = typer.Option(None),
    project: Optional[Path] = typer.Option(None, "--project", "-p"),
) -> None:
    """Start the HTTP API."""
    import uvicorn

    from ai_team.api.app import create_app

    settings = load_settings()
    uvicorn.run(
        create_app(_root(project), settings),
        host=host or settings.api_host,
        port=port or settings.api_port,
        log_level=settings.log_level.lower(),
    )


@app.command("mcp")
def mcp_cmd(project: Optional[Path] = typer.Option(None, "--project", "-p")) -> None:
    """Run the V1 MCP stdio server (filesystem, git, shell)."""
    from ai_team.mcp.server import serve_stdio

    serve_stdio(_root(project))


def _print_result(result) -> None:
    color = "green" if result.ok else "red"
    console.print(f"[{color}]{'OK' if result.ok else 'FAILED'}[/{color}] session={result.session_id}")
    if result.task_key:
        console.print(f"Task: {result.task_key}")
    console.print(result.summary)
    if result.details:
        console.print_json(data=_jsonable(result.details))


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


if __name__ == "__main__":
    app()
