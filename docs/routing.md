# Model Routing (Phase 8)

Routing tự chọn **provider + model per role** dựa trên độ phức tạp task và budget session.

Implementation: `src/ai_team/models/routing.py`  
Tích hợp: `TeamRuntime._refresh_agent_providers()` — trace step `routing`.

## Bật routing

Trong `.ai/config.yaml`:

```yaml
routing:
  enabled: true
  strategy: cost_optimized
  budget_usd_per_session: 2.0
  tiers:
    simple:
      coder: {provider: openai, model: gpt-4o-mini}
    standard:
      coder: {provider: openai, model: gpt-4o}
    complex:
      coder: {provider: anthropic, model: claude-sonnet-4-5}
```

Hoặc env (ghi đè khi set rõ):

```bash
AI_TEAM_ROUTING_ENABLED=true
AI_TEAM_ROUTING_STRATEGY=cost_optimized
AI_TEAM_ROUTING_BUDGET_USD=2.0
```

## Task tiers

`classify_task(prompt)` → `simple` | `standard` | `complex`

Heuristic (rút gọn):

| Tier | Điều kiện ví dụ |
|---|---|
| `simple` | Prompt ngắn (<40 ký tự), hoặc keyword "typo", "readme", "lint" |
| `complex` | Prompt dài (>400), hoặc keyword "security", "migration", "kubernetes", … |
| `standard` | Còn lại |

## Chiến lược (`strategy`)

| Strategy | Hành vi |
|---|---|
| `balanced` | Dùng tier map từ YAML; fallback settings per role |
| `cost_optimized` | Hạ model rẻ hơn theo tier; nếu `session_cost >= budget` → force `simple` |
| `quality` | Task `complex` hoặc upgrade architect/coder lên tier cao hơn |

## Luồng runtime

```text
workflow start(prompt)
    → ModelRouter.effective_tier(prompt, session_cost)
    → resolve(provider, model) per role
    → rebuild agent.model providers
    → tracer.emit("routing", snapshot)
    → tiếp tục agent calls
```

## Preview không chạy workflow

```bash
curl 'http://localhost:8080/routing/preview?prompt=Add%20authentication'
```

Hoặc Web UI → Dashboard → panel Routing.

## Cost budget

`budget_usd_per_session` dùng **cost đã tích lũy** trong session hiện tại (từ traces).

Với `cost_optimized`:

- `session_cost >= budget` → tier = `simple`
- `session_cost >= 70% budget` và tier would be `complex` → hạ xuống `standard`

## Bảng giá

`estimate_cost_usd()` trong `models/pricing.py` — ước lượng, không phải billing thật.

## Không nhầm với AgentRouter

| Module | Mục đích |
|---|---|
| `models/routing.py` `ModelRouter` | Chọn **LLM provider/model** |
| `orchestration/router.py` `AgentRouter` | Chọn **agent nào** chạy theo `ManagerPlan.chosen_agents` |

## Test

```bash
pytest tests/test_routing.py -q
```
