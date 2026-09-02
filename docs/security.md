# Security & Approvals

## Permission model

Ba mức (`security/permissions.py`):

| Mức | Ai approve | Ví dụ |
|---|---|---|
| **SAFE** | Tự động | `fs_read`, `web_search`, `git status`, `git diff` |
| **MODERATE** | Manager (hoặc auto) | `fs_write`, `git commit`, `pip install`, `docker build` |
| **DANGEROUS** | User (hoặc auto) | `git push`, `rm -rf`, `docker compose down -v`, `DROP TABLE` |

## Phân loại tool

| Tool | SAFE | MODERATE | DANGEROUS |
|---|---|---|---|
| `fs_read`, `fs_list`, `web_search` | ✓ | | |
| `fs_write`, `fs_mkdir` | | ✓ | |
| `fs_delete` | | | ✓ |
| `git status/diff/log` | ✓ | | |
| `git add/commit/checkout` | | ✓ | |
| `git push/reset --hard` | | | ✓ |
| `shell` | Theo regex command | | |

Logic: `classify_tool(name, arguments)`.

## ApprovalGate

`security/approvals.py`:

```text
require(action, risk, requested_by)
    → auto_approve? → approved
    → defer mode?   → raise ApprovalPending (API)
    → TTY prompt?   → [y/N]
    → denied        → ApprovalDenied
```

### Chế độ CLI

```bash
ai-team implement TASK-001          # hỏi approval khi cần
ai-team implement TASK-001 --yes    # auto-approve (CI/demo only)
```

### Chế độ API

```json
{"yes": false}
```

→ `defer_approvals=True` → tạo row `pending` trong SQLite → HTTP 409 hoặc `needs_approval` trong response.

Approve:

```bash
curl -X POST http://localhost:8080/approvals/5 \
  -d '{"approved":true,"reason":"ok"}'
```

Chạy lại command — gate **reuse** approval vừa approve (one-shot).

### Config auto-approve

```yaml
# .ai/config.yaml
permissions:
  auto_approve_moderate: false
  auto_approve_dangerous: false
```

```bash
AI_TEAM_AUTO_APPROVE_MODERATE=true   # env override YAML
```

**Không** bật `auto_approve_dangerous` trên production NAS trừ khi bạn hiểu rủi ro.

## Git rules (đã chốt)

| Action | Risk |
|---|---|
| `git commit` | MODERATE |
| `git push` | DANGEROUS — **luôn** cần user |

`git.auto_push: false` mặc định trong config template.

## Web UI

Tab **Approvals** — duyệt pending mà không cần TTY.

## Audit

Mọi tool call quan trọng ghi `tool_calls` + `trace_events`. Approval rows trong bảng `approvals`.

## Threat model V1 (giới hạn)

- **Không có auth** trên HTTP API / Web UI
- **Không sandbox** shell — Coder chạy lệnh trong project root
- Chỉ expose LAN hoặc qua reverse proxy có auth
- Mock provider không gọi network nhưng vẫn có thể chạy shell thật nếu workflow implement

## Checklist production

- [ ] `auto_approve_dangerous: false`
- [ ] Không dùng `--yes` trên workflow tự động
- [ ] API chỉ listen nội bộ hoặc sau VPN
- [ ] Review `.ai/RULES.md` cho project
- [ ] Backup `.ai/` và git repo trước implement lớn
