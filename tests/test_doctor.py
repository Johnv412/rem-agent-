"""
Tests for `remagent doctor` — the pipeline self-audit.

Doctor exists so that "is my memory working?" is a scriptable yes/no.
These tests pin both directions: healthy pipelines pass, and each failure
mode (backlog, stale dreams, fallback fingerprints, memory erasure,
missing key, missing DB) exits non-zero with the check named.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from remagent.schemas import Fact, MemoryProfile, RawTurnLog, current_utc_iso, generate_uuid
from remagent.storage.sqlite import SQLiteStorageAdapter

KEYED_ENV = {**os.environ, "GEMINI_API_KEY": "doctor-test-key"}
KEYLESS_ENV = {k: v for k, v in os.environ.items() if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}


def run_doctor_cli(db_path: str, *extra_args: str, env=None) -> subprocess.CompletedProcess:
    args = ["remagent", "doctor", "--db", db_path, "--agent", "a", *extra_args]
    return subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.argv = {args!r}; from remagent.cli import main; main()"],
        capture_output=True, text=True, timeout=60, env=env or KEYED_ENV,
    )


class TestDoctor(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.storage = SQLiteStorageAdapter(db_path=self.db_path)
        await self.storage.initialize()

    async def asyncTearDown(self):
        await self.storage.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    async def _healthy_profile(self):
        profile = MemoryProfile(
            agent_id="a",
            facts=[Fact(entity="Vendor", attribute="price", value="$52")],
        )
        profile.last_dream_at = current_utc_iso()
        await self.storage.save_memory_profile(profile)

    async def test_healthy_pipeline_passes(self):
        await self._healthy_profile()
        proc = run_doctor_cli(self.db_path)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("ALL CHECKS PASSED", proc.stdout)

    async def test_json_output_shape(self):
        await self._healthy_profile()
        proc = run_doctor_cli(self.db_path, "--json")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])
        self.assertIn("timestamp", data)
        self.assertEqual(
            {c["name"] for c in data["checks"]},
            {"api_key", "database", "queue", "no_fallback", "no_erasure"},
        )

    async def test_queue_backlog_fails(self):
        await self._healthy_profile()
        for i in range(6):
            await self.storage.save_turn(RawTurnLog(role="user", content=f"turn {i}"))
        proc = run_doctor_cli(self.db_path, "--max-queue", "5")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("queue", proc.stdout)

    async def test_stale_dream_with_queue_fails(self):
        profile = MemoryProfile(agent_id="a", facts=[])
        profile.last_dream_at = time.time() - 3 * 86400  # 3 days ago
        await self.storage.save_memory_profile(profile)
        await self.storage.save_turn(RawTurnLog(role="user", content="queued"))
        proc = run_doctor_cli(self.db_path)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("dreams not keeping up", proc.stdout)

    async def test_never_dreamed_with_queue_fails(self):
        await self.storage.save_turn(RawTurnLog(role="user", content="queued"))
        proc = run_doctor_cli(self.db_path)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no dream has ever completed", proc.stdout)

    async def test_fallback_fingerprint_fails(self):
        await self._healthy_profile()
        con = sqlite3.connect(self.db_path)
        con.execute(
            "INSERT INTO dream_audit_history (run_id, agent_id, added_facts_json, "
            "updated_rules_json, contradiction_resolutions_json, pruned_noise_count, "
            "pruned_noise_reasons_json, reasoning_summary, consolidated_turn_ids_json, "
            "timestamp, estimated_token_savings) VALUES (?, 'a', '[]', '[]', '[]', 0, "
            "'[]', 'Fallback dream consolidation completed for 2 turns.', '[]', ?, 0)",
            (generate_uuid(), current_utc_iso()),
        )
        con.commit()
        con.close()
        proc = run_doctor_cli(self.db_path)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no_fallback", proc.stdout)

    async def test_superseded_without_replacement_fails(self):
        profile = MemoryProfile(
            agent_id="a",
            facts=[Fact(entity="Vendor", attribute="price", value="$40",
                        is_active=False, superseded_by="some-fact-id")],
        )
        profile.last_dream_at = current_utc_iso()
        await self.storage.save_memory_profile(profile)
        proc = run_doctor_cli(self.db_path)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("superseded without active replacement", proc.stdout)

    async def test_supersession_chain_across_entity_rename_is_clean(self):
        """Curator entity merges re-home facts: old fact -> moved fact ->
        new fact under the canonical entity. The erasure check must follow
        the chain, not just match entity/attribute pairs."""
        new = Fact(entity="Commander", attribute="worker_status", value="proven")
        moved = Fact(entity="Commander Project", attribute="worker_status",
                     value="proven", is_active=False, superseded_by=new.id)
        old = Fact(entity="Commander Project", attribute="worker_status",
                   value="no workers", is_active=False, superseded_by=moved.id)
        profile = MemoryProfile(agent_id="a", facts=[old, moved, new])
        profile.last_dream_at = current_utc_iso()
        await self.storage.save_memory_profile(profile)
        proc = run_doctor_cli(self.db_path)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout)

    async def test_decayed_without_replacement_is_fine(self):
        profile = MemoryProfile(
            agent_id="a",
            facts=[
                Fact(entity="Vendor", attribute="price", value="$52"),
                Fact(entity="Temp", attribute="scratch", value="x",
                     is_active=False, superseded_by=None),  # decayed, legitimate
            ],
        )
        profile.last_dream_at = current_utc_iso()
        await self.storage.save_memory_profile(profile)
        proc = run_doctor_cli(self.db_path)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout)

    async def test_missing_key_fails(self):
        await self._healthy_profile()
        proc = run_doctor_cli(self.db_path, env=KEYLESS_ENV)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("api_key", proc.stdout)

    async def test_missing_db_fails_and_is_not_created(self):
        ghost = self.db_path + ".ghost"
        proc = run_doctor_cli(ghost)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("does not exist", proc.stdout)
        self.assertFalse(os.path.exists(ghost), "doctor must never create the DB it audits")


if __name__ == "__main__":
    unittest.main()
