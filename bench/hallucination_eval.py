"""Slide 13: the hallucination check on its own, on RAGTruth and HaluEval QA (no agent, no LLM).

Each benchmark item (bench/loaders.py) is a proposed memory and the documents it should rest on. The production
HallucinationCheck (memledger/guards/hallucination.py: MiniCheck-RoBERTa-Large, threshold 0.5, split into facts,
overlapping chunks, verbatim shortcut) decides; "hallucinated" is the positive class:

    precision     hallucinated among the rejected          recall     rejected among the hallucinated
    F1            of the two                               false rejection   rejected among the supported

with 95% Wilson intervals (eval/metrics.py Rate). Official test splits: RAGTruth `test`; HaluEval has none, so the
loader's stable 70% hash split (`test`). Nothing is tuned on test: the threshold is the production one, and the
HaluEval item format was chosen on HaluEval dev (docs/results/hallucination_benchmarks.md says how).

    python -m bench.hallucination_eval --split test                    # MEMLEDGER_DEVICE=cuda|mps for speed
    python -m bench.hallucination_eval --split test --limit 500        # seeded sample per dataset

Per-item rows go to results/hallucination/raw/<split>.jsonl (gitignored) as they are judged; running the same
command again skips the items already there. The table goes to --out.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from pathlib import Path

from bench import load
from memledger.agent.episode import Episode
from memledger.core.types import Labels, Session, Source, WriteProposal

DATASETS = ("ragtruth", "halueval")
USER = Session("bench_user", "bench", "researcher", 0)


def sources_of(ep: Episode) -> list[Source]:
    return [Source(s.id, s.kind, s.content, Labels(s.team), 0.9) for s in ep.seeds]


def judge(check, ep: Episode) -> dict:
    """One item: the check's verdict on the proposed memory against its documents."""
    srcs = sources_of(ep)
    t0 = time.perf_counter()
    v = check.check(WriteProposal(ep.steps[0].text, [s.id for s in srcs], USER), srcs)
    return {"id": ep.id, "dataset": ep.source, "group": ep.category, "label": ep.expect.label,
            "rejected": not v.ok, "score": v.score, "ms": round((time.perf_counter() - t0) * 1000, 1),
            "reason": v.reason[:300]}


def scores(rows: list[dict]) -> dict:
    from eval.metrics import Rate

    tp = sum(r["rejected"] and r["label"] == "hallucinated" for r in rows)
    fp = sum(r["rejected"] and r["label"] != "hallucinated" for r in rows)
    fn = sum(not r["rejected"] and r["label"] == "hallucinated" for r in rows)
    tn = len(rows) - tp - fp - fn
    p, rec = Rate.of(tp, tp + fp), Rate.of(tp, tp + fn)
    f1 = 2 * p.p * rec.p / (p.p + rec.p) if p.p and rec.p else 0.0
    return {"n": len(rows), "hallucinated": tp + fn, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "f1": f1,
            "precision": p.__dict__, "recall": rec.__dict__, "false_rejection": Rate.of(fp, fp + tn).__dict__,
            "accuracy": (tp + tn) / len(rows) if rows else None}


def auroc(rows: list[dict]) -> float | None:
    """P(a hallucinated item scores below a supported one): how well the support score separates them, any threshold."""
    pos = sorted(r["score"] for r in rows if r["label"] == "hallucinated")
    neg = sorted(r["score"] for r in rows if r["label"] != "hallucinated")
    if not pos or not neg:
        return None
    import bisect
    wins = sum(len(neg) - bisect.bisect_right(neg, p) + 0.5 * (bisect.bisect_right(neg, p) - bisect.bisect_left(neg, p))
               for p in pos)
    return wins / (len(pos) * len(neg))


def at(rows: list[dict], threshold: float) -> list[dict]:
    """The rows as the check would decide them with another threshold: it rejects iff the weakest fact < threshold."""
    return [{**r, "rejected": r["score"] < threshold} for r in rows]


GRID = tuple(round(0.05 * k, 2) for k in range(1, 20))


def best_threshold(rows: list[dict], grid: tuple[float, ...] = GRID) -> float:
    """The threshold with the best F1 on these rows (use dev rows only)."""
    return max(grid, key=lambda t: (scores(at(rows, t))["f1"], -abs(t - 0.5)))


def evaluate(datasets: list[str], split: str, limit: int | None, seed: int, check=None,
             progress: bool = False, log: Path | None = None) -> tuple[dict, list[dict]]:
    """`log`: rows are appended to it as they are judged, and items already in it are not judged again (a run that
    stopped, e.g. the laptop slept, carries on where it was)."""
    if check is None:
        from memledger.guards.hallucination import HallucinationCheck
        check = HallucinationCheck()
    done = {}
    if log is not None and log.exists():
        done = {r["id"]: r for r in map(json.loads, log.read_text().splitlines()) if r}
    rows: list[dict] = []
    for name in datasets:
        eps = load(name, split=split, limit=limit, seed=seed)
        for i, ep in enumerate(eps, 1):
            if ep.id in done:
                rows.append(done[ep.id])
                continue
            rows.append(judge(check, ep))
            if log is not None:
                with log.open("a") as f:
                    f.write(json.dumps(rows[-1]) + "\n")
            if progress and (i % 100 == 0 or i == len(eps)):
                print(f"[{name} {i}/{len(eps)}]", flush=True)
    out: dict = {}
    for name in datasets:
        mine = [r for r in rows if r["dataset"] == name]
        groups = defaultdict(list)
        for r in mine:
            groups[r["group"]].append(r)
        out[name] = {"all": scores(mine), "auroc": auroc(mine), "by_group": {g: scores(rs) for g, rs in sorted(groups.items())} if len(groups) > 1
                     else {}, "median_ms": sorted(r["ms"] for r in mine)[len(mine) // 2] if mine else None}
    return out, rows


def _rate(d: dict) -> str:
    from eval.metrics import Rate

    return Rate(**d).text()


def tuned(res: dict, rows: list[dict], dev_rows: list[dict]) -> None:
    """Add, per dataset, the test scores at the threshold that is best on that dataset's dev rows."""
    for name, r in res.items():
        dev = [x for x in dev_rows if x["dataset"] == name]
        if dev:
            t = best_threshold(dev)
            r["tuned"] = {"threshold": t, "dev_n": len(dev),
                                  **scores(at([r for r in rows if r["dataset"] == name], t))}


def markdown(res: dict, meta: dict) -> str:
    out = [f"# Hallucination check on RAGTruth and HaluEval ({meta['split']} split)", "",
           (f"Check: `HallucinationCheck` with scorer `{meta['scorer']}`, threshold {meta['threshold']}, "
           f"chunks of {meta['chunk_words']} words (production settings, nothing tuned on test). "
           f"Sample: {meta['limit'] or 'all'} items per dataset, seed {meta['seed']}. Positive class = hallucinated. "
           "95% Wilson intervals."), "",
           "| dataset | n (halluc.) | precision | recall | F1 | false rejection | AUROC | median ms |",
           "|---|---|---|---|---|---|---|---|"]
    for name, r in res.items():
        rows = [(name, r["all"])] + [(f"{name} / {g}", s) for g, s in r["by_group"].items()]
        if "tuned" in r:
            rows.append((f"{name}, threshold {r['tuned']['threshold']} (best F1 on {r['tuned']['dev_n']} dev items)",
                         r["tuned"]))
        for label, s in rows:
            top = label == name
            auc = f"{r['auroc']:.3f}" if top and r.get("auroc") is not None else ""
            out.append(f"| {label} | {s['n']} ({s['hallucinated']}) | {_rate(s['precision'])} | {_rate(s['recall'])} | "
                       f"{s['f1']:.3f} | {_rate(s['false_rejection'])} | {auc} | {r['median_ms'] if top else ''} |")
    return "\n".join(out + ["", meta.get("notes", "")]).rstrip() + "\n"


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    ap.add_argument("--datasets", default=",".join(DATASETS))
    ap.add_argument("--limit", type=int, help="seeded sample per dataset (default: all)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--backend", default="hf", choices=["hf", "lexical"], help="hf = MiniCheck (production)")
    ap.add_argument("--out", default="docs/results/hallucination_benchmarks.md")
    ap.add_argument("--raw", default="results/hallucination/raw")
    ap.add_argument("--notes", default="", help="text appended under the table (how the run was made)")
    ap.add_argument("--dev-rows", help="rows of a --split dev run: add test scores at the dev-best threshold")
    a = ap.parse_args(argv)
    os.environ["MEMLEDGER_GUARD_BACKEND"] = a.backend
    from memledger.guards.hallucination import HallucinationCheck
    from memledger.guards.models import MINICHECK

    check = HallucinationCheck()
    t0 = time.time()
    raw = Path(a.raw)
    raw.mkdir(parents=True, exist_ok=True)
    res, rows = evaluate([d.strip() for d in a.datasets.split(",") if d.strip()], a.split, a.limit, a.seed, check,
                         progress=True, log=raw / f"{a.split}.jsonl")
    meta = {"split": a.split, "limit": a.limit, "seed": a.seed, "threshold": check.threshold,
            "chunk_words": check.chunk_words, "notes": a.notes, "minutes": round((time.time() - t0) / 60, 1),
            "scorer": os.environ.get("MEMLEDGER_MINICHECK_MODEL", MINICHECK) if a.backend == "hf" else "lexical",
            "device": os.environ.get("MEMLEDGER_DEVICE", "cpu")}
    if a.dev_rows:
        tuned(res, rows, [json.loads(x) for x in Path(a.dev_rows).read_text().splitlines() if x.strip()])
    (raw / f"{a.split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (raw / f"{a.split}.json").write_text(json.dumps({"meta": meta, "results": res}, indent=1) + "\n")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(markdown(res, meta))
    print(Path(a.out).read_text())
    return res


if __name__ == "__main__":
    main()
