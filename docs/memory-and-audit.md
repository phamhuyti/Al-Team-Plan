# Memory & Audit

## Shared project memory (`.ai/`)

Source of truth cho team — **không** dựa conversation history.

| File / thư mục | Mục đích |
|---|---|
| `PROJECT.md` | Mô tả project, mục tiêu |
| `RULES.md` | Quy tắc coding, approval |
| `DECISIONS.md` | Log quyết định (mirror SQLite) |
| `TASKS.md` | Bảng task human-readable |
| `config.yaml` | Cấu hình runtime |
| `agents/*.md` | Ghi chú per-role override prompt |
| `discussions/*.md` | Transcript debate |
| `sessions/*.md` | Log session (optional markdown) |

`ProjectMemory` (`memory/project.py`) đọc/ghi các file này.

## SQLite (`.ai/ai-team.db`)

URL: `AI_TEAM_DATABASE_URL` hoặc mặc định `sqlite:///./.ai/ai-team.db`.

### Bảng chính

| Bảng | Nội dung |
|---|---|
| `projects` | Root path, config snapshot |
| `tasks` | TASK-001, title, status, description |
| `agents` | Role, provider, model (seed từ settings) |
| `sessions` | kind, status, task_id, timestamps |
| `decisions` | decision, reason, confidence, risks |
| `tool_calls` | tool name, args, output, risk |
| `approvals` | pending/approved/denied |
| `trace_events` | step, actor, payload, tokens, cost_usd |

## Context engine

`context/engine.py` — retrieval **keyword-based**:

- Quét `.ai/*.md`, docs, source paths liên quan task
- Không vector DB V1
- Giới hạn `AI_TEAM_MAX_CONTEXT_CHARS`

**Không** dump toàn bộ repo vào prompt.

## Tracing

`Tracer` (`tracing/audit.py`) emit các step:

| Step | Ý nghĩa |
|---|---|
| `task` | Bắt đầu workflow / user request |
| `routing` | Phase 8 snapshot |
| `agent_prompt` | Input rút gọn |
| `agent_response` | Output + tokens + cost |
| `tool_call` | Tool execution |
| `decision` | Manager decision recorded |

## Cost tracking

Mỗi `agent_response` tính:

```text
cost_usd = estimate_cost_usd(model, tokens_in, tokens_out)
```

Aggregate:

- `GET /sessions/{id}/cost`
- `GET /dashboard`
- `ai-team replay SESSION_ID`

Bảng giá: `models/pricing.py` (ước lượng per 1M tokens).

## Replay

```bash
ai-team replay 42
```

Trả về:

- `session` metadata
- `timeline` — events rút gọn
- `cost` — tổng tokens + USD
- `markdown` — nội dung `sessions/42.md` nếu có

Dùng để debug workflow và audit sau implement.

## Retention

V1 **không** tự purge — DB và markdown tăng theo thời gian. Trên NAS nên backup định kỳ `.ai/`.

## Backup khuyến nghị

```bash
tar czf ai-team-backup-$(date +%F).tar.gz .ai/
```

Hoặc snapshot volume Docker `ai-team-data`.
