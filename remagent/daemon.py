"""
DreamDaemon: Autonomous background worker for RemAgent.
Monitors agent activity, triggers biological sleep / REM consolidation cycles during idle windows,
and commits consolidated structured memory to storage.
"""

import asyncio
import logging
import time
from typing import Callable, Coroutine, List, Optional
from datetime import datetime, timezone

from remagent.schemas import (
    MemoryProfile,
    DreamConsolidationResult,
    current_utc_iso,
)
from remagent.storage.base import StorageAdapter
from remagent.engine.synthesizer import DreamSynthesizer

logger = logging.getLogger("remagent.daemon")


class DreamDaemon:
    """
    Background daemon that runs autonomous REM consolidation passes
    when the agent is idle or when explicitly triggered.
    """

    def __init__(
        self,
        storage: StorageAdapter,
        synthesizer: Optional[DreamSynthesizer] = None,
        agent_id: str = "default_agent",
        idle_threshold_seconds: float = 30.0,
        check_interval_seconds: float = 5.0,
        min_turns_to_dream: int = 1,
        on_dream_completed: Optional[Callable[[DreamConsolidationResult], Coroutine]] = None,
    ):
        self.storage = storage
        self.synthesizer = synthesizer or DreamSynthesizer()
        self.agent_id = agent_id
        self.idle_threshold_seconds = idle_threshold_seconds
        self.check_interval_seconds = check_interval_seconds
        self.min_turns_to_dream = min_turns_to_dream
        self.on_dream_completed = on_dream_completed

        self._last_activity_time: float = time.time()
        self._is_running: bool = False
        self._is_dreaming: bool = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def record_activity(self) -> None:
        """Call whenever user or agent interacts to reset idle countdown."""
        self._last_activity_time = time.time()

    @property
    def is_idle(self) -> bool:
        return (time.time() - self._last_activity_time) >= self.idle_threshold_seconds

    @property
    def idle_seconds(self) -> float:
        return time.time() - self._last_activity_time

    @property
    def is_dreaming(self) -> bool:
        return self._is_dreaming

    async def start(self) -> None:
        """Start the background daemon loop."""
        if self._is_running:
            return
        self._is_running = True
        await self.storage.initialize()
        self._task = asyncio.create_task(self._daemon_loop())
        logger.info(f"RemAgent DreamDaemon started for agent '{self.agent_id}' (idle threshold: {self.idle_threshold_seconds}s)")

    async def stop(self) -> None:
        """Stop background daemon gracefully."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"RemAgent DreamDaemon stopped for agent '{self.agent_id}'")

    async def _daemon_loop(self) -> None:
        while self._is_running:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                if not self._is_running:
                    break

                if self.is_idle and not self._is_dreaming:
                    # Check if there are unconsolidated turns
                    turns = await self.storage.get_unconsolidated_turns(limit=50)
                    if len(turns) >= self.min_turns_to_dream:
                        logger.info(f"Idle detected ({self.idle_seconds:.1f}s). Triggering REM consolidation for {len(turns)} turns.")
                        await self.consolidate_now()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in DreamDaemon loop: {e}", exc_info=True)

    async def consolidate_now(self) -> Optional[DreamConsolidationResult]:
        """
        Forces an immediate REM consolidation pass regardless of idle timer.
        """
        async with self._lock:
            if self._is_dreaming:
                logger.warning("Consolidation cycle is already in progress.")
                return None

            self._is_dreaming = True
            try:
                # 1. Fetch pending turns
                unconsolidated = await self.storage.get_unconsolidated_turns(limit=100)
                if not unconsolidated:
                    logger.debug("No turns to consolidate.")
                    return None

                # 2. Load existing profile
                profile = await self.storage.load_memory_profile(agent_id=self.agent_id)

                # 3. Run Gemini Dream Synthesizer
                result = await self.synthesizer.consolidate_window(
                    unconsolidated_turns=unconsolidated,
                    existing_profile=profile,
                )

                # 4. Apply Contradiction Invalidation
                # If any contradiction was detected, mark prior facts inactive
                for resolution in result.contradiction_resolutions:
                    for fact in profile.facts:
                        if (
                            fact.entity.lower() == resolution.entity.lower()
                            and fact.attribute.lower() == resolution.attribute.lower()
                            and fact.is_active
                        ):
                            fact.is_active = False
                            fact.superseded_by = result.run_id

                # 5. Append new active facts
                for new_fact in result.added_facts:
                    profile.facts.append(new_fact)

                # 6. Update or append operational rules
                existing_rule_map = {r.rule.lower(): r for r in profile.rules}
                for new_rule in result.updated_rules:
                    if new_rule.rule.lower() in existing_rule_map:
                        existing_rule_map[new_rule.rule.lower()].priority = new_rule.priority
                        existing_rule_map[new_rule.rule.lower()].rationale = new_rule.rationale
                        existing_rule_map[new_rule.rule.lower()].updated_at = current_utc_iso()
                    else:
                        profile.rules.append(new_rule)

                # 7. Update profile metadata
                profile.total_pruned_turns += result.pruned_noise_count
                profile.last_dream_at = result.timestamp

                # 8. Save updated profile & mark turns consolidated
                await self.storage.save_memory_profile(profile)
                await self.storage.mark_turns_consolidated(result.consolidated_turn_ids)
                await self.storage.record_consolidation_audit(result, agent_id=self.agent_id)

                logger.info(
                    f"REM consolidation finished. Added {len(result.added_facts)} facts, "
                    f"updated {len(result.updated_rules)} rules, pruned {result.pruned_noise_count} noise items. "
                    f"Estimated savings: {result.estimated_token_savings} tokens."
                )

                # Reset activity clock so it doesn't dream in a tight loop
                self.record_activity()

                if self.on_dream_completed:
                    try:
                        await self.on_dream_completed(result)
                    except Exception as cb_err:
                        logger.warning(f"Error in on_dream_completed callback: {cb_err}")

                return result

            except Exception as e:
                logger.error(f"Failed to execute REM consolidation: {e}", exc_info=True)
                raise
            finally:
                self._is_dreaming = False
