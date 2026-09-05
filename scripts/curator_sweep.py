#!/usr/bin/env python3
"""
Curator sweep: deterministic one-time merge of split entities and duplicate
rules in a RemAgent memory database. NO LLM involved — a bulk rewrite is
exactly where model judgment must not touch the data.

Modes:
  --dry-run (default): detect candidates, print the full proposed merge
      list, and write it to a plan JSON for human curation. Writes NOTHING
      to the database.
  --apply --plan FILE: execute exactly the (possibly hand-edited) plan.
      Supersede-only: every displaced fact gets is_active=false +
      superseded_by pointing at its successor; duplicate rules are
      deactivated with a merge note on the survivor. Nothing is deleted.
      The sweep is recorded as a dream_audit_history row.

Exit non-zero on any invariant violation; the DB is only written once,
at the end, after all checks pass in memory.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from itertools import combinations
from uuid import uuid4

SEED_ENTITY_PAIRS = [
    ("Commander Project", "Commander"),
    ("Vincent", "Vincent Agent"),
    ("Edip.ai SOC 2 audit scanner", "Edip.ai SOC 2 scanner"),
    ("Edip.ai SOC 2 audit scanner", "SOC2_Scanner"),
]
JACCARD_THRESHOLD = 0.6
RULE_JACCARD_THRESHOLD = 0.6


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def tokens(text: str) -> frozenset:
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load(db_path: str, agent: str):
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT facts_json, rules_json FROM memory_profiles WHERE agent_id = ?", (agent,)
    ).fetchone()
    if row is None:
        print(f"FAILED: no profile for agent '{agent}' in {db_path}", file=sys.stderr)
        sys.exit(1)
    return conn, json.loads(row[0]), json.loads(row[1])


def detect_entity_candidates(facts):
    active_by_entity = {}
    for f in facts:
        if f.get("is_active"):
            active_by_entity.setdefault(f["entity"], []).append(f)
    entities = sorted(active_by_entity)

    def canonical_of(a, b):
        # More facts wins; tie -> longer (more specific) name.
        ca, cb = len(active_by_entity[a]), len(active_by_entity[b])
        if ca != cb:
            return (a, b) if ca > cb else (b, a)
        return (a, b) if len(a) >= len(b) else (b, a)

    candidates, seen = [], set()

    def add(canon, alias, source):
        key = frozenset((canon, alias))
        if key in seen or canon == alias:
            return
        seen.add(key)
        candidates.append({
            "canonical": canon,
            "alias": alias,
            "facts_to_move": len(active_by_entity.get(alias, [])),
            "canonical_fact_count": len(active_by_entity.get(canon, [])),
            "source": source,
        })

    existing = set(entities)
    for a, b in SEED_ENTITY_PAIRS:
        if a in existing and b in existing:
            canon, alias = canonical_of(a, b)
            add(canon, alias, "seed")

    for a, b in combinations(entities, 2):
        ta, tb = tokens(a), tokens(b)
        if not ta or not tb:
            continue
        subset = ta < tb or tb < ta
        if subset or jaccard(ta, tb) >= JACCARD_THRESHOLD:
            canon, alias = canonical_of(a, b)
            add(canon, alias, "heuristic — review carefully")
    return candidates, active_by_entity


def detect_rule_candidates(rules):
    active = [r for r in rules if r.get("is_active")]
    candidates = []
    for a, b in combinations(active, 2):
        ta, tb = tokens(a["rule"]), tokens(b["rule"])
        sim = jaccard(ta, tb)
        same_head = a["rule"].split()[:8] == b["rule"].split()[:8]
        if sim >= RULE_JACCARD_THRESHOLD or same_head:
            # Survivor: higher priority (lower number); tie -> longer text.
            if (a["priority"], -len(a["rule"])) <= (b["priority"], -len(b["rule"])):
                keep, drop = a, b
            else:
                keep, drop = b, a
            candidates.append({
                "keep_id": keep["id"], "keep_priority": keep["priority"],
                "keep_text": keep["rule"],
                "drop_id": drop["id"], "drop_priority": drop["priority"],
                "drop_text": drop["rule"],
                "similarity": round(sim, 2),
            })
    return candidates


def apply_plan(conn, agent, facts, rules, plan):
    stamp = now_iso()
    new_facts, resolutions = [], []
    facts_by_id = {f["id"]: f for f in facts}

    for merge in plan.get("entity_merges", []):
        canon, alias = merge["canonical"], merge["alias"]
        canon_active = {f["attribute"].lower(): f for f in facts
                        if f.get("is_active") and f["entity"] == canon}
        for f in [x for x in facts if x.get("is_active") and x["entity"] == alias]:
            attr = f["attribute"].lower()
            existing = canon_active.get(attr)
            if existing is not None:
                # Same attribute on both: newer timestamp survives.
                def ts(x):
                    return str(x.get("timestamp", ""))
                winner, loser = (f, existing) if ts(f) > ts(existing) else (existing, f)
                if winner is f:
                    moved = dict(f, id=str(uuid4()), entity=canon, timestamp=stamp)
                    new_facts.append(moved)
                    existing["is_active"] = False
                    existing["superseded_by"] = moved["id"]
                    f["is_active"] = False
                    f["superseded_by"] = moved["id"]
                    canon_active[attr] = moved
                    successor = moved
                else:
                    f["is_active"] = False
                    f["superseded_by"] = existing["id"]
                    successor = existing
                resolutions.append({
                    "prior_fact_id": loser["id"], "entity": canon, "attribute": f["attribute"],
                    "prior_value": loser["value"], "new_value": successor["value"],
                    "resolution_reasoning": f"curator entity merge: '{alias}' unified into '{canon}'",
                })
            else:
                moved = dict(f, id=str(uuid4()), entity=canon, timestamp=stamp)
                new_facts.append(moved)
                f["is_active"] = False
                f["superseded_by"] = moved["id"]
                canon_active[attr] = moved

    rules_by_id = {r["id"]: r for r in rules}
    for merge in plan.get("rule_merges", []):
        keep = rules_by_id.get(merge["keep_id"])
        drop = rules_by_id.get(merge["drop_id"])
        if keep is None or drop is None or not drop.get("is_active"):
            continue
        drop["is_active"] = False
        drop["updated_at"] = stamp
        keep["rationale"] = (keep.get("rationale") or "") + \
            f" [curator 2026-09-05: merged duplicate rule {drop['id'][:8]}]"
        keep["updated_at"] = stamp

    facts.extend(new_facts)

    # Invariant: every superseded fact has an active same-entity/attr successor.
    active_pairs = {(f["entity"].lower(), f["attribute"].lower())
                    for f in facts if f.get("is_active")}
    orphans = [f"{f['entity']}.{f['attribute']}" for f in facts
               if not f.get("is_active") and f.get("superseded_by")
               and (f["entity"].lower(), f["attribute"].lower()) not in active_pairs]
    # Facts merged AWAY from an alias legitimately have their successor under
    # the canonical entity — check by successor id instead for those.
    real_orphans = []
    for f in facts:
        if f.get("is_active") or not f.get("superseded_by"):
            continue
        succ = facts_by_id.get(f["superseded_by"]) or next(
            (n for n in new_facts if n["id"] == f["superseded_by"]), None)
        if succ is None or not succ.get("is_active"):
            real_orphans.append(f"{f['entity']}.{f['attribute']}")
    if real_orphans:
        print(f"FAILED invariant: superseded facts without active successor: {real_orphans}",
              file=sys.stderr)
        sys.exit(1)

    conn.execute(
        "UPDATE memory_profiles SET facts_json = ?, rules_json = ? WHERE agent_id = ?",
        (json.dumps(facts), json.dumps(rules), agent),
    )
    conn.execute(
        "INSERT INTO dream_audit_history (run_id, agent_id, added_facts_json, "
        "updated_rules_json, contradiction_resolutions_json, pruned_noise_count, "
        "pruned_noise_reasons_json, reasoning_summary, consolidated_turn_ids_json, "
        "timestamp, estimated_token_savings) VALUES (?, ?, ?, '[]', ?, 0, '[]', ?, '[]', ?, 0)",
        (f"curator-sweep-{stamp[:10]}", agent, json.dumps(new_facts), json.dumps(resolutions),
         f"Curator sweep (deterministic, no LLM): unified {len(plan.get('entity_merges', []))} "
         f"entity aliases and deactivated {len(plan.get('rule_merges', []))} duplicate rules. "
         f"Supersede-only; zero deletions.", stamp),
    )
    conn.commit()
    return len(new_facts), len(resolutions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("REMAGENT_DB", "remagent_memory.db"))
    ap.add_argument("--agent", default=os.environ.get("REMAGENT_AGENT", "default_agent"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--plan", help="plan JSON (required with --apply)")
    ap.add_argument("--plan-out", default=os.path.expanduser("~/.remagent/curator_plan.json"))
    args = ap.parse_args()

    db = os.path.expanduser(args.db)
    conn, facts, rules = load(db, args.agent)

    if args.apply:
        if not args.plan:
            print("FAILED: --apply requires --plan FILE", file=sys.stderr)
            sys.exit(2)
        plan = json.load(open(os.path.expanduser(args.plan)))
        before_active = sum(1 for f in facts if f.get("is_active"))
        before_rules = sum(1 for r in rules if r.get("is_active"))
        added, resolved = apply_plan(conn, args.agent, facts, rules, plan)
        after_active = sum(1 for f in facts if f.get("is_active"))
        after_rules = sum(1 for r in rules if r.get("is_active"))
        print(f"✅ Sweep applied: {added} facts re-homed, {resolved} same-attribute conflicts resolved.")
        print(f"   Active facts {before_active} -> {after_active} | active rules {before_rules} -> {after_rules}")
        print(f"   Total records {len(facts)} (supersede-only, zero deletions).")
        conn.close()
        return

    entity_c, _ = detect_entity_candidates(facts)
    rule_c = detect_rule_candidates(rules)
    plan = {"entity_merges": [{k: c[k] for k in ("canonical", "alias")} for c in entity_c],
            "rule_merges": [{k: c[k] for k in ("keep_id", "drop_id")} for c in rule_c]}
    os.makedirs(os.path.dirname(args.plan_out), exist_ok=True)
    json.dump(plan, open(args.plan_out, "w"), indent=2)

    print(f"=== DRY RUN (nothing written) — plan saved to {args.plan_out} ===\n")
    print(f"--- ENTITY MERGE CANDIDATES ({len(entity_c)}) ---")
    for c in entity_c:
        print(f"  [{c['source']}] '{c['alias']}' ({c['facts_to_move']} facts) "
              f"-> '{c['canonical']}' ({c['canonical_fact_count']} facts)")
    print(f"\n--- RULE DEDUP CANDIDATES ({len(rule_c)}) ---")
    for c in rule_c:
        print(f"  KEEP  [P{c['keep_priority']}] {c['keep_text'][:100]}")
        print(f"  DROP  [P{c['drop_priority']}] {c['drop_text'][:100]}")
        print(f"        (similarity {c['similarity']})\n")
    conn.close()


if __name__ == "__main__":
    main()
