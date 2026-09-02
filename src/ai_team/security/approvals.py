"""Approval gate for MODERATE and DANGEROUS actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ai_team.memory.database import Approval, Database, ToolCall
from ai_team.security.permissions import RiskLevel

Approver = Callable[[str, RiskLevel, str], bool]


class ApprovalDenied(PermissionError):
    pass


class ApprovalPending(PermissionError):
    """Raised when an action needs an async / API decision."""

    def __init__(self, approval: Approval) -> None:
        self.approval = approval
        super().__init__(f"{approval.risk_level} action pending approval #{approval.id}: {approval.action}")


class ApprovalGate:
    def __init__(
        self,
        db: Database,
        auto_moderate: bool = False,
        auto_dangerous: bool = False,
        prompt: Approver | None = None,
        defer: bool = False,
    ) -> None:
        self.db = db
        self.auto_moderate = auto_moderate
        self.auto_dangerous = auto_dangerous
        self.prompt = prompt or _default_prompt
        # When True, create pending rows instead of interactive prompt (HTTP API).
        self.defer = defer

    def decide(
        self,
        action: str,
        risk: RiskLevel,
        requested_by: str,
        tool_call_id: int | None = None,
        reason: str = "",
    ) -> Approval:
        reused = self._find_reusable(action, risk)
        if reused is not None:
            return reused

        status = "approved"
        decided_by = "policy"
        if risk is RiskLevel.SAFE:
            decided_by = "auto-safe"
        elif risk is RiskLevel.MODERATE:
            if self.auto_moderate or requested_by == "manager":
                decided_by = "manager" if requested_by == "manager" else "auto-moderate"
            elif self.defer:
                status = "pending"
                decided_by = ""
            elif self.prompt(action, risk, reason):
                decided_by = "user"
            else:
                status = "denied"
                decided_by = "user"
        else:
            if self.auto_dangerous:
                decided_by = "auto-dangerous"
            elif self.defer:
                status = "pending"
                decided_by = ""
            elif self.prompt(action, risk, reason):
                decided_by = "user"
            else:
                status = "denied"
                decided_by = "user"

        with self.db.session() as s:
            row = Approval(
                tool_call_id=tool_call_id,
                risk_level=risk.value,
                action=action,
                requested_by=requested_by,
                status=status,
                decided_by=decided_by,
                reason=reason,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def require(
        self,
        action: str,
        risk: RiskLevel,
        requested_by: str,
        tool_call_id: int | None = None,
        reason: str = "",
    ) -> Approval:
        row = self.decide(action, risk, requested_by, tool_call_id, reason)
        if row.status == "pending":
            raise ApprovalPending(row)
        if row.status != "approved":
            raise ApprovalDenied(f"{risk.value} action denied: {action}")
        return row

    def resolve(self, approval_id: int, approved: bool, decided_by: str = "api", reason: str = "") -> Approval:
        with self.db.session() as s:
            row = s.get(Approval, approval_id)
            if row is None:
                raise KeyError(f"Unknown approval id {approval_id}")
            if row.status != "pending":
                raise ValueError(f"Approval {approval_id} is already {row.status}")
            row.status = "approved" if approved else "denied"
            row.decided_by = decided_by
            if reason:
                row.reason = reason
            s.commit()
            s.refresh(row)
            return row

    def list_approvals(self, status: str | None = None, limit: int = 100) -> list[Approval]:
        with self.db.session() as s:
            q = s.query(Approval).order_by(Approval.id.desc())
            if status:
                q = q.filter(Approval.status == status)
            return q.limit(limit).all()

    def get_approval(self, approval_id: int) -> Approval | None:
        with self.db.session() as s:
            return s.get(Approval, approval_id)

    def _find_reusable(self, action: str, risk: RiskLevel) -> Approval | None:
        """One-shot reuse after POST /approvals/{id} (same action + risk)."""
        with self.db.session() as s:
            row = (
                s.query(Approval)
                .filter(
                    Approval.action == action,
                    Approval.risk_level == risk.value,
                    Approval.status == "approved",
                    Approval.decided_by.in_(("api", "user")),
                )
                .order_by(Approval.id.desc())
                .first()
            )
            if row is None:
                return None
            row.status = "applied"
            applied = Approval(
                tool_call_id=row.tool_call_id,
                risk_level=row.risk_level,
                action=row.action,
                requested_by=row.requested_by,
                status="approved",
                decided_by=f"reuse:{row.id}",
                reason=row.reason,
            )
            s.add(applied)
            s.commit()
            s.refresh(applied)
            return applied


def record_tool_call(
    db: Database,
    session_id: int,
    agent_role: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: str,
    risk: RiskLevel,
    approved: bool,
) -> ToolCall:
    with db.session() as s:
        row = ToolCall(
            session_id=session_id,
            agent_role=agent_role,
            tool_name=tool_name,
            arguments=arguments,
            result=result[:20_000],
            risk_level=risk.value,
            approved=approved,
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def _default_prompt(action: str, risk: RiskLevel, reason: str) -> bool:
    if risk is RiskLevel.SAFE:
        return True
    print()
    print(f"AI wants to execute:\n\n{action}\n")
    print(f"Risk: {risk.value.upper()}")
    if reason:
        print(f"Reason:\n{reason}")
    try:
        answer = input("Approve? [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}
