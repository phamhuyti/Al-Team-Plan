# Contributing

Cảm ơn bạn đóng góp AI-Team. Đọc [guidelines.md](guidelines.md) trước khi code.

## Setup dev

```bash
git clone https://github.com/phamhuyti/Al-Team-Plan.git
cd Al-Team-Plan
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest -q
```

Cloud Agent:

```bash
bash scripts/cloud-agent-install.sh
```

## Branch naming

```text
cursor/<mô-tả-ngắn>-<suffix>
```

Ví dụ: `cursor/phase7-8-v1-hardening-d5f5`

## Commit

- Một logical change mỗi commit
- Message dạng câu hoàn chỉnh (tiếng Anh hoặc Việt đều được)
- Không amend / force-push trừ khi owner yêu cầu

## Pull request

1. Push branch: `git push -u origin cursor/...`
2. Mở PR draft → ready khi test xanh
3. Mô tả: **what / why / how to test**
4. Link issue nếu có

Template (gợi ý):

```markdown
## Summary
- ...

## Testing
- pytest -q (47 passed)
- Manual: ai-team serve + ...

## Docs
- docs/... updated
```

## Test requirements

| Loại thay đổi | Test tối thiểu |
|---|---|
| Bugfix workflow | `test_workflow.py` + reproduce case |
| API | `test_api.py` / `test_web_ui.py` |
| Config | `test_hardening.py` |
| Routing | `test_routing.py` |
| Provider | `test_providers.py` |
| MCP / web | `test_mcp.py` / `test_web_search.py` |

```bash
pytest -q                    # full suite
pytest tests/test_workflow.py -q   # nhanh khi sửa pipeline
```

## Lint

```bash
ruff check .
```

Repo có pre-existing findings — chỉ fix findings do PR của bạn introduce.

## Docs

Feature user-facing → cập nhật `docs/` tương ứng + link từ `README.md`.

## Không commit

- `.venv/`, `*.db`, `.ai/` runtime
- API keys, `.env` (chỉ `.env.example`)
- Artifact demo tạm

## Agent contributors (Cursor)

1. Đọc `HANDOFF.md` + `docs/guidelines.md`
2. Dùng mock provider khi không có key
3. `ai-team` qua `.venv/bin/ai-team`
4. Demo project ngoài repo: `--project /tmp/demo`
5. Cập nhật HANDOFF khi đổi trạng thái phase lớn

## License

MIT — contribution đồng ý license repo.
