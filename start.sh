#!/usr/bin/env bash
# Start the DAM Governance Intelligence Platform locally.
#   Frontend → http://localhost:3010   Backend/API → http://localhost:8010
# Frees the ports first (kills any current listener), then starts both apps.
set -euo pipefail

FRONTEND_PORT=3010
BACKEND_PORT=8010
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/.run"
mkdir -p "$LOG_DIR"

free_port() {
  local port=$1
  local pids
  pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "  port $port in use by PID(s): $pids — killing"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -n "$pids" ]; then
      echo "  still up — force killing: $pids"
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
    fi
  else
    echo "  port $port free"
  fi
}

# Load root .env (ANTHROPIC_API_KEY etc.) so the local backend sees it —
# Docker Compose auto-loads .env on its own.
if [ -f "$ROOT/.env" ]; then
  set -a; . "$ROOT/.env"; set +a
  echo "==> Loaded .env ($([ -n "${ANTHROPIC_API_KEY:-}" ] && [ "${ANTHROPIC_API_KEY}" != "sk-ant-..." ] && echo "ANTHROPIC_API_KEY set" || echo "ANTHROPIC_API_KEY NOT set — agent endpoints will fail"))"
fi

echo "==> Freeing ports"
free_port "$BACKEND_PORT"
free_port "$FRONTEND_PORT"

echo "==> Starting backend (uvicorn) on :$BACKEND_PORT"
cd "$ROOT/backend"
PYBIN="$ROOT/backend/.venv/bin/python"
[ -x "$PYBIN" ] || PYBIN="python3"
"$PYBIN" -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  backend PID $BACKEND_PID — logs: $LOG_DIR/backend.log"

echo "==> Starting frontend (vite) on :$FRONTEND_PORT"
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
PORT="$FRONTEND_PORT" npm run dev -- --port "$FRONTEND_PORT" \
  > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  frontend PID $FRONTEND_PID — logs: $LOG_DIR/frontend.log"

echo "$BACKEND_PID $FRONTEND_PID" > "$LOG_DIR/pids"

cat <<EOF

==> Up.
    Frontend : http://localhost:$FRONTEND_PORT
    API docs : http://localhost:$BACKEND_PORT/docs
    Logs     : $LOG_DIR/{backend,frontend}.log
    Stop     : ./stop.sh   (or: kill $BACKEND_PID $FRONTEND_PID)
EOF
