"""Tracing / audit trail for every workflow step."""

from __future__ import annotations

from typing import Any

from ai_team.memory.database import Database, TraceEvent


class Tracer:
    def __init__(self, db: Database, session_id: int, task_id: int | None = None) -> None:
        self.db = db
        self.session_id = session_id
        self.task_id = task_id

    def emit(
        self,
        step: str,
        actor: str = "",
        payload: dict[str, Any] | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
    ) -> TraceEvent:
        with self.db.session() as s:
            event = TraceEvent(
                session_id=self.session_id,
                task_id=self.task_id,
                step=step,
                actor=actor,
                payload=payload or {},
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
            )
            s.add(event)
            s.commit()
            s.refresh(event)
            return event

    def list_events(self) -> list[TraceEvent]:
        with self.db.session() as s:
            return (
                s.query(TraceEvent)
                .filter(TraceEvent.session_id == self.session_id)
                .order_by(TraceEvent.id.asc())
                .all()
            )
