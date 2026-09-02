# Agents & Contracts

## Vai trò agent

Mỗi agent kế thừa `BaseAgent` (`agents/base.py`):

1. Load system prompt từ `prompts/<role>.md` + optional `.ai/agents/<role>.md`
2. Gọi `model.generate(...)` với `response_schema`
3. Ghi trace `agent_prompt` / `agent_response` (tokens + `cost_usd`)

| Role | Class | Contract output |
|---|---|---|
| manager | `ManagerAgent` | `ManagerPlan`, `ManagerDecision` |
| architect | `ArchitectAgent` | `ArchitectProposal` |
| researcher | `ResearcherAgent` | `ResearchFinding` |
| coder | `CoderAgent` | `CoderOutput` |
| reviewer | `ReviewerAgent` | `ReviewerOutput` |
| redteam | `RedTeamAgent` | `RedTeamOutput` |
| judge | `JudgeAgent` | `JudgeOutput` (debate only) |

## Contracts chính

Định nghĩa đầy đủ: `src/ai_team/agents/contracts.py`.

### ManagerPlan

```json
{
  "understanding": "string",
  "tasks": ["..."],
  "chosen_agents": ["architect", "coder"],
  "questions": [],
  "risks": [],
  "next_action": "string"
}
```

### ManagerDecision

```json
{
  "decision": "string",
  "approved": true,
  "confidence": 0.85,
  "reason": "string",
  "rejected_alternatives": [],
  "remaining_risks": [],
  "follow_up": "string"
}
```

### CoderOutput

```json
{
  "task": "string",
  "changes": [{"path": "src/foo.py", "action": "create", "content": "...", "reason": "..."}],
  "files_modified": ["src/foo.py"],
  "reasoning_summary": "string",
  "tests": ["pytest -q"],
  "risks": [],
  "needs_approval": true
}
```

### ReviewerOutput

`verdict`: `approve` | `request_changes` | `reject`

### RedTeamOutput

Bao gồm `failure_scenarios`, `should_block`, `severity`, `exploitability`.

## Prompts

| File | Agent |
|---|---|
| `prompts/manager.md` | Manager |
| `prompts/architect.md` | Architect |
| `prompts/researcher.md` | Researcher |
| `prompts/coder.md` | Coder |
| `prompts/reviewer.md` | Reviewer |
| `prompts/redteam.md` | Red Team |
| `prompts/judge.md` | Judge |

Override theo project: `.ai/agents/<role>.md` (được nối vào system prompt).

## Provider per role

Agent không gọi SDK trực tiếp — luôn qua `build_provider(settings, role)`.

Cấu hình:

- Env: `AI_TEAM_CODER_PROVIDER`, `AI_TEAM_CODER_MODEL`, …
- YAML: `.ai/config.yaml` → `agents.coder.provider/model`
- Phase 8 routing: override động theo tier (xem [routing.md](routing.md))

Thứ tự ưu tiên: xem [configuration.md](configuration.md).

## Mock provider

Khi `provider=openai` nhưng không có `OPENAI_API_KEY` → tự fallback `mock`.

Mock trả JSON hợp lệ theo contract — đủ cho CI, không phản ánh hành vi LLM thật (Coder mock luôn tạo `src/{auth|queue|feature}.py`).

## Judge vs Manager

- **Manager** — member team V1, điều phối mọi workflow
- **Judge** — chỉ trong `DebateEngine`, chấm điểm proposals và chốt verdict

Không nhầm với `orchestration/router.py` (`AgentRouter`) — chọn agent theo `ManagerPlan.chosen_agents`.
