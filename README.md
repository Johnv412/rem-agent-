

 # RemAgent 🧠💤

**Zero-Vector Autonomous Memory Framework for AI Agents**

Powered by Google Gemini and modeled on biological sleep / REM memory consolidation.

dreamengine.dev • remagent.dev

<!-- Once CI workflows are live, add the badge here:
[![CI](https://github.com/Johnv412/rem-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Johnv412/rem-agent/actions/workflows/ci.yml)
-->

---

## ⚡ The Problem: Vector Databases Are Noisy, Brittle & Expensive

Traditional AI agent architectures rely on Vector RAG (Retrieval-Augmented Generation). In long-running, autonomous agent workloads, vector databases fail in predictable ways:

| Failure Mode in Vector RAG | How RemAgent Resolves It |
| --- | --- |
| **Semantic Drift & Chaff Bloat** — RAG stores every pleasantry ("Thanks!"), failed tool trace, and typo as embeddings. | RemAgent prunes ephemeral noise during background sleep cycles, keeping only durable facts and rules. |
| **Contradiction Paralysis** — a user says "Use MySQL" on Day 1 and "Switch to Postgres" on Day 2; RAG retrieves both chunks and the agent guesses. | RemAgent explicitly resolves contradictions and marks obsolete facts as superseded, with a pointer to what replaced them. |
| **Token Bloat & Cost** — injecting ten raw text chunks burns thousands of context tokens per query. | RemAgent injects a tight, deterministic graph of attributed facts, filtered to a configurable token budget. |
| **Zero Cognitive Synthesis** — vector DBs are indexers; they never learn anything. | RemAgent synthesizes behavioral heuristics and operational directives from raw session history. |

The core bet: for a single agent or team, **a small, legible, versioned store of resolved facts beats a large pile of embeddings.** You can `cat` it, `diff` it, and audit it — no retrieval ranking to debug.

## 🆚 Why Not Mem0, Zep, or Letta?

Those are excellent projects, and if you need hosted, multi-tenant, vector-hybrid memory at scale, use them. RemAgent makes different trade-offs on purpose:

- **Zero-vector.** No embeddings, no similarity search, no "why did it rank the wrong chunk third." Facts are structured records you can read.
- **Local-first.** Memory is a SQLite file on your machine by default. Nothing leaves your computer except consolidation calls to the LLM (see Privacy below).
- **Consolidation-centered.** The sleep cycle — pruning, contradiction resolution, heuristic extraction — is the product, not a bolt-on.
- **Small enough to audit.** One Python package, one database file, plain schemas.

If your memory problem is "one developer / one team, long-running agents, facts that change" — that's what this is built for.

## 🧬 How It Works: The REM Sleep Cycle

RemAgent mimics mammalian memory consolidation:

```
[Agent Awake] ──> Logs raw episodic turns (user, tools, LLM) into a buffer
                       │
                       ▼  (idle timer or scheduled trigger — see Dream Modes)
[Dream Daemon] ──> Wakes in background (zero latency to the active user)
                       │
                       ├─► 1. NOISE PRUNING          (discards ephemeral tool traces, chatter)
                       ├─► 2. FACT EXTRACTION         (builds an entity-attribute graph)
                       ├─► 3. CONTRADICTION RESOLUTION (supersedes stale beliefs with new truth)
                       └─► 4. OPERATIONAL HEURISTICS   (extracts durable directives)
                       │
                       ▼
[Structured Memory Graph]  (zero-vector, deterministic — SQLite or Firestore)
                       │
                       ▼  (next session / next query)
[Agent Recall] ──> Deterministic memory injection into the prompt, within token budget
```

### Dream Modes

RemAgent consolidates in two ways, and you can use either or both:

1. **Idle-trigger (embedded).** The `DreamDaemon` runs inside your Python process and dreams after a configurable period of agent inactivity. Best for long-running agent loops.
2. **Scheduled (system-level).** For Claude Code and desktop use, `remagent init-claude` can wire dreams to session lifecycle hooks, and consolidation can also run on a schedule (launchd on macOS, cron elsewhere). Best for capturing work across many short sessions.

A note on cadence: consolidation benefits from seeing *batches* of sessions. Dreaming too frequently over a young memory store mostly re-processes the same entries. Nightly is a sensible default for scheduled mode; tune from there.

## 🔒 Privacy & Data Handling

Read this before installing. RemAgent captures interaction turns — which for developers can include code, file paths, client names, and anything else you type.

- **What's stored:** raw turns and consolidated facts, in a local SQLite database (`memory.db`) you own. Nothing is stored by RemAgent anywhere else.
- **What leaves your machine:** during a dream cycle, buffered turns are sent to the Gemini API for consolidation. That is the only network egress. If your sessions may contain secrets or client-confidential material, treat this the same way you'd treat any LLM API usage — and don't log what you can't send.
- **Purging:** delete the database file, or use `remagent decay` to age out low-confidence facts. Superseded facts retain history until purged.
- **Enterprise:** the `[firestore]` extra moves storage to Google Cloud Firestore under your own GCP project and IAM. Bring your own compliance posture; RemAgent doesn't add one for you.

## 📦 Installation

> RemAgent is not yet published on PyPI. Install from source:

```bash
git clone https://github.com/Johnv412/rem-agent.git
cd rem-agent

# Standard installation with Gemini & SQLite
pip install -e .

# Claude Code terminal & IDE integration (MCP server + hooks)
pip install -e ".[claude]"

# Enterprise cloud installation with Google Cloud Firestore
pip install -e ".[firestore]"
```

Set your Gemini API key:

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

> **Provider note:** consolidation currently runs on Gemini. The synthesizer is built as an adapter; additional providers (Claude, OpenAI-compatible endpoints) are on the roadmap. Contributions welcome.

## 🚀 Quickstart (Python 3.11+)

```python
import asyncio
from remagent import DreamDaemon, SQLiteStorageAdapter, DreamSynthesizer, RawTurnLog

async def main():
    # 1. Initialize local SQLite storage
    storage = SQLiteStorageAdapter("my_agent_memory.db")
    await storage.initialize()

    # 2. Start the autonomous background Dream Daemon
    daemon = DreamDaemon(
        storage=storage,
        idle_threshold_seconds=15.0,  # dreams after 15s of agent inactivity
    )
    await daemon.start()

    # 3. Log agent interaction turns
    await storage.save_turn(RawTurnLog(
        role="user",
        content="Hey! For this project, let's use PostgreSQL instead of SQLite, and enable strict TypeScript mode."
    ))
    daemon.record_activity()

    # 4. Trigger an immediate dream cycle (or let the daemon dream during idle)
    result = await daemon.consolidate_now()

    print(f"✨ Consolidation: {result.reasoning_summary}")
    print(f"   Added facts: {len(result.added_facts)}")
    print(f"   Updated rules: {len(result.updated_rules)}")
    print(f"   Estimated token savings: ~{result.estimated_token_savings} tokens")

    # 5. Inspect consolidated memory
    profile = await storage.load_memory_profile()
    for fact in profile.facts:
        if fact.is_active:
            print(f"📌 {fact.entity}.{fact.attribute} = {fact.value} (conf: {fact.confidence})")

    await daemon.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🤖 Hermes Agent Framework Integration

RemAgent provides a first-class connector and tool integration for autonomous agent loops:

```python
from remagent.integrations.hermes import HermesMemoryConnector, RemAgentTool

connector = HermesMemoryConnector(agent_id="coding_assistant")
await connector.initialize()

# 1. Before generating a response, inject recalled memory into the system prompt
memory_context = await connector.get_system_prompt_injection(
    query_context="database configuration"
)

# 2. When the user or agent speaks, log the turn (resets the idle clock)
await connector.log_interaction(
    role="user",
    content="Remember to always run tests with pytest before committing."
)

# 3. Expose memory to the LLM as a tool
tool = RemAgentTool(connector)
tool_definition = tool.get_tool_schema()
```

## 🧠 Claude Code Integration

RemAgent has native support for Claude Code (Anthropic's agentic CLI). Developers running Claude Code gain autonomous zero-vector memory, deterministic memory injection at session start, and background consolidation across sessions.

### 2-Step Setup

```bash
# 1. Install RemAgent with Claude MCP support (from a clone of this repo)
pip install -e ".[claude]"

# 2. Scaffold .claude/settings.json and lifecycle hooks
remagent init-claude
```

By default `init-claude` configures the current repository. To share one memory across every Claude Code session on the machine, install the hooks globally (see docs) so all projects write to the same store.

### What init-claude configures

```json
{
  "mcpServers": {
    "remagent": {
      "command": "remagent-mcp",
      "args": []
    }
  },
  "hooks": {
    "SessionStart": [
      { "type": "command", "command": "remagent recall --format injection" }
    ],
    "Stop": [
      { "type": "command", "command": "remagent dream --agent claude_code" }
    ]
  }
}
```

### Exposed MCP Tools

- **`remagent_recall`** — recalls active entity facts and prioritized operational directives, filtered to the prompt token budget.
- **`remagent_log`** — appends raw developer or agent interaction turns to the unconsolidated buffer.
- **`remagent_dream`** — triggers an immediate consolidation pass: extract facts, resolve contradictions, prune noise.

## 🛠️ CLI Usage

```bash
# Scaffold Claude Code hooks and settings in the current repository
remagent init-claude

# Recall consolidated memory context for prompt injection
remagent recall --format injection

# Trigger an immediate consolidation pass
remagent dream --db my_agent_memory.db

# Inspect active facts, directives, and estimated token savings
remagent status --db my_agent_memory.db

# Run the built-in observation-period check: prints a plain-English
# PASSED / FAILED / IN PROGRESS verdict on memory health over time
remagent soak

# Append a raw turn from bash/scripts
remagent log --role user --content "Deploying to us-west2 region."

# Apply Ebbinghaus temporal decay to long-dormant, low-confidence facts
remagent decay --db my_agent_memory.db --half-life-days 30 --floor 0.2

# Export active memory as a readable markdown mirror (one file per entity,
# rules in rules.md) — cat/grep/diff your agent's memory. The database stays
# the source of truth; add --export-md to `remagent dream` to regenerate the
# mirror after every dream cycle.
remagent export --markdown --db my_agent_memory.db

# Self-audit the installation (hooks, jobs, database integrity)
remagent doctor
```

## 🏛️ Architecture & Schemas

### Fact

| Field | Description |
| --- | --- |
| `entity` | Target entity (e.g. `User`, `ProjectBackend`, `AuthService`) |
| `attribute` | Specific property (e.g. `database`, `port`, `framework`) |
| `value` | Ground-truth value (e.g. `PostgreSQL`, `3000`, `Express`) |
| `confidence` | Confidence score, 0.0–1.0 |
| `superseded_by` | Optional ID of the fact that invalidated this record |
| `is_active` | Boolean state flag |

### OperationalRule

| Field | Description |
| --- | --- |
| `category` | `user_preference` \| `coding_standard` \| `architecture_heuristic` \| `operational_directive` \| `domain_constraint` |
| `rule` | Concise, actionable heuristic |
| `rationale` | Reasoning behind the rule |
| `priority` | 1 (critical) to 5 (minor) |

Every fact carries provenance (where it came from), a supersession chain (what replaced it), and decay (how it ages out). Memory you can't audit is just configuration with extra steps.

## 🖥️ Demo Dashboard

The repo contains a web dashboard (Vite + React + Express, `npm run dev`) that visualizes the dream cycle. **It is a demo playground running on seeded, in-memory simulation data** — not a live view of a real RemAgent database. Its Gemini-backed features (consolidation, agent chat) require `GEMINI_API_KEY` and return explicit errors without it.

## 🗺️ Roadmap

- [ ] PyPI release (v1.0.0 — pending soak validation)
- [ ] Additional LLM providers for the synthesizer (Claude, OpenAI-compatible)
- [ ] Global (machine-wide) Claude Code hook install as a first-class command
- [ ] Team-shared memory stores with per-agent namespaces
- [ ] Reproducible benchmark suite for pruning and recall quality

## 👤 Maintainer

Built by **John Vincent** ([@Johnv412](https://github.com/Johnv412)) — JV.AI Systems. I build production AI voice and automation systems for service businesses; RemAgent is the memory layer extracted from that work. Issues and PRs welcome.

## 📄 License

Apache-2.0. Built with Google Gemini for the next generation of autonomous AI systems.
