"""Decision records in SQLite + markdown."""

from __future__ import annotations

from ai_team.memory.database import Database, Decision
from ai_team.memory.project import DecisionRecord, ProjectMemory


class DecisionStore:
    def __init__(self, db: Database, memory: ProjectMemory) -> None:
        self.db = db
        self.memory = memory

    def record(
        self,
        project_id: int,
        title: str,
        decision: str,
        reason: str,
        task_id: int | None = None,
        task_key: str = "",
        alternatives: list[str] | None = None,
        rejected: list[str] | None = None,
        risks: list[str] | None = None,
        confidence: float = 0.5,
        consequences: list[str] | None = None,
    ) -> Decision:
        alternatives = alternatives or []
        rejected = rejected or []
        risks = risks or []
        consequences = consequences or []
        with self.db.session() as s:
            row = Decision(
                project_id=project_id,
                task_id=task_id,
                decision=decision,
                reason=reason,
                alternatives=alternatives,
                rejected_alternatives=rejected,
                risks=risks,
                confidence=confidence,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
        self.memory.append_decision(
            DecisionRecord(
                title=title,
                decision=decision,
                reason=reason,
                alternatives=alternatives,
                rejected=rejected,
                risks=risks,
                consequences=consequences,
                task_key=task_key,
                confidence=confidence,
            )
        )
        return row
