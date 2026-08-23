"""
Claude Code Hooks & Settings Generator for RemAgent.
Automatically scaffolds .claude/settings.json and hook scripts to connect Claude Code
with RemAgent's zero-vector memory lifecycle (SessionStart recall & Stop dream consolidation).
"""

import json
import os
import stat
from pathlib import Path
from typing import Dict, Optional


def generate_claude_configuration(
    target_dir: str = ".",
    db_path: str = "remagent_memory.db",
    agent_id: str = "claude_code",
    force: bool = False,
) -> Dict[str, str]:
    """
    Generates .claude/settings.json and executable hook shell scripts in target_dir.
    Returns a mapping of relative file paths to their creation status.
    """
    base_dir = Path(target_dir).resolve()
    claude_dir = base_dir / ".claude"
    hooks_dir = claude_dir / "hooks"

    claude_dir.mkdir(parents=True, exist_ok=True)
    hooks_dir.mkdir(parents=True, exist_ok=True)

    settings_path = claude_dir / "settings.json"
    session_start_hook_path = hooks_dir / "session_start.sh"
    stop_hook_path = hooks_dir / "stop.sh"

    settings_content = {
        "mcpServers": {
            "remagent": {
                "command": "remagent-mcp",
                "args": ["--db", db_path, "--agent", agent_id],
            }
        },
        "hooks": {
            "SessionStart": [
                {
                    "type": "command",
                    "command": f"remagent recall --format injection --agent {agent_id} --db {db_path}",
                }
            ],
            "Stop": [
                {
                    "type": "command",
                    "command": f"remagent dream --agent {agent_id} --db {db_path}",
                }
            ],
        },
    }

    session_start_script = f"""#!/bin/bash
# RemAgent SessionStart Hook for Claude Code
# Recalls active operational directives and discrete entity facts into Claude's context.
remagent recall --format injection --agent {agent_id} --db {db_path}
"""

    stop_script = f"""#!/bin/bash
# RemAgent Stop / Idle Hook for Claude Code
# Triggers background REM sleep consolidation to prune noise and extract newly learned facts.
remagent dream --agent {agent_id} --db {db_path}
"""

    results = {}

    # Write settings.json
    if not settings_path.exists() or force:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings_content, f, indent=2)
        results[str(settings_path)] = "created"
    else:
        results[str(settings_path)] = "skipped (already exists, use --force to overwrite)"

    # Write session_start.sh
    if not session_start_hook_path.exists() or force:
        with open(session_start_hook_path, "w", encoding="utf-8") as f:
            f.write(session_start_script)
        # Make script executable
        current_perms = os.stat(session_start_hook_path).st_mode
        os.chmod(session_start_hook_path, current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        results[str(session_start_hook_path)] = "created"
    else:
        results[str(session_start_hook_path)] = "skipped (already exists, use --force to overwrite)"

    # Write stop.sh
    if not stop_hook_path.exists() or force:
        with open(stop_hook_path, "w", encoding="utf-8") as f:
            f.write(stop_script)
        # Make script executable
        current_perms = os.stat(stop_hook_path).st_mode
        os.chmod(stop_hook_path, current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        results[str(stop_hook_path)] = "created"
    else:
        results[str(stop_hook_path)] = "skipped (already exists, use --force to overwrite)"

    return results
