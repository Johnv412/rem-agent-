"""
RemAgent Doctor: read-only self-audit of the memory pipeline.

Turns "is my memory working?" into a scriptable yes/no. Every check is
read-only (the DB is opened in read-only mode and is never created or
modified). Exit contract for the CLI wrapper: 0 only if ALL checks pass.
"""

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Union

FALLBACK_SUMMARY_PREFIX = "Fallback dream consolidation"
FALLBACK_FACT = ("session", "last_consolidated_turns_count")


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _key_check() -> CheckResult:
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return CheckResult("api_key", True, "GEMINI_API_KEY present in environment")
    return CheckResult(
        "api_key", False,
        "GEMINI_API_KEY is not set — dreams will fail (honestly, but they will fail)",
    )


def _parse_ts(ts: Union[str, float, int, None]) -> Optional[float]:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        return float(ts)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _dream_age_ok(last_dream_at, max_age_hours: float) -> Tuple[bool, str]:
    parsed = _parse_ts(last_dream_at)
    if parsed is None:
        return False, "no dream has ever completed"
    age_hours = (time.time() - parsed) / 3600.0
    if age_hours <= max_age_hours:
        return True, f"last dream {age_hours:.1f}h ago (limit {max_age_hours:.0f}h)"
    return False, f"last dream {age_hours:.1f}h ago exceeds limit {max_age_hours:.0f}h"


def run_doctor(
    db_path: str,
    agent_id: str = "default_agent",
    max_queue: int = 100,
    max_dream_age_hours: float = 24.0,
    require_key: bool = True,
) -> List[CheckResult]:
    results: List[CheckResult] = []
    db = os.path.expanduser(db_path)

    if require_key:
        results.append(_key_check())

    # 1. DB exists and is structurally sound (read-only open: never creates).
    if not os.path.exists(db):
        results.append(CheckResult("database", False, f"{db} does not exist"))
        return results
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        row = conn.execute("PRAGMA quick_check;").fetchone()
        quick = row[0] if row else "no result"
        results.append(CheckResult("database", quick == "ok", f"{db} quick_check={quick}"))
        if quick != "ok":
            conn.close()
            return results
    except Exception as exc:
        results.append(CheckResult("database", False, f"cannot open {db}: {exc}"))
        return results

    try:
        # 2. Queue health: capture without consumption means a broken pipeline.
        queue = conn.execute(
            "SELECT count(*) FROM raw_turns WHERE is_consolidated = 0"
        ).fetchone()[0]
        prow = conn.execute(
            "SELECT last_dream_at FROM memory_profiles WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        last_dream_at = prow[0] if prow else None

        if queue > max_queue:
            results.append(CheckResult(
                "queue", False, f"{queue} unconsolidated turns exceeds max {max_queue}"
            ))
        elif queue > 0:
            age_ok, age_detail = _dream_age_ok(last_dream_at, max_dream_age_hours)
            if age_ok:
                results.append(CheckResult("queue", True, f"{queue} queued; {age_detail}"))
            else:
                results.append(CheckResult(
                    "queue", False, f"{queue} queued but {age_detail} — dreams not keeping up"
                ))
        else:
            results.append(CheckResult("queue", True, "queue empty"))

        # 3. Fallback fingerprints: any hit means a fabricated dream reached disk.
        fb_audits = conn.execute(
            "SELECT count(*) FROM dream_audit_history WHERE reasoning_summary LIKE ?",
            (FALLBACK_SUMMARY_PREFIX + "%",),
        ).fetchone()[0]
        facts = []
        for (facts_json,) in conn.execute("SELECT facts_json FROM memory_profiles"):
            facts.extend(json.loads(facts_json))
        fb_facts = [
            f for f in facts
            if f.get("entity", "").lower() == FALLBACK_FACT[0]
            and f.get("attribute", "").lower() == FALLBACK_FACT[1]
        ]
        fb_clean = fb_audits == 0 and not fb_facts
        results.append(CheckResult(
            "no_fallback", fb_clean,
            "clean" if fb_clean
            else f"{fb_audits} fallback audit row(s), {len(fb_facts)} fabricated fact(s)",
        ))

        # 4. Erasure invariant at rest: a superseded fact must have an active
        # replacement. Decayed facts (superseded_by null) are legitimately
        # inactive without one.
        active = {
            (f["entity"].lower(), f["attribute"].lower())
            for f in facts if f.get("is_active")
        }
        violations = sorted({
            f"{f['entity']}.{f['attribute']}"
            for f in facts
            if not f.get("is_active")
            and f.get("superseded_by")
            and (f["entity"].lower(), f["attribute"].lower()) not in active
        })
        results.append(CheckResult(
            "no_erasure", not violations,
            "clean" if not violations
            else f"superseded without active replacement: {', '.join(violations)}",
        ))
    finally:
        conn.close()

    return results
