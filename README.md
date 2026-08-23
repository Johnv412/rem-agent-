# RemAgent 🧠💤

> **Zero-Vector Autonomous Memory Framework for AI Agents**  
> Powered by **Google Gemini** and biological sleep / REM consolidation principles.  
> [dreamengine.dev](https://dreamengine.dev) • [remagent.dev](https://remagent.dev)

---

## ⚡ The Problem: Vector Databases Are Noisy, Brittle & Expensive

Traditional AI agent architectures rely on **Vector RAG (Retrieval-Augmented Generation)**. However, in long-running, autonomous agent workloads, vector databases fail predictably:

| Failure Mode in Vector RAG | How RemAgent Resolves It via REM Consolidation |
|---|---|
| **Semantic Drift & Chaff Bloat** | RAG stores every pleasantry ("Thanks!"), failed tool trace, and typo as embeddings. **RemAgent prunes 80%+ noise** during background sleep cycles. |
| **Contradiction Paralysis** | If a user says *"Use MySQL"* on Day 1 and *"Switch to Postgres"* on Day 2, RAG retrieves both chunks and hallucinates. **RemAgent explicitly resolves contradictions** and marks obsolete facts superseded. |
| **Token Bloat & Cost** | Injecting 10 large raw text chunks wastes thousands of context tokens. **RemAgent injects a tight, deterministic graph** (<200 tokens) of attributed facts. |
| **Zero Cognitive Synthesis** | Vector DBs are dumb indexers. **RemAgent synthesizes behavioral heuristics & operational directives** autonomously. |

---

## 🧬 How It Works: The Biological REM Sleep Cycle

RemAgent mimics mammalian memory consolidation:

```
[Agent Awake] ──> Logs Raw Episodic Turns (User, Tools, LLM) into Buffer
                       │
                       ▼ (Agent Inactivity / Idle Timer Triggered)
[Dream Daemon] ──> Wakes in Background (Zero Latency to Active User)
                       │
                       ├─► 1. NOISE PRUNING (Discards ephemeral tool traces, chatter)
                       ├─► 2. FACT EXTRACTION (Builds high-confidence entity-attribute graph)
                       ├─► 3. CONTRADICTION RESOLUTION (Supersedes stale beliefs with new truth)
                       └─► 4. OPERATIONAL HEURISTICS (Extracts durable directives)
                       │
                       ▼
[Structured Memory Graph] (Zero-Vector, Pure Deterministic JSON/SQLite/Firestore)
                       │
                       ▼ (Next User Query)
[Agent Instant Recall] ──> Zero-shot prompt injection with 100% precision!
```

---

## 📦 Installation

```bash
# Standard installation with Gemini & SQLite
pip install remagent

# Enterprise cloud installation with Google Cloud Firestore
pip install "remagent[firestore]"
```

Set your Gemini API key:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

---

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
        idle_threshold_seconds=15.0,  # Dreams after 15s of agent inactivity
    )
    await daemon.start()

    # 3. Log agent interaction turns
    await storage.save_turn(RawTurnLog(
        role="user",
        content="Hey! For this project, let's use PostgreSQL instead of SQLite, and enable strict TypeScript mode."
    ))
    daemon.record_activity()

    # 4. Trigger an immediate dream cycle (or let daemon dream during idle)
    result = await daemon.consolidate_now()

    print(f"✨ Consolidation Result: {result.reasoning_summary}")
    print(f"   Added Facts: {len(result.added_facts)}")
    print(f"   Updated Rules: {len(result.updated_rules)}")
    print(f"   Estimated Token Savings: ~{result.estimated_token_savings} tokens")

    # 5. Inspect consolidated memory profile
    profile = await storage.load_memory_profile()
    for fact in profile.facts:
        if fact.is_active:
            print(f"📌 {fact.entity}.{fact.attribute} = {fact.value} (conf: {fact.confidence})")

    await daemon.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🤖 Hermes Agent Framework Integration

RemAgent provides a first-class connector and tool integration for autonomous agent loops:

```python
from remagent.integrations.hermes import HermesMemoryConnector, RemAgentTool

connector = HermesMemoryConnector(agent_id="coding_assistant")
await connector.initialize()

# 1. Before generating responses, inject zero-vector recalled memory into system prompt
memory_prompt_injection = await connector.get_system_prompt_injection(query_context="database configuration")

# 2. When user or agent speaks, log turn (resets idle clock)
await connector.log_interaction(
    role="user",
    content="Remember to always run tests with pytest before committing."
)

# 3. LLM tool access
tool = RemAgentTool(connector)
tool_definition = tool.get_tool_schema()
```

---

## 🛠️ CLI Usage

```bash
# Trigger an immediate REM consolidation pass on your database
remagent dream --db my_agent_memory.db

# Inspect active facts, directives, and token savings
remagent status --db my_agent_memory.db

# Append a raw turn from bash/scripts
remagent log --role user --content "Deploying to us-west2 region."
```

---

## 🏛️ Architecture & Schemas

### `Fact`
- `entity`: Target entity (e.g. `User`, `ProjectBackend`, `AuthService`)
- `attribute`: Specific property (e.g. `database`, `port`, `framework`)
- `value`: Ground-truth value (e.g. `PostgreSQL`, `3000`, `Express`)
- `confidence`: Mathematical confidence score (0.0 to 1.0)
- `superseded_by`: Optional ID of fact that invalidated this record
- `is_active`: Boolean state flag

### `OperationalRule`
- `category`: `user_preference` | `coding_standard` | `architecture_heuristic` | `operational_directive` | `domain_constraint`
- `rule`: Concise, actionable heuristic
- `rationale`: Cognitive reasoning behind the rule
- `priority`: Priority scale 1 (critical) to 5 (minor)

---

## 📄 License
Apache-2.0. Built with Google Gemini for the next generation of autonomous AI systems.
