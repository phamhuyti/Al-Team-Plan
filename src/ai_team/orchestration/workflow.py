"""V1 end-to-end workflow.

User → Task → Manager → Architect → Researcher → Debate → Red Team
→ Decision → Coder → Tests → Reviewer → Approval → Git commit
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_team.agents.architect import ArchitectAgent
from ai_team.agents.coder import CoderAgent
from ai_team.agents.contracts import CoderOutput, RedTeamOutput, ReviewerOutput
from ai_team.agents.manager import ManagerAgent
from ai_team.agents.redteam import RedTeamAgent
from ai_team.agents.researcher import ResearcherAgent
from ai_team.agents.reviewer import ReviewerAgent
from ai_team.config import Settings, apply_project_config, load_settings
from ai_team.context.engine import ContextEngine
from ai_team.memory.database import (
    AgentRecord,
    Database,
    Project,
    Review,
    Task,
    ensure_sqlite_parent,
)
from ai_team.memory.decisions import DecisionStore
from ai_team.memory.project import ProjectMemory
from ai_team.memory.sessions import SessionStore
from ai_team.models.factory import build_provider
from ai_team.orchestration.debate import DebateEngine
from ai_team.orchestration.judge import JudgeAgent
from ai_team.security.approvals import ApprovalDenied, ApprovalGate, ApprovalPending, record_tool_call
from ai_team.security.permissions import RiskLevel, classify_filesystem
from ai_team.tools.filesystem import FilesystemTools
from ai_team.tools.git import GitTools
from ai_team.tools.registry import ToolRegistry
from ai_team.tools.shell import ShellError, ShellTools
from ai_team.tracing.audit import Tracer


@dataclass
class WorkflowResult:
    ok: bool
    task_key: str
    session_id: int
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


class TeamRuntime:
    def __init__(
        self,
        root: Path,
        settings: Settings | None = None,
        auto_approve: bool = False,
        defer_approvals: bool = False,
    ) -> None:
        self.root = Path(root).resolve()
        base = settings or load_settings()
        self.settings = apply_project_config(base, self.root)
        self.memory = ProjectMemory(self.root)
        db_url = self._db_url()
        ensure_sqlite_parent(db_url)
        self.db = Database(db_url)
        self.db.create_all()
        self._seed_agents()
        self.sessions = SessionStore(self.db)
        self.decisions = DecisionStore(self.db, self.memory)
        self.context = ContextEngine(self.root, self.memory, max_chars=self.settings.max_context_chars)
        self.fs = FilesystemTools(self.root)
        self.git = GitTools(self.root)
        self.shell = ShellTools(self.root)
        self.tools = ToolRegistry(self.fs, self.git, self.shell)
        self.gate = ApprovalGate(
            self.db,
            auto_moderate=auto_approve or self.settings.auto_approve_moderate,
            auto_dangerous=auto_approve or self.settings.auto_approve_dangerous,
            defer=defer_approvals and not auto_approve,
        )
        extra = {
            role: self.memory.read(f"agents/{role}.md")
            for role in ("manager", "architect", "researcher", "coder", "reviewer", "redteam")
        }
        self.manager = ManagerAgent(build_provider(self.settings, "manager"), extra.get("manager", ""))
        self.architect = ArchitectAgent(build_provider(self.settings, "architect"), extra.get("architect", ""))
        self.researcher = ResearcherAgent(build_provider(self.settings, "researcher"), extra.get("researcher", ""))
        self.coder = CoderAgent(build_provider(self.settings, "coder"), extra.get("coder", ""))
        self.reviewer = ReviewerAgent(build_provider(self.settings, "reviewer"), extra.get("reviewer", ""))
        self.redteam = RedTeamAgent(build_provider(self.settings, "redteam"), extra.get("redteam", ""))
        self.judge = JudgeAgent(build_provider(self.settings, "manager"))
        self.debate_engine = DebateEngine(self.judge, rounds=self.settings.debate_rounds)
        self.project_row = self._ensure_project()

    def _db_url(self) -> str:
        url = self.settings.database_url
        if url.startswith("sqlite:///./"):
            rel = url.removeprefix("sqlite:///")
            return "sqlite:///" + str((self.root / rel).resolve())
        return url

    def _seed_agents(self) -> None:
        with self.db.session() as s:
            for role in ("manager", "architect", "researcher", "coder", "reviewer", "redteam"):
                provider = self.settings.provider_for_role(role)
                model = self.settings.model_for_role(role)
                row = s.query(AgentRecord).filter(AgentRecord.name == role).one_or_none()
                if row is None:
                    s.add(AgentRecord(name=role, role=role, provider=provider, model=model))
                else:
                    row.provider = provider
                    row.model = model
            s.commit()

    def _ensure_project(self) -> Project:
        with self.db.session() as s:
            row = s.query(Project).filter(Project.path == str(self.root)).one_or_none()
            if row is None:
                row = Project(
                    name=self.root.name,
                    path=str(self.root),
                    config_json=dict(self.settings.project_config or {}),
                )
                s.add(row)
                s.commit()
                s.refresh(row)
            else:
                row.config_json = dict(self.settings.project_config or {})
                s.commit()
                s.refresh(row)
            return row

    def next_task_key(self) -> str:
        with self.db.session() as s:
            count = s.query(Task).filter(Task.project_id == self.project_row.id).count()
        return f"TASK-{count + 1:03d}"

    def get_task(self, task_key: str) -> Task | None:
        with self.db.session() as s:
            return (
                s.query(Task)
                .filter(Task.project_id == self.project_row.id, Task.task_key == task_key)
                .one_or_none()
            )

    def create_task(self, title: str, description: str = "", status: str = "pending") -> Task:
        key = self.next_task_key()
        with self.db.session() as s:
            task = Task(
                project_id=self.project_row.id,
                task_key=key,
                title=title,
                description=description or title,
                status=status,
            )
            s.add(task)
            s.commit()
            s.refresh(task)
        self.memory.upsert_task(task.task_key, task.title, task.status, task.description)
        return task

    def set_status(self, task: Task, status: str) -> None:
        with self.db.session() as s:
            row = s.get(Task, task.id)
            if row is None:
                return
            row.status = status
            s.commit()
            task.status = status
        self.memory.upsert_task(task.task_key, task.title, status, task.description)

    def list_agents(self) -> list[dict[str, str]]:
        with self.db.session() as s:
            rows = s.query(AgentRecord).all()
            return [{"name": r.name, "role": r.role, "provider": r.provider, "model": r.model} for r in rows]

    def list_sessions(self) -> list[dict[str, Any]]:
        from ai_team.memory.database import Session

        with self.db.session() as s:
            rows = (
                s.query(Session)
                .filter(Session.project_id == self.project_row.id)
                .order_by(Session.id.desc())
                .limit(50)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "kind": r.kind,
                    "status": r.status,
                    "task_id": r.task_id,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                }
                for r in rows
            ]

    def list_decisions(self) -> list[dict[str, Any]]:
        from ai_team.memory.database import Decision

        with self.db.session() as s:
            rows = (
                s.query(Decision)
                .filter(Decision.project_id == self.project_row.id)
                .order_by(Decision.id.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "decision": r.decision,
                    "reason": r.reason,
                    "confidence": r.confidence,
                    "risks": r.risks,
                }
                for r in rows
            ]

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.db.session() as s:
            rows = s.query(Task).filter(Task.project_id == self.project_row.id).order_by(Task.id.asc()).all()
            return [
                {
                    "task_key": r.task_key,
                    "title": r.title,
                    "status": r.status,
                    "description": r.description,
                }
                for r in rows
            ]

    def list_approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        rows = self.gate.list_approvals(status=status)
        return [
            {
                "id": r.id,
                "action": r.action,
                "risk_level": r.risk_level,
                "status": r.status,
                "requested_by": r.requested_by,
                "decided_by": r.decided_by,
                "reason": r.reason,
                "tool_call_id": r.tool_call_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    def resolve_approval(self, approval_id: int, approved: bool, reason: str = "") -> dict[str, Any]:
        row = self.gate.resolve(approval_id, approved=approved, decided_by="api", reason=reason)
        return {
            "id": row.id,
            "action": row.action,
            "risk_level": row.risk_level,
            "status": row.status,
            "requested_by": row.requested_by,
            "decided_by": row.decided_by,
            "reason": row.reason,
        }

    def session_cost(self, session_id: int) -> dict[str, Any]:
        from ai_team.memory.database import TraceEvent

        with self.db.session() as s:
            rows = s.query(TraceEvent).filter(TraceEvent.session_id == session_id).all()
        tokens_in = sum(r.tokens_in or 0 for r in rows)
        tokens_out = sum(r.tokens_out or 0 for r in rows)
        cost_usd = sum(float(r.cost_usd or 0.0) for r in rows)
        return {
            "session_id": session_id,
            "events": len(rows),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost_usd, 8),
        }

    async def ask(self, request: str) -> WorkflowResult:
        session = self.sessions.start(self.project_row.id, kind="ask")
        tracer = Tracer(self.db, session.id)
        tracer.emit("task", actor="user", payload={"request": request})
        context = self.context.build(request)
        plan = await self.manager.plan(request, context, tracer)
        architect = await self.architect.run(request, context, tracer)
        research = await self.researcher.run(request, context, tracer)
        decision = await self.manager.decide(
            request,
            context,
            tracer,
            extra={"plan": plan.model_dump(), "architect": architect.model_dump(), "research": research.model_dump()},
        )
        self.decisions.record(
            self.project_row.id,
            title=f"Ask: {request[:80]}",
            decision=decision.decision,
            reason=decision.reason,
            alternatives=getattr(architect, "alternatives", []),
            rejected=decision.rejected_alternatives,
            risks=decision.remaining_risks,
            confidence=decision.confidence,
        )
        self.sessions.finish(session.id)
        self._write_session_log(session.id, "ask", request, {"plan": plan, "decision": decision})
        return WorkflowResult(
            ok=True,
            task_key="",
            session_id=session.id,
            summary=decision.decision,
            details={
                "plan": plan.model_dump(),
                "architect": architect.model_dump(),
                "research": research.model_dump(),
                "decision": decision.model_dump(),
            },
        )

    async def research(self, topic: str) -> WorkflowResult:
        session = self.sessions.start(self.project_row.id, kind="research")
        tracer = Tracer(self.db, session.id)
        context = self.context.build(topic)
        finding = await self.researcher.run(topic, context, tracer)
        self.sessions.finish(session.id)
        return WorkflowResult(True, "", session.id, finding.recommendation, finding.model_dump())

    async def debate(self, question: str, force: bool = True) -> WorkflowResult:
        session = self.sessions.start(self.project_row.id, kind="debate")
        tracer = Tracer(self.db, session.id)
        context = self.context.build(question)
        proposals, verdict, ran = await self.debate_engine.debate(
            [self.architect, self.researcher, self.coder],
            question,
            context,
            tracer,
            force=force,
        )
        if verdict:
            self.decisions.record(
                self.project_row.id,
                title=f"Debate: {question[:80]}",
                decision=verdict.decision,
                reason=verdict.reason,
                rejected=verdict.rejected_alternatives,
                risks=verdict.remaining_risks,
                confidence=verdict.confidence,
            )
            slug = re.sub(r"[^a-z0-9]+", "-", question.lower())[:40].strip("-")
            self.memory.write_discussion(
                slug or "debate",
                _render_discussion(question, proposals, verdict),
            )
        self.sessions.finish(session.id)
        summary = verdict.decision if verdict else proposals[0].position
        return WorkflowResult(
            True,
            "",
            session.id,
            summary,
            {
                "proposals": [p.model_dump() for p in proposals],
                "verdict": verdict.model_dump() if verdict else None,
                "debated": ran,
            },
        )

    async def plan(self, request: str) -> WorkflowResult:
        task = self.create_task(request, status="planning")
        session = self.sessions.start(self.project_row.id, kind="plan", task_id=task.id)
        tracer = Tracer(self.db, session.id, task.id)
        tracer.emit("task", actor="user", payload={"request": request, "task_key": task.task_key})
        context = self.context.build(request)
        manager_plan = await self.manager.plan(request, context, tracer)
        architect = await self.architect.run(request, context, tracer)
        research = await self.researcher.run(request, context, tracer)
        proposals, verdict, ran = await self.debate_engine.debate(
            [self.architect, self.researcher],
            request,
            context,
            tracer,
            force=False,
        )
        red = await self.redteam.run(
            "Attack this plan. Prove it wrong if you can.",
            context,
            tracer,
            extra={"architect": architect.model_dump(), "research": research.model_dump()},
        )
        assert isinstance(red, RedTeamOutput)
        decision = await self.manager.decide(
            request,
            context,
            tracer,
            extra={
                "plan": manager_plan.model_dump(),
                "architect": architect.model_dump(),
                "research": research.model_dump(),
                "debate": verdict.model_dump() if verdict else None,
                "redteam": red.model_dump(),
            },
        )
        self.decisions.record(
            self.project_row.id,
            title=f"{task.task_key}: {request[:80]}",
            decision=decision.decision,
            reason=decision.reason,
            task_id=task.id,
            task_key=task.task_key,
            alternatives=architect.alternatives,
            rejected=decision.rejected_alternatives,
            risks=decision.remaining_risks + red.mitigation,
            confidence=decision.confidence,
            consequences=[f"Red Team severity: {red.severity}"],
        )
        status = "planned" if decision.approved and not red.should_block else "blocked"
        self.set_status(task, status)
        self.sessions.finish(session.id)
        return WorkflowResult(
            ok=status == "planned",
            task_key=task.task_key,
            session_id=session.id,
            summary=decision.decision,
            details={
                "manager_plan": manager_plan.model_dump(),
                "architect": architect.model_dump(),
                "research": research.model_dump(),
                "debate": verdict.model_dump() if verdict else None,
                "debated": ran,
                "redteam": red.model_dump(),
                "decision": decision.model_dump(),
                "status": status,
            },
        )

    async def implement(self, task_key: str) -> WorkflowResult:
        task = self.get_task(task_key)
        if task is None:
            raise ValueError(f"Unknown task: {task_key}")
        session = self.sessions.start(self.project_row.id, kind="implement", task_id=task.id)
        tracer = Tracer(self.db, session.id, task.id)
        tracer.emit("task", actor="manager", payload={"task_key": task_key, "title": task.title})
        self.set_status(task, "implementing")
        context = self.context.build(f"{task.task_key} {task.title} {task.description}")

        branch = _branch_name(task.task_key, task.title, self.settings.git_branch_prefix)
        if self.git.is_repo():
            self.git.ensure_identity()
            self.git.create_branch(branch)
            tracer.emit("tool_call", actor="git", payload={"branch": branch})

        last_coder: CoderOutput | None = None
        last_review: ReviewerOutput | None = None
        last_red: RedTeamOutput | None = None
        test_output = ""
        approved = False
        summary = ""
        pending_approval: dict[str, Any] | None = None

        try:
            for attempt in range(self.settings.max_review_loops):
                coder_out = await self.coder.run(
                    f"Implement {task.task_key}: {task.title}\n{task.description}",
                    context,
                    tracer,
                )
                assert isinstance(coder_out, CoderOutput)
                last_coder = coder_out
                self._apply_coder_output(session.id, coder_out)

                test_output = self._run_tests(session.id, coder_out)
                tracer.emit("result", actor="test", payload={"output": test_output[:4000]})

                context = self.context.build(f"{task.task_key} {task.title}")
                last_review = await self.reviewer.run(
                    f"Review implementation of {task.task_key}",
                    context,
                    tracer,
                    extra={"coder": coder_out.model_dump(), "tests": test_output},
                )
                assert isinstance(last_review, ReviewerOutput)
                self._store_review(task.id, "reviewer", last_review.verdict, last_review.model_dump())

                last_red = await self.redteam.run(
                    f"Attack the implementation of {task.task_key}",
                    context,
                    tracer,
                    extra={"coder": coder_out.model_dump(), "review": last_review.model_dump()},
                )
                assert isinstance(last_red, RedTeamOutput)
                self._store_review(task.id, "redteam", last_red.severity, last_red.model_dump())

                decision = await self.manager.decide(
                    f"Approve commit for {task.task_key}?",
                    context,
                    tracer,
                    extra={
                        "coder": coder_out.model_dump(),
                        "tests": test_output,
                        "review": last_review.model_dump(),
                        "redteam": last_red.model_dump(),
                    },
                )
                tracer.emit("decision", actor="manager", payload=decision.model_dump())
                summary = decision.decision
                if (
                    decision.approved
                    and last_review.verdict == "approve"
                    and not last_red.should_block
                    and "FAIL" not in test_output
                ):
                    approved = True
                    break
                if last_review.verdict == "reject" or last_red.should_block:
                    break

            if approved and last_coder is not None and self.settings.git_auto_commit:
                try:
                    self.gate.require(
                        f"git commit for {task.task_key}",
                        RiskLevel.MODERATE,
                        requested_by="manager",
                        reason=summary,
                    )
                    commit_msg = f"{task.task_key}: {task.title}\n\n{summary}"
                    if self.git.is_repo():
                        self.git.ensure_identity()
                        commit_out = self.git.commit(commit_msg)
                        tracer.emit("result", actor="git", payload={"commit": commit_out})
                    self.set_status(task, "completed")
                    ok = True
                except ApprovalDenied as exc:
                    self.set_status(task, "needs_approval")
                    ok = False
                    summary = str(exc)
                except ApprovalPending as exc:
                    self.set_status(task, "needs_approval")
                    ok = False
                    summary = str(exc)
                    pending_approval = {
                        "id": exc.approval.id,
                        "action": exc.approval.action,
                        "risk_level": exc.approval.risk_level,
                        "status": exc.approval.status,
                    }
            elif approved and last_coder is not None:
                self.set_status(task, "completed")
                ok = True
            else:
                self.set_status(task, "changes_requested")
                ok = False
                summary = summary or "Implementation was not approved"
        except ApprovalPending as exc:
            self.set_status(task, "needs_approval")
            ok = False
            summary = str(exc)
            pending_approval = {
                "id": exc.approval.id,
                "action": exc.approval.action,
                "risk_level": exc.approval.risk_level,
                "status": exc.approval.status,
            }

        self.sessions.finish(session.id, "completed" if ok else "failed")
        details: dict[str, Any] = {
            "branch": branch,
            "coder": last_coder.model_dump() if last_coder else None,
            "tests": test_output,
            "review": last_review.model_dump() if last_review else None,
            "redteam": last_red.model_dump() if last_red else None,
            "approved": approved,
            "cost": self.session_cost(session.id),
        }
        if pending_approval:
            details["pending_approval"] = pending_approval
        return WorkflowResult(
            ok=ok,
            task_key=task.task_key,
            session_id=session.id,
            summary=summary,
            details=details,
        )

    async def review_task(self, task_key: str) -> WorkflowResult:
        task = self.get_task(task_key)
        if task is None:
            raise ValueError(f"Unknown task: {task_key}")
        session = self.sessions.start(self.project_row.id, kind="review", task_id=task.id)
        tracer = Tracer(self.db, session.id, task.id)
        context = self.context.build(f"{task.task_key} {task.title}")
        review = await self.reviewer.run(f"Review {task.task_key}", context, tracer)
        red = await self.redteam.run(f"Attack {task.task_key}", context, tracer, extra={"review": review.model_dump()})
        self.sessions.finish(session.id)
        return WorkflowResult(
            True,
            task.task_key,
            session.id,
            getattr(review, "summary", ""),
            {"review": review.model_dump(), "redteam": red.model_dump()},
        )

    def _apply_coder_output(self, session_id: int, output: CoderOutput) -> None:
        for change in output.changes:
            risk = classify_filesystem(change.action)
            action = f"{change.action} {change.path}"
            call = record_tool_call(
                self.db,
                session_id,
                "coder",
                "fs_write" if change.action != "delete" else "fs_delete",
                {"path": change.path, "action": change.action},
                "",
                risk,
                False,
            )
            self.gate.require(action, risk, requested_by="manager", tool_call_id=call.id, reason=change.reason)
            if change.action == "delete":
                result = self.fs.delete(change.path)
            else:
                if change.content is None:
                    continue
                result = self.fs.write(change.path, change.content)
            call_ok = record_tool_call(
                self.db, session_id, "coder", "fs_write", {"path": change.path}, result, risk, True
            )
            _ = call_ok

    def _run_tests(self, session_id: int, output: CoderOutput) -> str:
        commands = output.tests or [f"{sys.executable} -m pytest -q -c /dev/null"]
        chunks: list[str] = []
        for command in commands:
            command = _normalize_shell_command(command)
            risk = self.tools.classify("shell", {"command": command})
            try:
                self.gate.require(command, risk, requested_by="coder")
                text = self.shell.run(command)
                chunks.append(f"$ {command}\n{text}")
                record_tool_call(self.db, session_id, "coder", "shell", {"command": command}, text, risk, True)
            except (ApprovalDenied, ShellError) as exc:
                chunks.append(f"$ {command}\nFAIL: {exc}")
                record_tool_call(self.db, session_id, "coder", "shell", {"command": command}, str(exc), risk, False)
        return "\n\n".join(chunks) or "No tests executed"

    def _store_review(self, task_id: int, role: str, verdict: str, payload: dict[str, Any]) -> None:
        with self.db.session() as s:
            s.add(Review(task_id=task_id, agent_role=role, verdict=verdict, issues_json=payload))
            s.commit()

    def _write_session_log(self, session_id: int, kind: str, request: str, payload: dict[str, Any]) -> None:
        stamp = datetime.now(timezone.utc).isoformat()
        lines = [f"# Session {session_id}", f"- Kind: {kind}", f"- At: {stamp}", f"- Request: {request}", ""]
        for key, value in payload.items():
            dumped = value.model_dump() if hasattr(value, "model_dump") else value
            lines.append(f"## {key}\n\n```json\n{dumped}\n```\n")
        self.memory.write_session(str(session_id), "\n".join(lines))


def _normalize_shell_command(command: str) -> str:
    if command.startswith("python "):
        return f"{sys.executable} {command[7:]}"
    if command.startswith("python3 "):
        return f"{sys.executable} {command[8:]}"
    if command.startswith("pytest"):
        return f"{sys.executable} -m {command}"
    return command


def _branch_name(task_key: str, title: str, prefix: str = "ai/") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    prefix = prefix if prefix.endswith("/") else f"{prefix}/"
    return f"{prefix}{task_key.lower()}-{slug or 'work'}"


def _render_discussion(question: str, proposals, verdict) -> str:
    lines = [f"# {question}", ""]
    for proposal in proposals:
        lines.append(f"## {proposal.agent}")
        lines.append(f"Position: {proposal.position}")
        for arg in proposal.arguments:
            lines.append(f"- {arg}")
        lines.append("")
    if verdict:
        lines.append("## Judge")
        lines.append(verdict.decision)
        lines.append(verdict.reason)
    return "\n".join(lines)


def init_project(path: Path, name: str | None = None, purpose: str = "") -> ProjectMemory:
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    memory = ProjectMemory(root)
    memory.init_structure(name or root.name, purpose)
    git = GitTools(root)
    if not git.is_repo():
        git.init()
        git.ensure_identity()
        git.commit("chore: initialize AI-Team project")
    settings = load_settings()
    db_url = settings.database_url
    if db_url.startswith("sqlite:///./"):
        db_url = "sqlite:///" + str((root / db_url.removeprefix("sqlite:///")).resolve())
    ensure_sqlite_parent(db_url)
    db = Database(db_url)
    db.create_all()
    return memory
