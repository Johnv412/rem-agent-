# RemAgent Finish-Line Roadmap

Worked by an autonomous loop: one task per iteration, first unchecked task
first. A task is checked off ONLY after its "Done when" gate passes. Tasks
marked **[GATED]** are user-only decisions — the loop must skip them and
list them when everything else is done.

**Standing rules (every iteration):**
- No operation reports success unless it did the thing it claims. Failures
  exit non-zero and preserve state. Never fake, stub, or work around a
  failing gate to check a box.
- Never publish to PyPI, deploy anything, change repo visibility, or map
  domains.
- Gates: `python3 -m pytest tests/ -q` for Python tasks; add
  `npm run lint && npm run build` when web files are touched.
- Commit each completed task with a descriptive message before moving on.

---

## Phase 1 — Engine correctness

- [x] **T1. `superseded_by` stores the replacing fact's ID, not the run_id.**
  The Fact schema docstring promises "Fact ID that invalidated/superseded
  this record" but `daemon.consolidate_now()` writes the dream run_id.
  Store the ID of the replacing fact (the added/materialized fact for the
  same entity/attribute); fall back to run_id only if no replacing fact
  exists (invariant should make that impossible). Update schema docstring
  and existing tests.
  *Done when:* a supersession test asserts `old.superseded_by == new.id`;
  pytest green.

- [x] **T2. Distinguish "busy" from "up to date" in `consolidate_now()`.**
  (Audit finding.) `daemon.consolidate_now()` returns `None` both when
  there are no unconsolidated turns AND when the lock is held (dream in
  progress), so callers report "memory is fully consolidated" while turns
  sit unprocessed. Make the two outcomes distinguishable (e.g. raise a
  `ConsolidationBusyError` or return a typed status) and update ALL
  callers — `cli.py` dream, the MCP `remagent_dream` tool in
  `remagent/integrations/claude_code.py`, and any hook/daemon paths —
  so "busy" is reported as busy, never as up-to-date.
  *Done when:* a failure-path test triggers the lock-contention path and
  asserts callers do NOT report up-to-date; pytest green.

- [x] **T3. Enforce the governor's token budget on P1 rules.**
  (Audit finding.) `governor.py:68-70` appends all priority-1 rules
  unconditionally, so `max_tokens` can silently overflow — the token
  budget is a headline feature. Enforce the budget (truncate with an
  explicit marker) or signal the overflow to the caller; silent overflow
  is not an option. Verify the cited lines first and fix whatever the
  real shape is.
  *Done when:* a failure-path test builds a profile whose P1 rules alone
  exceed `max_tokens` and asserts the output either fits the budget or
  carries an explicit overflow signal; pytest green.

- [x] **T4. Wire the decay engine in.**
  `remagent/decay.py` is complete but dead code — nothing calls it. Add a
  `remagent decay` CLI subcommand (same `--db`/`--agent` flags) that
  applies decay to the stored profile and persists it, printing what was
  pruned. Failures exit non-zero and do not persist.
  *Done when:* tests cover the happy path and a failure path (e.g. missing
  profile); pytest green.

- [x] **T5. Mocked-Gemini success-path tests.**
  The suite proves failures fail but the success path is only proven by
  live runs. Stub `generate_content` to return typed JSON and test:
  parsing into `DreamSynthesisOutput`, fact/rule/contradiction mapping,
  and end-to-end daemon persistence. Add one optional live smoke test
  gated behind `RUN_LIVE_GEMINI=1` (skipped by default).
  *Done when:* new tests pass without any network access; pytest green.

- [x] **T6. Bounded retry for transient Gemini errors.**
  In `synthesizer.consolidate_window`, retry the Gemini call up to 2
  extra times with short backoff on transient errors (timeouts, 5xx,
  429), then raise `DreamSynthesisError` as today. Never retry on
  schema/parse errors. Log each retry.
  *Done when:* a test with a stub that fails twice then succeeds passes,
  and a test with a persistent failure still exits via
  `DreamSynthesisError`; pytest green.

## Phase 2 — Packaging honesty

- [ ] **T7. Fix package metadata.**
  pyproject URLs point at `github.com/remagent/remagent` (wrong repo) —
  point them at `https://github.com/Johnv412/rem-agent-`. Remove unused
  `typer`/`rich` from the `all` extra. Confirm a LICENSE file exists
  matching the Apache-2.0 claims (dashboard footer, README); add the
  Apache-2.0 text if missing.
  *Done when:* `pip install -e ".[all]"` succeeds; metadata matches
  reality; pytest green.

- [ ] **T8. Build and validate the wheel (NO upload).**
  `python3 -m build` then `twine check dist/*` (install both tools if
  needed). Artifacts stay local/gitignored.
  *Done when:* twine check passes on sdist and wheel.

## Phase 3 — Claude Code integration proof

- [ ] **T9. Verify the MCP integration end-to-end and audit it for fake
  success.**
  Install the `[claude]` extra (the `mcp` dependency is not currently
  installed). Audit every tool handler in
  `remagent/integrations/claude_code.py` and the generated hooks in
  `claude_hooks.py` for the caught-failure-returns-success shape — in
  particular `remagent_dream` must surface `DreamSynthesisError` and the
  T2 busy state, not report success. Run `remagent init-claude` in a
  sandbox temp dir and verify the scaffold. Add failure-path tests for
  the MCP dream tool.
  *Done when:* MCP failure-path tests pass; pytest green.

## Phase 4 — Dashboard & CI

- [ ] **T10. Label the dashboard honestly as a demo playground.**
  The dashboard looks like a live view of real memory but runs on seeded
  in-memory simulation state. Add a clear "Demo playground — simulated
  data" indicator in the UI (e.g. Navbar badge) and a README sentence.
  (Wiring it to the real SQLite DB is deliberately out of scope — record
  it as a future idea in this file's Icebox instead.)
  *Done when:* badge renders; `npm run lint && npm run build` green.

- [ ] **T11. GitHub Actions CI.**
  `.github/workflows/ci.yml`: on push/PR run (a) Python 3.11:
  `pip install -e ".[claude]" && python -m pytest tests/ -q`, (b) Node 22:
  `npm ci && npm run lint && npm run build`. No secrets required; the
  suite must stay green without `GEMINI_API_KEY`.
  *Done when:* workflow file is valid (yaml parses, actions pinned to
  major versions) and the same commands pass locally; committed & pushed.

## Phase 5 — Finish-line verification

- [ ] **T12. Clean-environment install test.**
  Fresh venv in a temp dir; follow README verbatim (clone step may be
  simulated by the local checkout): `pip install -e ".[claude]"`, then
  `remagent log`/`dream`/`recall` E2E with the real key sourced from
  `.env`, and `remagent dream` without a key must exit non-zero. Fix any
  README/UX gaps discovered.
  *Done when:* every README command works exactly as written from the
  clean venv.

## Gated — user-only decisions (loop must skip)

- [ ] **[GATED] G1. Publish `remagent` to PyPI** (name verified free).
  After: flip README back to `pip install remagent` instructions.
- [ ] **[GATED] G2. Deploy dashboard to Cloud Run** via
  `scripts/deploy-cloudrun.sh` and map the custom domain.
- [ ] **[GATED] G3. Repo visibility** — decide public vs private; if
  public, secrets scan + README badges first.

## Icebox (not scheduled)

- Wire the dashboard to the real SQLite DB instead of simulated state.
- `remagent decay` auto-run inside the dream cycle.
