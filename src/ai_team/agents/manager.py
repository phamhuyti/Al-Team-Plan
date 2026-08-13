from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import ManagerDecision, ManagerPlan


class ManagerAgent(BaseAgent):
    role = "manager"
    prompt_file = "manager"
    output_schema = ManagerPlan

    async def plan(self, request: str, context=None, tracer=None) -> ManagerPlan:
        result = await self.run(f"Create an execution plan for:\n{request}", context, tracer)
        assert isinstance(result, ManagerPlan)
        return result

    async def decide(self, request: str, context=None, tracer=None, extra=None) -> ManagerDecision:
        previous = self.output_schema
        self.output_schema = ManagerDecision
        try:
            result = await self.run(
                "Make a decision. Approve only if remaining risk is acceptable.\n" + request,
                context,
                tracer,
                extra=extra,
            )
        finally:
            self.output_schema = previous
        assert isinstance(result, ManagerDecision)
        return result
