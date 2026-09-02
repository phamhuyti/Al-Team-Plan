# Cấu hình

## Hai lớp cấu hình

1. **Repo / process** — `.env` hoặc biến môi trường `AI_TEAM_*`
2. **Per project** — `.ai/config.yaml` (sau `ai-team init`)

## Thứ tự ưu tiên

Cao → thấp:

1. Constructor `Settings(...)` / test fixtures (field được set rõ)
2. Env role-specific: `AI_TEAM_CODER_MODEL`, `AI_TEAM_CODER_PROVIDER`
3. `.ai/config.yaml` — **chỉ ghi đè field chưa set rõ** (`exclude_unset`)
4. Env global: `AI_TEAM_PROVIDER`, `AI_TEAM_MODEL`
5. Default trong code

## Biến môi trường chính

| Biến | Mặc định | Mô tả |
|---|---|---|
| `AI_TEAM_PROVIDER` | `openai` | `mock`, `openai`, `anthropic`, `google`, `openrouter` |
| `AI_TEAM_MODEL` | `gpt-4o` | Model global fallback |
| `AI_TEAM_{ROLE}_PROVIDER` | — | Override theo role (MANAGER, CODER, …) |
| `AI_TEAM_{ROLE}_MODEL` | — | Override model theo role |
| `OPENAI_API_KEY` | — | Bắt buộc nếu provider=openai (không có → mock) |
| `ANTHROPIC_API_KEY` | — | Cho anthropic |
| `GOOGLE_API_KEY` | — | Cho google |
| `OPENROUTER_API_KEY` | — | Cho openrouter |
| `AI_TEAM_DATABASE_URL` | `sqlite:///./.ai/ai-team.db` | SQLite path |
| `AI_TEAM_AUTO_APPROVE_MODERATE` | `false` | Tự approve MODERATE |
| `AI_TEAM_AUTO_APPROVE_DANGEROUS` | `false` | Tự approve DANGEROUS |
| `AI_TEAM_DEBATE_ROUNDS` | `2` | Số round debate |
| `AI_TEAM_MAX_REVIEW_LOOPS` | `2` | Vòng review tối đa |
| `AI_TEAM_MAX_CONTEXT_CHARS` | `80000` | Giới hạn context bundle |
| `AI_TEAM_WEB_SEARCH_ENABLED` | `true` | Bật web search |
| `AI_TEAM_WEB_SEARCH_BACKEND` | `duckduckgo` | `duckduckgo`, `mock`, `off` |
| `AI_TEAM_ROUTING_ENABLED` | — | Override routing (thường dùng YAML) |
| `AI_TEAM_ROUTING_STRATEGY` | — | `balanced`, `cost_optimized`, `quality` |
| `AI_TEAM_ROUTING_BUDGET_USD` | — | Budget USD / session |
| `AI_TEAM_API_HOST` | `0.0.0.0` | API bind |
| `AI_TEAM_API_PORT` | `8080` | API port |

Xem đầy đủ: `.env.example`.

## `.ai/config.yaml`

Template: `templates/project/.ai/config.yaml`.

### `agents`

```yaml
agents:
  manager:
    provider: openai
    model: gpt-4o
  coder:
    provider: anthropic
    model: claude-sonnet-4-5
```

### `permissions`

```yaml
permissions:
  auto_approve_moderate: false
  auto_approve_dangerous: false
```

Chỉ áp dụng khi env `AI_TEAM_AUTO_APPROVE_*` **không** set.

### `git`

```yaml
git:
  branch_prefix: ai/
  auto_commit: true
  auto_push: false   # push = DANGEROUS, luôn cần user approval
```

### `web`

```yaml
web:
  enabled: true
  backend: duckduckgo   # mock | off
  max_results: 5
```

### `routing` (Phase 8)

```yaml
routing:
  enabled: false
  strategy: balanced          # cost_optimized | quality
  budget_usd_per_session: 2.0
  tiers:
    simple:
      coder: {provider: openai, model: gpt-4o-mini}
    complex:
      coder: {provider: anthropic, model: claude-sonnet-4-5}
```

Chi tiết: [routing.md](routing.md).

## Reload config

Config YAML được đọc khi khởi tạo `TeamRuntime`. Đổi YAML → restart `serve` hoặc tạo runtime mới.

## Cost estimation

`cost_usd` tính từ `models/pricing.py` (ước lượng per 1M tokens). **Không** phải invoice provider thật.
