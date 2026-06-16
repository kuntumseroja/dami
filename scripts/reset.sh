#!/usr/bin/env bash
# Wipe all demo data and reseed a clean 13-case dataset.
# Truncates the Postgres tables and clears the MinIO bucket (both internal to
# the compose network), then re-runs the seeder. Docker stack must be up.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Truncating database tables"
docker compose exec -T db psql -U dam -d dam_governance -c \
  "TRUNCATE cases, documents, artefacts, doc_chunks RESTART IDENTITY;" 2>/dev/null \
  && echo "  cleared cases / documents / artefacts / doc_chunks" \
  || { echo "  ERROR: db not reachable — is the stack up? (docker compose up -d)"; exit 1; }

echo "==> Clearing MinIO bucket"
docker compose exec -T minio sh -c \
  "mc alias set local http://localhost:9000 dam-admin dam-secret >/dev/null 2>&1; \
   mc rm --recursive --force local/governance-documents >/dev/null 2>&1; \
   mc mb -p local/governance-documents >/dev/null 2>&1; true" 2>/dev/null \
  && echo "  bucket emptied" || echo "  (minio clear skipped)"

echo "==> Reseeding"
PYBIN="$ROOT/backend/.venv/bin/python"; [ -x "$PYBIN" ] || PYBIN="python3"
"$PYBIN" "$ROOT/scripts/seed.py"
