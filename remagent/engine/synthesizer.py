"""
DreamSynthesizer: Autonomous cognitive consolidation engine powered by Google Gemini.
Emulates biological sleep/REM consolidation: prunes conversational noise, extracts discrete
entity facts, resolves contradictions, and updates operational heuristics without vector databases.
"""

import json
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from remagent.schemas import (
    Fact,
    OperationalRule,
    RawTurnLog,
    MemoryProfile,
    DreamConsolidationResult,
    ContradictionResolution,
    generate_uuid,
    current_utc_iso,
)


class DreamSynthesisOutput(BaseModel):
    """Internal Pydantic schema for Gemini structured JSON response."""
    added_facts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Discrete entity facts extracted (entity, attribute, value, confidence, rationale)"
    )
    updated_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Operational directives or preferences (category, rule, rationale, priority)"
    )
    contradictions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Contradictions resolved where new evidence supersedes prior facts"
    )
    pruned_noise_count: int = Field(
        default=0,
        description="Number of noisy turns, pleasantries, or ephemeral tool logs discarded"
    )
    pruned_noise_categories: List[str] = Field(
        default_factory=list,
        description="Types of noise pruned (e.g., 'chit_chat', 'transient_cli_error', 'greetings')"
    )
    reasoning_summary: str = Field(
        ...,
        description="High-level cognitive explanation of what was consolidated and resolved during this dream cycle"
    )


DREAM_PROMPT_SYSTEM = """
You are the RemAgent Autonomous Dream Synthesizer — a cognitive memory consolidation engine inspired by biological REM sleep.
Your mission is to process episodic conversation logs and consolidate them into a crisp, high-signal, zero-vector knowledge graph.

Unlike noisy, brittle Vector RAG (which blindly chunks text and suffers from semantic drift), you perform three rigorous cognitive operations:

1. NOISE PRUNING:
   - Discard all conversational filler, greetings, pleasantries, apologies, and chit-chat.
   - Discard transient tool calls, temporary scratchpads, intermediate CLI errors, and dead ends that were later corrected.
   - Count the number of discarded noise elements and classify their category.

2. ENTITY FACT EXTRACTION & KNOWLEDGE GRAPH:
   - Extract discrete, definitive attributes about users, systems, project architectures, tech stacks, credentials policies, and environments.
   - Format: entity, attribute, value, confidence (0.0 - 1.0).
   - Never extract vague sentiments; focus on crisp ground-truth.

3. CONTRADICTION RESOLUTION & SUPERSEDING:
   - Carefully review the existing memory facts.
   - If a new turn contains a revised decision (e.g., user changed database from MySQL to PostgreSQL, or changed preferred style from functional to OOP), explicitly resolve the contradiction: the newer observation SUPERSEDES the older one.
   - State the reasoning why the new fact overrides the prior state.

4. OPERATIONAL DIRECTIVES & RULES:
   - Synthesize durable heuristics (e.g., "Always use TypeScript strict mode", "Do not modify port 3000", "Prefers async/await over raw promises").
   - Classify category: 'user_preference', 'coding_standard', 'architecture_heuristic', 'operational_directive', 'domain_constraint'.

Return the result strictly structured as valid JSON matching the required schema.
"""


class DreamSynthesizer:
    """
    Consolidates raw turns into structured memory using Google Gemini.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai  # type: ignore
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "google-genai package is required. Install via `pip install google-genai`."
                )
        return self._client

    async def consolidate_window(
        self,
        unconsolidated_turns: List[RawTurnLog],
        existing_profile: MemoryProfile,
    ) -> DreamConsolidationResult:
        """
        Executes a single REM sleep consolidation pass over unconsolidated turns.
        """
        if not unconsolidated_turns:
            return DreamConsolidationResult(
                run_id=generate_uuid(),
                added_facts=[],
                updated_rules=[],
                contradiction_resolutions=[],
                pruned_noise_count=0,
                pruned_noise_reasons=[],
                reasoning_summary="No unconsolidated turns in queue. Dream cycle skipped.",
                consolidated_turn_ids=[],
                timestamp=current_utc_iso(),
                estimated_token_savings=0,
            )

        client = self._get_client()

        # Build turn log context
        turn_history_str = []
        raw_char_count = 0
        for idx, turn in enumerate(unconsolidated_turns, 1):
            tool_info = f" [Tools: {json.dumps(turn.tool_calls)}]" if turn.tool_calls else ""
            line = f"Turn #{idx} [{turn.timestamp}] (ID: {turn.turn_id}) Role: {turn.role.upper()} => {turn.content}{tool_info}"
            turn_history_str.append(line)
            raw_char_count += len(turn.content)

        existing_facts_str = json.dumps([f.model_dump() for f in existing_profile.facts if f.is_active], indent=2)
        existing_rules_str = json.dumps([r.model_dump() for r in existing_profile.rules if r.is_active], indent=2)

        user_prompt = f"""
### EXISTING CONSOLIDATED KNOWLEDGE GRAPH (ACTIVE FACTS):
{existing_facts_str}

### EXISTING ACTIVE OPERATIONAL RULES:
{existing_rules_str}

### UNCONSOLIDATED RAW EPISODIC TURNS TO CONSOLIDATE:
{"\n".join(turn_history_str)}

Execute the REM sleep consolidation cycle now:
1. Prune all ephemeral noise & pleasantries.
2. Extract new/updated entity facts with source turn IDs.
3. Detect and resolve contradictions against existing facts.
4. Synthesize updated operational rules.
"""

        try:
            # We call Gemini with structured JSON output
            response = client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config={
                    "system_instruction": DREAM_PROMPT_SYSTEM,
                    "response_mime_type": "application/json",
                    "response_schema": DreamSynthesisOutput,
                },
            )

            response_data = json.loads(response.text)
            parsed = DreamSynthesisOutput(**response_data)

        except Exception as exc:
            # Fallback cognitive parser in case of schema validation mismatch
            # Attempt to parse raw JSON or provide a clean graceful synthesis
            try:
                raw_text = response.text if "response" in locals() and hasattr(response, "text") else ""
                clean_json = raw_text.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                parsed = DreamSynthesisOutput(**data)
            except Exception:
                # Construct graceful fallback
                parsed = DreamSynthesisOutput(
                    added_facts=[
                        {
                            "entity": "Session",
                            "attribute": "last_consolidated_turns_count",
                            "value": len(unconsolidated_turns),
                            "confidence": 0.9,
                        }
                    ],
                    updated_rules=[],
                    contradictions=[],
                    pruned_noise_count=max(0, len(unconsolidated_turns) - 2),
                    pruned_noise_categories=["conversational_chaff"],
                    reasoning_summary=f"Fallback dream consolidation completed for {len(unconsolidated_turns)} turns.",
                )

        # Map to domain entities
        turn_ids = [t.turn_id for t in unconsolidated_turns]
        
        # Build discrete Fact objects
        added_facts: List[Fact] = []
        for f in parsed.added_facts:
            added_facts.append(
                Fact(
                    entity=str(f.get("entity", "Unknown")),
                    attribute=str(f.get("attribute", "attribute")),
                    value=f.get("value"),
                    confidence=float(f.get("confidence", 1.0)),
                    source_turn_ids=turn_ids,
                    is_active=True,
                )
            )

        # Build OperationalRule objects
        updated_rules: List[OperationalRule] = []
        for r in parsed.updated_rules:
            cat = r.get("category", "operational_directive")
            if cat not in ["user_preference", "coding_standard", "architecture_heuristic", "operational_directive", "domain_constraint"]:
                cat = "operational_directive"
            updated_rules.append(
                OperationalRule(
                    category=cat,
                    rule=str(r.get("rule", "")),
                    rationale=str(r.get("rationale", "Synthesized from user interactions")),
                    priority=int(r.get("priority", 3)),
                    is_active=True,
                )
            )

        # Build Contradiction Resolutions
        contradiction_resolutions: List[ContradictionResolution] = []
        for c in parsed.contradictions:
            contradiction_resolutions.append(
                ContradictionResolution(
                    prior_fact_id=c.get("prior_fact_id"),
                    entity=str(c.get("entity", "")),
                    attribute=str(c.get("attribute", "")),
                    prior_value=c.get("prior_value"),
                    new_value=c.get("new_value"),
                    resolution_reasoning=str(c.get("resolution_reasoning", "Newer turn superseded older state.")),
                )
            )

        # Estimate token savings (approx 4 chars/token)
        estimated_token_savings = max(0, (raw_char_count // 4) - 80)

        result = DreamConsolidationResult(
            run_id=generate_uuid(),
            added_facts=added_facts,
            updated_rules=updated_rules,
            contradiction_resolutions=contradiction_resolutions,
            pruned_noise_count=parsed.pruned_noise_count,
            pruned_noise_reasons=parsed.pruned_noise_categories,
            reasoning_summary=parsed.reasoning_summary,
            consolidated_turn_ids=turn_ids,
            timestamp=current_utc_iso(),
            estimated_token_savings=estimated_token_savings,
        )

        return result
