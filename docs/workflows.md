# Workflows

Tất cả workflow chạy qua `TeamRuntime` (`orchestration/workflow.py`).

## Tổng quan

| Workflow | CLI | API / UI | Session kind |
|---|---|---|---|
| Ask | `ai-team ask` | `POST /chat` mode=ask | `ask` |
| Research | `ai-team research` | `POST /chat` mode=research | `research` |
| Debate | `ai-team debate` | `POST /chat` mode=debate | `debate` |
| Plan | `ai-team plan` | `POST /chat` mode=plan | `plan` |
| Implement | `ai-team implement TASK-xxx` | `POST /tasks/{key}/run` | `implement` |
| Review | `ai-team review TASK-xxx` | `POST /tasks/{key}/run` command=review | `review` |

Mỗi session ghi traces; kết thúc có thể `ai-team replay SESSION_ID`.

## `ask`

```text
Manager.plan → Architect → web_search → Researcher → Manager.decide → Decision record
```

Dùng khi cần câu trả lời / quyết định thiết kế **không** tạo task implement.

## `plan`

```text
create TASK-xxx → Manager → Architect → Researcher → Debate (optional)
    → Red Team → Manager.decide → update TASKS.md + decision
```

Task status: `planning` → `planned` (hoặc tương đương).

## `implement`

```text
git branch ai/TASK-xxx-...
Coder loop (changes + apply files)
shell tests (pytest)
Reviewer loop (max AI_TEAM_MAX_REVIEW_LOOPS)
Red Team
Manager approval
git commit (nếu git_auto_commit)
```

Có thể dừng với `needs_approval` nếu DANGEROUS action pending.

## `debate`

```text
Architect + Researcher (+ Coder) proposals
→ disagreement detection
→ rounds (AI_TEAM_DEBATE_ROUNDS)
→ Judge verdict
→ DECISIONS.md + discussions/
```

`force=True` (CLI `debate`) luôn chạy rounds; trong `plan` chỉ debate khi detect disagreement.

## `research`

```text
web_search (optional) → Researcher → ResearchFinding
```

Web search: DuckDuckGo (default), `mock` (CI), `off`.

## Routing trace (Phase 8)

Đầu mỗi workflow (ask/plan/implement/…), runtime gọi `ModelRouter` và emit trace step `routing` với snapshot tier + model per role.

## Approval trong workflow

| Mode | Hành vi |
|---|---|
| CLI không `--yes` | Prompt TTY `[y/N]` cho MODERATE/DANGEROUS |
| CLI `--yes` | Auto-approve tất cả |
| API `yes: true` | Auto-approve |
| API `yes: false` | `defer` — tạo approval `pending`, trả 409 hoặc `needs_approval` trong body |

Sau approve qua `POST /approvals/{id}`, chạy lại command.

## Git branch convention

```text
{git.branch_prefix}{TASK-KEY}-{slug}
# mặc định: ai/TASK-001-authentication
```

Cấu hình `git.branch_prefix` trong `.ai/config.yaml`.

## Replay

```bash
ai-team replay 42
ai-team replay 42 --json
```

API: `GET /sessions/42/replay` — timeline + cost + markdown log (nếu có).
