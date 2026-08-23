"""
MemoryDecayEngine: Biological Synaptic Pruning & Temporal Decay.
Implements exponential Ebbinghaus retention decay for low-confidence or unreferenced facts,
ensuring multi-month agent operation remains lean and pristine without manual cleanup.
"""

import math
import time
from datetime import datetime
from typing import List, Tuple, Union
from remagent.schemas import Fact, MemoryProfile


def _parse_timestamp(ts: Union[str, float, int]) -> float:
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        try:
            return float(ts)
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            pass
    return time.time()


class MemoryDecayEngine:
    """
    Applies biological decay algorithms to long-dormant facts while reinforcing frequently cited knowledge.
    """

    def __init__(
        self,
        half_life_days: float = 30.0,
        reinforcement_boost: float = 0.15,
        min_confidence_floor: float = 0.20,
    ):
        self.half_life_seconds = half_life_days * 86400.0
        self.reinforcement_boost = reinforcement_boost
        self.min_confidence_floor = min_confidence_floor

    def apply_decay(
        self, profile: MemoryProfile, current_timestamp: float = None
    ) -> Tuple[MemoryProfile, List[Fact]]:
        """
        Applies exponential decay: C(t) = C_0 * e^(-lambda * delta_t)
        Returns (updated_profile, list_of_pruned_facts).
        """
        now = current_timestamp or time.time()
        decay_constant = math.log(2) / self.half_life_seconds

        active_facts: List[Fact] = []
        pruned_facts: List[Fact] = []

        for fact in profile.facts:
            # P1 or 1.0 confidence ground truth facts never decay
            if fact.confidence >= 1.0 or not fact.is_active:
                active_facts.append(fact)
                continue

            delta_t = max(0.0, now - _parse_timestamp(fact.timestamp))
            decayed_conf = fact.confidence * math.exp(-decay_constant * delta_t)

            if decayed_conf < self.min_confidence_floor:
                fact.is_active = False
                pruned_facts.append(fact)
            else:
                fact.confidence = round(decayed_conf, 3)
                active_facts.append(fact)

        profile.facts = active_facts + pruned_facts
        return profile, pruned_facts

    def reinforce_fact(self, fact: Fact) -> None:
        """Reinforces a fact when actively validated or referenced by the agent."""
        fact.confidence = min(1.0, fact.confidence + self.reinforcement_boost)
        fact.timestamp = time.time()
