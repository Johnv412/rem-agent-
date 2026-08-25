#!/usr/bin/env python3
"""
Live-Gemini canary: proves the real API still consolidates and supersedes.

This exists because mocked tests once stayed green while the engine was 100%
broken (the SDK rejected our schema client-side and a fallback fabricated
success). The canary runs the canonical $40 -> $52 supersession against the
REAL Gemini API in a throwaway DB and exits non-zero on any miss:

  1. log "$40/unit"  -> dream #1 must add an active price fact
  2. log "$52/unit"  -> dream #2 must leave the old fact inactive with
     superseded_by = the new active fact's id
  3. zero fallback fingerprints anywhere

Requires GEMINI_API_KEY. Never touches any real memory DB.
"""

import asyncio
import os
import sys
import tempfile

from remagent.daemon import DreamDaemon
from remagent.engine.synthesizer import DreamSynthesizer
from remagent.schemas import RawTurnLog
from remagent.storage.sqlite import SQLiteStorageAdapter

FALLBACK_PREFIX = "Fallback dream consolidation"


def fail(msg: str) -> None:
    print(f"❌ CANARY FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


async def run() -> None:
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        fail("GEMINI_API_KEY is not set — the canary needs the real API.")

    fd, db_path = tempfile.mkstemp(suffix=".canary.db")
    os.close(fd)
    storage = SQLiteStorageAdapter(db_path=db_path)
    await storage.initialize()
    try:
        daemon = DreamDaemon(storage=storage, synthesizer=DreamSynthesizer(), agent_id="canary")

        await storage.save_turn(RawTurnLog(role="user", content="vendor price is $40/unit"))
        r1 = await daemon.consolidate_now()
        if r1 is None:
            fail("dream #1 returned None despite a queued turn")
        if r1.reasoning_summary.startswith(FALLBACK_PREFIX):
            fail("dream #1 hit the fallback fingerprint — Gemini was not reached")
        print(f"dream #1 ok: {len(r1.added_facts)} fact(s) — {r1.reasoning_summary[:100]}")

        await storage.save_turn(RawTurnLog(role="user", content="vendor price is now $52/unit"))
        r2 = await daemon.consolidate_now()
        if r2 is None:
            fail("dream #2 returned None despite a queued turn")
        if r2.reasoning_summary.startswith(FALLBACK_PREFIX):
            fail("dream #2 hit the fallback fingerprint — Gemini was not reached")
        print(f"dream #2 ok: {len(r2.added_facts)} fact(s), "
              f"{len(r2.contradiction_resolutions)} contradiction(s) — {r2.reasoning_summary[:100]}")

        profile = await storage.load_memory_profile("canary")
        old = [f for f in profile.facts if "$40" in str(f.value)]
        new = [f for f in profile.facts if "$52" in str(f.value)]

        if not old:
            fail("no $40 fact was ever stored — dream #1 extracted nothing usable")
        if not new:
            fail("no $52 fact exists — the update erased or never stored the new value")
        if any(f.is_active for f in old):
            fail("the $40 fact is still active — supersession did not happen")
        if not any(f.is_active for f in new):
            fail("the $52 fact is not active")
        active_new = next(f for f in new if f.is_active)
        if old[0].superseded_by != active_new.id:
            fail(f"superseded_by mismatch: old points at {old[0].superseded_by!r}, "
                 f"expected the replacing fact id {active_new.id!r}")
        if any(f.entity.lower() == "session" and
               f.attribute.lower() == "last_consolidated_turns_count" for f in profile.facts):
            fail("fabricated Session.last_consolidated_turns_count fact present")

        print("✅ CANARY PASSED: live Gemini consolidation + supersession verified "
              f"($40 inactive, superseded_by={old[0].superseded_by[:8]}…; $52 active)")
    finally:
        await storage.close()
        os.remove(db_path)


if __name__ == "__main__":
    asyncio.run(run())
