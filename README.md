# AI-Team

Hệ thống **AI Development Team** chạy trên NAS/Docker: một Manager điều phối, các specialist agent dùng chung project memory, tranh luận khi bất đồng, Red Team tìm lỗi, Reviewer kiểm tra, Coder sửa code/chạy test, Git là checkpoint. Mọi hành động nguy hiểm đều qua approval. Mọi workflow đều có tracing/audit.

V1 dùng **OpenAI** làm model lõi. Claude, Gemini và OpenRouter đã có abstraction, chưa phải dependency cứng.

## V1 làm được gì

```text
User → Task → Manager → Architect → Researcher → Debate → Red Team
     → Decision → Coder → Tests → Reviewer → Approval → Git commit
```

Toàn bộ quá trình lưu lại trong SQLite + `.ai/` markdown.

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Gắn OPENAI_API_KEY. Nếu trống, hệ thống tự chuyển sang provider mock.
```

## CLI

```bash
ai-team init --name demo --purpose "Demo app"
ai-team ask "Thiết kế authentication"
ai-team research "So sánh Redis và RabbitMQ"
ai-team debate "Redis hay RabbitMQ?"
ai-team plan "Thêm authentication"
ai-team implement TASK-001
ai-team review TASK-001
ai-team status
```

`--yes` tự approve hành động MODERATE/DANGEROUS (dùng cho CI/demo, không dùng trên production).

Không có API key:

```bash
AI_TEAM_PROVIDER=mock ai-team plan "Thêm authentication"
```

## API

```bash
ai-team serve
```

| Method | Path |
|---|---|
| POST | `/projects` |
| POST | `/tasks` |
| POST | `/tasks/{id}/run` |
| POST | `/tasks/{id}/debate` |
| GET | `/tasks/{id}` |
| GET | `/agents` |
| GET | `/sessions` |
| GET | `/sessions/{id}/traces` |
| GET | `/decisions` |

Web UI **không** nằm trong V1.

## Docker / NAS

```bash
cp .env.example .env
docker compose up --build
```

- `ai-orchestrator`: Python orchestrator + HTTP API (`:8080`)
- `ai-mcp`: MCP stdio server (filesystem, git, shell) — bật bằng profile `mcp`

Mount project thật:

```bash
PROJECT_WORKSPACE=/volume1/projects/my-app docker compose up
```

## Shared project memory

Mỗi project có:

```text
project/
├── .ai/
│   ├── PROJECT.md
│   ├── RULES.md
│   ├── DECISIONS.md
│   ├── TASKS.md
│   ├── agents/
│   ├── discussions/
│   └── sessions/
├── src/
├── tests/
└── docs/
```

Đây là source of truth — không dựa vào conversation history.

## Agents (V1)

| Agent | Vai trò |
|---|---|
| Manager | Điều phối, phân task, quyết định. Không sửa code. |
| Architect | Kiến trúc, trade-off |
| Researcher | Nghiên cứu phương án |
| Coder | Viết/sửa code, đề xuất test |
| Reviewer | Code/design có đúng không? |
| Red Team | Làm sao chứng minh phương án này sai? |

Output của agent là **contract JSON**, không phải văn nói tự do.

## Permission model

| Mức | Ví dụ | Approval |
|---|---|---|
| SAFE | đọc file, search, test không phá dữ liệu | tự chạy |
| MODERATE | sửa source, cài dependency, `git commit` | Manager |
| DANGEROUS | `git push`, `docker compose down -v`, xóa data | User `[y/N]` |

## Model providers

Agent chỉ gọi `model.generate(...)`.

- `OpenAIProvider` (V1)
- `AnthropicProvider`
- `GoogleProvider`
- `OpenRouterProvider`
- `MockProvider` (test / không có API key)

Cấu hình:

```bash
AI_TEAM_PROVIDER=openai
AI_TEAM_MODEL=gpt-4o
AI_TEAM_CODER_MODEL=gpt-4o
```

## MCP (V1)

```bash
ai-team mcp
```

Tools: `filesystem`, `git`, `shell` (+ `docker` khi có CLI).

## Database

SQLite tại `.ai/ai-team.db`:

`projects`, `tasks`, `agents`, `sessions`, `messages`, `decisions`, `reviews`, `tool_calls`, `approvals`, `trace_events`.

Không dùng vector DB trong V1. Context engine chọn file/docs/decisions/diff liên quan theo task.

## Tests

```bash
pytest -q
```

## Nguyên tắc thiết kế

1. Multi-agent không mặc định tốt hơn single-agent.
2. Agent phải có role và contract rõ ràng.
3. Shared project state là source of truth.
4. Không để agent tự ý làm destructive actions.
5. Proposal → Review → Debate → Decision → Implementation.
6. Red Team phải tìm lỗi, không phải đồng ý.
7. Không nhét cả codebase vào prompt.
8. Không khóa kiến trúc vào một model provider.
9. V1 ưu tiên chạy ổn định hơn UI đẹp.
10. Mọi decision và tool call quan trọng đều có audit trail.

## Roadmap đã làm / chưa làm

Đã có (Phase 0–6, MCP V1, API): CLI, 6 agent, memory, tools, debate, coder+tests, approval, tracing, Docker.

Chưa làm (đúng theo plan): Web UI, vector DB, Claude/Gemini routing production, MCP V2/V3 (GitHub, Postgres, NAS…).
