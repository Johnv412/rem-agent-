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

**Review procedure (John, day 7):**
```bash
cat ~/.remagent/logs/soak.jsonl            # 7 lines, all "ok": true
grep -c "FAILED\|❌" ~/.remagent/logs/dream.log   # investigate any hit
remagent recall --format injection --agent john --db ~/.remagent/memory.db
sqlite3 ~/.remagent/memory.db "SELECT facts_json FROM memory_profiles WHERE agent_id='john';" | python3 -m json.tool
```

**On PASS:** proceed to the open-source flip (fresh secrets scan → tag
v1.0.0 → PyPI → README flip → public → deploy). **On FAIL:** the failing
check names the bug; fix it, reset the soak clock.
