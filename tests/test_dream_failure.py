"""
Failure-path tests for the dream consolidation pipeline.

These exist because the engine once shipped with a fallback that fabricated a
successful-looking result on every Gemini failure, and no test ever checked
that a failure looks like a failure. The invariants pinned here:
  - A failed dream exits non-zero and prints FAILED.
  - A failed dream writes no facts, no profile, no audit rows.
  - A failed dream leaves is_consolidated=0 so turns are reprocessed.
  - A contradiction resolution always leaves an active replacement fact,
    even when the synthesizer omits it from added_facts.
  - The daemon refuses to persist any result marked is_fallback / error.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from remagent.daemon import ConsolidationBusyError, DreamDaemon
from remagent.integrations.claude_code import create_claude_mcp_server
from remagent.engine.synthesizer import DreamSynthesizer, DreamSynthesisError
from remagent.schemas import (
    ContradictionResolution,
    DreamConsolidationResult,
    Fact,
    MemoryProfile,
    RawTurnLog,
    current_utc_iso,
    generate_uuid,
)
from remagent.storage.sqlite import SQLiteStorageAdapter


class _StubSynthesizer:
    """Returns a canned DreamConsolidationResult without calling Gemini."""

    def __init__(self, result: DreamConsolidationResult):
        self._result = result

    async def consolidate_window(self, unconsolidated_turns, existing_profile):
        self._result.consolidated_turn_ids = [t.turn_id for t in unconsolidated_turns]
        return self._result


class TestDreamFailurePaths(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.storage = SQLiteStorageAdapter(db_path=self.db_path)
        await self.storage.initialize()

    async def asyncTearDown(self):
        await self.storage.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    # ------------------------------------------------------------------
    # CLI failure path: missing API key
    # ------------------------------------------------------------------

    async def test_cli_dream_without_key_exits_nonzero_and_preserves_state(self):
        await self.storage.save_turn(
            RawTurnLog(role="user", content="vendor price is $40/unit")
        )
        await self.storage.close()

        env = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import sys; sys.argv = ['remagent', 'dream', '--db', {self.db_path!r}]; "
                "from remagent.cli import main; main()",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

        self.assertEqual(proc.returncode, 1, msg=f"stderr: {proc.stderr}")
        self.assertIn("FAILED", proc.stderr)

        con = sqlite3.connect(self.db_path)
        try:
            consolidated_flags = [r[0] for r in con.execute("SELECT is_consolidated FROM raw_turns")]
            self.assertEqual(consolidated_flags, [0], "failed dream must leave turns unconsolidated")
            self.assertEqual(
                con.execute("SELECT count(*) FROM memory_profiles").fetchone()[0], 0,
                "failed dream must not write a memory profile",
            )
            self.assertEqual(
                con.execute("SELECT count(*) FROM dream_audit_history").fetchone()[0], 0,
                "failed dream must not write an audit row",
            )
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Synthesizer: missing key raises instead of fabricating
    # ------------------------------------------------------------------

    async def test_synthesizer_missing_key_raises(self):
        saved = {k: os.environ.pop(k, None) for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
        try:
            synthesizer = DreamSynthesizer(api_key=None)
            with self.assertRaises(DreamSynthesisError):
                await synthesizer.consolidate_window(
                    unconsolidated_turns=[RawTurnLog(role="user", content="x")],
                    existing_profile=MemoryProfile(agent_id="a"),
                )
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    # ------------------------------------------------------------------
    # Daemon: contradiction without replacement fact gets materialized
    # ------------------------------------------------------------------

    async def test_daemon_materializes_replacement_for_contradiction(self):
        prior = Fact(entity="Vendor", attribute="price_per_unit", value="$40/unit")
        await self.storage.save_memory_profile(MemoryProfile(agent_id="a", facts=[prior]))
        await self.storage.save_turn(RawTurnLog(role="user", content="vendor price is now $52/unit"))

        run_id = generate_uuid()
        # Synthesizer misbehaves: reports the contradiction but omits the new
        # value from added_facts. The daemon must stay correct regardless.
        stub_result = DreamConsolidationResult(
            run_id=run_id,
            added_facts=[],
            contradiction_resolutions=[
                ContradictionResolution(
                    entity="Vendor",
                    attribute="price_per_unit",
                    prior_value="$40/unit",
                    new_value="$52/unit",
                    resolution_reasoning="newer turn supersedes",
                )
            ],
            reasoning_summary="stub",
            timestamp=current_utc_iso(),
        )
        daemon = DreamDaemon(storage=self.storage, synthesizer=_StubSynthesizer(stub_result), agent_id="a")
        result = await daemon.consolidate_now()
        self.assertIsNotNone(result)

        profile = await self.storage.load_memory_profile("a")
        old = [f for f in profile.facts if f.value == "$40/unit"]
        new = [f for f in profile.facts if f.value == "$52/unit"]
        self.assertEqual(len(old), 1)
        self.assertFalse(old[0].is_active)
        self.assertEqual(len(new), 1, "daemon must materialize the replacement fact")
        self.assertTrue(new[0].is_active)
        self.assertEqual(
            old[0].superseded_by, new[0].id,
            "superseded_by must point at the replacing fact's ID, not the run_id",
        )

        remaining = await self.storage.get_unconsolidated_turns()
        self.assertEqual(len(remaining), 0, "successful dream marks turns consolidated")

    # ------------------------------------------------------------------
    # Busy is not "up to date": lock contention must be distinguishable
    # ------------------------------------------------------------------

    async def test_consolidate_now_busy_raises_and_preserves_queue(self):
        await self.storage.save_turn(RawTurnLog(role="user", content="x"))
        stub_result = DreamConsolidationResult(
            run_id=generate_uuid(), reasoning_summary="stub", timestamp=current_utc_iso()
        )
        daemon = DreamDaemon(storage=self.storage, synthesizer=_StubSynthesizer(stub_result), agent_id="a")

        await daemon._lock.acquire()
        try:
            with self.assertRaises(ConsolidationBusyError):
                await daemon.consolidate_now()
        finally:
            daemon._lock.release()

        remaining = await self.storage.get_unconsolidated_turns()
        self.assertEqual(len(remaining), 1, "busy abort must leave turns queued")

    async def test_mcp_dream_reports_busy_not_up_to_date(self):
        server = create_claude_mcp_server(
            name="test_remagent", default_db_path=self.db_path, default_agent_id="a"
        )
        with mock.patch.object(
            DreamDaemon, "consolidate_now",
            side_effect=ConsolidationBusyError("cycle already in progress"),
        ):
            result = await server.call_tool("remagent_dream", {"db_path": self.db_path})
        self.assertFalse(result.is_error)
        data = json.loads(result.content[0].text)
        self.assertEqual(data["status"], "busy")
        self.assertNotIn("up to date", data.get("message", ""))

    # ------------------------------------------------------------------
    # Daemon: refuses to persist fallback / error results
    # ------------------------------------------------------------------

    async def test_daemon_rejects_fallback_result_and_preserves_state(self):
        await self.storage.save_turn(RawTurnLog(role="user", content="x"))
        stub_result = DreamConsolidationResult(
            run_id=generate_uuid(),
            reasoning_summary="fabricated",
            is_fallback=True,
            timestamp=current_utc_iso(),
        )
        daemon = DreamDaemon(storage=self.storage, synthesizer=_StubSynthesizer(stub_result), agent_id="a")
        with self.assertRaises(RuntimeError):
            await daemon.consolidate_now()

        remaining = await self.storage.get_unconsolidated_turns()
        self.assertEqual(len(remaining), 1, "rejected dream must leave turns unconsolidated")
        profile = await self.storage.load_memory_profile("a")
        self.assertEqual(profile.facts, [], "rejected dream must not write facts")


if __name__ == "__main__":
    unittest.main()
