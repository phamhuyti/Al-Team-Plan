from ai_team.agents.base import BaseAgent
from ai_team.agents.contracts import ReviewerOutput


class ReviewerAgent(BaseAgent):
    role = "reviewer"
    prompt_file = "reviewer"
    output_schema = ReviewerOutput
