"""HTTP API for later UI/Cursor/automation integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_team.config import Settings, load_settings
from ai_team.orchestration.workflow import TeamRuntime, init_project


class ProjectCreate(BaseModel):
    path: str
    name: str | None = None
    purpose: str = ""


class TaskCreate(BaseModel):
    title: str
    description: str = ""


class RunBody(BaseModel):
    command: str = Field(default="implement", description="implement | plan | review | ask | research | debate")
    prompt: str = ""
    yes: bool = True


def create_app(root: Path | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    default_root = (root or Path.cwd()).resolve()
    app = FastAPI(title="AI-Team", version="0.1.0")

    def runtime(path: Path | None = None, yes: bool = True) -> TeamRuntime:
        return TeamRuntime(path or default_root, settings=settings, auto_approve=yes)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/projects")
    def create_project(body: ProjectCreate) -> dict[str, Any]:
        memory = init_project(Path(body.path), name=body.name, purpose=body.purpose)
        rt = runtime(memory.root)
        return {"name": memory.root.name, "path": str(memory.root), "id": rt.project_row.id}

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        rt = runtime()
        return {"current": str(rt.root), "id": rt.project_row.id}

    @app.post("/tasks")
    def create_task(body: TaskCreate) -> dict[str, Any]:
        rt = runtime()
        task = rt.create_task(body.title, body.description)
        return {"task_key": task.task_key, "title": task.title, "status": task.status}

    @app.get("/tasks/{task_key}")
    def get_task(task_key: str) -> dict[str, Any]:
        rt = runtime()
        task = rt.get_task(task_key)
        if task is None:
            raise HTTPException(404, f"Unknown task {task_key}")
        return {
            "task_key": task.task_key,
            "title": task.title,
            "status": task.status,
            "description": task.description,
        }

    @app.post("/tasks/{task_key}/run")
    async def run_task(task_key: str, body: RunBody) -> dict[str, Any]:
        rt = runtime(yes=body.yes)
        if body.command == "implement":
            result = await rt.implement(task_key)
        elif body.command == "review":
            result = await rt.review_task(task_key)
        elif body.command == "plan":
            result = await rt.plan(body.prompt or task_key)
        else:
            raise HTTPException(400, f"Unsupported command {body.command}")
        return {"ok": result.ok, "summary": result.summary, "details": result.details, "session_id": result.session_id}

    @app.post("/tasks/{task_key}/debate")
    async def debate_task(task_key: str, body: RunBody) -> dict[str, Any]:
        rt = runtime(yes=body.yes)
        result = await rt.debate(body.prompt or task_key, force=True)
        return {"ok": result.ok, "summary": result.summary, "details": result.details, "session_id": result.session_id}

    @app.get("/agents")
    def agents() -> list[dict[str, str]]:
        return runtime().list_agents()

    @app.get("/sessions")
    def sessions() -> list[dict[str, Any]]:
        return runtime().list_sessions()

    @app.get("/decisions")
    def decisions() -> list[dict[str, Any]]:
        return runtime().list_decisions()

    @app.get("/sessions/{session_id}/traces")
    def traces(session_id: int) -> list[dict[str, Any]]:
        from ai_team.memory.database import TraceEvent

        rt = runtime()
        with rt.db.session() as s:
            rows = (
                s.query(TraceEvent)
                .filter(TraceEvent.session_id == session_id)
                .order_by(TraceEvent.id.asc())
                .all()
            )
            return [
                {
                    "id": row.id,
                    "step": row.step,
                    "actor": row.actor,
                    "tokens_in": row.tokens_in,
                    "tokens_out": row.tokens_out,
                    "payload": row.payload,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]

    return app
