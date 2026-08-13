from ai_team.agents.contracts import DebateProposal
from ai_team.orchestration.debate import detect_disagreement


def test_detects_disagreement() -> None:
    proposals = [
        DebateProposal(agent="architect", position="Use Redis"),
        DebateProposal(agent="coder", position="Use RabbitMQ"),
    ]
    assert detect_disagreement(proposals) is True


def test_agreement_is_not_debate() -> None:
    proposals = [
        DebateProposal(agent="architect", position="In-process first"),
        DebateProposal(agent="coder", position="in-process first"),
    ]
    assert detect_disagreement(proposals) is False
