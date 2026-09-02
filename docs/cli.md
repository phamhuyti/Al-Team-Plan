# CLI Reference

```bash
ai-team --help
ai-team <command> --help
```

Global: `--project PATH` / `-p` chọn project root (mặc định `cwd`).

## Lệnh

### `init`

```bash
ai-team init [PATH] --name NAME --purpose "..."
```

Tạo `.ai/` memory, copy template, `git init` nếu chưa có repo.

### `ask`

```bash
ai-team ask "Thiết kế authentication" [--yes]
```

Manager điều phối Architect + Researcher → decision.

### `research`

```bash
ai-team research "Redis vs RabbitMQ"
```

Chỉ Researcher (+ web search).

### `debate`

```bash
ai-team debate "Monolith hay microservices?"
```

Debate + Judge, ghi discussion.

### `plan`

```bash
ai-team plan "Thêm authentication" [--yes]
```

Tạo `TASK-xxx`, chạy full planning pipeline.

### `implement`

```bash
ai-team implement TASK-001 [--yes]
```

Coder → tests → review → red team → commit.

### `review`

```bash
ai-team review TASK-001
```

Reviewer + Red Team trên task hiện có.

### `status`

```bash
ai-team status
```

In bảng: tasks, agents (provider/model), sessions gần đây.

### `replay`

```bash
ai-team replay SESSION_ID [--json]
```

Timeline + cost từ SQLite traces.

### `serve`

```bash
ai-team serve [--host HOST] [--port PORT] [--project PATH]
```

Khởi động FastAPI + Web UI. Project root **cố định** lúc startup.

### `mcp`

```bash
ai-team mcp [--project PATH]
```

MCP JSON-RPC stdio — tools: filesystem, git, shell, web_search.

## Flags quan trọng

| Flag | Ý nghĩa |
|---|---|
| `--yes` | Auto-approve MODERATE + DANGEROUS |
| `--project PATH` | Project root (bắt buộc khi CLI từ repo khác project) |
| `--json` | Output JSON (replay) |

## Ví dụ NAS workflow

```bash
cd /volume1/projects/my-app
/path/to/Al-Team-Plan/.venv/bin/ai-team plan "Fix login bug"
/path/to/Al-Team-Plan/.venv/bin/ai-team implement TASK-003
```

Demo project **không** có `.venv` riêng — dùng venv của repo AI-Team.

## Exit codes

- `0` — thành công
- `1` — lỗi (unknown task, approval denied, v.v.)
