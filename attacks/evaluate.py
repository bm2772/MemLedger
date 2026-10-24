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
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from attacks import attribution
from attacks.benign import benign_twin
from attacks.oracle import by_family, overall
from attacks.suite import SuiteConfig, build
from eval.metrics import Rate
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
        pools.setdefault((fam, e.category) if e.kind == "clean" else fam, []).append(e)
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


def tables(episodes: list[Episode], rows: dict[str, list[dict]]) -> tuple[dict, str]:
    """(JSON-able results, markdown) from the raw rows of each version."""
    res: dict = {"overall": {}, "families": {}}
    head = ("| version | attack success | leak rate | tamper detection | side-channel count leak | benign task accuracy | "
            "legit payment denied | harmless write rejected | added write ms | added read ms | added gate ms |")
    md = [head, "|---" * 11 + "|"]
    base = None
    for v, rs in rows.items():
        o = overall(episodes, rs)
        m = o["metrics"]
        med = {op: m[f"{op}_ms"]["median"] for op in ("write", "read", "gate")}
        base = base or med
        added = {op: (None if med[op] is None or base[op] is None else med[op] - base[op]) for op in med}
        sc = o["side_channel"]
        res["overall"][v] = {"attack_success": o["attack_success"].__dict__, "leak_rate": m["leak_rate"],
                             "tamper_detected": o["tamper_detected"].__dict__, "task_accuracy": m["task_accuracy"],
                             "side_channel_count_leak": sc["count_leak"].__dict__,
                             "side_channel_timing_diff_ms": sc["timing_diff_ms"],
                             "false_denial_rate": m["false_denial_rate"], "false_rejection_rate": m["false_rejection_rate"],
                             "median_ms": med, "added_ms": added, "errors": m["error_rate"]["x"]}
        md.append(f"| {v} | {o['attack_success'].text()} | {_rate(m['leak_rate'])} | {o['tamper_detected'].text()} | "
                  f"{sc['count_leak'].text()} | {_rate(m['task_accuracy'])} | {_rate(m['false_denial_rate'])} | "
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

    block("Attack success per family (oracle of attacks/oracle.py):", lambda d: d and d["attack_success"], fams, "n_attack")
    block("Leak rate per family (a marker the user may not see appeared in anything visible):",
          lambda d: d and d["leak"], fams, "n_attack")
    block("Tamper detection per family (tampered item withheld and quarantined, read from the service state):",
          lambda d: d and d["tamper_detected"], [f for f in fams if any(
              res["families"][v].get(f, {}).get("tamper_detected") for v in rows)], "n_attack")
    for title, k in (("Legit payment denied per family (benign twins and clean payments; the payment was not made correctly):",
                      "false_denial_rate"),
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
                  episodes_label=f"attacks.suite:{a.split}", split=a.split, progress=not a.quiet)
    raw = Path(a.out) / "raw" / a.run_id
    rows = {v: [json.loads(x) for x in (raw / f"{v}.jsonl").read_text().splitlines()] for v in versions}
    res, md = tables(eps, rows)
    d = Path(a.out) / a.run_id
    (d / "families.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (d / "families.md").write_text(md + "\n")
    print(md)
    return summary


if __name__ == "__main__":
    main()
