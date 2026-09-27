#!/usr/bin/env bash
# mq.sh — 启停 Python Worker / Go Worker
# 用法: ./mq.sh start|stop|status|restart
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/log"
mkdir -p "$LOG_DIR"
PY_PID="$LOG_DIR/worker_py.pid"
GO_PID="$LOG_DIR/worker_go.pid"
PY_LOG="$LOG_DIR/worker_py.log"
GO_LOG="$LOG_DIR/worker_go.log"

py_python() {
  if [ -x "$ROOT/backend/.venv/bin/python" ]; then
    echo "$ROOT/backend/.venv/bin/python"
  elif command -v conda >/dev/null 2>&1 && conda env list 2>/dev/null | grep -qE '^workspace\s'; then
    echo "conda run -n workspace python"
  else
    echo "python3"
  fi
}

start_py() {
  if [ -f "$PY_PID" ] && kill -0 "$(cat "$PY_PID")" 2>/dev/null; then
    echo "worker_py already running pid=$(cat "$PY_PID")"
    return
  fi
  PY="$(py_python)"
  cd "$ROOT/worker_py"
  if [[ "$PY" == conda* ]]; then
    nohup $PY -m worker >>"$PY_LOG" 2>&1 &
  else
    PYTHONPATH="$ROOT/worker_py" nohup "$PY" -m worker >>"$PY_LOG" 2>&1 &
  fi
  echo $! >"$PY_PID"
  echo "started worker_py pid=$(cat "$PY_PID")"
}

start_go() {
  if [ -f "$GO_PID" ] && kill -0 "$(cat "$GO_PID")" 2>/dev/null; then
    echo "worker_go already running pid=$(cat "$GO_PID")"
    return
  fi
  cd "$ROOT/worker"
  # sqlite 默认相对路径：与 backend/data 对齐
  export TRACE_SQLITE_PATH="${TRACE_SQLITE_PATH:-$ROOT/backend/data/logs.db}"
  nohup go run ./cmd/worker -config "$ROOT/worker/configs/default.yaml" >>"$GO_LOG" 2>&1 &
  echo $! >"$GO_PID"
  echo "started worker_go pid=$(cat "$GO_PID")"
}

stop_one() {
  local pidfile=$1 name=$2
  if [ -f "$pidfile" ]; then
    local pid
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      kill -9 "$pid" 2>/dev/null || true
      echo "stopped $name pid=$pid"
    else
      echo "$name not running (stale pidfile)"
    fi
    rm -f "$pidfile"
  else
    echo "$name not running"
  fi
}

status_one() {
  local pidfile=$1 name=$2
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name running pid=$(cat "$pidfile")"
  else
    echo "$name stopped"
  fi
}

cmd="${1:-status}"
case "$cmd" in
  start) start_py; start_go ;;
  stop) stop_one "$PY_PID" worker_py; stop_one "$GO_PID" worker_go ;;
  restart) "$0" stop; "$0" start ;;
  status) status_one "$PY_PID" worker_py; status_one "$GO_PID" worker_go ;;
  *) echo "usage: $0 start|stop|status|restart"; exit 1 ;;
esac
