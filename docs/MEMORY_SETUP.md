# Memory Setup Roadmap — global RemAgent memory for John

Goal: one global memory at `/Users/test/.remagent/memory.db`, agent `john`,
fed automatically by Claude Code in this repo. Worked by an autonomous loop:
one task per iteration, FIRST unchecked task first, gates green before
check-off, each task committed, failures reported as failures.

**Standing rules:** no operation reports success unless it did the thing it
claims; failures exit non-zero and preserve state. No PyPI publish, no
deploy, no repo visibility change. Antigravity MCP wiring and cron dreaming
are explicitly OUT OF SCOPE until Claude Code memory is proven working.

Gates: `python3 -m pytest tests/ -q` for code tasks; task-specific
verification listed per task.

---

- [x] **M1. Close the turn-capture gap (the real build item).**
  The `init-claude` scaffold wires SessionStart (recall) and Stop (dream)
  hooks but nothing logs turns, so dreams have nothing to consolidate.
  Extend `remagent/integrations/claude_hooks.py` to also generate a
  **UserPromptSubmit** hook: a Python hook script that reads Claude Code's
  hook JSON on stdin, extracts the prompt, and appends it to the episodic
  buffer via the storage API directly (no PATH dependence). Rules:
  - Empty/whitespace prompt → exit 0, log nothing.
  - Any failure (bad JSON, storage error) → exit **1** (non-blocking error:
    Claude Code shows it but the prompt still goes through; exit 2 would
    block the user's prompt, which is worse than a missed log) and persist
    nothing.
  - `--db` path is expanduser'd and its parent dir auto-created.
  - Register the hook in the generated `.claude/settings.json` under
    `UserPromptSubmit`.
  Tests: scaffold generates the script + settings entry; functional
  subprocess tests for: prompt logged verbatim, empty prompt no-op,
  invalid JSON → exit 1 and nothing persisted.
  *Done when:* pytest green including the new tests.

- [ ] **M2. Machine prereqs in ~/.zshrc.**
  Append a clearly-marked block: put
  `/Library/Frameworks/Python.framework/Versions/3.11/bin` on PATH, and
  source `~/.remagent/env` (file mode 0600 holding
  `export GEMINI_API_KEY=...`, value copied from the repo `.env`, never
  committed or printed). Show John the exact block added (key redacted).
  *Done when:* `zsh -ic 'which remagent && [ -n "$GEMINI_API_KEY" ]'`
  succeeds from a fresh interactive shell.

- [ ] **M3. Delete the two stale bug-artifact DBs.**
  `remagent_memory.db` and `dream_live.db` in the repo root — both are
  pre-fix artifacts (fabricated fallback fact; shell-expanded empty
  prices). Gitignored, nothing references them.
  *Done when:* both files gone; `git status` unchanged.

- [ ] **M4. Wire this repo: `remagent init-claude` against the global DB.**
  Create `/Users/test/.remagent/` and run init-claude with
  `--db /Users/test/.remagent/memory.db --agent john` in this repo.
  Verify `.claude/settings.json` registers the MCP server, SessionStart,
  Stop, AND UserPromptSubmit hooks with the global DB path; hook scripts
  executable. Note: `.claude/` is gitignored — hooks are machine-local by
  design.
  *Done when:* scaffold files verified on disk with correct paths.

- [ ] **M5. Smoke test — raw output, not a summary.**
  Simulate the real pipeline end to end: pipe a genuine hook-JSON prompt
  (a real fact about this project) through the UserPromptSubmit hook
  script → run the exact Stop-hook dream command (live Gemini) → run the
  exact SessionStart recall command as a fresh session would → dump
  `raw_turns`, `facts_json`, and the audit row from the global DB.
  Fallback fingerprints must be absent; the injected context must contain
  the logged fact.
  *Done when:* raw output shows the fact flowing log → dream → injection.

## Out of scope (held until M5 proves the pipeline)
- Antigravity MCP registration (all seven windows).
- launchd/cron scheduled dreaming and weekly decay.
