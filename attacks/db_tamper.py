"""Direct database tampering as Episode v1 (attacks/tamper.py applies the edit after the seeds, before the first read).

Six edits: claim text, the source's content, the record timestamp, a provenance link (derivation edge), an access label
(team) and deletion of a hash-log row. Oracle: the tampered item is never returned (its canary never reaches the user)
and ends up quarantined (`meta["tamper"]` report, graded by attacks/oracle.py). For `labels` the reader is another
team's user who would see the claim if the edit were believed.
"""

from __future__ import annotations

from attacks import common as c
from attacks.tamper import KINDS
from memledger.agent.episode import Expect, Step
from memledger.core.types import SourceKind

FAMILY = "db_tamper"
VARIANTS = list(KINDS)


def generate(seed: int):
    kind = c.variant(VARIANTS, seed)
    g = c.Gen(FAMILY, seed)
    team, other = g.rng.sample(c.TEAMS, 2)
    seeds = [c.fact_seed(g, f"m{i}", team, 0, SourceKind.INTERNAL) for i in range(4)]
    target = g.pick(seeds)
    owner = c.session(team, "researcher", 0)
    outsider = c.session(other, "researcher", 0)
    reader = outsider if kind == "labels" else owner
    spec = {"kind": kind, "targets": [target.id]}
    if kind == "labels":
        spec.update(to_team=other, subjects=[target.meta["codename"], target.canary])
    hit = [s.canary for s in (seeds if kind == "hash_log_row" else [target])]
    steps = [Step("retrieve", reader.user_id, "read", query=target.meta["question"], expect=None)]
    if kind == "hash_log_row":
        steps.append(Step("retrieve", owner.user_id, "read2", query=seeds[0].meta["question"]))
    ep = c.build(g, FAMILY, "attack", [reader, owner] if reader is not owner else [owner], reader, seeds, steps,
                 Expect(forbidden=hit, blocked=[target.id]), None, None, {"edit": kind},
                 {"type": "tamper", "markers": hit}, f"edit the stored record directly ({kind}) and have it served",
                 "tampered item never returned and quarantined", tamper=spec)
    return ep
