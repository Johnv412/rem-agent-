#!/usr/bin/env bash
# Keyless E2E: fresh venv install + CLI flows must behave HONESTLY without
# any provider key (Gemini, Anthropic, OpenAI, xAI) — log works, dream fails with exit 1 preserving the queue,
# doctor flags the missing key, decay (which needs no key) works.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SB="$(mktemp -d)"
trap 'rm -rf "$SB"' EXIT
unset GEMINI_API_KEY GOOGLE_API_KEY ANTHROPIC_API_KEY OPENAI_API_KEY XAI_API_KEY REMAGENT_PROVIDER REMAGENT_MODEL || true

python3 -m venv "$SB/venv"
cd "$REPO"
"$SB/venv/bin/pip" install --quiet -e ".[claude,test]"
BIN="$SB/venv/bin/remagent"
DB="$SB/e2e.db"

echo "[1] log works keyless"
"$BIN" log --role user --content 'vendor price is $40/unit' --db "$DB"

echo "[2] dream without key must exit non-zero and preserve the queue"
if "$BIN" dream --db "$DB" >/dev/null 2>&1; then
  echo "FAIL: keyless dream exited 0 — a failure reported as success"
  exit 1
fi
"$SB/venv/bin/python3" - "$DB" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
n = con.execute("SELECT count(*) FROM raw_turns WHERE is_consolidated=0").fetchone()[0]
assert n == 1, f"queue not preserved after failed dream: {n} unconsolidated turns"
PY

echo "[3] doctor must flag the missing key (exit non-zero)"
if "$BIN" doctor --db "$DB" >/dev/null 2>&1; then
  echo "FAIL: keyless doctor exited 0"
  exit 1
fi

echo "[4] decay needs no key and must work"
"$SB/venv/bin/python3" - "$DB" <<'PY'
import asyncio, sys
from remagent.schemas import Fact, MemoryProfile
from remagent.storage.sqlite import SQLiteStorageAdapter

async def main():
    s = SQLiteStorageAdapter(db_path=sys.argv[1])
    await s.initialize()
    try:
        await s.save_memory_profile(MemoryProfile(
            agent_id="default_agent",
            facts=[Fact(entity="X", attribute="y", value="z")],
        ))
    finally:
        await s.close()

asyncio.run(main())
PY
"$BIN" decay --db "$DB"

echo "✅ KEYLESS E2E PASSED"
