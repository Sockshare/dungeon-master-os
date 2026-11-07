#!/usr/bin/env bash
# One-command launcher for Dungeon Master OS (port 8093)
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv
  elif [ -x "$HOME/.local/bin/uv" ]; then
    "$HOME/.local/bin/uv" venv .venv
  else
    "$PY" -m venv .venv
  fi
fi

if command -v uv >/dev/null 2>&1; then
  uv pip install -q -p .venv/bin/python -r requirements.txt
elif [ -x "$HOME/.local/bin/uv" ]; then
  "$HOME/.local/bin/uv" pip install -q -p .venv/bin/python -r requirements.txt
else
  .venv/bin/python -m pip install -q -r requirements.txt
fi

exec .venv/bin/python server.py "$@"
