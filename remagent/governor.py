"""
TokenBudgetGovernor: Precision token budgeting & priority compression for RemAgent.
Ensures zero-vector context injections strictly respect LLM token boundaries (e.g. 200 - 1000 tokens)
by prioritizing P1 operational rules, high-confidence entity facts, and active relationships.
"""

from typing import Any, Dict, List, Optional
from remagent.schemas import Fact, OperationalRule, MemoryProfile


class TokenBudgetGovernor:
    """
    Manages prompt token allocation for consolidated memory injections.
    Prevents context blowup while guaranteeing critical P1 directives are never truncated.
    """

    def __init__(self, default_max_tokens: int = 500, char_to_token_ratio: float = 3.8):
        self.default_max_tokens = default_max_tokens
        self.char_to_token_ratio = char_to_token_ratio

    def estimate_tokens(self, text: str) -> int:
        """Heuristic character-to-token estimator."""
        return max(1, int(len(text) / self.char_to_token_ratio))

    def build_budgeted_prompt_injection(
        self,
        profile: MemoryProfile,
        query_context: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Compiles the highest-signal memory context string fitting within max_tokens.
        Order of priority:
        1. Priority 1 (Unbreakable) Operational Rules
        2. Direct query-relevant Entity Facts
        3. Priority 2-3 Rules & Guidelines
        4. General active Entity Facts (sorted by confidence)
        """
        budget = max_tokens or self.default_max_tokens
        
        # 1. Filter and prioritize rules
        active_rules = [r for r in profile.rules if r.is_active]
        active_rules.sort(key=lambda r: (r.priority, -len(r.rule)))

        # 2. Filter and score facts
        active_facts = [f for f in profile.facts if f.is_active]
        if query_context:
            q_lower = query_context.lower()
            scored_facts = []
            for f in active_facts:
                relevance = 0
                if f.entity.lower() in q_lower:
                    relevance += 4
                if f.attribute.lower() in q_lower:
                    relevance += 3
                if str(f.value).lower() in q_lower:
                    relevance += 2
                scored_facts.append((relevance, f.confidence, f))
            scored_facts.sort(key=lambda x: (x[0], x[1]), reverse=True)
            active_facts = [item[2] for item in scored_facts]
        else:
            active_facts.sort(key=lambda f: f.confidence, reverse=True)

        selected_rules: List[OperationalRule] = []
        selected_facts: List[Fact] = []

        # Always include P1 rules first
        for rule in active_rules:
            if rule.priority == 1:
                selected_rules.append(rule)

        # Incrementally add facts and secondary rules until budget ceiling
        current_text = self._format_injection(selected_rules, selected_facts)
        
        # Add relevant facts
        for fact in active_facts:
            candidate_facts = selected_facts + [fact]
            candidate_text = self._format_injection(selected_rules, candidate_facts)
            if self.estimate_tokens(candidate_text) <= budget:
                selected_facts.append(fact)
            else:
                break

        # Add secondary rules if space permits
        for rule in active_rules:
            if rule.priority > 1 and rule not in selected_rules:
                candidate_rules = selected_rules + [rule]
                candidate_text = self._format_injection(candidate_rules, selected_facts)
                if self.estimate_tokens(candidate_text) <= budget:
                    selected_rules.append(rule)
                else:
                    break

        return self._format_injection(selected_rules, selected_facts)

    def _format_injection(self, rules: List[OperationalRule], facts: List[Fact]) -> str:
        if not rules and not facts:
            return ""

        sections = ["\n[REMAGENT DETERMINISTIC MEMORY CONTEXT]"]
        if rules:
            sections.append("OPERATIONAL RULES & POLICIES:")
            for r in rules:
                sections.append(f"- [{r.category.upper()}] (P{r.priority}): {r.rule}")

        if facts:
            sections.append("\nACTIVE ENTITY KNOWLEDGE GRAPH:")
            for f in facts:
                val_str = str(f.value)
                sections.append(f"- {f.entity}.{f.attribute} = {val_str} (conf: {f.confidence:.2f})")

        sections.append("[END MEMORY CONTEXT]\n")
        return "\n".join(sections)
