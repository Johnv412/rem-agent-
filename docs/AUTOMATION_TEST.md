# Automation & Test-Campaign Roadmap

Goal: fully automate the memory system and its testing at three altitudes
(mocked / live-API / real-usage soak) so the open-source flip is earned by
evidence. Worked by the loop: one task per iteration, FIRST unchecked task
first, gates green before check-off, each task committed, failures reported
as failures.

**Standing rules:** no operation reports success unless it did the thing it
claims; failures exit non-zero and preserve state. No PyPI publish, no
deploy, no repo visibility change. Workflow files under `.github/workflows/`
CANNOT be pushed from this machine (OAuth token lacks `workflow` scope) —
they are STAGED in `ci-staging/` for John to paste via the GitHub web UI.

Gates: `python3 -m pytest tests/ -q` for code tasks, plus each task's own
"Done when".

---

- [x] **A1. `remagent doctor` — pipeline self-audit command (keystone).**
  New `remagent/doctor.py` + CLI subcommand. Read-only checks against the
  DB, each printed ✅/❌; exit 0 only if ALL pass, else exit 1:
  1. DB file exists and passes `PRAGMA quick_check`.
  2. `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) present in the environment.
  3. Queue health: unconsolidated turns ≤ `--max-queue` (default 100), AND
     if any turns are queued, the profile's `last_dream_at` is within
     `--max-dream-age-hours` (default 24) — else dreams aren't keeping up.
  4. Zero fallback fingerprints anywhere in audit history
     (`Fallback dream consolidation%` summaries) or facts
     (`Session.last_consolidated_turns_count`).
  5. Erasure invariant at rest: every inactive fact with `superseded_by`
     set has an active fact for the same entity/attribute
     (case-insensitive). Decayed facts (`superseded_by` null) are exempt —
     decay without replacement is legitimate.
  Tests (subprocess, like other CLI tests): healthy DB → 0; queue backlog →
  1; stale dream with queue → 1; fallback fingerprint → 1; superseded
  without replacement → 1; decayed without replacement → 0; missing key →
  1.
  *Done when:* pytest green including the new tests.

- [x] **A2. launchd: scheduled dreaming every 30 min.**
  `~/Library/LaunchAgents/com.remagent.dream.plist` (template committed at
  `config/launchd/`): every 1800s run dream then doctor against the global
  DB (`--agent john`), absolute paths, sourcing `~/.remagent/env` (launchd
  does not read `.zshrc`), stdout/stderr to `~/.remagent/logs/dream.log`.
  Non-zero exits (busy=2, failure=1) are the honest signal, not a problem.
  *Done when:* agent loaded (`launchctl list`), one triggered run logged,
  log shows real dream-or-clean-empty output plus doctor verdict.

- [x] **A3. launchd: weekly decay (Sunday).**
  `com.remagent.decay.plist` same pattern, `StartCalendarInterval` Sunday
  03:00, logs to `~/.remagent/logs/decay.log`.
  *Done when:* agent loaded and one manually-triggered (`launchctl
  kickstart`) run logged successfully.

- [x] **A4. Live-Gemini canary script + staged (disabled) workflow.**
  `scripts/live_canary.py`: temp DB → log $40 → dream → log $52 → dream →
  assert old fact inactive with `superseded_by` = new fact id, new fact
  active, zero fallback fingerprints; exit non-zero with details on any
  miss; never touches the real memory DB. Stage
  `ci-staging/live-canary.yml`: `workflow_dispatch` trigger only, with the
  nightly `schedule` block present but commented out, and a fail-fast step
  if the `GEMINI_API_KEY` secret is absent. DO NOT install it — activation
  is John's ([GATED] G-CI). Loop must not block on the secret.
  *Done when:* `scripts/live_canary.py` run locally against live Gemini
  exits 0 with the supersession proven; workflow YAML parses.

- [x] **A5. Keyless E2E scripts + staged CI job.**
  (a) `scripts/ci_keyless_e2e.sh`: fresh venv, `pip install -e
  ".[claude,test]"`, CLI E2E without any key — log works, dream fails
  honestly (exit 1, turns preserved), decay works, doctor reports the
  missing key. (b) `scripts/test_dashboard_keyless.sh`: build if needed,
  start `dist/server.cjs` keyless on a random port, assert `/api/health`
  200 with `hasApiKey:false` and POST `/api/dream/consolidate` → 503, then
  clean shutdown. Stage the corresponding CI job additions in
  `ci-staging/ci-additions.yml` (includes wheel build + `twine check`).
  *Done when:* both scripts exit 0 locally (and correctly exit non-zero
  when their assertions are violated); staged YAML parses.

- [x] **A6. Soak instrumentation + criteria doc, then STOP.**
  `docs/SOAK_CRITERIA.md`: the 7-day pass/fail criteria (≥1 real dream/day
  with zero fallback and zero erasure hits; ≥1 organic contradiction
  correctly superseded; queue bounded; injection under budget and
  subjectively useful — John's judgment). Instrumentation: the A2 job
  already appends doctor verdicts to the log; add a daily doctor snapshot
  launchd job writing one JSON line per day to
  `~/.remagent/logs/soak.jsonl` (needs `remagent doctor --json`).
  Per John: set up and stop — NO week-long check-ins scheduled.
  *Done when:* criteria doc committed; snapshot job loaded and one line
  verified in soak.jsonl.

## Gated — John only (loop must skip)

- [ ] **[GATED] G-CI.** Paste `ci-staging/live-canary.yml` into
  `.github/workflows/` via the web UI, add the `GEMINI_API_KEY` repo
  secret, uncomment the nightly schedule; merge `ci-staging/
  ci-additions.yml` jobs into ci.yml the same way.
- [ ] **[GATED] G-SOAK.** Run the 7-day soak; John reviews
  `soak.jsonl` + criteria and calls pass/fail. Loop does not schedule
  check-ins.
- Standing gates unchanged: PyPI publish, Cloud Run deploy, repo
  visibility.
