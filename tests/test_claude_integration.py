"""
Unit & Integration Tests for Claude Code MCP Server and Configuration Hooks.
Verifies tool registration, execution, hook generation, and CLI subcommands.
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from remagent.schemas import Fact, OperationalRule, RawTurnLog, MemoryProfile
from remagent.storage.sqlite import SQLiteStorageAdapter
from remagent.integrations.claude_code import create_claude_mcp_server
from remagent.integrations.claude_hooks import generate_claude_configuration


class TestClaudeIntegrationSuite(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="claude_test_")
        self.db_path = os.path.join(self.temp_dir, "test_claude_mem.db")
        self.storage = SQLiteStorageAdapter(db_path=self.db_path)
        await self.storage.initialize()

    async def asyncTearDown(self):
        await self.storage.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_mcp_server_tools_registered(self):
        server = create_claude_mcp_server(
            name="test_remagent",
            default_db_path=self.db_path,
            default_agent_id="test_claude_agent",
        )
        self.assertIsNotNone(server)

        # Verify tool registration via tool manager
        tool_names = list(server._tool_manager._tools.keys())
        self.assertIn("remagent_recall", tool_names)
        self.assertIn("remagent_log", tool_names)
        self.assertIn("remagent_dream", tool_names)

    async def test_mcp_log_and_recall_tools(self):
        server = create_claude_mcp_server(
            name="test_remagent",
            default_db_path=self.db_path,
            default_agent_id="test_claude_agent",
        )

        # 1. Log a turn via MCP tool call
        log_result = await server.call_tool(
            "remagent_log",
            {
                "role": "user",
                "content": "Configure backend to use FastAPI with Python 3.11",
                "session_id": "claude_session_1",
                "agent_id": "test_claude_agent",
                "db_path": self.db_path,
            },
        )
        self.assertFalse(log_result.is_error)
        
        # Verify turn in SQLite
        turns = await self.storage.get_unconsolidated_turns(session_id="claude_session_1")
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].content, "Configure backend to use FastAPI with Python 3.11")

        # 2. Seed memory profile with fact and rule
        fact = Fact(
            entity="Backend",
            attribute="framework",
            value="FastAPI",
            confidence=0.98,
        )
        rule = OperationalRule(
            category="coding_standard",
            rule="Always write async route handlers in FastAPI",
            rationale="Maintains non-blocking I/O performance",
            priority=1,
        )
        profile = MemoryProfile(
            agent_id="test_claude_agent",
            facts=[fact],
            rules=[rule],
        )
        await self.storage.save_memory_profile(profile)

        # 3. Recall memory via MCP tool call
        recall_result = await server.call_tool(
            "remagent_recall",
            {
                "query_context": "FastAPI async",
                "agent_id": "test_claude_agent",
                "db_path": self.db_path,
                "max_tokens": 300,
            },
        )
        self.assertFalse(recall_result.is_error)
        
        # Parse output
        output_text = recall_result.content[0].text
        data = json.loads(output_text)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_active_facts"], 1)
        self.assertEqual(data["total_active_rules"], 1)
        self.assertIn("REMAGENT DETERMINISTIC MEMORY CONTEXT", data["prompt_injection"])
        self.assertIn("Always write async route handlers in FastAPI", data["prompt_injection"])

    async def test_mcp_dream_tool(self):
        server = create_claude_mcp_server(
            name="test_remagent",
            default_db_path=self.db_path,
            default_agent_id="test_claude_agent",
        )

        # Trigger dream when no unconsolidated turns exist -> skipped status
        dream_result = await server.call_tool(
            "remagent_dream",
            {
                "agent_id": "test_claude_agent",
                "db_path": self.db_path,
            },
        )
        self.assertFalse(dream_result.is_error)
        data = json.loads(dream_result.content[0].text)
        self.assertEqual(data["status"], "skipped")

    def test_claude_hooks_and_settings_generation(self):
        target_dir = os.path.join(self.temp_dir, "workspace")
        os.makedirs(target_dir, exist_ok=True)

        results = generate_claude_configuration(
            target_dir=target_dir,
            db_path="workspace_memory.db",
            agent_id="dev_claude",
            force=False,
        )

        settings_file = Path(target_dir) / ".claude" / "settings.json"
        session_start_script = Path(target_dir) / ".claude" / "hooks" / "session_start.sh"
        stop_script = Path(target_dir) / ".claude" / "hooks" / "stop.sh"

        self.assertTrue(settings_file.exists())
        self.assertTrue(session_start_script.exists())
        self.assertTrue(stop_script.exists())

        # Verify executable permissions
        self.assertTrue(os.access(session_start_script, os.X_OK))
        self.assertTrue(os.access(stop_script, os.X_OK))

        # Check settings.json content
        with open(settings_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        self.assertIn("mcpServers", config)
        self.assertIn("remagent", config["mcpServers"])
        self.assertEqual(config["mcpServers"]["remagent"]["command"], "remagent-mcp")
        self.assertIn("hooks", config)
        self.assertIn("SessionStart", config["hooks"])
        self.assertIn("Stop", config["hooks"])

        # Check idempotency
        second_run = generate_claude_configuration(target_dir=target_dir, force=False)
        for status in second_run.values():
            self.assertIn("skipped", status)


if __name__ == "__main__":
    unittest.main()
