# Deployment (Docker / NAS)

## Docker Compose

```bash
cp .env.example .env
# chỉnh OPENAI_API_KEY, AI_TEAM_* nếu cần
docker compose up --build
```

| Service | Port | Mô tả |
|---|---|---|
| `ai-orchestrator` | `8080` | `ai-team serve` + Web UI |
| `ai-mcp` | — | Profile `mcp` — stdio MCP |

## Gắn project NAS

```bash
PROJECT_WORKSPACE=/volume1/projects/my-app docker compose up --build
```

Volume mapping:

- `${PROJECT_WORKSPACE}` → `/workspace` (working_dir container)
- `./projects` → `/app/projects`
- `ai-team-data` → `/app/data` (global DB nếu dùng)

**Quan trọng:** `serve` dùng `/workspace` làm project root — set `PROJECT_WORKSPACE` trỏ đúng app đang dev.

## Biến môi trường container

Từ `docker-compose.yml`:

```yaml
AI_TEAM_PROJECTS_ROOT: /app/projects
AI_TEAM_DATABASE_URL: sqlite:////app/data/ai-team.db
```

Project-specific DB vẫn có thể nằm tại `/workspace/.ai/ai-team.db` tùy `DATABASE_URL`.

## Build image

```dockerfile
# Dockerfile — ai-team:v1
ENTRYPOINT ["ai-team"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]
```

Rebuild sau khi đổi code:

```bash
docker compose up --build
```

## Cursor Cloud Agent

```bash
bash scripts/cloud-agent-install.sh
```

Config: `.cursor/environment.json`  
Gotchas: [AGENTS.md](../AGENTS.md)

- Venv tại `.venv` — `ai-team` không trên global PATH
- Mock provider khi không có API key
- Demo project ngoài repo: dùng `.venv/bin/ai-team` từ repo AI-Team

## Reverse proxy (khuyến nghị NAS)

V1 không có auth — đặt nginx/Caddy với:

- Basic auth hoặc SSO
- Chỉ bind LAN / VPN
- TLS nếu expose ngoài LAN

## Health check

```bash
curl http://localhost:8080/health
```

## Logs

```bash
docker compose logs -f ai-orchestrator
```

## Upgrade

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

Giữ volume `ai-team-data` và backup `.ai/` project trước upgrade lớn.
