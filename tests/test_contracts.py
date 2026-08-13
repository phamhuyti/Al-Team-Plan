from ai_team.agents.contracts import CoderOutput, RedTeamOutput, ReviewerOutput


def test_coder_contract_roundtrip() -> None:
    payload = {
        "task": "Add ping",
        "changes": [{"path": "src/ping.py", "action": "create", "content": "x = 1\n", "reason": "init"}],
        "files_modified": ["src/ping.py"],
        "reasoning_summary": "tiny slice",
        "tests": ["python -m pytest -q"],
        "risks": [],
        "needs_approval": True,
    }
    out = CoderOutput.model_validate(payload)
    assert out.files_modified == ["src/ping.py"]
    assert out.changes[0].action == "create"


def test_reviewer_and_redteam_contracts() -> None:
    review = ReviewerOutput(verdict="approve", summary="ok")
    red = RedTeamOutput(severity="medium", should_block=False)
    assert review.verdict == "approve"
    assert red.should_block is False
