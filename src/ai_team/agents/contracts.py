"""Structured agent contracts. Agents must not return free-form prose as the only output."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    path: str
    action: Literal["create", "modify", "delete"]
    content: str | None = None
    reason: str = ""


class ManagerPlan(BaseModel):
    understanding: str
    tasks: list[str] = Field(default_factory=list)
    chosen_agents: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_action: str = ""


class ManagerDecision(BaseModel):
    decision: str
    approved: bool
    confidence: float = Field(ge=0, le=1, default=0.5)
    reason: str
    rejected_alternatives: list[str] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    follow_up: str = ""


class ArchitectProposal(BaseModel):
    summary: str
    architecture: str
    technology_choices: list[str] = Field(default_factory=list)
    trade_offs: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_option: str = ""


class ResearchFinding(BaseModel):
    topic: str
    findings: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    recommendation: str = ""
    evidence: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class CoderOutput(BaseModel):
    task: str
    changes: list[FileChange] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""
    tests: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    needs_approval: bool = True


class ReviewerOutput(BaseModel):
    verdict: Literal["approve", "request_changes", "reject"]
    critical_issues: list[str] = Field(default_factory=list)
    major_issues: list[str] = Field(default_factory=list)
    minor_issues: list[str] = Field(default_factory=list)
    security_issues: list[str] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
    summary: str = ""


class FailureScenario(BaseModel):
    name: str
    description: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    exploitability: Literal["low", "medium", "high"] = "medium"


class RedTeamOutput(BaseModel):
    attack_surface: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    failure_scenarios: list[FailureScenario] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    exploitability: Literal["low", "medium", "high"] = "medium"
    mitigation: list[str] = Field(default_factory=list)
    should_block: bool = False


class DebateProposal(BaseModel):
    agent: str
    position: str
    arguments: list[str] = Field(default_factory=list)
    counterarguments: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class JudgeOutput(BaseModel):
    decision: str
    confidence: float = Field(ge=0, le=1, default=0.5)
    reason: str
    rejected_alternatives: list[str] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class AgentEnvelope(BaseModel):
    """Normalized wrapper stored in sessions/audit."""

    role: str
    contract: str
    payload: dict[str, Any]
    raw_text: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


CONTRACTS: dict[str, type[BaseModel]] = {
    "manager_plan": ManagerPlan,
    "manager_decision": ManagerDecision,
    "architect": ArchitectProposal,
    "researcher": ResearchFinding,
    "coder": CoderOutput,
    "reviewer": ReviewerOutput,
    "redteam": RedTeamOutput,
    "debate": DebateProposal,
    "judge": JudgeOutput,
}
