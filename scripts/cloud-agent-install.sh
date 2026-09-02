#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! python3 -m venv /tmp/ai-team-venv-check >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-venv
fi
rm -rf /tmp/ai-team-venv-check

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

.venv/bin/pip install -U pip wheel
.venv/bin/pip install -e ".[dev]"
.venv/bin/pip install ruff
