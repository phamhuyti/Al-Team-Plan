# Tổng quan

## AI-Team là gì?

AI-Team là **đội phát triển phần mềm đa agent** chạy trên máy bạn (hoặc NAS/Docker). Một Manager điều phối các specialist — Architect, Researcher, Coder, Reviewer, Red Team — qua workflow có audit, approval và git commit có kiểm soát.

Mục tiêu dài hạn: *“AI Software Company”* trên NAS, OpenAI làm model lõi, các provider khác (Claude, Gemini, OpenRouter) là tùy chọn.

## Success path

```text
User → Task → Manager → Architect → Researcher → Debate → Red Team
     → Decision → Coder → Tests → Reviewer → Approval → Git commit
```

Mọi bước được ghi vào:

- **SQLite** — `.ai/ai-team.db` (sessions, traces, approvals, cost)
- **Markdown** — `.ai/*.md` (PROJECT, RULES, DECISIONS, TASKS, discussions)

## 6 agent V1 (+ Judge)

| Agent | Việc chính | Sửa code? |
|---|---|---|
| Manager | Điều phối, lập kế hoạch, quyết định | Không |
| Architect | Kiến trúc, trade-off | Không |
| Researcher | Phương án, evidence, web search | Không |
| Coder | Thay đổi file, chạy test | Có (qua tool) |
| Reviewer | Đánh giá chất lượng | Không |
| Red Team | Tấn công ý tưởng / thiết kế | Không |
| Judge | Chỉ khi debate — chốt quyết định | Không |

Output của mỗi agent là **JSON contract** (xem [agents.md](agents.md)), không phải prose tự do.

## Entry points

| Cách dùng | Lệnh / URL |
|---|---|
| CLI | `ai-team` |
| HTTP API | `ai-team serve` → `:8080` |
| Web UI | `http://localhost:8080/` |
| MCP stdio | `ai-team mcp` |

## Roadmap phase

| Phase | Nội dung | Trạng thái |
|---|---|---|
| 0–1 | Architecture, OpenAI, Manager, CLI | ✅ |
| 2 | 6 agent roles | ✅ |
| 3 | `.ai/` memory, context engine | ✅ |
| 4 | Filesystem, Git, Shell, MCP | ✅ |
| 5 | Debate, Judge, decisions | ✅ |
| 6 | Implement, test, review, commit | ✅ |
| 7 | Web UI (dashboard, chat, tasks, approvals, cost) | ✅ |
| 8 | Multi-model routing + cost optimization | ✅ |
| Sau V1 | MCP V2, vector DB, agent mở rộng, Postgres | 🔜 |

## Nguyên tắc thiết kế (tóm tắt)

1. Shared project state (`.ai/`) là source of truth — không dựa conversation history.
2. Agent có role và contract rõ; không free-form output.
3. Context theo task (keyword + path), không dump cả repo.
4. Destructive actions luôn qua approval gate.
5. Proposal → Review → Debate → Decision → Implementation.
6. Red Team phải phản biện, không đồng thuận mặc định.
7. Provider abstraction — không khóa vào một vendor.
8. Mọi tool call và decision quan trọng có audit trail.

Chi tiết quy tắc phát triển: [guidelines.md](guidelines.md).
