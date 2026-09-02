# AI-Team — Tài liệu

Bộ tài liệu chính thức cho **AI-Team**: multi-agent orchestrator chạy CLI, HTTP API, Web UI và MCP trên NAS/Docker.

> README ngắn gọn cho người mới: [../README.md](../README.md)  
> Handoff cho agent/dev tiếp theo: [../HANDOFF.md](../HANDOFF.md)  
> Gotchas Cursor Cloud: [../AGENTS.md](../AGENTS.md)

---

## Mục lục

### Bắt đầu

| Tài liệu | Nội dung |
|---|---|
| [overview.md](overview.md) | Mục tiêu, success path, roadmap phase |
| [getting-started.md](getting-started.md) | Cài đặt, quick start, demo mock |

### Vận hành

| Tài liệu | Nội dung |
|---|---|
| [cli.md](cli.md) | Tham chiếu lệnh `ai-team` |
| [api.md](api.md) | HTTP API đầy đủ |
| [web-ui.md](web-ui.md) | Dashboard Phase 7 |
| [configuration.md](configuration.md) | `.env`, `.ai/config.yaml`, thứ tự ưu tiên |
| [deployment.md](deployment.md) | Docker, NAS, Cloud Agent |

### Kiến trúc & hành vi

| Tài liệu | Nội dung |
|---|---|
| [architecture.md](architecture.md) | Lớp hệ thống, luồng dữ liệu, bản đồ code |
| [agents.md](agents.md) | 6 agent, Judge, JSON contracts |
| [workflows.md](workflows.md) | ask, plan, implement, debate, review |
| [routing.md](routing.md) | Phase 8 — chọn model theo tier & budget |
| [security.md](security.md) | SAFE / MODERATE / DANGEROUS, approvals |
| [memory-and-audit.md](memory-and-audit.md) | `.ai/`, SQLite, trace, replay, cost |
| [mcp.md](mcp.md) | MCP stdio, tools |

### Guidelines

| Tài liệu | Nội dung |
|---|---|
| [guidelines.md](guidelines.md) | **Quy tắc sử dụng & phát triển** (đọc trước khi chỉnh code) |
| [contributing.md](contributing.md) | PR, test, commit, mở rộng agent/provider |

---

## Đọc nhanh theo vai trò

| Bạn là… | Đọc |
|---|---|
| User / PM | [overview](overview.md) → [cli](cli.md) hoặc [web-ui](web-ui.md) |
| Dev tích hợp API | [api](api.md) → [configuration](configuration.md) |
| Dev sửa orchestrator | [architecture](architecture.md) → [workflows](workflows.md) → [guidelines](guidelines.md) |
| Dev NAS/Docker | [deployment](deployment.md) |
| Agent Cursor / contributor | [guidelines](guidelines.md) → [contributing](contributing.md) → [HANDOFF.md](../HANDOFF.md) |

---

## Phiên bản tài liệu

Tài liệu này mô tả **V1 + Phase 7 (Web UI) + Phase 8 (routing)** trên nhánh `main` / PR #6.
