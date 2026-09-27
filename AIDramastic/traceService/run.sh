#!/usr/bin/env bash
# run.sh — 启动 FastAPI API（uvicorn :8100）
# 用法: ./run.sh
# 环境: 优先 conda activate workspace；否则 backend/.venv
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
mkdir -p "$ROOT/log" "$ROOT/backend/data"

activate_env() {
  if command -v conda >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    if [ -f "$(conda info --base 2>/dev/null)/etc/profile.d/conda.sh" ]; then
      source "$(conda info --base)/etc/profile.d/conda.sh"
      if conda env list | grep -qE '^workspace\s'; then
        conda activate workspace
        echo "[run.sh] using conda env: workspace"
        return 0
      fi
    fi
  fi
  if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install -U pip
    .venv/bin/pip install -r requirements.txt
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  echo "[run.sh] using venv: $ROOT/backend/.venv"
}

activate_env
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
HOST="${TRACE_HOST:-127.0.0.1}"
PORT="${TRACE_PORT:-8100}"
echo "[run.sh] uvicorn app.main:app --host $HOST --port $PORT"
echo "[run.sh] healthz: curl -s http://$HOST:$PORT/healthz"
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
