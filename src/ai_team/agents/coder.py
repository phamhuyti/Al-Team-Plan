from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import CoderOutput


class CoderAgent(BaseAgent):
    role = "coder"
    prompt_file = "coder"
    output_schema = CoderOutput
