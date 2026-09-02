"""
Unit and Integration Test Suite for RemAgent.
Covers Schemas, SQLite Storage, Governor, Decay, and Daemon Logic.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import time
import unittest
from remagent.schemas import Fact, OperationalRule, RawTurnLog, MemoryProfile, DreamConsolidationResult
from remagent.storage.sqlite import SQLiteStorageAdapter
from remagent.governor import GovernorBudgetError, TokenBudgetGovernor
from remagent.decay import MemoryDecayEngine


class TestRemAgentSuite(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.storage = SQLiteStorageAdapter(database_path=self.db_path)
        await self.storage.initialize()

    async def asyncTearDown(self):
        await self.storage.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    async def test_turn_lifecycle_and_consolidation(self):
        turn1 = RawTurnLog(
            turn_id="turn_001",
            session_id="test_session",
            role="user",
            content="Please use PostgreSQL 16 on Cloud SQL.",
            timestamp=time.time(),
        )
        turn2 = RawTurnLog(
            turn_id="turn_002",
            session_id="test_session",
            role="assistant",
            content="Understood, configured PostgreSQL 16.",
            timestamp=time.time() + 1,
        )

        await self.storage.save_turn(turn1)
        await self.storage.save_turn(turn2)

        unconsolidated = await self.storage.get_unconsolidated_turns(session_id="test_session")
        self.assertEqual(len(unconsolidated), 2)

        # Mark consolidated
        await self.storage.mark_turns_consolidated(["turn_001", "turn_002"])
        remaining = await self.storage.get_unconsolidated_turns(session_id="test_session")
        self.assertEqual(len(remaining), 0)

    async def test_memory_profile_persistence(self):
        fact = Fact(
            id="f_1",
            entity="Architecture",
            attribute="database",
            value="PostgreSQL 16",
            confidence=0.95,
            source_turn_ids=["turn_001"],
        )
        rule = OperationalRule(
            id="r_1",
            category="coding_standard",
            rule="Always use strict TypeScript types",
            rationale="Enforces code safety",
            priority=1,
        )

        profile = MemoryProfile(
            agent_id="test_agent",
            facts=[fact],
            rules=[rule],
        )

        await self.storage.save_memory_profile(profile)
        loaded = await self.storage.load_memory_profile("test_agent")

        self.assertEqual(len(loaded.facts), 1)
        self.assertEqual(loaded.facts[0].attribute, "database")
        self.assertEqual(loaded.facts[0].value, "PostgreSQL 16")
        self.assertEqual(len(loaded.rules), 1)
        self.assertEqual(loaded.rules[0].priority, 1)

    def test_token_budget_governor(self):
        governor = TokenBudgetGovernor(default_max_tokens=60)
        profile = MemoryProfile(
            agent_id="test_agent",
            facts=[
                Fact(id="f1", entity="User", attribute="name", value="Alex", confidence=0.9),
                Fact(id="f2", entity="User", attribute="role", value="Admin", confidence=0.8),
                Fact(id="f3", entity="Project", attribute="framework", value="React Vite Tailwind", confidence=0.7),
            ],
            rules=[
                OperationalRule(id="r1", category="user_preference", rule="Prefer dark mode", priority=1, rationale=""),
            ],
        )

        injection = governor.build_budgeted_prompt_injection(profile, query_context="framework", max_tokens=150)
        self.assertIn("REMAGENT DETERMINISTIC MEMORY CONTEXT", injection)
        self.assertIn("Prefer dark mode", injection)
        self.assertNotIn("TOKEN BUDGET OVERFLOW", injection)

    def test_token_budget_governor_rules_overflow_raises_loudly(self):
        # Rules are NEVER trimmed. If they alone exceed the budget, the
        # governor must refuse loudly — a rule-less injection is worse than
        # no injection.
        governor = TokenBudgetGovernor(default_max_tokens=80)
        rules = [
            OperationalRule(
                id=f"r{i}",
                category="operational_directive",
                rule=f"Critical unbreakable directive number {i}: " + ("x" * 120),
                rationale="",
                priority=1,
            )
            for i in range(6)
        ]
        profile = MemoryProfile(agent_id="overflow_test", facts=[], rules=rules)

        with self.assertRaises(GovernorBudgetError) as ctx:
            governor.build_budgeted_prompt_injection(profile, max_tokens=80)
        self.assertIn("never trimmed", str(ctx.exception))

    def test_token_budget_governor_all_rules_present_facts_truncated(self):
        # All rules (every priority) must appear; facts fill what's left and
        # the cut is explicitly noted, with the output still under budget.
        governor = TokenBudgetGovernor()
        rules = [
            OperationalRule(id="r1", category="operational_directive",
                            rule="P1 unbreakable directive", rationale="", priority=1),
            OperationalRule(id="r2", category="coding_standard",
                            rule="P2 secondary standard", rationale="", priority=2),
            OperationalRule(id="r3", category="architecture_heuristic",
                            rule="P3 minor guideline", rationale="", priority=3),
        ]
        facts = [
            Fact(id=f"f{i}", entity="Thing", attribute=f"attr_{i}",
                 value="v" * 80, confidence=0.9)
            for i in range(40)
        ]
        profile = MemoryProfile(agent_id="trunc_test", facts=facts, rules=rules)

        budget = 300
        injection = governor.build_budgeted_prompt_injection(profile, max_tokens=budget)
        self.assertLessEqual(governor.estimate_tokens(injection), budget)
        for r in rules:
            self.assertIn(r.rule, injection, f"rule {r.id} must never be dropped")
        self.assertIn("omitted by token budget", injection)
        self.assertIn("Thing.attr_0", injection, "highest-value facts should fill remaining budget")

    async def test_recall_cli_rules_overflow_exits_nonzero(self):
        rules = [
            OperationalRule(id=f"r{i}", category="operational_directive",
                            rule=f"Long critical directive {i}: " + ("y" * 150),
                            rationale="", priority=1)
            for i in range(5)
        ]
        await self.storage.save_memory_profile(
            MemoryProfile(agent_id="overflow_agent", rules=rules)
        )
        args = ["remagent", "recall", "--format", "injection", "--agent", "overflow_agent",
                "--db", self.db_path, "--max-tokens", "40"]
        proc = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.argv = {args!r}; from remagent.cli import main; main()"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAILED", proc.stderr)
        self.assertIn("never trimmed", proc.stderr)

    def test_memory_decay_engine(self):
        decay_engine = MemoryDecayEngine(half_life_days=1.0, min_confidence_floor=0.3)
        old_fact = Fact(
            id="f_decay",
            entity="Temp",
            attribute="scratchpad",
            value="123",
            confidence=0.5,
            timestamp=time.time() - (86400 * 2),  # 2 days old
        )
        profile = MemoryProfile(agent_id="decay_test", facts=[old_fact], rules=[])

        updated_profile, pruned = decay_engine.apply_decay(profile, current_timestamp=time.time())
        # After 2 half-lives, 0.5 * 0.5 * 0.5 = 0.125 < 0.3 floor -> pruned
        self.assertEqual(len(pruned), 1)
        self.assertFalse(updated_profile.facts[0].is_active)

    def _run_decay_cli(self, agent: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                "-c",
                f"import sys; sys.argv = ['remagent', 'decay', '--db', {self.db_path!r}, "
                f"'--agent', {agent!r}, '--half-life-days', '1.0', '--floor', '0.3']; "
                "from remagent.cli import main; main()",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

    async def test_decay_cli_happy_path_persists(self):
        stale = Fact(
            id="f_stale", entity="Temp", attribute="scratch", value="old",
            confidence=0.5, timestamp=time.time() - (86400 * 2),
        )
        durable = Fact(
            id="f_durable", entity="Arch", attribute="db", value="PostgreSQL",
            confidence=1.0, timestamp=time.time() - (86400 * 2),
        )
        await self.storage.save_memory_profile(
            MemoryProfile(agent_id="decay_agent", facts=[stale, durable], rules=[])
        )

        proc = self._run_decay_cli("decay_agent")
        self.assertEqual(proc.returncode, 0, msg=f"stderr: {proc.stderr}")
        self.assertIn("Decay pass complete", proc.stdout)

        loaded = await self.storage.load_memory_profile("decay_agent")
        by_id = {f.id: f for f in loaded.facts}
        self.assertFalse(by_id["f_stale"].is_active, "decayed fact must be persisted as inactive")
        self.assertTrue(by_id["f_durable"].is_active, "confidence-1.0 facts never decay")

    async def test_decay_cli_missing_profile_fails_nonzero(self):
        proc = self._run_decay_cli("ghost_agent")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAILED", proc.stderr)


if __name__ == "__main__":
    unittest.main()
