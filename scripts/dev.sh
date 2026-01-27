#!/usr/bin/env bash
set -euo pipefail

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  python3 -m pip install -r requirements-dev.txt
fi

uvicorn app.main:app --reload --port 8000
