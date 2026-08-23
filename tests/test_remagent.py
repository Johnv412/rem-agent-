"""
Unit and Integration Test Suite for RemAgent.
Covers Schemas, SQLite Storage, Governor, Decay, and Daemon Logic.
"""

import asyncio
import os
import tempfile
import time
import unittest
from remagent.schemas import Fact, OperationalRule, RawTurnLog, MemoryProfile, DreamConsolidationResult
from remagent.storage.sqlite import SQLiteStorageAdapter
from remagent.governor import TokenBudgetGovernor
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


if __name__ == "__main__":
    unittest.main()
