"""Judge evaluates debate arguments. It does not have to invent a new solution."""

from __future__ import annotations

from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import DebateProposal, JudgeOutput
from ai_team.context.engine import ContextBundle
from ai_team.tracing.audit import Tracer


class JudgeAgent(BaseAgent):
    role = "judge"
    prompt_file = "judge"
    output_schema = JudgeOutput

    async def evaluate(
        self,
        question: str,
        proposals: list[DebateProposal],
        context: ContextBundle | None = None,
        tracer: Tracer | None = None,
    ) -> JudgeOutput:
        payload = {
            "question": question,
            "proposals": [p.model_dump() for p in proposals],
            "criteria": [
                "correctness",
                "evidence",
                "project_compatibility",
                "complexity",
                "cost",
                "security",
                "maintainability",
                "risks",
            ],
        }
        result = await self.run(
            "Evaluate the proposals. Pick a winner or a synthesis of existing options. "
            "You do not need to invent a new solution.",
            context,
            tracer,
            extra=payload,
        )
        assert isinstance(result, JudgeOutput)
        return result
