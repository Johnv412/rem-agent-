#!/usr/bin/env python3
"""
Live provider check: the MySQL -> PostgreSQL contradiction fixture.

Runs two real dream cycles against whichever provider the environment selects,
in a THROWAWAY temp database that is deleted on exit. It never reads or writes
~/.remagent/memory.db or any REMAGENT_DB path.

Invariant asserted (not wording, not phrasing):
  1. dream #1 stores an active Project.database = MySQL fact
  2. dream #2 leaves the MySQL fact INACTIVE with superseded_by pointing at
     the id of the ACTIVE PostgreSQL fact
  3. no fallback fingerprint, and both facts live under ONE entity name
"""

import asyncio
import os
import sys
import tempfile

from remagent.daemon import DreamDaemon
from remagent.engine.errors import ProviderConfigError
from remagent.engine.providers import make_backend, resolve_provider
from remagent.engine.synthesizer import DreamSynthesizer
from remagent.schemas import RawTurnLog
from remagent.storage.sqlite import SQLiteStorageAdapter

FALLBACK_PREFIX = "Fallback dream consolidation"
AGENT = "live_fixture"


def fail(msg: str) -> None:
    print(f"❌ LIVE RUN FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


async def run() -> None:
    try:
        provider = resolve_provider()
        backend = make_backend(provider)
    except ProviderConfigError as exc:
        fail(str(exc))

    print(f"provider: {provider.provider} | model: {provider.model} | key from: {provider.key_env}"
          + (f" | base_url: {provider.base_url}" if provider.base_url else ""))

    fd, db_path = tempfile.mkstemp(suffix=".live-fixture.db")
    os.close(fd)
    print(f"throwaway db: {db_path}")

    storage = SQLiteStorageAdapter(db_path=db_path)
    await storage.initialize()
    try:
        daemon = DreamDaemon(
            storage=storage,
            synthesizer=DreamSynthesizer(provider=provider, backend=backend),
            agent_id=AGENT,
        )

        await storage.save_turn(RawTurnLog(
            role="user",
            content="For this project the database is MySQL. Set up the connection against MySQL.",
        ))
        r1 = await daemon.consolidate_now()
        if r1 is None:
            fail("dream #1 returned None despite a queued turn")
        if r1.reasoning_summary.startswith(FALLBACK_PREFIX):
            fail("dream #1 hit the fallback fingerprint — the provider was not reached")
        print(f"dream #1 ok: {len(r1.added_facts)} fact(s) — {r1.reasoning_summary[:120]}")

        await storage.save_turn(RawTurnLog(
            role="user",
            content="Change of plan: we are migrating the project database from MySQL to PostgreSQL. Use PostgreSQL from now on.",
        ))
        r2 = await daemon.consolidate_now()
        if r2 is None:
            fail("dream #2 returned None despite a queued turn")
        if r2.reasoning_summary.startswith(FALLBACK_PREFIX):
            fail("dream #2 hit the fallback fingerprint — the provider was not reached")
        print(f"dream #2 ok: {len(r2.added_facts)} fact(s), "
              f"{len(r2.contradiction_resolutions)} contradiction(s) — {r2.reasoning_summary[:120]}")

        profile = await storage.load_memory_profile(AGENT)
        print("\n--- all stored facts ---")
        for f in profile.facts:
            print(f"  {f.entity}.{f.attribute} = {f.value!r} | active={f.is_active} | "
                  f"id={f.id[:8]} | superseded_by={(f.superseded_by or '')[:8] or '-'}")

        old = [f for f in profile.facts if "mysql" in str(f.value).lower()]
        new = [f for f in profile.facts if "postgres" in str(f.value).lower()]

        if not old:
            fail("no MySQL fact was ever stored — dream #1 extracted nothing usable")
        if not new:
            fail("no PostgreSQL fact exists — the update erased or never stored the new value")
        if any(f.is_active for f in old):
            fail("the MySQL fact is still ACTIVE — supersession did not happen")
        if not any(f.is_active for f in new):
            fail("the PostgreSQL fact is not active")

        active_new = next(f for f in new if f.is_active)
        if old[0].superseded_by != active_new.id:
            fail(f"superseded_by mismatch: MySQL fact points at {old[0].superseded_by!r}, "
                 f"expected the replacing PostgreSQL fact id {active_new.id!r}")

        if any(f.entity.lower() == "session" and
               f.attribute.lower() == "last_consolidated_turns_count" for f in profile.facts):
            fail("fabricated Session.last_consolidated_turns_count fact present")

        db_entities = {f.entity for f in old + new}
        if len(db_entities) != 1:
            fail(f"entity drift: database facts split across {sorted(db_entities)}")

        print(f"\n✅ LIVE RUN PASSED on {provider.provider} ({provider.model})")
        print(f"   MySQL fact inactive, superseded_by={old[0].superseded_by[:8]}… -> "
              f"active PostgreSQL fact id={active_new.id[:8]}…")
        print(f"   single entity: {db_entities.pop()!r}")
    finally:
        await storage.close()
        os.remove(db_path)
        print(f"throwaway db removed: {db_path}")


if __name__ == "__main__":
    asyncio.run(run())
