"""
Command-line interface for the RemAgent framework.
"""

import argparse
import asyncio
import json
import sys
from remagent.daemon import DreamDaemon
from remagent.engine.synthesizer import DreamSynthesizer
from remagent.schemas import RawTurnLog
from remagent.storage.sqlite import SQLiteStorageAdapter
from remagent.governor import TokenBudgetGovernor
from remagent.integrations.claude_hooks import generate_claude_configuration


async def run_cli():
    parser = argparse.ArgumentParser(
        prog="remagent",
        description="RemAgent: Autonomous Zero-Vector Memory Framework for AI Agents",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: dream
    dream_parser = subparsers.add_parser("dream", help="Trigger an immediate REM consolidation cycle")
    dream_parser.add_argument("--db", default="remagent_memory.db", help="SQLite database path")
    dream_parser.add_argument("--agent", default="default_agent", help="Agent identifier")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Inspect active memory profile and consolidated facts")
    status_parser.add_argument("--db", default="remagent_memory.db", help="SQLite database path")
    status_parser.add_argument("--agent", default="default_agent", help="Agent identifier")

    # Command: recall
    recall_parser = subparsers.add_parser("recall", help="Recall consolidated memory and active directives")
    recall_parser.add_argument("--format", choices=["injection", "json"], default="injection", help="Output format")
    recall_parser.add_argument("--query", default=None, help="Query context for fact relevance filtering")
    recall_parser.add_argument("--agent", default="default_agent", help="Agent identifier")
    recall_parser.add_argument("--max-tokens", type=int, default=500, help="Maximum token budget for prompt injection")
    recall_parser.add_argument("--db", default="remagent_memory.db", help="SQLite database path")

    # Command: log
    log_parser = subparsers.add_parser("log", help="Append a raw interaction turn into the memory buffer")
    log_parser.add_argument("--role", choices=["user", "assistant", "system", "tool"], required=True, help="Turn role")
    log_parser.add_argument("--content", required=True, help="Turn message content")
    log_parser.add_argument("--session", default="default_session", help="Session ID")
    log_parser.add_argument("--db", default="remagent_memory.db", help="SQLite database path")

    # Command: init-claude
    init_claude_parser = subparsers.add_parser("init-claude", help="Scaffold Claude Code hooks and settings.json")
    init_claude_parser.add_argument("--dir", default=".", help="Target workspace directory")
    init_claude_parser.add_argument("--db", default="remagent_memory.db", help="SQLite database path")
    init_claude_parser.add_argument("--agent", default="claude_code", help="Agent identifier")
    init_claude_parser.add_argument("--force", action="store_true", help="Overwrite existing configuration and hooks")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "init-claude":
        results = generate_claude_configuration(
            target_dir=args.dir,
            db_path=args.db,
            agent_id=args.agent,
            force=args.force,
        )
        print("🧠 [RemAgent] Claude Code Integration Scaffolding:")
        for path, status in results.items():
            print(f"   • {path}: {status}")
        print("\n✨ Claude Code is now wired to RemAgent memory!")
        print("   - SessionStart hook: Pre-loads active rules & knowledge into context.")
        print("   - Stop hook: Runs background REM sleep consolidation when work completes.")
        print("   - MCP server: Exposes remagent_recall, remagent_log, and remagent_dream tools.")
        return

    storage = SQLiteStorageAdapter(db_path=args.db)
    await storage.initialize()

    try:
        if args.command == "dream":
            print("🧠 [RemAgent] Initiating REM Sleep Consolidation Cycle...")
            synthesizer = DreamSynthesizer()
            daemon = DreamDaemon(storage=storage, synthesizer=synthesizer, agent_id=args.agent)
            result = await daemon.consolidate_now()
            if result:
                print(f"✨ Consolidation Complete! Run ID: {result.run_id}")
                print(f"   - Added Facts: {len(result.added_facts)}")
                print(f"   - Updated Rules: {len(result.updated_rules)}")
                print(f"   - Pruned Noise Items: {result.pruned_noise_count}")
                print(f"   - Token Savings: ~{result.estimated_token_savings} tokens")
                print(f"   - Cognitive Reasoning: {result.reasoning_summary}")
            else:
                print("💤 No unconsolidated turns found. Agent memory is already fully consolidated.")

        elif args.command == "status":
            profile = await storage.load_memory_profile(agent_id=args.agent)
            print(f"📊 [RemAgent Profile: {profile.agent_id}]")
            print(f"   Last Dream: {profile.last_dream_at or 'Never'}")
            print(f"   Total Pruned Turns: {profile.total_pruned_turns}")
            print(f"\n📌 Active Facts ({len([f for f in profile.facts if f.is_active])}):")
            for f in profile.facts:
                if f.is_active:
                    print(f"   • {f.entity}.{f.attribute} = {f.value} (conf: {f.confidence})")
            print(f"\n📜 Operational Directives & Rules ({len([r for r in profile.rules if r.is_active])}):")
            for r in profile.rules:
                if r.is_active:
                    print(f"   • [{r.category.upper()}] P{r.priority}: {r.rule}")

        elif args.command == "recall":
            profile = await storage.load_memory_profile(agent_id=args.agent)
            if args.format == "json":
                active_facts = [f.model_dump() for f in profile.facts if f.is_active]
                active_rules = [r.model_dump() for r in profile.rules if r.is_active]
                print(json.dumps({
                    "agent_id": args.agent,
                    "facts": active_facts,
                    "rules": active_rules,
                    "last_dream_at": profile.last_dream_at,
                }, indent=2))
            else:
                governor = TokenBudgetGovernor(default_max_tokens=args.max_tokens)
                injection = governor.build_budgeted_prompt_injection(
                    profile=profile,
                    query_context=args.query,
                    max_tokens=args.max_tokens,
                )
                if injection:
                    print(injection)
                else:
                    print("[No active memory facts or rules found]")

        elif args.command == "log":
            turn = RawTurnLog(session_id=args.session, role=args.role, content=args.content)
            await storage.save_turn(turn)
            print(f"📥 Logged raw turn {turn.turn_id} to buffer.")
    finally:
        await storage.close()


def main():
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
