#!/usr/bin/env bash
# Stop the DAM platform — frees the frontend (3010) and backend (8010) ports.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for port in 3010 8010; do
  pids=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "stopping port $port (PID $pids)"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
  else
    echo "port $port already free"
  fi
done
rm -f "$ROOT/.run/pids"
