"""HTTP API for UI/Cursor/automation integration."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_team.config import Settings, load_settings
from ai_team.orchestration.workflow import TeamRuntime, init_project
from ai_team.security.approvals import ApprovalPending
from ai_team.web import static_dir


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


class ChatBody(BaseModel):
    mode: str = Field(default="ask", description="ask | research | debate | plan")
    message: str
    yes: bool = True


class ApprovalDecision(BaseModel):
    approved: bool = True
    reason: str = ""


def create_app(root: Path | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    default_root = (root or Path.cwd()).resolve()
    app = FastAPI(title="AI-Team", version="0.2.0")

    def runtime(path: Path | None = None, yes: bool = True) -> TeamRuntime:
        return TeamRuntime(
            path or default_root,
            settings=settings,
            auto_approve=yes,
            defer_approvals=not yes,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/dashboard")
    def dashboard() -> dict[str, Any]:
        rt = runtime()
        summary = rt.project_cost_summary()
        return {
            **summary,
            "project": str(rt.root),
            "routing_enabled": rt.settings.resolved_routing_enabled(),
            "routing_strategy": rt.settings.resolved_routing_strategy(),
        }

    @app.get("/routing/preview")
    def routing_preview(prompt: str = Query(default="Add authentication")) -> dict[str, Any]:
        rt = runtime()
        return rt.router.routing_snapshot(prompt)

    @app.post("/projects")
    def create_project(body: ProjectCreate) -> dict[str, Any]:
        memory = init_project(Path(body.path), name=body.name, purpose=body.purpose)
        rt = runtime(memory.root)
        return {"name": memory.root.name, "path": str(memory.root), "id": rt.project_row.id}

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        rt = runtime()
        return {
            "current": str(rt.root),
            "id": rt.project_row.id,
            "config": rt.settings.project_config,
        }

    @app.get("/tasks")
    def list_tasks() -> list[dict[str, Any]]:
        return runtime().list_tasks()

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
        try:
            if body.command == "implement":
                result = await rt.implement(task_key)
            elif body.command == "review":
                result = await rt.review_task(task_key)
            elif body.command == "plan":
                result = await rt.plan(body.prompt or task_key)
            else:
                raise HTTPException(400, f"Unsupported command {body.command}")
        except ApprovalPending as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "needs_approval": True,
                    "approval_id": exc.approval.id,
                    "action": exc.approval.action,
                    "risk_level": exc.approval.risk_level,
                    "status": exc.approval.status,
                },
            ) from exc
        payload = {
            "ok": result.ok,
            "summary": result.summary,
            "details": result.details,
            "session_id": result.session_id,
        }
        if result.details.get("pending_approval"):
            payload["needs_approval"] = True
            payload["approval_id"] = result.details["pending_approval"]["id"]
        return payload

    @app.post("/chat")
    async def chat(body: ChatBody) -> dict[str, Any]:
        rt = runtime(yes=body.yes)
        mode = body.mode.lower().strip()
        if mode == "ask":
            result = await rt.ask(body.message)
        elif mode == "research":
            result = await rt.research(body.message)
        elif mode == "debate":
            result = await rt.debate(body.message, force=True)
        elif mode == "plan":
            result = await rt.plan(body.message)
        else:
            raise HTTPException(400, f"Unsupported chat mode {body.mode}")
        return {
            "ok": result.ok,
            "session_id": result.session_id,
            "task_key": result.task_key,
            "summary": result.summary,
            "details": result.details,
        }

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

    @app.get("/approvals")
    def approvals(status: str | None = Query(default=None)) -> list[dict[str, Any]]:
        return runtime().list_approvals(status=status)

    @app.get("/approvals/{approval_id}")
    def get_approval(approval_id: int) -> dict[str, Any]:
        rt = runtime()
        row = rt.gate.get_approval(approval_id)
        if row is None:
            raise HTTPException(404, f"Unknown approval {approval_id}")
        return {
            "id": row.id,
            "action": row.action,
            "risk_level": row.risk_level,
            "status": row.status,
            "requested_by": row.requested_by,
            "decided_by": row.decided_by,
            "reason": row.reason,
            "tool_call_id": row.tool_call_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @app.post("/approvals/{approval_id}")
    def decide_approval(approval_id: int, body: ApprovalDecision) -> dict[str, Any]:
        rt = runtime(yes=False)
        try:
            return rt.resolve_approval(approval_id, approved=body.approved, reason=body.reason)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

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
                    "cost_usd": row.cost_usd,
                    "payload": row.payload,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]

    @app.get("/sessions/{session_id}/cost")
    def session_cost(session_id: int) -> dict[str, Any]:
        return runtime().session_cost(session_id)

    @app.get("/sessions/{session_id}/replay")
    def replay_session(session_id: int) -> dict[str, Any]:
        try:
            return runtime().replay_session(session_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/sessions/{session_id}/events")
    async def session_events(session_id: int) -> StreamingResponse:
        """SSE stream of trace events for live chat UI."""

        async def event_generator():
            rt = runtime()
            seen = 0
            for _ in range(120):
                rows = traces(session_id)
                for row in rows[seen:]:
                    summary = row.get("step") or ""
                    if row.get("actor"):
                        summary = f"{row['actor']}: {summary}"
                    yield f"data: {json.dumps({'type': 'trace', 'summary': summary, 'payload': row})}\n\n"
                seen = len(rows)
                replay = rt.replay_session(session_id)
                if replay["session"].get("ended_at"):
                    result = {
                        "type": "result",
                        "summary": replay["timeline"][-1]["summary"] if replay["timeline"] else "done",
                        "payload": replay,
                    }
                    yield f"data: {json.dumps(result)}\n\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return
                await asyncio.sleep(0.5)
            yield f"data: {json.dumps({'type': 'done', 'summary': 'timeout'})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    ui_dir = static_dir()
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")

        @app.get("/", include_in_schema=False)
        def ui_index() -> FileResponse:
            return FileResponse(ui_dir / "index.html")

    return app
