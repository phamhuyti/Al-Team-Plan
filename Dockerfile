FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY prompts ./prompts
COPY templates ./templates

RUN pip install --no-cache-dir .

VOLUME ["/workspace", "/app/projects", "/app/data"]

ENV AI_TEAM_PROJECTS_ROOT=/app/projects
ENV AI_TEAM_DATABASE_URL=sqlite:////app/data/ai-team.db

WORKDIR /workspace

EXPOSE 8080

ENTRYPOINT ["ai-team"]
CMD ["--help"]
