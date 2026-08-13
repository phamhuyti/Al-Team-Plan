from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import ArchitectProposal


class ArchitectAgent(BaseAgent):
    role = "architect"
    prompt_file = "architect"
    output_schema = ArchitectProposal
