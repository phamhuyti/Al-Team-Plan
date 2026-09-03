# Kiến trúc

## Sơ đồ lớp

```text
┌─────────────────────────────────────────────────────────┐
│  User: CLI · HTTP API · Web UI · MCP client             │
└───────────────────────────┬─────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│  TeamRuntime (orchestration/workflow.py)                │
│  plan · implement · ask · debate · research · review    │
└───────────────────────────┬─────────────────────────────┘
                            ▼
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   Agents (6)         DebateEngine          ApprovalGate
        │                   │                   │
        ▼                   ▼                   ▼
  ModelProvider        JudgeAgent          SQLite approvals
  (+ ModelRouter)                           │
        │                                   ▼
        ▼                              ToolRegistry
  ContextEngine ──► ProjectMemory (.ai/*.md)
        │
        ▼
  Tracer ──► TraceEvent (cost, tokens, audit)
```

## Luồng `implement` (rút gọn)

```text
create branch → Coder (file changes) → shell tests
    → Reviewer loop → Red Team → Manager approve
    → git commit (MODERATE) → session finish
```

Nếu `git push` hoặc lệnh DANGEROUS → ApprovalGate chặn hoặc defer (API).

## Bản đồ code

```text
src/ai_team/
  main.py                    CLI (Typer)
  api/app.py                 FastAPI + Web UI mount
  web/static/                Phase 7 UI assets
  config.py                  Settings, apply_project_config
  orchestration/
    workflow.py              ★ Pipeline chính
    debate.py                Phát hiện disagreement, rounds
    judge.py                 Judge agent
    router.py                Chọn agent theo ManagerPlan (khác model routing)
  agents/                    6 role + contracts.py
  models/
    factory.py               build_provider
    routing.py               Phase 8 ModelRouter
    pricing.py               cost_usd ước lượng
    {openai,anthropic,...}.py
  memory/                    SQLite + markdown project memory
  context/engine.py          Retrieval keyword (không vector)
  tools/                     fs, git, shell, docker, web
  mcp/server.py              JSON-RPC stdio
  security/
    permissions.py           Phân loại risk
    approvals.py             Gate + defer mode
  tracing/audit.py           Tracer → trace_events
prompts/                     System prompt theo role
templates/project/           Skeleton `ai-team init`
tests/                       pytest (mock provider)
```

## Entry points

| Binary | Module | Mô tả |
|---|---|---|
| `ai-team` | `ai_team.main:app` | CLI |
| `ai-team serve` | `ai_team.api.app:create_app` | HTTP |
| `ai-team mcp` | `ai_team.mcp.server:serve_stdio` | MCP |

## Runtime per project

Mỗi thư mục project (sau `ai-team init`):

- `.ai/config.yaml` — cấu hình agent, git, web, routing
- `.ai/ai-team.db` — SQLite (hoặc path từ `AI_TEAM_DATABASE_URL`)
- `.ai/*.md` — shared memory (source of truth)

`ai-team serve` **cố định project root lúc startup** (`cwd` hoặc `--project`). HTTP không đổi root theo request.

## Quyết định kỹ thuật đã chốt

| Chủ đề | Quyết định |
|---|---|
| Database | SQLite V1; không Postgres |
| Context | Keyword + path; không vector DB V1 |
| Agent output | JSON contract bắt buộc |
| History | `.ai/` markdown, không chat history |
| `git commit` | MODERATE (Manager approval) |
| `git push` | DANGEROUS (user approval) |
| Không có OpenAI key | Fallback `mock` provider |
| Debate engine | Tên `debate_engine` (tránh shadow method `debate`) |

## Mở rộng an toàn

| Muốn thêm… | Sửa ở… |
|---|---|
| Agent mới | `agents/`, `contracts.py`, `workflow.py`, `prompts/` |
| Provider mới | `models/`, `factory.py`, `config.py` |
| Tool mới | `tools/`, `registry.py`, `permissions.py`, `mcp/server.py` |
| Workflow step | `orchestration/workflow.py` + test `test_workflow.py` |
| API endpoint | `api/app.py` + `tests/test_api.py` hoặc `test_web_ui.py` |

Xem [guidelines.md](guidelines.md) trước khi sửa.
