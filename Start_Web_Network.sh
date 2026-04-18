#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "ERROR: python3 or python3.11 is required." >&2
    exit 1
  fi
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Creating .venv with $PYTHON_BIN ..."
  "$PYTHON_BIN" -m venv .venv
fi

echo "Ensuring uv is available in .venv ..."
".venv/bin/python" -m pip install --upgrade pip uv

echo "Installing project requirements ..."
".venv/bin/python" -m uv pip install -r requirements_cu129.txt

echo "Starting VisoMaster Network Web Console on 0.0.0.0:8000 ..."
exec ".venv/bin/python" main_web.py --host 0.0.0.0 --port 8000
