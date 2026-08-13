"""Session helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from ai_team.memory.database import Database, Message, Session, utcnow


class SessionStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def start(self, project_id: int, kind: str, task_id: int | None = None) -> Session:
        with self.db.session() as s:
            session = Session(project_id=project_id, task_id=task_id, kind=kind, status="running")
            s.add(session)
            s.commit()
            s.refresh(session)
            return session

    def finish(self, session_id: int, status: str = "completed") -> None:
        with self.db.session() as s:
            session = s.get(Session, session_id)
            if session is None:
                return
            session.status = status
            session.ended_at = utcnow()
            s.commit()

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        agent_role: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> Message:
        with self.db.session() as s:
            msg = Message(
                session_id=session_id,
                role=role,
                content=content,
                agent_role=agent_role,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                created_at=datetime.now(timezone.utc),
            )
            s.add(msg)
            s.commit()
            s.refresh(msg)
            return msg
