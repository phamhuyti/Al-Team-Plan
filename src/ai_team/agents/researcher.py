from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import ResearchFinding


class ResearcherAgent(BaseAgent):
    role = "researcher"
    prompt_file = "researcher"
    output_schema = ResearchFinding
