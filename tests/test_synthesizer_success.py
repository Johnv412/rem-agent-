"""
Success-path tests for the dream synthesizer with a mocked Gemini client.

The failure paths are pinned in test_dream_failure.py; these tests prove the
success path — typed response parsing, value clamping, contradiction mapping,
and end-to-end daemon persistence — without any network access. A real
live-Gemini smoke test is included but gated behind RUN_LIVE_GEMINI=1.
"""

import json
import os
import tempfile
import unittest

from remagent.daemon import DreamDaemon
from remagent.engine.synthesizer import DreamSynthesizer, DreamSynthesisError
from remagent.schemas import Fact, MemoryProfile, RawTurnLog
from remagent.storage.sqlite import SQLiteStorageAdapter


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModels:
    def __init__(self, text: str):
        self._text = text
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        return _FakeResponse(self._text)


class _FakeClient:
    def __init__(self, text: str):
        self.models = _FakeModels(text)


GEMINI_PAYLOAD = {
    "added_facts": [
        {
            "entity": "Vendor",
            "attribute": "price_per_unit",
            "value": "$52/unit",
            "confidence": 1.5,  # out of range on purpose: mapping must clamp to 1.0
        }
    ],
    "updated_rules": [
        {
            "category": "bogus_category",  # invalid on purpose: must coerce
            "rule": "Always pin dependency versions",
            "rationale": "reproducible builds",
            "priority": 9,  # out of range on purpose: must clamp to 5
        }
    ],
    "contradictions": [
        {
            "entity": "Vendor",
            "attribute": "price_per_unit",
            "prior_value": "$40/unit",
            "new_value": "$52/unit",
            "resolution_reasoning": "newer turn supersedes",
        }
    ],
    "pruned_noise_count": 1,
    "pruned_noise_categories": ["chit_chat"],
    "reasoning_summary": "Consolidated vendor pricing.",
}


def _synthesizer_with_fake(text: str) -> DreamSynthesizer:
    s = DreamSynthesizer(api_key="test-key-not-used")
    s._client = _FakeClient(text)
    return s


class TestSynthesizerSuccessPath(unittest.IsolatedAsyncioTestCase):

    async def test_parses_typed_output_and_clamps_values(self):
        s = _synthesizer_with_fake(json.dumps(GEMINI_PAYLOAD))
        turns = [RawTurnLog(role="user", content="vendor price is now $52/unit")]
        result = await s.consolidate_window(
            unconsolidated_turns=turns,
            existing_profile=MemoryProfile(agent_id="a"),
        )

        self.assertFalse(result.is_fallback)
        self.assertIsNone(result.error)
        self.assertEqual(result.reasoning_summary, "Consolidated vendor pricing.")
        self.assertEqual(result.consolidated_turn_ids, [turns[0].turn_id])

        self.assertEqual(len(result.added_facts), 1)
        fact = result.added_facts[0]
        self.assertEqual((fact.entity, fact.attribute, fact.value), ("Vendor", "price_per_unit", "$52/unit"))
        self.assertEqual(fact.confidence, 1.0, "confidence must clamp to [0, 1]")
        self.assertEqual(fact.source_turn_ids, [turns[0].turn_id])

        self.assertEqual(len(result.updated_rules), 1)
        rule = result.updated_rules[0]
        self.assertEqual(rule.category, "operational_directive", "invalid category must coerce")
        self.assertEqual(rule.priority, 5, "priority must clamp to [1, 5]")

        self.assertEqual(len(result.contradiction_resolutions), 1)
        contra = result.contradiction_resolutions[0]
        self.assertEqual((contra.prior_value, contra.new_value), ("$40/unit", "$52/unit"))

        self.assertEqual(result.pruned_noise_count, 1)
        self.assertEqual(s._client.models.calls, 1)

    async def test_daemon_persists_mocked_success_end_to_end(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        storage = SQLiteStorageAdapter(db_path=db_path)
        await storage.initialize()
        try:
            prior = Fact(entity="Vendor", attribute="price_per_unit", value="$40/unit")
            await storage.save_memory_profile(MemoryProfile(agent_id="a", facts=[prior]))
            await storage.save_turn(RawTurnLog(role="user", content="vendor price is now $52/unit"))

            daemon = DreamDaemon(
                storage=storage,
                synthesizer=_synthesizer_with_fake(json.dumps(GEMINI_PAYLOAD)),
                agent_id="a",
            )
            result = await daemon.consolidate_now()
            self.assertIsNotNone(result)

            profile = await storage.load_memory_profile("a")
            old = next(f for f in profile.facts if f.value == "$40/unit")
            new = next(f for f in profile.facts if f.value == "$52/unit")
            self.assertFalse(old.is_active)
            self.assertEqual(old.superseded_by, new.id)
            self.assertTrue(new.is_active)

            self.assertEqual(await storage.get_unconsolidated_turns(), [])
            self.assertEqual(len(profile.audit_history), 1)
        finally:
            await storage.close()
            os.remove(db_path)

    async def test_unparseable_response_raises_not_fabricates(self):
        s = _synthesizer_with_fake("this is not json")
        with self.assertRaises(DreamSynthesisError):
            await s.consolidate_window(
                unconsolidated_turns=[RawTurnLog(role="user", content="x")],
                existing_profile=MemoryProfile(agent_id="a"),
            )

    @unittest.skipUnless(
        os.environ.get("RUN_LIVE_GEMINI") == "1",
        "live Gemini smoke test; set RUN_LIVE_GEMINI=1 (and GEMINI_API_KEY) to run",
    )
    async def test_live_gemini_smoke(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        storage = SQLiteStorageAdapter(db_path=db_path)
        await storage.initialize()
        try:
            await storage.save_turn(RawTurnLog(role="user", content="vendor price is $40/unit"))
            daemon = DreamDaemon(storage=storage, synthesizer=DreamSynthesizer(), agent_id="a")
            result = await daemon.consolidate_now()
            self.assertIsNotNone(result)
            self.assertFalse(result.is_fallback)
            self.assertNotIn("Fallback dream consolidation", result.reasoning_summary)
        finally:
            await storage.close()
            os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
