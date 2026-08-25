#!/usr/bin/env bash
# Dashboard keyless test: the production server must serve the SPA and
# report honest 503s on Gemini-backed endpoints when no key is configured.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
unset GEMINI_API_KEY GOOGLE_API_KEY || true

[ -f dist/server.cjs ] || npm run build

PORT=$(( (RANDOM % 20000) + 20000 ))
LOG="$(mktemp)"
NODE_ENV=production PORT=$PORT node dist/server.cjs > "$LOG" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true; rm -f "$LOG"' EXIT

for _ in $(seq 1 20); do
  curl -sf "http://localhost:$PORT/api/health" >/dev/null 2>&1 && break
  sleep 0.5
done

HEALTH=$(curl -sf "http://localhost:$PORT/api/health") || { echo "FAIL: health endpoint unreachable"; cat "$LOG"; exit 1; }
echo "$HEALTH" | grep -q '"hasApiKey":false' || { echo "FAIL: expected hasApiKey:false, got: $HEALTH"; exit 1; }

curl -sf "http://localhost:$PORT/" | grep -q "<!doctype html>" || { echo "FAIL: SPA not served"; exit 1; }

CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:$PORT/api/dream/consolidate")
[ "$CODE" = "503" ] || { echo "FAIL: keyless consolidate returned $CODE, expected 503"; exit 1; }

CODE2=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H 'Content-Type: application/json' \
  -d '{"message":"hi"}' "http://localhost:$PORT/api/agent/chat")
[ "$CODE2" = "503" ] || { echo "FAIL: keyless chat returned $CODE2, expected 503"; exit 1; }

echo "✅ DASHBOARD KEYLESS PASSED"
