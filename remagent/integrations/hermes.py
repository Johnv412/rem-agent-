"""
Hermes Agent Framework Integration for RemAgent.
Provides drop-in tool connectors and memory callback handlers for autonomous Hermes agents.
"""

import json
from typing import Any, Dict, List, Optional
from remagent.schemas import RawTurnLog, MemoryProfile, Fact, OperationalRule
from remagent.storage.base import StorageAdapter
from remagent.storage.sqlite import SQLiteStorageAdapter
from remagent.daemon import DreamDaemon


class HermesMemoryConnector:
    """
    High-level connector linking an autonomous Hermes agent to RemAgent zero-vector memory.
    """

    def __init__(
        self,
        storage: Optional[StorageAdapter] = None,
        daemon: Optional[DreamDaemon] = None,
        agent_id: str = "hermes_agent",
        auto_start_daemon: bool = True,
    ):
        self.agent_id = agent_id
        self.storage = storage or SQLiteStorageAdapter(db_path="hermes_memory.db")
        self.daemon = daemon or DreamDaemon(
            storage=self.storage,
            agent_id=self.agent_id,
            idle_threshold_seconds=20.0,
            check_interval_seconds=3.0,
        )
        self.auto_start_daemon = auto_start_daemon
        self._initialized = False

    async def initialize(self) -> None:
        if not self._initialized:
            await self.storage.initialize()
            if self.auto_start_daemon:
                await self.daemon.start()
            self._initialized = True

    async def log_interaction(
        self,
        role: str,
        content: str,
        session_id: str = "hermes_session",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RawTurnLog:
        """
        Appends raw turn event into the unconsolidated buffer and resets the daemon idle clock.
        """
        await self.initialize()
        turn = RawTurnLog(
            session_id=session_id,
            role=role,  # type: ignore
            content=content,
            tool_calls=tool_calls,
            metadata=metadata or {},
        )
        await self.storage.save_turn(turn)
        self.daemon.record_activity()
        return turn

    async def recall_memory(
        self, query_context: Optional[str] = None, max_facts: int = 25, max_rules: int = 15
    ) -> Dict[str, Any]:
        """
        Fetches active consolidated facts and operational directives for immediate agent reasoning.
        """
        await self.initialize()
        profile: MemoryProfile = await self.storage.load_memory_profile(agent_id=self.agent_id)

        active_facts = [f for f in profile.facts if f.is_active]
        active_rules = [r for r in profile.rules if r.is_active]

        # Sort rules by priority (1 is highest)
        active_rules.sort(key=lambda r: r.priority)

        # Basic context filtering if query provided
        if query_context:
            query_lower = query_context.lower()
            scored_facts = []
            for f in active_facts:
                score = 0
                if f.entity.lower() in query_lower:
                    score += 3
                if f.attribute.lower() in query_lower:
                    score += 2
                if str(f.value).lower() in query_lower:
                    score += 1
                scored_facts.append((score, f))
            scored_facts.sort(key=lambda x: x[0], reverse=True)
            active_facts = [item[1] for item in scored_facts[:max_facts]]
        else:
            active_facts = active_facts[:max_facts]

        active_rules = active_rules[:max_rules]

        return {
            "facts": [f.model_dump() for f in active_facts],
            "rules": [r.model_dump() for r in active_rules],
            "total_facts_count": len(profile.facts),
            "last_dream_at": profile.last_dream_at,
        }

    async def get_system_prompt_injection(self, query_context: Optional[str] = None) -> str:
        """
        Generates a clean, deterministic context block to inject into the Hermes system prompt.
        Zero vector embeddings, zero hallucinated noise.
        """
        memory_data = await self.recall_memory(query_context=query_context)
        facts = memory_data.get("facts", [])
        rules = memory_data.get("rules", [])

        if not facts and not rules:
            return ""

        sections = ["\n[REMAGENT AUTONOMOUS MEMORY CONTEXT]"]
        if rules:
            sections.append("OPERATIONAL HEURISTICS & USER PREFERENCES:")
            for r in rules:
                sections.append(f"- [{r['category'].upper()}] (Priority {r['priority']}): {r['rule']}")

        if facts:
            sections.append("\nCONSOLIDATED ENTITY KNOWLEDGE GRAPH:")
            for f in facts:
                sections.append(f"- {f['entity']}.{f['attribute']} = {f['value']} (confidence: {f['confidence']:.2f})")

        sections.append("[END MEMORY CONTEXT]\n")
        return "\n".join(sections)

    async def trigger_dream_cycle(self) -> Dict[str, Any]:
        """
        Forces an immediate REM sleep consolidation pass.
        """
        await self.initialize()
        result = await self.daemon.consolidate_now()
        if result:
            return {
                "status": "consolidated",
                "run_id": result.run_id,
                "added_facts_count": len(result.added_facts),
                "updated_rules_count": len(result.updated_rules),
                "pruned_noise_count": result.pruned_noise_count,
                "reasoning_summary": result.reasoning_summary,
                "estimated_token_savings": result.estimated_token_savings,
            }
        return {"status": "skipped", "message": "No unconsolidated turns to process."}

    async def shutdown(self) -> None:
        await self.daemon.stop()
        await self.storage.close()


class RemAgentTool:
    """
    Hermes Agent Tool definition allowing LLMs to directly inspect, query, or trigger memory.
    """

    def __init__(self, connector: HermesMemoryConnector):
        self.connector = connector

    def get_tool_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "remagent_memory",
                "description": (
                    "Zero-vector autonomous memory tool. Allows the agent to recall synthesized entity facts, "
                    "operational rules, or trigger background REM dream consolidation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["recall", "trigger_sleep", "get_status"],
                            "description": "The memory action to perform",
                        },
                        "query_context": {
                            "type": "string",
                            "description": "Optional context to filter recalled facts and directives",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, action: str, query_context: Optional[str] = None) -> str:
        if action == "recall":
            data = await self.connector.recall_memory(query_context=query_context)
            return json.dumps(data, indent=2)
        elif action == "trigger_sleep":
            data = await self.connector.trigger_dream_cycle()
            return json.dumps(data, indent=2)
        elif action == "get_status":
            return json.dumps({
                "agent_id": self.connector.agent_id,
                "is_dreaming": self.connector.daemon.is_dreaming,
                "is_idle": self.connector.daemon.is_idle,
                "idle_seconds": round(self.connector.daemon.idle_seconds, 1),
            }, indent=2)
        return json.dumps({"error": f"Unknown action: {action}"})
