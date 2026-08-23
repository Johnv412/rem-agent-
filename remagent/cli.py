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

    # Command: log
    log_parser = subparsers.add_parser("log", help="Append a raw interaction turn into the memory buffer")
    log_parser.add_argument("--role", choices=["user", "assistant", "system", "tool"], required=True, help="Turn role")
    log_parser.add_argument("--content", required=True, help="Turn message content")
    log_parser.add_argument("--db", default="remagent_memory.db", help="SQLite database path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    storage = SQLiteStorageAdapter(db_path=args.db)
    await storage.initialize()

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

    elif args.command == "log":
        turn = RawTurnLog(role=args.role, content=args.content)
        await storage.save_turn(turn)
        print(f"📥 Logged raw turn {turn.turn_id} to buffer.")


def main():
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
