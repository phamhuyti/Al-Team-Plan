"""Manager-facing helper that selects specialist agents for a request."""

from __future__ import annotations

from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import ManagerPlan


class AgentRouter:
    def __init__(self, agents: dict[str, BaseAgent]) -> None:
        self.agents = agents

    def resolve(self, plan: ManagerPlan) -> list[BaseAgent]:
        chosen = []
        for name in plan.chosen_agents:
            key = name.lower().replace(" ", "").replace("_", "")
            if key == "redteam":
                key = "redteam"
            agent = self.agents.get(name.lower()) or self.agents.get(key)
            if agent is not None:
                chosen.append(agent)
        if chosen:
            return chosen
        return [
            agent
            for role, agent in self.agents.items()
            if role in {"architect", "researcher", "coder", "reviewer", "redteam"}
        ]
