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


def find_erasure_orphans(facts: List[dict]) -> List[str]:
    """
    A superseded fact is healthy if following its superseded_by chain reaches
    an ACTIVE fact (entity renames re-home the chain legitimately), or — as a
    legacy fallback for run-id-valued superseded_by — if an active fact still
    exists for the same entity/attribute pair. Anything else is erased memory.
    """
    by_id = {f.get("id"): f for f in facts}
    active_pairs = {
        (f["entity"].lower(), f["attribute"].lower()) for f in facts if f.get("is_active")
    }
    orphans = []
    for f in facts:
        if f.get("is_active") or not f.get("superseded_by"):
            continue
        ok, seen, cur = False, set(), f
        while cur is not None and cur.get("superseded_by") and cur["superseded_by"] not in seen:
            seen.add(cur["superseded_by"])
            nxt = by_id.get(cur["superseded_by"])
            if nxt is None:
                break
            if nxt.get("is_active"):
                ok = True
                break
            cur = nxt
        if not ok and (f["entity"].lower(), f["attribute"].lower()) in active_pairs:
            ok = True
        if not ok:
            orphans.append(f"{f['entity']}.{f['attribute']}")
    return sorted(set(orphans))


def _provider_checks() -> List[CheckResult]:
    """Active provider, which keys are present (names only), and whether the
    provider's SDK extra is importable. Never prints a secret."""
    from remagent.engine.errors import ProviderConfigError
    from remagent.engine.providers import (
        ALL_KEY_NAMES, EXTRA_NAME, SDK_MODULE, present_keys, resolve_provider, sdk_importable,
    )
    results: List[CheckResult] = []
    keys = present_keys()
    if keys:
        results.append(CheckResult("api_key", True, f"present: {', '.join(keys)}"))
    else:
        results.append(CheckResult(
            "api_key", False,
            "no provider key set — set one of " + ", ".join(ALL_KEY_NAMES)
            + " (dreams will fail honestly, but they will fail)",
        ))
    try:
        cfg = resolve_provider()
    except ProviderConfigError as exc:
        results.append(CheckResult("provider", False, f"no active provider: {exc}"))
        return results
    detail = f"{cfg.provider} via {cfg.key_env}, model {cfg.model}"
    if cfg.base_url:
        detail += f", base_url {cfg.base_url}"
    results.append(CheckResult("provider", True, detail))
    module = SDK_MODULE[cfg.backend]
    if sdk_importable(cfg.backend):
        results.append(CheckResult("provider_sdk", True, f"{module} importable"))
    else:
        results.append(CheckResult(
            "provider_sdk", False,
            f'{module} not installed — pip install "remagent[{EXTRA_NAME[cfg.backend]}]"',
        ))
    return results


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
        results.extend(_provider_checks())

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

        # 4. Erasure invariant at rest: a superseded fact must lead (via its
        # supersession chain) to an active fact. Decayed facts (superseded_by
        # null) are legitimately inactive without one.
        violations = find_erasure_orphans(facts)
        results.append(CheckResult(
            "no_erasure", not violations,
            "clean" if not violations
            else f"superseded without active replacement: {', '.join(violations)}",
        ))
    finally:
        conn.close()

    return results
