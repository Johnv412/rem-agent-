"""
DreamSynthesizer: Autonomous cognitive consolidation engine powered by Google Gemini.
Emulates biological sleep/REM consolidation: prunes conversational noise, extracts discrete
entity facts, resolves contradictions, and updates operational heuristics without vector databases.
"""

import asyncio
import json
import logging
import os
from typing import List, Optional
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


logger = logging.getLogger("remagent.synthesizer")

RULE_CATEGORIES = [
    "user_preference",
    "coding_standard",
    "architecture_heuristic",
    "operational_directive",
    "domain_constraint",
]


class DreamSynthesisError(RuntimeError):
    """
    Raised when the Gemini consolidation call fails for any reason (missing API
    key, transport error, schema rejection, unparseable response).
    A failed dream must never look like a successful one: callers must let this
    propagate and must not persist any state derived from the failed run.
    """


class SynthesizedFact(BaseModel):
    """A single extracted fact, as returned by Gemini."""
    entity: str = Field(..., description="Target entity, user, project, or domain object (e.g., 'User', 'Vendor')")
    attribute: str = Field(..., description="Specific property or relation (e.g., 'price_per_unit', 'auth_strategy')")
    value: str = Field(..., description="Current ground-truth value as a string (e.g., '$52/unit', 'OAuth 2.0')")
    confidence: float = Field(default=1.0, description="Confidence score of the synthesized fact (0.0 - 1.0)")


class SynthesizedRule(BaseModel):
    """A single operational rule, as returned by Gemini."""
    category: str = Field(..., description="One of: 'user_preference', 'coding_standard', 'architecture_heuristic', 'operational_directive', 'domain_constraint'")
    rule: str = Field(..., description="Concise, actionable rule statement")
    rationale: str = Field(default="Synthesized from user interactions", description="Reasoning or empirical turn context justifying this directive")
    priority: int = Field(default=3, description="Priority weight (1 = critical/unbreakable, 5 = minor guideline)")


class SynthesizedContradiction(BaseModel):
    """A contradiction between a new observation and an existing fact, as returned by Gemini."""
    entity: str = Field(..., description="Subject entity of the contradicted fact (must match the existing fact's entity exactly)")
    attribute: str = Field(..., description="Subject attribute of the contradicted fact (must match the existing fact's attribute exactly)")
    prior_value: str = Field(..., description="The outdated value being superseded")
    new_value: str = Field(..., description="The new ground-truth value")
    resolution_reasoning: str = Field(..., description="Reasoning why the new observation overrides the prior state")


class DreamSynthesisOutput(BaseModel):
    """Internal Pydantic schema for Gemini structured JSON response."""
    added_facts: List[SynthesizedFact] = Field(
        default_factory=list,
        description="Discrete entity facts extracted from the unconsolidated turns"
    )
    updated_rules: List[SynthesizedRule] = Field(
        default_factory=list,
        description="Operational directives or preferences synthesized from the turns"
    )
    contradictions: List[SynthesizedContradiction] = Field(
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
   - MANDATORY ENTITY REUSE: before introducing a new entity name, scan the EXISTING CONSOLIDATED KNOWLEDGE GRAPH for an entity that refers to the same real-world thing and REUSE its exact name (e.g. do not create "Commander" if "Commander Project" already exists, or "Vincent Agent" if "Vincent" exists). Same-thing-different-name splits break contradiction resolution. Reuse existing attribute names the same way.
   - Format: entity, attribute, value, confidence (0.0 - 1.0).
   - Never extract vague sentiments; focus on crisp ground-truth.

3. CONTRADICTION RESOLUTION & SUPERSEDING:
   - Carefully review the existing memory facts.
   - If a new turn contains a revised decision (e.g., user changed database from MySQL to PostgreSQL, or changed preferred style from functional to OOP), explicitly resolve the contradiction: the newer observation SUPERSEDES the older one.
   - State the reasoning why the new fact overrides the prior state.
   - MANDATORY: every contradiction you report MUST be accompanied by an entry in added_facts carrying the same entity and attribute with the new ground-truth value. A contradiction entry alone does NOT store the new value — omitting the added_facts entry would erase the memory instead of updating it.

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
        max_attempts: int = 3,
        retry_backoff_seconds: float = 1.0,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.max_attempts = max(1, max_attempts)
        self.retry_backoff_seconds = retry_backoff_seconds
        self._client = None

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        """Retry only genuinely transient transport failures: timeouts,
        connection drops, 429 rate limits, and 5xx server errors."""
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if isinstance(code, int) and (code == 429 or 500 <= code <= 599):
            return True
        transient_names = ("Timeout", "ConnectionError", "ConnectionReset", "ServiceUnavailable", "DeadlineExceeded")
        return any(name in type(exc).__name__ for name in transient_names)

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

        if not (self.api_key or os.environ.get("GOOGLE_API_KEY")):
            raise DreamSynthesisError(
                "GEMINI_API_KEY is not set; cannot run dream consolidation. "
                "No memory was modified and unconsolidated turns remain queued."
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
        turns_block = "\n".join(turn_history_str)

        user_prompt = f"""
### EXISTING CONSOLIDATED KNOWLEDGE GRAPH (ACTIVE FACTS):
{existing_facts_str}

### EXISTING ACTIVE OPERATIONAL RULES:
{existing_rules_str}

### UNCONSOLIDATED RAW EPISODIC TURNS TO CONSOLIDATE:
{turns_block}

Execute the REM sleep consolidation cycle now:
1. Prune all ephemeral noise & pleasantries.
2. Extract new/updated entity facts with source turn IDs.
3. Detect and resolve contradictions against existing facts.
4. Synthesize updated operational rules.
"""

        # We call Gemini with structured JSON output. Transient transport
        # errors get a bounded retry with backoff; anything else — and any
        # retry exhaustion — fails loudly. Parse errors are never retried.
        response = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config={
                        "system_instruction": DREAM_PROMPT_SYSTEM,
                        "response_mime_type": "application/json",
                        "response_schema": DreamSynthesisOutput,
                    },
                )
                break
            except Exception as exc:
                if attempt < self.max_attempts and self._is_transient_error(exc):
                    delay = self.retry_backoff_seconds * attempt
                    logger.warning(
                        "Transient Gemini error on attempt %d/%d: %s — retrying in %.1fs",
                        attempt, self.max_attempts, exc, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error("Dream synthesis failed; no memory will be written: %s", exc, exc_info=True)
                raise DreamSynthesisError(f"Gemini dream synthesis failed: {exc}") from exc

        try:
            response_data = json.loads(response.text)
            parsed = DreamSynthesisOutput(**response_data)
        except Exception as exc:
            logger.error(
                "Dream synthesis returned an unparseable response; no memory will be written: %s",
                exc, exc_info=True,
            )
            raise DreamSynthesisError(f"Gemini dream synthesis failed: {exc}") from exc

        # Map to domain entities
        turn_ids = [t.turn_id for t in unconsolidated_turns]
        
        # Build discrete Fact objects
        added_facts: List[Fact] = []
        for f in parsed.added_facts:
            added_facts.append(
                Fact(
                    entity=f.entity,
                    attribute=f.attribute,
                    value=f.value,
                    confidence=max(0.0, min(1.0, f.confidence)),
                    source_turn_ids=turn_ids,
                    is_active=True,
                )
            )

        # Build OperationalRule objects
        updated_rules: List[OperationalRule] = []
        for r in parsed.updated_rules:
            cat = r.category if r.category in RULE_CATEGORIES else "operational_directive"
            updated_rules.append(
                OperationalRule(
                    category=cat,
                    rule=r.rule,
                    rationale=r.rationale,
                    priority=max(1, min(5, r.priority)),
                    is_active=True,
                )
            )

        # Build Contradiction Resolutions
        contradiction_resolutions: List[ContradictionResolution] = []
        for c in parsed.contradictions:
            contradiction_resolutions.append(
                ContradictionResolution(
                    prior_fact_id=None,
                    entity=c.entity,
                    attribute=c.attribute,
                    prior_value=c.prior_value,
                    new_value=c.new_value,
                    resolution_reasoning=c.resolution_reasoning,
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
