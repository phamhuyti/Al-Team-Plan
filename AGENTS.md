# AGENTS.md

## Cursor Cloud specific instructions

AI-Team is a Python 3.11+ project: a multi-agent orchestrator exposed as a Typer
CLI (`ai-team`) and a FastAPI HTTP API. There is no web UI. Standard usage is
documented in `README.md` and `HANDOFF.md`; the notes below only cover
non-obvious, durable gotchas for working in the cloud environment.

### Environment / how to run

- Dependencies are installed into a virtualenv at `.venv` (managed by the update
  script). Either activate it (`. .venv/bin/activate`) or call binaries directly
  (`.venv/bin/ai-team`, `.venv/bin/pytest`, `.venv/bin/ruff`). The `ai-team`
  entry point is **not** on the global `PATH`.
- No API key is required for development. When `OPENAI_API_KEY` is empty the app
  falls back to the **mock provider** automatically, so real model calls never
  happen. To force it explicitly, set `AI_TEAM_PROVIDER=mock`. Commands and tests
  are fully runnable offline in this mode.
- `pytest -q` runs the suite (all mock-based, no network). See `README.md` /
  `HANDOFF.md` for the CLI and API command reference.

### Non-obvious gotchas

- `ai-team serve` uses the process's **current working directory** as the project
  root for all `/tasks` operations (not the `--project` flag for those routes).
  Start the server from the target project directory, and run `ai-team init`
  there first so `.ai/` and the SQLite DB exist.
- The `implement`/`plan`/`run` workflows perform a real `git commit` inside the
  target project, so the working directory must be a git repo with a usable git
  identity. Interactive approval prompts are skipped only with `--yes` (CLI) or
  `yes: true` (API `RunBody`).
- `ruff` is configured in `pyproject.toml` (`[tool.ruff]`) but is **not** a
  declared dependency; the update script installs it so `ruff check .` works. The
  repo currently has pre-existing lint findings — do not treat a non-zero
  `ruff check` exit as a regression from your change unless you introduced it.
- Per-project runtime state (`.ai/`, `*.db`, `projects/*`) is gitignored; the
  demo projects created during setup live outside the repo (e.g. `/tmp/demo`).
