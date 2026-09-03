# MCP (Model Context Protocol)

## Khởi động

```bash
ai-team mcp [--project PATH]
```

JSON-RPC **stdio** — một message JSON mỗi dòng.

Docker (profile riêng):

```bash
docker compose --profile mcp up --build
```

Service `ai-mcp` không expose port — client (Cursor, v.v.) attach stdio.

## Methods

| Method | Mô tả |
|---|---|
| `tools/list` | Liệt kê tools |
| `tools/call` | Gọi tool |

## Tools V1

| Tool | Risk | Mô tả |
|---|---|---|
| `fs_read` | SAFE | Đọc file trong project root |
| `fs_write` | MODERATE | Ghi file |
| `fs_list` | SAFE | List directory |
| `fs_delete` | DANGEROUS | Xóa file |
| `git` | Theo subcommand | Wrapper `git` |
| `shell` | Theo command | Chạy shell trong project root |
| `web_search` | SAFE | DuckDuckGo / mock / off |

Implementation: `tools/registry.py`, expose qua `mcp/server.py`.

## Ví dụ `tools/list`

Request:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

## Ví dụ `web_search`

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "web_search",
    "arguments": {"query": "OAuth2 best practices", "max_results": 3}
  }
}
```

## Web search backends

| Backend | Khi nào dùng |
|---|---|
| `duckduckgo` | Mặc định — không cần API key |
| `mock` | CI / offline — trả kết quả giả |
| `off` | Tắt hoàn toàn |

Cấu hình: `.ai/config.yaml` → `web.backend` hoặc `AI_TEAM_WEB_SEARCH_BACKEND`.

## Giới hạn V1

- MCP V1 = filesystem + git + shell + web_search
- **Chưa có** MCP V2 (GitHub API, Postgres, …)
- Docker tool có trong codebase (`tools/docker.py`) nhưng không phải focus MCP V1

## Test

```bash
pytest tests/test_mcp.py tests/test_web_search.py -q
```

## Tích hợp Cursor

Attach MCP server `ai-team mcp` với project root = workspace đang dev. Tools tuân permission model khi gọi qua orchestrator; MCP stdio trực tiếp **không** qua ApprovalGate — cẩn thận khi expose.
