"""Mechanism benchmarks that need no agent model (slide 18 metrics the agent runs do not measure).

clean-up    Random provenance graphs: memories built from clean sources, poisoned sources and other memories, some
            with a second, independent justification. All poisoned sources are flagged; the JTMS result is compared
            with an independent recomputation of which memories still have a poison-free justification.
                clean-up recall      = poison-derived memories quarantined / poison-derived memories
                false quarantine     = clean memories quarantined / clean memories
conflicts   Planted fact pairs scored by the production contradiction check (ContradictionCheck.is_conflict):
            real conflicts (same subject and attribute, different value) are positives; restatements, a different
            attribute of the same subject, and the same attribute of a different subject are negatives.
                precision, recall, F1, and the false-conflict rate per negative kind

    python -m eval.mechanisms --out docs/results/mechanisms.md                      # lexical NLI (offline)
    MEMLEDGER_GUARD_BACKEND=hf python -m eval.mechanisms --out docs/results/mechanisms.md   # production NLI
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from memledger.core.types import Session, SourceKind, Status, WriteProposal

USER = Session("bench", "team_a", "researcher", 1)


# ------------------------------------------------------------------------------------------------ clean-up
def _graph(rng: random.Random, n_clean: int, n_poison: int, n_mem: int) -> dict:
    """Sources and memories with justifications (lists of parents); parents point only to earlier nodes."""
    sources = {f"c{i}": False for i in range(n_clean)} | {f"p{i}": True for i in range(n_poison)}  # id -> poisoned
    mems: dict[str, list[list[str]]] = {}
    for i in range(n_mem):
        pool = list(sources) + list(mems)
        justs = [rng.sample(pool, rng.randint(1, min(3, len(pool))))]
        if rng.random() < 0.3:  # a second, independent justification (e.g. new evidence)
            justs.append(rng.sample(pool, rng.randint(1, min(2, len(pool)))))
        mems[f"m{i}"] = justs
    return {"sources": sources, "mems": mems}


def _oracle(g: dict) -> dict[str, bool]:
    """Independent ground truth: a memory is clean iff some justification has only clean sources and clean memories
    as parents (least fixed point; justifications only point to earlier nodes, so one ordered pass suffices)."""
    clean: dict[str, bool] = {s: not bad for s, bad in g["sources"].items()}
    for m, justs in g["mems"].items():
        clean[m] = any(all(clean[p] for p in j) for j in justs)
    return {m: clean[m] for m in g["mems"]}


def cleanup(n_graphs: int = 300, seed: int = 0, n_clean: int = 4, n_poison: int = 2, n_mem: int = 12) -> dict:
    from eval.versions import build

    rng = random.Random(seed)
    tp = fn = fp = tn = 0
    for gi in range(n_graphs):
        g = _graph(rng, n_clean, n_poison, n_mem)
        svc = build("provenance", {}).service  # JTMS + provenance, no write checks: only retraction is measured
        ids = {}
        for s, bad in g["sources"].items():
            kind = SourceKind.WEB if bad else rng.choice([SourceKind.PAPER, SourceKind.TOOL, SourceKind.INTERNAL])
            ids[s] = svc.ingest(f"graph {gi} source {s}: fact {rng.random():.6f}", kind, USER).id
        for m, justs in g["mems"].items():
            res = svc.propose_write(WriteProposal(f"graph {gi} memory {m}", [ids[p] for p in justs[0]], USER, "agent"))
            ids[m] = res.claim_ids[0]
            for j in justs[1:]:
                svc.add_justification(ids[m], [ids[p] for p in j])
        for s, bad in g["sources"].items():
            if bad:
                svc.flag_source(ids[s], "poisoned (benchmark)")
        truth = _oracle(g)
        for m, is_clean in truth.items():
            quarantined = svc.store.get_claim(ids[m]).status == Status.QUARANTINED
            if is_clean:
                fp, tn = fp + quarantined, tn + (not quarantined)
            else:
                tp, fn = tp + quarantined, fn + (not quarantined)
    return {"graphs": n_graphs, "memories": tp + fn + fp + tn, "poison_derived": tp + fn, "clean": fp + tn,
            "recall": (tp, tp + fn), "false_quarantine": (fp, fp + tn)}


# ------------------------------------------------------------------------------------------------ conflicts
ENTITIES = ["Acme Ltd", "Borealis Labs", "Cobalt Systems", "Dunmore Bank", "Everly Health", "Fjord Logistics",
            "Granite Capital", "Halcyon Robotics", "Ironwood Energy", "Juniper Media", "Kestrel AI", "Lumen Foods",
            "Meridian Telecom", "Northwind Retail", "Orion Cloud", "Pinecrest Insurance", "Quarry Mining",
            "Redwood Pharma", "Saltmarsh Analytics", "Tidewater Shipping"]
ATTRS = [  # (template, values)
    ("{e}'s bank account number is {v}.", ["1234", "9876", "4417", "5520", "7731"]),
    ("{e} is headquartered in {v}.", ["Bengaluru", "Pune", "Chennai", "Mumbai", "Hyderabad"]),
    ("The CEO of {e} is {v}.", ["Ravi Menon", "Anita Shah", "Karan Iyer", "Meera Rao", "Vikram Das"]),
    ("{e} was founded in {v}.", ["1998", "2004", "2011", "2016", "2020"]),
    ("{e}'s support email is {v}.", ["help@acme.example", "support@corp.example", "care@mail.example",
                                     "desk@service.example", "info@team.example"]),
]
RESTATE = {"{e}'s bank account number is {v}.": "The bank account number of {e} is {v}.",
           "{e} is headquartered in {v}.": "The headquarters of {e} are in {v}.",
           "The CEO of {e} is {v}.": "{e}'s chief executive is {v}.",
           "{e} was founded in {v}.": "{e} has existed since it was founded in {v}.",
           "{e}'s support email is {v}.": "You can reach {e}'s support at {v}."}


# Free-text facts about the same subject that do not contradict each other (the kind the NLI models over-flag:
# found with the console tour, see docs/results/final_numbers_v1.md weak spot 4)
FREE_TEXT = [
    ("Kestrel reaches 91% recall on Saltmarsh", "Kestrel runs on the Orion cluster"),
    ("Kestrel reaches 91% recall on Saltmarsh", "Kestrel needs no safety review"),
    ("Acme Ltd ships lab consumables within 5 working days", "Acme Ltd has an office in Pune"),
    ("Borealis Labs released its first model in 2021", "Borealis Labs uses Python for its data pipeline"),
    ("The Orion cluster has 64 nodes", "The Orion cluster is maintained by the platform team"),
    ("Project Falcon reached 93.1 F1 on Halcyon", "Project Falcon is led by team A"),
    ("Dunmore Bank's quarterly report is due in March", "Dunmore Bank sponsors a cricket team"),
    ("Everly Health's app has 2 million users", "Everly Health was audited last year"),
    ("Cobalt Systems' API has a rate limit of 100 requests per minute", "Cobalt Systems hires interns every summer"),
    ("Juniper Media's newsletter goes out on Fridays", "Juniper Media moved to a new office"),
]


def conflict_pairs(n: int = 400, seed: int = 0) -> list[tuple[str, str, str]]:
    """(a, b, kind); kind in conflict | restatement | other_attribute | other_subject."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        e, (tpl, vals) = rng.choice(ENTITIES), rng.choice(ATTRS)
        v1, v2 = rng.sample(vals, 2)
        a = tpl.format(e=e, v=v1)
        kind = ["conflict", "restatement", "other_attribute", "other_subject"][i % 4]
        if kind == "conflict":
            b = tpl.format(e=e, v=v2)
        elif kind == "restatement":
            b = RESTATE[tpl].format(e=e, v=v1)
        elif kind == "other_attribute":
            tpl2, vals2 = rng.choice([x for x in ATTRS if x[0] != tpl])
            b = tpl2.format(e=e, v=rng.choice(vals2))
        else:
            b = tpl.format(e=rng.choice([x for x in ENTITIES if x != e]), v=v2)
        out.append((a, b, kind))
    return out + [(a, b, "free_text_unrelated") for a, b in FREE_TEXT]


def conflicts(n: int = 400, seed: int = 0, nli=None) -> dict:
    from memledger.guards.contradiction import ContradictionCheck

    check = ContradictionCheck(nli=nli) if nli is not None else ContradictionCheck()
    by: dict[str, list[int]] = {}
    tp = fp = fn = 0
    for a, b, kind in conflict_pairs(n, seed):
        flagged = check.is_conflict(a, b)[0]
        by.setdefault(kind, [0, 0])
        by[kind][0] += flagged
        by[kind][1] += 1
        if kind == "conflict":
            tp, fn = tp + flagged, fn + (not flagged)
        else:
            fp += flagged
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"pairs": n, "precision": (tp, tp + fp), "recall": (tp, tp + fn), "f1": 2 * p * r / (p + r) if p + r else 0.0,
            "flagged_by_kind": {k: tuple(v) for k, v in by.items()}, "nli": type(check.nli).__name__ if not callable(
                getattr(check.nli, "model_id", None)) else check.nli.model_id}


# ------------------------------------------------------------------------------------------------ report
def _rate(x: int, n: int) -> str:
    from eval.metrics import Rate

    return Rate.of(x, n).text()


def markdown(c: dict, k: dict, backend: str) -> str:
    kinds = k["flagged_by_kind"]
    return "\n".join([
        "# Mechanism benchmarks (no agent model)", "",
        "Generated by `python -m eval.mechanisms`. 95% Wilson intervals.", "",
        "## Clean-up after a poisoned source is flagged (JTMS retraction)", "",
        (f"{c['graphs']} random provenance graphs: {c['memories']} memories ({c['poison_derived']} poison-derived, "
        f"{c['clean']} with a poison-free justification). Ground truth is an independent recomputation."), "",
        "| metric | value |", "|---|---|",
        f"| clean-up recall (poison-derived memories quarantined) | {_rate(*c['recall'])} |",
        f"| false quarantine rate (clean memories quarantined) | {_rate(*c['false_quarantine'])} |", "",
        "## Contradiction detection on planted conflicts", "",
        (f"{k['pairs']} templated fact pairs over 20 companies and 5 attributes, plus {len(FREE_TEXT)} free-text pairs; checker backend `{backend}`. Positive = a real "
        "conflict (same company and attribute, different value)."), "",
        "| metric | value |", "|---|---|",
        f"| precision | {_rate(*k['precision'])} |", f"| recall | {_rate(*k['recall'])} |",
        f"| F1 | {k['f1']:.3f} |",
        f"| flagged: restatement of the same fact (should be 0) | {_rate(*kinds.get('restatement', (0, 0)))} |",
        f"| flagged: other attribute, same company (should be 0) | {_rate(*kinds.get('other_attribute', (0, 0)))} |",
        f"| flagged: same attribute, other company (should be 0) | {_rate(*kinds.get('other_subject', (0, 0)))} |",
        (f"| flagged: unrelated free-text facts, same subject (should be 0) | "
        f"{_rate(*kinds.get('free_text_unrelated', (0, 0)))} |"),
        ""])


def main(argv: list[str] | None = None) -> dict:
    import os

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--graphs", type=int, default=300)
    ap.add_argument("--pairs", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="docs/results/mechanisms.md")
    a = ap.parse_args(argv)
    backend = os.environ.get("MEMLEDGER_GUARD_BACKEND", "lexical")
    c, k = cleanup(a.graphs, a.seed), conflicts(a.pairs, a.seed)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(markdown(c, k, backend))
    Path(a.out).with_suffix(".json").write_text(json.dumps({"cleanup": c, "conflicts": k, "backend": backend}, indent=1))
    print(Path(a.out).read_text())
    return {"cleanup": c, "conflicts": k}


if __name__ == "__main__":
    main()
