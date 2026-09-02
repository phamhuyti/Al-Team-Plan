# HTTP API Reference

Base URL: `http://localhost:8080` (sau `ai-team serve`).

OpenAPI tự động: `http://localhost:8080/docs` (Swagger UI).

## Health & dashboard

### `GET /health`

```json
{"status": "ok"}
```

### `GET /dashboard`

Tổng hợp cost project + routing flags.

```json
{
  "sessions": 3,
  "events": 24,
  "tokens_in": 5000,
  "tokens_out": 1200,
  "cost_usd": 0.045,
  "pending_approvals": 1,
  "project": "/path/to/project",
  "routing_enabled": false,
  "routing_strategy": "balanced"
}
```

### `GET /routing/preview?prompt=...`

Xem routing snapshot cho một prompt (không chạy workflow).

## Projects

### `GET /projects`

Project hiện tại (root cố định lúc `serve`).

### `POST /projects`

```json
{"path": "/tmp/new-app", "name": "demo", "purpose": "..."}
```

## Tasks

### `GET /tasks`

Danh sách task.

### `POST /tasks`

```json
{"title": "Add auth", "description": "OAuth2 login"}
```

### `GET /tasks/{task_key}`

Chi tiết một task.

### `POST /tasks/{task_key}/run`

```json
{
  "command": "implement",
  "prompt": "",
  "yes": true
}
```

`command`: `implement` | `plan` | `review`

Response:

```json
{
  "ok": true,
  "summary": "...",
  "details": {},
  "session_id": 7,
  "needs_approval": false
}
```

`409` + `detail.needs_approval` nếu `ApprovalPending` và `yes: false`.

### `POST /tasks/{task_key}/debate`

```json
{"prompt": "Redis or RabbitMQ?", "yes": true}
```

## Chat (Web UI / automation)

### `POST /chat`

```json
{
  "mode": "ask",
  "message": "Thiết kế authentication",
  "yes": true
}
```

`mode`: `ask` | `research` | `debate` | `plan`

## Agents & sessions

### `GET /agents`

```json
[{"name": "coder", "role": "coder", "provider": "openai", "model": "gpt-4o"}]
```

### `GET /sessions`

50 session gần nhất.

### `GET /sessions/{id}/traces`

Trace events theo thứ tự thời gian.

### `GET /sessions/{id}/cost`

```json
{
  "session_id": 1,
  "events": 8,
  "tokens_in": 1200,
  "tokens_out": 400,
  "cost_usd": 0.012
}
```

### `GET /sessions/{id}/replay`

Timeline đầy đủ + cost + markdown log.

### `GET /sessions/{id}/events` (SSE)

Server-Sent Events cho live UI. Message types: `trace`, `result`, `done`.

## Approvals

### `GET /approvals?status=pending`

### `GET /approvals/{id}`

### `POST /approvals/{id}`

```json
{"approved": true, "reason": "ship it"}
```

Sau approve, chạy lại task/command bị defer.

## Decisions

### `GET /decisions`

Danh sách quyết định đã ghi.

## Ví dụ curl

```bash
# Plan
curl -X POST http://localhost:8080/tasks/TASK-001/run \
  -H 'Content-Type: application/json' \
  -d '{"command":"plan","prompt":"Add auth","yes":true}'

# Chat research
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"mode":"research","message":"Redis vs RabbitMQ","yes":true}'

# Approve dangerous action
curl -X POST http://localhost:8080/approvals/3 \
  -H 'Content-Type: application/json' \
  -d '{"approved":true,"reason":"ok"}'
```
