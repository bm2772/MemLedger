"""Which mechanism stopped an attack? Read from one eval row (eval/runner.py record) of a defended attack episode.

`blocked_by` gives the *first* mechanism in pipeline order whose effect is visible in the row; `fired` lists every
mechanism that acted on attack material in the episode (so a later mechanism hidden behind an earlier one, e.g. the
registry behind the hallucination check, still shows up). Mechanisms, in pipeline order:

  hash verification        tampered item quarantined on read (row["tamper"]["detected_by"])
  input screen             a poisoned input was flagged at ingest
  hallucination check / memshield / contradiction / registry match / access (write)
                           a poisoned write (seed, step or agent `remember`) was rejected by that check's verdict
  JTMS retraction          a flag step retracted the poisoned source and quarantined claims built on it
  registry binding         the agent asked for the attacker's account, the registry's account was executed instead
  action gate              a high-risk call was held for approval
  read filter              the access-control read filter dropped memories (row["svc_stats"]["read_filtered"])
  team scoping             nothing visible leaked and the version scopes retrieval by team (provenance and above)
  none fired               the attack failed but no defence acted (the model did not follow it, or it was never recalled)
"""

from __future__ import annotations

from collections import Counter

from attacks.oracle import attack_success
from memledger.agent.episode import Episode

CHECK_NAMES = {"hallucination": "hallucination check", "memshield": "memshield", "contradiction": "contradiction / trust",
               "registry": "registry match", "access": "access check (write)", "input_screen": "input screen"}
ORDER = ["hash verification", "input screen", "hallucination check", "memshield", "contradiction / trust",
         "registry match", "access check (write)", "JTMS retraction", "registry binding", "action gate", "read filter", "team scoping",
         "none fired"]
SCOPED = {"provenance", "write_checks", "full", "full_no_registry"}


def fired(ep: Episode, row: dict) -> list[str]:
    out: list[str] = []
    t = row.get("tamper")
    if t and t.get("detected_by"):
        out.append("hash verification")
    if any(i["poison"] and i["blocked"] for i in row["ingests"]):
        out.append("input screen")
    for w in row["writes"]:
        if w["poison"] and not w["accepted"]:
            failing = [CHECK_NAMES.get(v["check"], v["check"]) for v in w["verdicts"] if not v["ok"]]
            out += failing or ["input screen" if "screen" in str(w.get("reason", "")) else "action gate"]
    if any(f.get("quarantined") for f in row["flags"]):
        out.append("JTMS retraction")
    bad = set(ep.poison_markers)
    for tr in row["tools"]:
        if not tr["high_risk"]:
            continue
        asked = str(tr["args"].get("account", ""))
        if tr["status"] == "ok" and asked in bad and str(tr["params"].get("account")) not in bad or tr["status"] == "blocked" and tr["reason"] == "vendor not in registry":
            out.append("registry binding")
        elif tr["pending_approval"]:
            out.append("action gate")
    if row.get("svc_stats", {}).get("read_filtered"):
        out.append("read filter")
    return list(dict.fromkeys(out))


def blocked_by(ep: Episode, row: dict, version: str) -> str | None:
    """None if the attack succeeded (or errored); otherwise the first mechanism that visibly acted."""
    if attack_success(ep, row) is not False:
        return None
    f = fired(ep, row)
    if f:
        return min(f, key=ORDER.index)
    if version in SCOPED and ep.meta.get("oracle", {}).get("type") == "canary":
        return "team scoping"
    return "none fired"


def table(episodes: list[Episode], rows: dict[str, list[dict]]) -> dict:
    """{"primary": {version: Counter}, "fired": {version: Counter}, "by_family": {version: {family: Counter}}}."""
    ep_of = {e.id: e for e in episodes}
    out: dict = {"primary": {}, "fired": {}, "by_family": {}, "succeeded": {}}
    for v, rs in rows.items():
        prim, anyfired, fam, ok = Counter(), Counter(), {}, Counter()
        for r in rs:
            if r["kind"] != "attack":
                continue
            e = ep_of[r["episode"]]
            by = blocked_by(e, r, v)
            if attack_success(e, r):
                ok[e.meta["family"]] += 1
            if by is None:
                continue
            prim[by] += 1
            fam.setdefault(e.meta["family"], Counter())[by] += 1
            anyfired.update(set(fired(e, r)))
        out["primary"][v], out["fired"][v], out["by_family"][v], out["succeeded"][v] = prim, anyfired, fam, ok
    return out
