# Web UI (Phase 7)

## Khởi động

```bash
cd /path/to/your/project
ai-team serve
# hoặc: ai-team serve --project /path/to/project --port 8080
```

Mở trình duyệt: **http://localhost:8080/**

Static assets: `/ui/styles.css`, `/ui/app.js`

## Các tab

### Dashboard

- Đường dẫn project hiện tại
- Bảng **Agents** (role, provider, model)
- **Routing preview** (Phase 8) — JSON snapshot tier + routes
- Sessions, decisions gần đây
- Header pills: tổng sessions, cost, pending approvals

### Tasks

- Form tạo task (title + description)
- Bảng tasks với nút **Plan** / **Implement**
- Gọi `POST /tasks` và `POST /tasks/{key}/run`

### Live Chat

- Mode: Ask, Research, Debate, Plan
- Checkbox **Auto-approve** (`yes: true/false`)
- Gửi message → `POST /chat`
- Stream traces qua SSE `GET /sessions/{id}/events`

### Approvals

- Danh sách `pending` approvals
- Nút Approve / Deny → `POST /approvals/{id}`
- Nút **Làm mới**

### Cost Monitor

- **Project Cost Summary**: sessions, events, tokens, total USD
- **Session Costs**: bảng cost theo từng session

## Lưu ý vận hành

| Chủ đề | Chi tiết |
|---|---|
| Project root | Cố định lúc `serve` — UI không đổi project qua HTTP |
| Ngôn ngữ UI | Một phần label tiếng Việt |
| Offline / mock | Dùng `AI_TEAM_PROVIDER=mock` — cost vẫn tính theo bảng giá model name |
| Approval | Tắt auto-approve → action DANGEROUS tạo pending; duyệt ở tab Approvals rồi chạy lại |

## Docker / NAS

```bash
docker compose up --build
# UI tại http://<nas-ip>:8080
PROJECT_WORKSPACE=/volume1/projects/my-app docker compose up --build
```

Container `serve` với `working_dir` = project workspace.

## Tích hợp tùy chỉnh

UI là static SPA đơn giản (`src/ai_team/web/static/`). Có thể:

- Fork `app.js` cho workflow riêng
- Gọi API trực tiếp từ Cursor/automation (không cần UI)
- Đặt reverse proxy (nginx) trước `:8080` nếu expose ra LAN

Không có auth built-in V1 — **không expose công khai** không có reverse proxy + auth.
