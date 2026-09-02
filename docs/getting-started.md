# Bắt đầu nhanh

## Yêu cầu

- Python **3.11+**
- Git
- Docker + Docker Compose (nếu chạy NAS)
- `OPENAI_API_KEY` (tùy chọn — không có key thì dùng **mock provider**)

## Cài đặt

```bash
git clone https://github.com/phamhuyti/Al-Team-Plan.git
cd Al-Team-Plan
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

**Cursor Cloud Agent:**

```bash
bash scripts/cloud-agent-install.sh
```

## Demo không cần API key

```bash
AI_TEAM_PROVIDER=mock ai-team init --name demo --purpose "Demo app"
AI_TEAM_PROVIDER=mock ai-team plan "Thêm authentication"
AI_TEAM_PROVIDER=mock ai-team implement TASK-001 --yes
AI_TEAM_PROVIDER=mock ai-team status
AI_TEAM_PROVIDER=mock ai-team replay 1
```

`--yes` tự approve MODERATE/DANGEROUS — chỉ dùng CI/demo.

## Demo với OpenAI

Trong `.env`:

```bash
OPENAI_API_KEY=sk-...
AI_TEAM_PROVIDER=openai
AI_TEAM_MODEL=gpt-4o
```

```bash
ai-team init --name myapp --purpose "Production app"
ai-team plan "Thêm rate limiting"
ai-team implement TASK-001   # sẽ hỏi approval nếu cần
```

## Web UI

```bash
cd /path/to/your/project   # sau ai-team init
ai-team serve
```

Mở `http://localhost:8080/` — xem [web-ui.md](web-ui.md).

## Chạy test

```bash
pytest -q
```

Bắt buộc giữ xanh `tests/test_workflow.py` khi sửa pipeline.

## Project layout sau `init`

```text
myapp/
├── .ai/
│   ├── PROJECT.md
│   ├── RULES.md
│   ├── DECISIONS.md
│   ├── TASKS.md
│   ├── config.yaml
│   ├── agents/
│   ├── discussions/
│   ├── sessions/
│   └── ai-team.db
├── src/
├── tests/
└── docs/
```

## Bước tiếp theo

- Cấu hình provider/model: [configuration.md](configuration.md)
- Lệnh CLI đầy đủ: [cli.md](cli.md)
- Deploy NAS: [deployment.md](deployment.md)
