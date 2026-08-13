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

V1 **đã implement và có test**. `pytest -q` = **15 passed** (mock, không cần API key).

| Phần | Trạng thái |
|---|---|
| Phase 0–6 (arch, agents, memory, tools, debate, autonomous coding) | Xong |
| CLI + HTTP API + Docker Compose | Xong |
| MCP V1: filesystem, git, shell | Xong |
| OpenAI + abstraction Anthropic/Gemini/OpenRouter/Mock | Adapter xong |
| README GitHub | Xong |
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

Provider hiện tại: **một** `AI_TEAM_PROVIDER` cho cả team. Có thể override **model** theo role (`AI_TEAM_CODER_MODEL`), chưa override **hãng** theo role.

---

## Việc còn đọng (ưu tiên gợi ý)

Làm tiếp theo thứ tự plan: **không** nhảy UI nếu owner chưa yêu cầu. Việc hữu ích ngay trên V1:

1. **Đọc `templates/project/.ai/config.yaml` lúc runtime** — file có provider/model per agent nhưng `TeamRuntime` bỏ qua, chỉ dùng env.
2. **Provider per role** — factory đã nhận `role` cho model; chưa nhận provider khác nhau (Manager=OpenAI, Coder=Claude).
3. **Tính `cost_usd` thật** — `TraceEvent.cost_usd` luôn 0; token đã lưu.
4. **API approval** — CLI có `[y/N]` / `--yes`; chưa `POST /approvals/{id}`.
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

- `templates/project/.ai/config.yaml` chưa được load.
- Anthropic/Google/OpenRouter mới test qua adapter HTTP, **chưa có integration test live**.
- Mock Coder luôn tạo `src/{auth|queue|feature}.py` + test `ping()` — đủ cho CI, không phản ánh coder LLM thật.
- `Researcher` không search web.
- Approval interactive cần TTY; CI phải `--yes` hoặc `AI_TEAM_AUTO_APPROVE_*`.
- Cost/token chưa có báo cáo.
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
# nhánh làm việc
git checkout cursor/ai-team-v1-implementation-0e40
git pull origin cursor/ai-team-v1-implementation-0e40

# sau khi sửa
git add -A
git commit -m "..."
git push -u origin cursor/ai-team-v1-implementation-0e40
```

PR #1 đang draft. Merge vào `main` khi owner review.
