# Handoff — AI-Team V1

Tài liệu này để người hoặc agent tiếp theo nhận việc, không phải README người dùng.

- **Repo:** https://github.com/phamhuyti/Al-Team-Plan
- **Branch làm việc:** `main`
- **HEAD:** `75b252f` — Cloud Agent env setup (merge PR #4); V1 + hardening đã trên `main`
- **PR đã merge gần đây:** [#2 hardening](https://github.com/phamhuyti/Al-Team-Plan/pull/2), [#3/#4 AGENTS + env](https://github.com/phamhuyti/Al-Team-Plan/pull/4)
- **Plan gốc:** AI-Team Multi-Agent Development Team (NAS/Docker), V1 = 6 agent + workflow có audit
- **Ngôn ngữ làm việc với owner:** tiếng Việt (Huy)

Toàn bộ code V1, Phase 7/8 và hardening nằm trên `main`. Cloud Agent dùng `.cursor/environment.json` + `scripts/cloud-agent-install.sh`.

**Tài liệu đầy đủ:** [docs/README.md](docs/README.md) · **Guidelines:** [docs/guidelines.md](docs/guidelines.md)

---

## Mục tiêu đã chốt

Xây hệ thống AI Development Team chạy NAS/Docker:

User → Task → Manager → Architect → Researcher → Debate → Red Team → Decision → Coder → Tests → Reviewer → Approval → Git commit

OpenAI là model lõi V1. Không làm UI, vector DB, hay MCP V2/V3 trong V1.

---

## Hiện trạng

V1 **đã implement, hardening xong, Cloud Agent env setup xong** — tất cả trên `main`.

| Phần | Trạng thái |
|---|---|
| Phase 0–6 (arch, agents, memory, tools, debate, autonomous coding) | Xong |
| CLI + HTTP API + Docker Compose | Xong |
| MCP V1: filesystem, git, shell, web_search | Xong |
| OpenAI + abstraction Anthropic/Gemini/OpenRouter/Mock | Adapter xong |
| README GitHub | Xong |
| Đọc `.ai/config.yaml` lúc runtime | Xong |
| Provider + model per role | Xong |
| `cost_usd` từ token + bảng giá | Xong |
| API `GET/POST /approvals` + `/sessions/{id}/cost` | Xong |
| Replay session | Xong (`ai-team replay`, `GET /sessions/{id}/replay`) |
| Researcher web search | Xong (`web_search` tool + DuckDuckGo/mock) |
| Cloud Agent: `AGENTS.md`, `.cursor/environment.json`, install script | Xong |
| **Phase 7 Web UI** (dashboard, chat, tasks, approvals, cost) | Xong (`/` + `/ui/*`) |
| **Phase 8 routing + cost optimization** | Xong (`models/routing.py`, `.ai/config.yaml routing`) |
| Provider HTTP integration tests (mocked) | Xong (`tests/test_providers.py`) |
| Web UI, vector DB, MCP V2 GitHub/Postgres, 8 role sau V1 | Phase 7 UI xong; MCP V2/vector chưa |

---

## Cách chạy nhanh

```bash
git clone https://github.com/phamhuyti/Al-Team-Plan.git
cd Al-Team-Plan
bash scripts/cloud-agent-install.sh   # hoặc: python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/pytest -q
```

Demo không cần key:

```bash
AI_TEAM_PROVIDER=mock .venv/bin/ai-team init /tmp/demo --name demo --purpose "Demo"
cd /tmp/demo
AI_TEAM_PROVIDER=mock /path/to/Al-Team-Plan/.venv/bin/ai-team plan "Thêm authentication"
AI_TEAM_PROVIDER=mock /path/to/Al-Team-Plan/.venv/bin/ai-team implement TASK-001 --yes
```

Model thật: gắn `OPENAI_API_KEY` trong `.env`, `AI_TEAM_PROVIDER=openai`, `AI_TEAM_MODEL=gpt-4o`.

NAS:

```bash
docker compose up --build
# API :8080
PROJECT_WORKSPACE=/volume1/projects/my-app docker compose up --build
```

### Cursor Cloud Agent

- Cấu hình repo: `.cursor/environment.json` → `bash scripts/cloud-agent-install.sh`
- Gotchas cho agent: xem `AGENTS.md` (venv, mock provider, `serve` root, CLI ngoài repo)

---

## Bản đồ code (nơi sửa việc tiếp theo)

Tài liệu chi tiết: [docs/architecture.md](docs/architecture.md)

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
  tools/                       fs, git, shell, docker, web
  mcp/server.py                MCP JSON-RPC stdio
  security/permissions.py      SAFE / MODERATE / DANGEROUS
  security/approvals.py        gate + CLI [y/N]
  tracing/audit.py             trace_events
prompts/                       system prompt theo role
templates/project/             skeleton khi `ai-team init`
tests/test_workflow.py         success path V1
.cursor/environment.json       Cloud Agent install
scripts/cloud-agent-install.sh
AGENTS.md                      Cloud Agent gotchas
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

V1 + hardening + Cloud env **xong**. Làm tiếp theo thứ tự plan — **không** nhảy UI nếu owner chưa yêu cầu.

1. ~~Đọc `.ai/config.yaml` lúc runtime~~ — xong
2. ~~Provider per role~~ — xong
3. ~~Tính `cost_usd` thật~~ — xong
4. ~~API approval~~ — xong
5. ~~Replay session~~ — xong
6. ~~Researcher web search~~ — xong
7. ~~Cloud Agent env setup~~ — xong (`AGENTS.md`, install script, `environment.json`)

**Sau V1 (chọn một hướng với owner):**

- ~~**Phase 7:** dashboard, live chat, task UI, approval UI, cost monitor~~ — xong
- ~~**Phase 8:** routing + cost optimization~~ — xong
- ~~**Cứng hóa V1:** integration test mocked Anthropic/Gemini/OpenRouter~~ — xong
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
- `ai-team serve` cố định project root lúc startup (`cwd` hoặc `--project`).

---

## Rủi ro / nợ kỹ thuật

- Anthropic/Google/OpenRouter mới test qua adapter HTTP, **chưa có integration test live**.
- Mock Coder luôn tạo `src/{auth|queue|feature}.py` + test `ping()` — đủ cho CI, không phản ánh coder LLM thật.
- `Researcher` có `web_search` (DuckDuckGo HTML, không cần key); offline thì degrade về `[]` / backend `mock|off`.
- Approval interactive cần TTY; CI phải `--yes` hoặc `AI_TEAM_AUTO_APPROVE_*`. API dùng `defer` + `POST /approvals/{id}`.
- Bảng giá `cost_usd` là ước lượng (per 1M tokens), không phải invoice provider.
- Docker tool = `docker …` qua shell, profile `mcp` tách container stdio.

---

## Test cần giữ xanh

```bash
.venv/bin/pytest -q
```

Bắt buộc: `tests/test_workflow.py` (plan + implement + audit + debate). Đụng `workflow.py`, permissions, mock provider, git/shell thì chạy file này trước.

---

## Owner / sản phẩm

- Owner GitHub: `phamhuyti` (Huy)
- Mục tiêu cuối: “AI Software Company” trên NAS, OpenAI lõi, Cursor/Claude/Gemini/OpenRouter là client/provider dần.
- **Bước tiếp theo:** MCP V2, agent mở rộng, vector DB, hoặc live provider tests với key thật.

## Lệnh git hiện tại

```bash
git checkout main
git pull origin main

# feature branch mới
git checkout -b cursor/<ten-mo-ta>-1676
# ... sửa, commit, push ...
git push -u origin cursor/<ten-mo-ta>-1676
```

Nhánh feature cũ (`cursor/ai-team-v1-implementation-0e40`, `cursor/v1-hardening-*`, `cursor/setup-dev-environment-*`) đã merge — có thể xóa trên remote sau khi xác nhận.
