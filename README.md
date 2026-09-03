# AI-Team

Multi-agent **AI Development Team** chạy trên NAS/Docker.

Một Manager điều phối toàn bộ dự án. Architect, Researcher, Coder, Reviewer và Red Team dùng chung project memory, có thể tranh luận, phản biện và ghi quyết định. Coder đọc/sửa code, chạy test và commit Git. Hành động nguy hiểm luôn cần approval. Mọi workflow đều có tracing/audit.

> V1 dùng **OpenAI** làm model lõi. Claude, Gemini và OpenRouter đã có abstraction — chưa phải dependency cứng.

[Yêu cầu](#yêu-cầu) · [Cài đặt](#cài-đặt) · [Quick start](#quick-start) · [CLI](#cli) · [Docker](#docker--nas) · [Kiến trúc](#kiến-trúc) · **[Tài liệu đầy đủ](docs/README.md)** · **[GitHub Page](https://phamhuyti.github.io/Al-Team-Plan/)**

---

## V1 success path

```text
User → Task → Manager → Architect → Researcher → Debate → Red Team
     → Decision → Coder → Tests → Reviewer → Approval → Git commit
```

Toàn bộ quá trình được lưu trong SQLite (`.ai/ai-team.db`) và markdown (`.ai/`).

---

## Yêu cầu

- Python 3.11+
- Git
- Docker + Docker Compose (nếu chạy trên NAS)
- `OPENAI_API_KEY` cho model thật — không có key thì hệ thống tự dùng **mock provider**

---

## Cài đặt

Clone repo rồi cài package:

```bash
git clone https://github.com/phamhuyti/Al-Team-Plan.git
cd Al-Team-Plan
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Mở `.env` và gắn key (tùy chọn):

```bash
OPENAI_API_KEY=sk-...
AI_TEAM_PROVIDER=openai
AI_TEAM_MODEL=gpt-4o
```

Nếu để trống `OPENAI_API_KEY`, chạy với:

```bash
AI_TEAM_PROVIDER=mock
```

---

## Quick start

```bash
ai-team init --name demo --purpose "Demo app"
ai-team plan "Thêm authentication"
ai-team implement TASK-001
ai-team status
```

Chạy demo không cần API key:

```bash
AI_TEAM_PROVIDER=mock ai-team init --name demo
AI_TEAM_PROVIDER=mock ai-team plan "Thêm authentication"
AI_TEAM_PROVIDER=mock ai-team implement TASK-001 --yes
```

`--yes` tự approve hành động MODERATE/DANGEROUS. Chỉ dùng cho CI/demo, không dùng trên production.

---

## CLI

| Lệnh | Việc làm |
|---|---|
| `ai-team init` | Tạo `.ai/` memory + git repo |
| `ai-team ask "..."` | Manager điều phối câu trả lời |
| `ai-team research "..."` | Researcher |
| `ai-team debate "..."` | Debate + Judge |
| `ai-team plan "..."` | Tạo task, design, Red Team, decision |
| `ai-team implement TASK-001` | Coder → test → review → commit |
| `ai-team review TASK-001` | Reviewer + Red Team |
| `ai-team status` | Tasks, agents, sessions |
| `ai-team replay SESSION_ID` | Xem lại timeline / cost của session |
| `ai-team serve` | HTTP API (`:8080`) |
| `ai-team mcp` | MCP stdio (filesystem, git, shell, web_search) |

Ví dụ:

```bash
ai-team ask "Thiết kế authentication"
ai-team research "So sánh Redis và RabbitMQ"
ai-team debate "Redis hay RabbitMQ?"
ai-team plan "Thêm authentication"
ai-team implement TASK-001
ai-team review TASK-001
ai-team status
```

---

## API

```bash
ai-team serve
```

| Method | Path |
|---|---|
| `GET` | `/health` |
| `GET` | `/dashboard` |
| `GET` | `/routing/preview` |
| `POST` | `/chat` |
| `GET` | `/tasks` |
| `POST` | `/projects` |
| `POST` | `/tasks` |
| `POST` | `/tasks/{id}/run` |
| `POST` | `/tasks/{id}/debate` |
| `GET` | `/tasks/{id}` |
| `GET` | `/agents` |
| `GET` | `/sessions` |
| `GET` | `/sessions/{id}/traces` |
| `GET` | `/sessions/{id}/cost` |
| `GET` | `/sessions/{id}/replay` |
| `GET` | `/approvals` |
| `GET` | `/approvals/{id}` |
| `POST` | `/approvals/{id}` |
| `GET` | `/decisions` |

`POST /approvals/{id}` body: `{"approved": true, "reason": ""}`. Khi chạy task với `"yes": false`, hành động DANGEROUS tạo approval `pending` — approve rồi chạy lại.

Mỗi project có thể ghi đè provider/model theo role trong `.ai/config.yaml` (ưu tiên sau env role-specific như `AI_TEAM_CODER_PROVIDER`).

Researcher có thể gọi `web_search` (DuckDuckGo, không cần API key). Tắt bằng `AI_TEAM_WEB_SEARCH_ENABLED=false` hoặc `backend: off` trong `.ai/config.yaml`. CI/demo dùng `AI_TEAM_WEB_SEARCH_BACKEND=mock`.

### Web UI (Phase 7)

Chạy `ai-team serve` rồi mở `http://localhost:8080/`:

- **Dashboard** — agents, sessions, decisions, routing preview
- **Tasks** — tạo task, chạy plan/implement
- **Live Chat** — ask / research / debate / plan qua API + SSE traces
- **Approvals** — duyệt/từ chối pending approvals
- **Cost Monitor** — tổng cost project và theo session

### Routing (Phase 8)

Bật trong `.ai/config.yaml`:

```yaml
routing:
  enabled: true
  strategy: cost_optimized   # balanced | quality
  budget_usd_per_session: 2.0
  tiers:
    simple:
      coder: {provider: openai, model: gpt-4o-mini}
    complex:
      coder: {provider: anthropic, model: claude-sonnet-4-5}
```

Mỗi workflow ghi trace `routing` và chọn model theo độ phức tạp task + budget session.

---

## Docker / NAS

```bash
cp .env.example .env
docker compose up --build
```

| Service | Vai trò |
|---|---|
| `ai-orchestrator` | Orchestrator + HTTP API tại `:8080` |
| `ai-mcp` | MCP stdio — bật bằng profile `mcp` |

Gắn project thật trên NAS:

```bash
PROJECT_WORKSPACE=/volume1/projects/my-app docker compose up --build
```

Bật MCP:

```bash
docker compose --profile mcp up --build
```

---

## Kiến trúc

```text
                         YOU
                          │
                          ▼
                       MANAGER
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   ARCHITECT           CODER          RESEARCHER
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
                      REVIEWER
                          │
                          ▼
                       RED TEAM
                          │
                          ▼
                        JUDGE
                          │
                          ▼
                       MANAGER
                     approve / reject
                          │
                          ▼
                  CODER → TEST → COMMIT
```

Lớp chính: CLI/API → Orchestrator → Agents → Model Provider → Context/Memory → MCP/Tools → Git → SQLite → Tracing → Approval.

### Agents V1

| Agent | Vai trò |
|---|---|
| Manager | Điều phối, phân task, quyết định. **Không sửa code.** |
| Architect | Kiến trúc, trade-off |
| Researcher | Nghiên cứu phương án |
| Coder | Viết/sửa code, đề xuất test |
| Reviewer | Code/design có đúng không? |
| Red Team | Làm sao chứng minh phương án này sai? |

Output của agent là **contract JSON**, không phải văn nói tự do.

### Permission model

| Mức | Ví dụ | Approval |
|---|---|---|
| SAFE | đọc file, search, test không phá dữ liệu | tự chạy |
| MODERATE | sửa source, cài dependency, `git commit` | Manager |
| DANGEROUS | `git push`, `docker compose down -v`, xóa data | User `[y/N]` |

### Model providers

Agent chỉ gọi `model.generate(...)`:

- `OpenAIProvider` — V1
- `AnthropicProvider`
- `GoogleProvider`
- `OpenRouterProvider`
- `MockProvider` — test / không có API key

```bash
AI_TEAM_PROVIDER=openai
AI_TEAM_MODEL=gpt-4o
AI_TEAM_CODER_MODEL=gpt-4o
```

---

## Shared project memory

Mỗi project do `ai-team init` tạo ra:

```text
project/
├── .ai/
│   ├── PROJECT.md
│   ├── RULES.md
│   ├── DECISIONS.md
│   ├── TASKS.md
│   ├── config.yaml
│   ├── agents/
│   ├── discussions/
│   └── sessions/
├── src/
├── tests/
└── docs/
```

Đây là source of truth — không dựa vào conversation history.

Git branch convention:

```text
ai/TASK-001-authentication
```

---

## Cấu trúc repo

```text
Al-Team-Plan/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── src/ai_team/          # orchestrator, agents, tools, API
├── prompts/              # system prompts theo role
├── templates/project/    # skeleton .ai/ khi `ai-team init`
├── tests/
└── projects/             # workspace runtime (không commit code app)
```

---

## Database & audit

SQLite tại `.ai/ai-team.db`:

`projects`, `tasks`, `agents`, `sessions`, `messages`, `decisions`, `reviews`, `tool_calls`, `approvals`, `trace_events`.

Không dùng vector DB trong V1. Context engine chọn file/docs/decisions/diff liên quan theo task.

---

## Tests

```bash
pytest -q
```

---

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

---

## Roadmap

| Phase | Nội dung | V1 |
|---|---|---|
| 0–1 | Architecture, Python, OpenAI, Manager, CLI | Có |
| 2 | Architect, Researcher, Coder, Reviewer, Red Team | Có |
| 3 | `.ai/` memory, sessions, context engine | Có |
| 4 | Filesystem, Git, Shell, MCP | Có |
| 5 | Debate, Judge, decision records | Có |
| 6 | Branch, code, tests, review, approval, commit | Có |
| 7 | Web UI dashboard, chat, tasks, approvals, cost | Có |
| 8 | Claude / Gemini / OpenRouter routing + cost optimization | Có |

---

## License

MIT

## Handoff cho agent/dev tiếp theo

- **[GitHub Page (giới thiệu trực quan)](https://phamhuyti.github.io/Al-Team-Plan/)** — landing + hướng dẫn
- **[docs/README.md](docs/README.md)** — tài liệu đầy đủ + guidelines
- **[docs/guidelines.md](docs/guidelines.md)** — quy tắc sử dụng & phát triển
- [HANDOFF.md](HANDOFF.md) — trạng thái repo, bản đồ code, việc còn đọng
