# Handoff — AI-Team V1

Tài liệu này để người hoặc agent tiếp theo nhận việc, không phải README người dùng.

- **Repo:** https://github.com/phamhuyti/Al-Team-Plan
- **PR:** https://github.com/phamhuyti/Al-Team-Plan/pull/1
- **Branch:** `cursor/ai-team-v1-implementation-0e40` (base: `main`)
- **HEAD:** `ea85ff4` — README GitHub; implement chính ở `c555d54`
- **Plan gốc:** AI-Team Multi-Agent Development Team (NAS/Docker), V1 = 6 agent + workflow có audit
- **Ngôn ngữ làm việc với owner:** tiếng Việt (Huy)

`main` hiện chỉ có commit khởi tạo (`# Al-Team-Plan`). Toàn bộ code nằm trên PR.

---

## Mục tiêu đã chốt

Xây hệ thống AI Development Team chạy NAS/Docker:

User → Task → Manager → Architect → Researcher → Debate → Red Team → Decision → Coder → Tests → Reviewer → Approval → Git commit

OpenAI là model lõi V1. Không làm UI, vector DB, hay MCP V2/V3 trong V1.

---

## Hiện trạng

V1 **đã implement và có test**. Hardening tiếp theo (config.yaml, provider/role, cost, approval API) nằm trên nhánh / PR hiện tại.

| Phần | Trạng thái |
|---|---|
| Phase 0–6 (arch, agents, memory, tools, debate, autonomous coding) | Xong |
| CLI + HTTP API + Docker Compose | Xong |
| MCP V1: filesystem, git, shell | Xong |
| OpenAI + abstraction Anthropic/Gemini/OpenRouter/Mock | Adapter xong |
| README GitHub | Xong |
| Đọc `.ai/config.yaml` lúc runtime | Xong |
| Provider + model per role | Xong |
| `cost_usd` từ token + bảng giá | Xong |
| API `GET/POST /approvals` + `/sessions/{id}/cost` | Xong |
| Replay session | Chưa |
| Researcher web search | Chưa |
| Web UI, vector DB, MCP V2/V3, 8 role sau V1 | Chưa |
| Routing đa model + cost optimization | Chưa |

---

## Cách chạy nhanh

```bash
git clone https://github.com/phamhuyti/Al-Team-Plan.git
cd Al-Team-Plan
git checkout cursor/ai-team-v1-implementation-0e40
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest -q
```

Demo không cần key:

```bash
AI_TEAM_PROVIDER=mock ai-team init --name demo --purpose "Demo"
AI_TEAM_PROVIDER=mock ai-team plan "Thêm authentication"
AI_TEAM_PROVIDER=mock ai-team implement TASK-001 --yes
```

Model thật: gắn `OPENAI_API_KEY` trong `.env`, `AI_TEAM_PROVIDER=openai`, `AI_TEAM_MODEL=gpt-4o`.

NAS:

```bash
docker compose up --build
# API :8080
PROJECT_WORKSPACE=/volume1/projects/my-app docker compose up --build
```

---

## Bản đồ code (nơi sửa việc tiếp theo)

```text
src/ai_team/
  main.py                      CLI
  api/app.py                   FastAPI
  config.py                    env AI_TEAM_* + keys
  orchestration/workflow.py    pipeline V1 (file quan trọng nhất)
  orchestration/debate.py      disagreement → rounds → judge
  orchestration/judge.py
  agents/                      6 role + contracts.py
  models/factory.py            chọn provider
  models/{openai,anthropic,google,openrouter,mock}.py
  memory/                      SQLite + .ai markdown
  context/engine.py            retrieval keyword, không vector
  tools/                       fs, git, shell, docker
  mcp/server.py                MCP JSON-RPC stdio
  security/permissions.py      SAFE / MODERATE / DANGEROUS
  security/approvals.py        gate + CLI [y/N]
  tracing/audit.py             trace_events
prompts/                       system prompt theo role
templates/project/             skeleton khi `ai-team init`
tests/test_workflow.py         success path V1
```

Entry points:

- CLI: `ai-team` → `ai_team.main:app`
- API: `ai-team serve` → `create_app()`
- MCP: `ai-team mcp`

Runtime per project: `.ai/` + SQLite `.ai/ai-team.db`.

---

## 6 vai trò V1

| Role | Class | Việc | Sửa code? |
|---|---|---|---|
| Manager | `ManagerAgent` | Điều phối, quyết định | Không |
| Architect | `ArchitectAgent` | Design, trade-off | Không |
| Researcher | `ResearcherAgent` | Phương án, evidence | Không |
| Coder | `CoderAgent` | File changes + tests | Có, qua tool |
| Reviewer | `ReviewerAgent` | Đúng chưa? | Không |
| Red Team | `RedTeamAgent` | Chứng minh sai | Không |

Judge (`JudgeAgent`) chỉ chạy khi debate, không tính là member team V1.

Output bắt buộc là JSON contract trong `agents/contracts.py`.

Provider hiện tại: có thể set **provider + model theo role** qua `.ai/config.yaml` hoặc env `AI_TEAM_{ROLE}_PROVIDER` / `AI_TEAM_{ROLE}_MODEL`. Global vẫn là `AI_TEAM_PROVIDER` / `AI_TEAM_MODEL`.

---

## Việc còn đọng (ưu tiên gợi ý)

Làm tiếp theo thứ tự plan: **không** nhảy UI nếu owner chưa yêu cầu.

1. ~~Đọc `.ai/config.yaml` lúc runtime~~ — xong (`apply_project_config`)
2. ~~Provider per role~~ — xong (`provider_for_role` + factory)
3. ~~Tính `cost_usd` thật~~ — xong (`models/pricing.py` + trace)
4. ~~API approval~~ — xong (`GET/POST /approvals/{id}`, defer mode)
5. **Replay session** — đã ghi `.ai/sessions/` + SQLite, chưa lệnh replay.
6. **Researcher web search** — MCP V2 `web`; hiện chỉ local context.

Sau V1 (plan):

- Phase 7: dashboard, live chat, task UI, approval UI, cost monitor
- Phase 8: routing + cost optimization
- Agent mới: Security, DevOps, Tester, Database, Performance, Documentation, Product Manager, UI/UX
- MCP V2: GitHub, Postgres, web; Docker MCP đúng nghĩa
- MCP V3: NAS/Synology, Home Assistant, Grafana, Prometheus
- Vector DB khi repo đủ lớn
- SQLite → Postgres khi scale

---

## Quyết định kỹ thuật đã chốt (đừng đảo trừ khi owner bảo)

- SQLite, không Postgres, không vector DB trong V1.
- Agent contract JSON, không free-form.
- Shared memory = `.ai/*.md`, không conversation history.
- Context theo task (keyword + path), không dump cả repo.
- `git commit` = MODERATE (Manager). `git push` = DANGEROUS (user).
- Mock khi `provider=openai` mà không có `OPENAI_API_KEY`.
- Test subprocess dùng `sys.executable`, không giả định binary `python`.
- `self.debate` bị shadow method — engine tên `debate_engine`.

---

## Rủi ro / nợ kỹ thuật

- Anthropic/Google/OpenRouter mới test qua adapter HTTP, **chưa có integration test live**.
- Mock Coder luôn tạo `src/{auth|queue|feature}.py` + test `ping()` — đủ cho CI, không phản ánh coder LLM thật.
- `Researcher` không search web.
- Approval interactive cần TTY; CI phải `--yes` hoặc `AI_TEAM_AUTO_APPROVE_*`. API dùng `defer` + `POST /approvals/{id}`.
- Bảng giá `cost_usd` là ước lượng (per 1M tokens), không phải invoice provider.
- Docker tool = `docker …` qua shell, profile `mcp` tách container stdio.

---

## Test cần giữ xanh

```bash
pytest -q
```

Bắt buộc: `tests/test_workflow.py` (plan + implement + audit + debate). Đụng `workflow.py`, permissions, mock provider, git/shell thì chạy file này trước.

---

## Owner / sản phẩm

- Owner GitHub: `phamhuyti` (Huy)
- Mục tiêu cuối: “AI Software Company” trên NAS, OpenAI lõi, Cursor/Claude/Gemini/OpenRouter là client/provider dần.
- Khi nhận việc: hỏi owner muốn **cứng V1** (config.yaml, cost, approval API) hay **nhảy Phase 7/8**.

## Lệnh git hiện tại

```bash
# nhánh hardening V1
git checkout cursor/v1-hardening-config-cost-approvals-85d2
git pull origin cursor/v1-hardening-config-cost-approvals-85d2

# sau khi sửa
git add -A
git commit -m "..."
git push -u origin cursor/v1-hardening-config-cost-approvals-85d2
```

PR hardening đang draft. Merge vào `main` khi owner review.
