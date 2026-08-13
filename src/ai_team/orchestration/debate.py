"""Multi-agent debate: proposals → disagreement → rounds → judge."""

from __future__ import annotations

from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import DebateProposal, JudgeOutput
from ai_team.context.engine import ContextBundle
from ai_team.orchestration.judge import JudgeAgent
from ai_team.tracing.audit import Tracer


def detect_disagreement(proposals: list[DebateProposal]) -> bool:
    positions = {_normalize(p.position) for p in proposals if p.position.strip()}
    return len(positions) > 1


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


class DebateEngine:
    def __init__(self, judge: JudgeAgent, rounds: int = 2) -> None:
        self.judge = judge
        self.rounds = rounds

    async def collect_proposals(
        self,
        agents: list[BaseAgent],
        question: str,
        context: ContextBundle | None = None,
        tracer: Tracer | None = None,
    ) -> list[DebateProposal]:
        proposals: list[DebateProposal] = []
        for agent in agents:
            previous = agent.output_schema
            agent.output_schema = DebateProposal
            try:
                result = await agent.run(
                    f"Take a position on this question and argue for it:\n{question}",
                    context,
                    tracer,
                )
            finally:
                agent.output_schema = previous
            if isinstance(result, DebateProposal):
                result.agent = agent.role
                proposals.append(result)
        return proposals

    async def run_rounds(
        self,
        agents: list[BaseAgent],
        question: str,
        proposals: list[DebateProposal],
        context: ContextBundle | None = None,
        tracer: Tracer | None = None,
    ) -> list[DebateProposal]:
        current = proposals
        for round_no in range(self.rounds):
            if tracer:
                tracer.emit("debate_round", actor="debate", payload={"round": round_no + 1})
            nxt: list[DebateProposal] = []
            for agent in agents:
                others = [p.model_dump() for p in current if p.agent != agent.role]
                previous = agent.output_schema
                agent.output_schema = DebateProposal
                try:
                    result = await agent.run(
                        f"Debate round {round_no + 1}. Question:\n{question}\n"
                        "Respond to the other agents. Keep or revise your position.",
                        context,
                        tracer,
                        extra={"others": others},
                    )
                finally:
                    agent.output_schema = previous
                if isinstance(result, DebateProposal):
                    result.agent = agent.role
                    nxt.append(result)
            current = nxt or current
        return current

    async def debate(
        self,
        agents: list[BaseAgent],
        question: str,
        context: ContextBundle | None = None,
        tracer: Tracer | None = None,
        force: bool = False,
    ) -> tuple[list[DebateProposal], JudgeOutput | None, bool]:
        proposals = await self.collect_proposals(agents, question, context, tracer)
        disagreed = detect_disagreement(proposals)
        if tracer:
            tracer.emit(
                "disagreement",
                actor="debate",
                payload={"disagreed": disagreed, "positions": [p.position for p in proposals]},
            )
        if disagreed or force:
            proposals = await self.run_rounds(agents, question, proposals, context, tracer)
            verdict = await self.judge.evaluate(question, proposals, context, tracer)
            if tracer:
                tracer.emit("judge", actor="judge", payload=verdict.model_dump())
            return proposals, verdict, True
        return proposals, None, False
