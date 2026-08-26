# 7-Day Soak — Pass/Fail Criteria

The soak is the real-usage gate before open-sourcing: John works normally
for 7 days while the automated pipeline (hooks → scheduled dreams →
weekly decay) runs untouched. Evidence accumulates in
`~/.remagent/logs/` — nothing is graded on vibes.

**Instrumentation (all already running):**
- `~/.remagent/logs/dream.log` — every 30-min dream + doctor verdict.
- `~/.remagent/logs/decay.log` — Sunday decay passes.
- `~/.remagent/logs/soak.jsonl` — one `remagent doctor --json` line per
  day at 21:00 (launchd job `com.remagent.soak`). Seven lines = seven
  days of evidence.

**PASS requires all of the following over the 7 days:**

1. **Dreams are real and clean.** Every soak.jsonl line has `"ok": true`
   — in particular `no_fallback` and `no_erasure` never fail. A single
   fallback fingerprint or erasure-invariant hit is an automatic FAIL
   (that class of bug is why this project has a test campaign).
2. **The pipeline consumes what it captures.** The `queue` check never
   fails: no backlog growth, no stale-dream condition. Days with zero
   activity (queue empty, no new dreams) are fine — silence is not
   failure.
3. **At least one organic contradiction superseded correctly.** During
   normal work John will change his mind about something; the graph must
   show the old fact `is_active=false` with `superseded_by` pointing at
   the active replacement. Verify with a raw facts dump at review time.
4. **Injection stays useful.** `remagent recall --format injection
   --agent john --db ~/.remagent/memory.db` at day 7: under the token
   budget, no junk facts, and — John's judgment call, the one criterion
   no script can grade — the content would genuinely help a fresh
   session.

**Soak window:** day 1 = 2026-08-25, day 7 = 2026-08-31 (final snapshot
21:00 that evening). Baseline: the pre-soak DB state (4 facts, 1 audit,
1 turn) is archived at `~/.remagent/baselines/memory.baseline-2026-08-25.db`
and recorded in `~/.remagent/soak_config.json`; dreaming writes live —
that IS the system being soaked — and everything after the baseline is
observed and diffable.

**Review procedure (John, any day — one command):**
```bash
remagent soak
```
It prints, in plain English: IN PROGRESS (with health so far), or
SOAK PASSED / SOAK FAILED with every reason named, plus the recall
injection for the one criterion only you can grade. Exit 0 = pass or
healthy-in-progress, 1 = failed. The raw evidence remains in
`~/.remagent/logs/` if you want to dig.

**On PASS:** proceed to the open-source flip (fresh secrets scan → tag
v1.0.0 → PyPI → README flip → public → deploy). **On FAIL:** the failing
check names the bug; fix it, reset the soak clock.
