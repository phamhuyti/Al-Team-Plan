# Guidelines — Quy tắc sử dụng & phát triển

Tài liệu này là **chuẩn bắt buộc** khi vận hành AI-Team hoặc chỉnh sửa codebase.

---

## Phần 1: Guidelines cho người dùng / operator

### 1.1 Luôn bắt đầu bằng `init`

```bash
ai-team init --name myapp --purpose "..."
```

Không chạy `plan`/`implement` trên thư mục chưa có `.ai/` và git identity hợp lệ.

### 1.2 Workflow đúng thứ tự

```text
plan → (review decision) → implement → (replay / status)
```

Không nhảy thẳng `implement` cho task chưa được plan (trừ khi bạn chắc context đủ trong TASK/description).

### 1.3 Approval có chủ đích

| Môi trường | Khuyến nghị |
|---|---|
| Dev local | Có thể `--yes` để nhanh |
| CI / test | `AI_TEAM_PROVIDER=mock` + `--yes` |
| NAS / production | **Không** `--yes`; duyệt DANGEROUS qua UI hoặc CLI |

### 1.4 Cấu hình provider

- Production: OpenAI hoặc provider có SLA rõ
- Dev offline: `AI_TEAM_PROVIDER=mock`
- Per-role: ưu tiên `.ai/config.yaml` cho team, env cho secret/override cá nhân

### 1.5 Cost & routing

- Bật `routing.enabled` khi muốn tiết kiệm token
- Set `budget_usd_per_session` realistic — cost là **ước lượng**
- Xem Cost Monitor sau mỗi session lớn

### 1.6 Bảo mật

- Không expose `:8080` ra internet không auth
- Review output Coder trước khi merge branch `ai/*`
- `git push` luôn cần user approval — đừng auto-approve DANGEROUS

### 1.7 Shared memory

- Cập nhật `PROJECT.md` / `RULES.md` khi đổi convention
- Đọc `DECISIONS.md` trước task mới — tránh trùng quyết định cũ

---

## Phần 2: Guidelines cho developer / agent

### 2.1 Nguyên tắc code

1. **Minimize scope** — diff nhỏ, đúng việc được giao
2. **Match conventions** — đọc code xung quanh trước khi sửa
3. **Contracts bắt buộc** — agent output phải qua Pydantic schema
4. **Không phá quyết định đã chốt** — xem [architecture.md](architecture.md) và HANDOFF

### 2.2 File quan trọng nhất

| Thay đổi | File | Test bắt buộc |
|---|---|---|
| Pipeline workflow | `orchestration/workflow.py` | `test_workflow.py` |
| Permissions | `security/permissions.py` | `test_permissions.py` |
| Approvals | `security/approvals.py` | `test_hardening.py` |
| Config | `config.py` | `test_hardening.py` |
| Routing | `models/routing.py` | `test_routing.py` |
| API | `api/app.py` | `test_api.py`, `test_web_ui.py` |
| Provider mới | `models/*.py`, `factory.py` | `test_providers.py` |

```bash
pytest -q
```

### 2.3 Thêm agent mới

1. Contract trong `agents/contracts.py`
2. Class trong `agents/`
3. Prompt `prompts/<role>.md` + template `.ai/agents/`
4. Wire trong `workflow.py`
5. Seed role trong `_seed_agents`
6. Test end-to-end mock

### 2.4 Thêm provider mới

1. Subclass `ModelProvider` → `generate()`
2. Đăng ký `factory.py` + `ProviderName` trong `config.py`
3. Pricing entry trong `pricing.py`
4. Mock HTTP test trong `test_providers.py`
5. Document trong `configuration.md`

### 2.5 Thêm tool MCP

1. Implement trong `tools/`
2. `ToolRegistry._register_v1()`
3. `classify_tool()` risk level
4. `mcp/server.py` expose
5. Test `test_mcp.py`

### 2.6 Config precedence

Khi overlay YAML lên Settings:

- Dùng `settings.model_dump(exclude_unset=True)` để biết field nào user/test đã set rõ
- **Không** ghi đè explicit values bằng YAML mặc định

### 2.7 Test

- Mock provider cho CI — không cần API key
- Subprocess dùng `sys.executable`
- `implement`/`plan` thật sự `git commit` — test dùng `tmp_path` + fixture `project_root`
- Không coi `ruff check` non-zero là regression trừ khi bạn introduce finding mới

### 2.8 Tên & shadowing

- Debate engine: `self.debate_engine` (không `self.debate` — shadow method)
- Model routing: `ModelRouter` (`models/routing.py`)
- Agent picking: `AgentRouter` (`orchestration/router.py`)

### 2.9 Documentation

Khi thêm feature user-facing:

- Cập nhật doc tương ứng trong `docs/`
- Link từ `README.md` nếu là entry point chính
- HANDOFF chỉ cho agent nội bộ — không thay thế `docs/`

### 2.10 Git / PR

- Branch: `cursor/<mô-tả>-<suffix>`
- Commit message: câu hoàn chỉnh, một logical change mỗi commit
- PR draft mặc định; mô tả có test evidence
- Không force-push trừ khi owner yêu cầu

---

## Phần 3: Anti-patterns (tránh)

| ❌ Không làm | ✅ Làm thay thế |
|---|---|
| Dump cả repo vào prompt | Context engine + task keywords |
| Free-form agent output | JSON contract |
| `auto_approve_dangerous: true` trên NAS | User approval qua UI |
| Sửa workflow không test | `pytest tests/test_workflow.py` |
| Vector DB V1 | Keyword context đến khi cần scale |
| Expose API không auth | Reverse proxy / LAN only |
| Hardcode API keys | `.env` + gitignore |

---

## Phần 4: Checklist trước khi merge

- [ ] `pytest -q` pass
- [ ] Đụng `workflow.py` → chạy `test_workflow.py`
- [ ] Doc cập nhật nếu đổi API/CLI/config
- [ ] Không commit secret / `.ai/` runtime / `*.db`
- [ ] HANDOFF cập nhật nếu đổi trạng thái phase hoặc quyết định kỹ thuật

---

## Liên quan

- [contributing.md](contributing.md) — quy trình PR chi tiết
- [HANDOFF.md](../HANDOFF.md) — trạng thái repo cho agent tiếp theo
- [AGENTS.md](../AGENTS.md) — Cursor Cloud gotchas
