"""Approval gate for MODERATE and DANGEROUS actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ai_team.memory.database import Approval, Database, ToolCall
from ai_team.security.permissions import RiskLevel

Approver = Callable[[str, RiskLevel, str], bool]


class ApprovalDenied(PermissionError):
    pass


class ApprovalGate:
    def __init__(
        self,
        db: Database,
        auto_moderate: bool = False,
        auto_dangerous: bool = False,
        prompt: Approver | None = None,
    ) -> None:
        self.db = db
        self.auto_moderate = auto_moderate
        self.auto_dangerous = auto_dangerous
        self.prompt = prompt or _default_prompt

    def decide(
        self,
        action: str,
        risk: RiskLevel,
        requested_by: str,
        tool_call_id: int | None = None,
        reason: str = "",
    ) -> Approval:
        status = "approved"
        decided_by = "policy"
        if risk is RiskLevel.SAFE:
            decided_by = "auto-safe"
        elif risk is RiskLevel.MODERATE:
            if self.auto_moderate or requested_by == "manager":
                decided_by = "manager" if requested_by == "manager" else "auto-moderate"
            elif self.prompt(action, risk, reason):
                decided_by = "user"
            else:
                status = "denied"
                decided_by = "user"
        else:
            if self.auto_dangerous:
                decided_by = "auto-dangerous"
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
        if row.status != "approved":
            raise ApprovalDenied(f"{risk.value} action denied: {action}")
        return row


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
