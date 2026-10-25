"""Run the attack suite through eval/runner.py on all versions and print per-version and per-family tables.

    python -m attacks.evaluate --split dev --guards lexical --llm fake --out results/attacks --run-id dev-lexical
    python -m attacks.evaluate --split dev --limit-per-family 3 --llm openai --model qwen3:8b     # Ollama smoke test

Writes <out>/<run_id>/summary.json (eval/runner.py) and <out>/<run_id>/families.json / families.md (this module), and the
raw per-episode rows to <out>/raw/<run_id>/<version>.jsonl. Rates are x/n with Wilson 95% intervals and the rule-of-three
bound when x = 0 (eval/metrics.py). "Attack success" is the per-episode oracle of attacks/oracle.py; "added delay" is
the per-call median minus the baseline's, in ms.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from attacks import attribution, classify
from attacks.benign import benign_twin
from attacks.oracle import attack_success, by_family, overall
from attacks.suite import SuiteConfig, build
from eval.metrics import Rate, compute
from eval.runner import make_llm, run
from eval.versions import VERSIONS
from memledger.agent.episode import Episode


def select(eps: list[Episode], limit_per_family: int | None, families: list[str] | None,
           benign_per_family: int = 0) -> list[Episode]:
    """First `limit_per_family` attack episodes of each family, `limit_per_family` clean episodes of each clean
    category (recall, shared_recall, payment), and the benign twin (attacks/benign.py) of the first `benign_per_family`
    selected episodes of each generated family. A `families` filter applies to attack families only; the clean
    scenario episodes are kept whenever the filter is absent or names "clean"."""
    pools: dict = {}
    for e in eps:
        fam = e.meta["family"]
        if families and fam not in families:
            continue
        bench = e.meta.get("part") == "benchmark"  # a benchmark gets its own pool (memshield + MemEvoBench share a family)
        group = (fam, e.source) if bench else fam
        pools.setdefault(group if e.kind != "clean" else (group, "clean" if bench else e.category), []).append(e)
    out = []
    for pool in pools.values():
        if limit_per_family is None or len(pool) <= limit_per_family:
            out += pool
        else:  # stride 7 (coprime to every variant count) visits distinct variants instead of the first N consecutive seeds
            step = 7 if len(pool) % 7 else 1
            out += [pool[(i * step) % len(pool)] for i in range(limit_per_family)]
    twins: Counter = Counter()
    for e in list(out):
        if e.kind == "attack" and twins[e.meta["family"]] < benign_per_family and (t := benign_twin(e)) is not None:
            twins[e.meta["family"]] += 1
            out.append(t)
    return out


def _ms(x) -> str:
    return "–" if x is None else f"{x:+.2f}"


def _rate(d: dict | None) -> str:
    return Rate(**d).text() if d else "–"


def _counts(c: dict, keys: list[str]) -> str:
    return ", ".join(f"{k} {c[k]}" for k in keys if c.get(k)) or "–"


def benchmark_block(episodes: list[Episode], rows: dict[str, list[dict]]) -> tuple[dict, list[str]]:
    """Per benchmark and version: attack success, what harmless input it wrongly stopped, LLM calls, top blocking mechanism."""
    ep_of = {e.id: e for e in episodes}
    sources = sorted({e.source for e in episodes if e.meta.get("part") == "benchmark"})
    res: dict = {}
    md = ["", ("Benchmark episodes (agent runs with the benchmark payload; attack success by the per-episode oracle, "
               "'harmless blocked' = clean-twin writes rejected / clean tool outputs quarantined, 'top mechanism' = what "
               "most often stopped an attack):"), "",
          ("| benchmark | version | oracle attack success | harmless write rejected | clean input quarantined | "
           "clean task accuracy | LLM calls | top mechanism |"), "|---" * 8 + "|"]
    for src in sources:
        for v, rs in rows.items():
            mine = [r for r in rs if ep_of[r["episode"]].source == src]
            atk = [(ep_of[r["episode"]], r) for r in mine if r["kind"] == "attack"]
            verdicts = [x for e, r in atk if (x := attack_success(e, r)) is not None]
            m = compute([r for r in mine if r["kind"] == "clean"]) if any(r["kind"] == "clean" for r in mine) else None
            top = Counter(b for e, r in atk if (b := attribution.blocked_by(e, r, v)))
            top_s = ", ".join(f"{k} {n}" for k, n in top.most_common(2)) or "–"
            calls = sum(r["llm"]["calls"] for r in mine)
            res.setdefault(src, {})[v] = {
                "oracle_attack_success": Rate.of(sum(verdicts), len(verdicts)).__dict__,
                "attack_success": Rate.of(sum(verdicts), len(verdicts)).__dict__,  # deprecated alias (F6)
                "llm_calls": calls,
                "harmless_write_rejected": m["false_rejection_rate"] if m else None,
                "clean_input_quarantined": m["input_false_block_rate"] if m else None,
                "clean_task_accuracy": m["task_accuracy"] if m else None, "blocked_by": dict(top)}
            md.append(f"| {src} | {v} | {Rate.of(sum(verdicts), len(verdicts)).text()} | "
                      f"{_rate(m and m['false_rejection_rate'])} | {_rate(m and m['input_false_block_rate'])} | "
                      f"{_rate(m and m['task_accuracy'])} | {calls} | {top_s} |")
    return res, md if sources else []


def tables(episodes: list[Episode], rows: dict[str, list[dict]]) -> tuple[dict, str]:
    """(JSON-able results, markdown) from the raw rows of each version."""
    res: dict = {"overall": {}, "families": {}}
    head = ("| version | oracle attack success | hijacked action | leak rate | tamper detection | side-channel count leak | "
            "benign task accuracy | legit payment not completed correctly | legit payment held or refused (false denial) | "
            "harmless write rejected | added write ms | added read ms | added gate ms |")
    md = [head, "|---" * 13 + "|"]
    base = None
    for v, rs in rows.items():
        o = overall(episodes, rs)
        m = o["metrics"]
        med = {op: m[f"{op}_ms"]["median"] for op in ("write", "read", "gate")}
        base = base or med
        added = {op: (None if med[op] is None or base[op] is None else med[op] - base[op]) for op in med}
        sc = o["side_channel"]
        res["overall"][v] = {"oracle_attack_success": o["oracle_attack_success"].__dict__,
                             "attack_success": o["oracle_attack_success"].__dict__,  # deprecated alias (F6)
                             "hijacked_action_rate": m["hijacked_action_rate"], "leak_rate": m["leak_rate"],
                             "tamper_detected": o["tamper_detected"].__dict__, "task_accuracy": m["task_accuracy"],
                             "side_channel_count_leak": sc["count_leak"].__dict__,
                             "side_channel_timing_diff_ms": sc["timing_diff_ms"],
                             "legit_not_completed_rate": m["legit_not_completed_rate"],
                             "gate_denial_rate": m["gate_denial_rate"],
                             "false_denial_rate": m["legit_not_completed_rate"],  # deprecated alias (F1)
                             "false_rejection_rate": m["false_rejection_rate"],
                             "median_ms": med, "added_ms": added, "errors": m["error_rate"]["x"]}
        md.append(f"| {v} | {o['oracle_attack_success'].text()} | {_rate(m['hijacked_action_rate'])} | "
                  f"{_rate(m['leak_rate'])} | {o['tamper_detected'].text()} | "
                  f"{sc['count_leak'].text()} | {_rate(m['task_accuracy'])} | {_rate(m['legit_not_completed_rate'])} | "
                  f"{_rate(m['gate_denial_rate'])} | "
                  f"{_rate(m['false_rejection_rate'])} | {_ms(added['write'])} | {_ms(added['read'])} | "
                  f"{_ms(added['gate'])} |")
        res["families"][v] = by_family(episodes, rs)
    fams = sorted({k for v in res["families"].values() for k, d in v.items() if d["n_attack"]})
    allf = sorted({k for v in res["families"].values() for k in v})

    def block(title: str, key, names: list[str], nkey: str) -> None:
        md.extend(["", title, "", "| family | n | " + " | ".join(rows) + " |", "|---" * (2 + len(rows)) + "|"])
        for fam in names:
            n = next((res["families"][v][fam][nkey] for v in rows if fam in res["families"][v]), 0)
            md.append(f"| {fam} | {n} | " + " | ".join(
                _rate(key(res["families"][v].get(fam))) for v in rows) + " |")

    block("Oracle attack success per family (attacks/oracle.py):", lambda d: d and d["oracle_attack_success"], fams,
          "n_attack")
    block("Leak rate per family (a marker the user may not see appeared in anything visible):",
          lambda d: d and d["leak"], fams, "n_attack")
    block("Tamper detection per family (tampered item withheld and quarantined, read from the service state):",
          lambda d: d and d["tamper_detected"], [f for f in fams if any(
              res["families"][v].get(f, {}).get("tamper_detected") for v in rows)], "n_attack")
    for title, k in ((("Legit payment not completed correctly per family (benign twins and clean payments; not made, or "
                      "made to a wrong account):"), "legit_not_completed_rate"),
                     ("Legit payment held or refused per family (false denial: the gate or registry stopped it):",
                      "gate_denial_rate"),
                     ("Harmless write rejected per family (benign twins and clean episodes):", "false_rejection_rate"),
                     ("Benign task accuracy per family:", "task_accuracy")):
        block(title, lambda d, k=k: d and d["metrics"][k], [f for f in allf if any(
            (res["families"][v].get(f) or {"metrics": {k: {"n": 0}}})["metrics"][k]["n"] for v in rows)], "n")
    att = attribution.table(episodes, rows)
    res["attribution"] = {k: {v: dict(c) if not isinstance(c, dict) or not c or isinstance(next(iter(c.values())), int)
                              else {f: dict(x) for f, x in c.items()} for v, c in d.items()} for k, d in att.items()}
    md += ["", ("Blocked attacks per version, by the first mechanism that visibly stopped them (attacks/attribution.py); "
                "'attack succeeded' is the complement:"), "", "| mechanism | " + " | ".join(rows) + " |", "|---" * (1 + len(rows)) + "|"]
    for mech in attribution.ORDER:
        md.append(f"| {mech} | " + " | ".join(str(att["primary"][v].get(mech, 0) or "–") for v in rows) + " |")
    md.append("| attack succeeded | " + " | ".join(str(sum(att["succeeded"][v].values()) or "–") for v in rows) + " |")
    md += ["", ("Mechanisms that acted on attack material in any attack episode (a later mechanism hidden behind an "
                "earlier one still counts here):"), "", "| mechanism | " + " | ".join(rows) + " |", "|---" * (1 + len(rows)) + "|"]
    for mech in attribution.ORDER[:-2]:
        md.append(f"| {mech} | " + " | ".join(str(att["fired"][v].get(mech, 0) or "–") for v in rows) + " |")
    res["benchmarks"], bmd = benchmark_block(episodes, rows)
    md += bmd
    res["classification"] = classify.classification(episodes, rows)
    md.append(classify.markdown(res["classification"], list(rows)))
    if "full" in rows and "full_no_registry" in rows:
        md += ["", "What the registry adds (blocked-by, full vs full_no_registry, per family):", "",
               "| family | succeeded full | succeeded full_no_registry | full: blocked by | full_no_registry: blocked by |",
               "|---|---|---|---|---|"]
        for fam in fams:
            a, b = att["by_family"]["full"].get(fam, {}), att["by_family"]["full_no_registry"].get(fam, {})
            md.append(f"| {fam} | {att['succeeded']['full'].get(fam, 0)} | {att['succeeded']['full_no_registry'].get(fam, 0)}"
                      f" | {_counts(a, attribution.ORDER)} | {_counts(b, attribution.ORDER)} |")
    return res, "\n".join(md)


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--versions", default=",".join(VERSIONS))
    ap.add_argument("--limit-per-family", type=int)
    ap.add_argument("--families", help="comma list, e.g. minja,db_tamper (use clean for the scenario clean episodes)")
    ap.add_argument("--benign-per-family", type=int,
                    help="benign twins per generated family (default: --limit-per-family, else 12)")
    ap.add_argument("--no-benchmarks", action="store_true", help="skip downloaded benchmarks (default: use what exists)")
    ap.add_argument("--llm", choices=["fake", "openai"], default="fake")
    ap.add_argument("--model")
    ap.add_argument("--base-url")
    ap.add_argument("--guards", choices=["hf", "lexical", "auto"], default="lexical",
                    help="auto = the Hugging Face checkers if transformers and torch import, else the lexical fallback")
    ap.add_argument("--out", default="results/attacks")
    ap.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%d-%H%M%S"))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--workers", type=int, default=1,
                    help="episodes played concurrently (vLLM on Brev: 16); take added-ms latencies from a 1-worker run")
    ap.add_argument("--resume", action="store_true",
                    help="same --run-id: keep versions whose raw rows are already complete (restart after a crash)")
    ap.add_argument("--max-consecutive-errors", type=int, default=20,
                    help="stop the run after this many errored episodes in a row, e.g. the LLM server died (0: never)")
    a = ap.parse_args(argv)
    cfg = SuiteConfig(benchmarks=[] if a.no_benchmarks else SuiteConfig().benchmarks)
    eps, skipped = build(a.split, cfg)
    benign = a.benign_per_family if a.benign_per_family is not None else (a.limit_per_family or 12)
    eps = select(eps, a.limit_per_family, a.families.split(",") if a.families else None, benign)
    print(f"{len(eps)} episodes ({a.split}); skipped benchmarks: {sorted(skipped) or 'none'}", flush=True)
    if a.guards == "auto":
        a.guards = "hf" if importlib.util.find_spec("transformers") and importlib.util.find_spec("torch") else "lexical"
        print(f"guards: {a.guards}" + ("" if a.guards == "hf" else " (transformers/torch not installed: lexical fallback)"))
    os.environ["MEMLEDGER_GUARD_BACKEND"] = a.guards
    versions = [v.strip() for v in a.versions.split(",") if v.strip()]
    summary = run(eps, versions, a.out, a.run_id, make_llm(a.llm, a.model, a.base_url), backend=a.guards,
                  episodes_label=f"attacks.suite:{a.split}", split=a.split, progress=not a.quiet,
                  workers=a.workers, resume=a.resume, max_consecutive_errors=a.max_consecutive_errors)
    raw = Path(a.out) / "raw" / a.run_id
    rows = {v: [json.loads(x) for x in (raw / f"{v}.jsonl").read_text().splitlines()] for v in versions}
    res, md = tables(eps, rows)
    res["latency_valid"] = summary["latency_valid"]
    if not summary["latency_valid"]:
        md = (f"> **Added ms (write/read/gate) are NOT meaningful here**: {a.workers} parallel episodes add thread "
              "contention. Take latency from a 1-worker run (`make eval-latency`).\n\n" + md)
    d = Path(a.out) / a.run_id
    (d / "families.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (d / "families.md").write_text(md + "\n")
    print(md)
    for line in error_warnings(rows):
        print(line, file=sys.stderr)
    return summary


def error_warnings(rows: dict[str, list[dict]]) -> list[str]:
    """One loud line per version whose episodes raised: their rows count as no verdict / rejected writes, so a version
    that failed to load its checkers would otherwise look like one that blocks everything."""
    out = []
    for v, rs in rows.items():
        errs = Counter((r["error"] or "").splitlines()[0][:160] for r in rs if r.get("error"))
        if errs:
            top, k = errs.most_common(1)[0]
            out.append(f"WARNING: {sum(errs.values())}/{len(rs)} episodes errored in {v}; most common ({k}x): {top}")
    return out


if __name__ == "__main__":
    main()
