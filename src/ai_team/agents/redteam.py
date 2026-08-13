from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import RedTeamOutput


class RedTeamAgent(BaseAgent):
    role = "redteam"
    prompt_file = "redteam"
    output_schema = RedTeamOutput
