#!/usr/bin/env python3
"""
Hermes -> RemAgent session bridge (reference copy).

This is the canonical, version-controlled copy of the hook. Install it by
copying it into your Hermes home and declaring it in that home's config.yaml::

    cp remagent/integrations/hermes_session_log_hook.py \\
       "$HERMES_HOME/hooks/remagent_session_log.py"
    chmod +x "$HERMES_HOME/hooks/remagent_session_log.py"

    # $HERMES_HOME/config.yaml
    hooks:
      on_session_finalize:
        - command: /absolute/path/to/hooks/remagent_session_log.py
          timeout: 60

Hermes records first-use consent only inside its startup registration path,
so `hermes hooks doctor` can report an un-allowlisted hook but can never
approve one. Approve by starting an agent entrypoint once with
HERMES_ACCEPT_HOOKS=1 (or --accept-hooks, which exists on the chat/gateway/
cron/mcp/acp subparsers but NOT on `hooks`), then re-run `hermes hooks doctor`.


Fires on `on_session_finalize` (the real end-of-session boundary; note that
`on_session_end` fires once per TURN and would re-log the whole conversation
after every user message). Exports the finished session's user prompts and
feeds them into the shared brain through the sanctioned CLI:

    hermes sessions export --format jsonl --only user-prompts --session-id ID -
      |  remagent log --role user --session ID --content-file -

Contract:
  * memory.db is NEVER opened here. Every write goes through `remagent log`.
  * Always exits 0. A memory problem must never block or fail Vincent's turn.
  * stdout stays empty. Hermes parses hook stdout as JSON; diagnostics go to stderr.
  * Idempotent. A marker per session id means a second finalize (atexit after
    /reset, say) does not double-log the same session into memory.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EVENT = "on_session_finalize"
STATE_DIR = Path(os.environ.get("HERMES_HOME", "~/.hermes-020")).expanduser() / "hooks" / ".remagent-state"
DEFAULT_DB = "~/.remagent/memory.db"
EXPORT_TIMEOUT = 60
LOG_TIMEOUT = 30


def note(msg: str) -> None:
    print(f"remagent-hook: {msg}", file=sys.stderr)


def resolve(name: str):
    found = shutil.which(name)
    if found:
        return found
    for candidate in (
        Path.home() / ".local" / "bin" / name,
        Path("/Library/Frameworks/Python.framework/Versions/3.11/bin") / name,
        Path("/opt/homebrew/bin") / name,
        Path("/usr/local/bin") / name,
    ):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        note(f"unreadable hook payload on stdin: {exc}")
        return 0
    if not isinstance(payload, dict):
        note("hook payload was not a JSON object")
        return 0

    # Defensive: this script is only meaningful at the session boundary.
    event = payload.get("hook_event_name")
    if event and event != EVENT:
        note(f"ignoring event {event!r}; this hook only handles {EVENT}")
        return 0

    session_id = (payload.get("session_id") or "").strip()
    if not session_id:
        note("no session_id in payload; nothing to log")
        return 0

    marker = STATE_DIR / f"{session_id.replace('/', '_')}.done"
    if marker.exists():
        note(f"session {session_id} already logged; skipping")
        return 0

    hermes = resolve("hermes")
    remagent = resolve("remagent")
    if not hermes or not remagent:
        note(f"missing binary (hermes={hermes}, remagent={remagent}); nothing logged")
        return 0

    db = os.path.expanduser(os.environ.get("REMAGENT_DB") or DEFAULT_DB)

    try:
        export = subprocess.run(
            [hermes, "sessions", "export", "--format", "jsonl",
             "--only", "user-prompts", "--session-id", session_id, "-"],
            capture_output=True, text=True, timeout=EXPORT_TIMEOUT,
        )
    except Exception as exc:
        note(f"session export failed for {session_id}: {exc}")
        return 0
    if export.returncode != 0:
        note(f"session export exited {export.returncode} for {session_id}: "
             f"{(export.stderr or '').strip()[:200]}")
        return 0

    prompts = []
    for line in (export.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = (rec.get("text") or "").strip()
        if text:
            prompts.append(text)

    if not prompts:
        note(f"session {session_id} had no user prompts; nothing logged")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("empty\n", encoding="utf-8")
        return 0

    logged = 0
    for text in prompts:
        try:
            proc = subprocess.run(
                [remagent, "log", "--role", "user", "--session", session_id,
                 "--db", db, "--content-file", "-"],
                input=text, capture_output=True, text=True, timeout=LOG_TIMEOUT,
            )
        except Exception as exc:
            note(f"remagent log failed: {exc}")
            break
        if proc.returncode != 0:
            note(f"remagent log exited {proc.returncode}: {(proc.stderr or '').strip()[:200]}")
            break
        logged += 1

    if logged:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"{logged}\n", encoding="utf-8")
    note(f"session {session_id}: logged {logged}/{len(prompts)} user prompt(s) into {db}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never let a hook crash the agent
        print(f"remagent-hook: unexpected error: {exc}", file=sys.stderr)
        sys.exit(0)
