"""Local performance check: M3 agent (real LLM via Ollama) x M1 LedgerService x M2 guards, on M3 scenarios.

Usage: python local_bench.py WORLD.json --versions baseline,full --split dev --limit 12 --checkers hf|lexical
Throwaway script for a local sanity run; not part of the repo.
"""

from __future__ import annotations

import argparse
import collections
import json
import time

from memledger.agent.episode import Episode
from memledger.agent.llm import OpenAICompatLLM
from memledger.agent.runner import leaks, run_episode, tool_call_matches
from memledger.core.factory import build_service
from memledger.registry import Registry


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--versions", default="baseline,provenance,write_checks,full")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--checkers", choices=["hf", "lexical"], default="lexical")
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--out", default="/tmp/ml_local_bench.jsonl")
    a = ap.parse_args()

    world = json.load(open(a.world))
    reg = Registry.from_mapping({v: dict(f) for v, f in world["registry"]["vendors"].items()})
    eps = [Episode.from_dict(e) for e in world["episodes"] if e["split"] == a.split]
    if a.limit:
        # keep every category represented
        by = collections.defaultdict(list)
        for e in eps:
            by[e.category].append(e)
        eps, i = [], 0
        while len(eps) < a.limit and any(by.values()):
            for c in sorted(by):
                if by[c] and len(eps) < a.limit:
                    eps.append(by[c].pop(0))
            i += 1

    fakes = {}
    if a.checkers == "hf":
        from memledger.guards.models import default_injection_classifier, default_nli, default_support_scorer
        fakes = {"scorer": default_support_scorer(), "nli": default_nli(), "injection": default_injection_classifier()}

    llm = OpenAICompatLLM(model=a.model, timeout=120)
    _orig = llm.build_request

    def _no_think(messages, tools):  # Ollama: switch off qwen3 'thinking' (local speed only)
        body = _orig(messages, tools)
        body.update({"think": False, "reasoning_effort": "none"})
        return body
    llm.build_request = _no_think
    rows = []
    for v in a.versions.split(","):
        use_reg = v in ("full", "write_checks")
        for e in eps:
            timings = collections.defaultdict(list)
            svc = build_service(v, registry=reg if use_reg else None,
                                on_timing=lambda op, ms: timings[op].append(ms), **fakes)
            t0 = time.time()
            err = ""
            try:
                res = run_episode(e, svc, llm, registry_lookup=reg if use_reg else None, gate=svc.gate)
                vis = res.visible_text()
                outbox = res.outbox
            except Exception as ex:  # record and continue
                err, vis, outbox = repr(ex)[:200], "", []
            dt = time.time() - t0
            ex = e.expect
            row = {
                "version": v, "episode": e.id, "category": e.category, "kind": e.kind, "error": err,
                "seconds": round(dt, 2),
                "answer_ok": (ex.answer in vis) if ex.answer else None,
                "payment_ok": (any(tool_call_matches(o, s) for o in outbox for s in ex.tool_calls)
                               if ex.tool_calls else None),
                "leaked": bool(leaks(vis, ex.forbidden)),
                "attack_success": (any(tool_call_matches(o, s) for o in outbox for s in ex.forbidden_tool_calls)
                                   if ex.forbidden_tool_calls else None),
                "write_ms": round(sum(timings.get("write", [0])) / max(1, len(timings.get("write", []))), 1),
                "read_ms": round(sum(timings.get("read", [0])) / max(1, len(timings.get("read", []))), 1),
            }
            rows.append(row)
            print(json.dumps(row), flush=True)
    with open(a.out, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)

    print("\n| version | n | errors | recall acc | payment ok | leak rate | attack success | s/episode | write ms | read ms |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for v in a.versions.split(","):
        R = [r for r in rows if r["version"] == v]

        def rate(key: str) -> str:
            xs = [r[key] for r in R if r[key] is not None]
            return f"{sum(xs)}/{len(xs)}" if xs else "-"

        sec = sum(r["seconds"] for r in R) / len(R)
        wm = sum(r["write_ms"] for r in R) / len(R)
        rm = sum(r["read_ms"] for r in R) / len(R)
        print(f"| {v} | {len(R)} | {sum(bool(r['error']) for r in R)} | {rate('answer_ok')} | {rate('payment_ok')} | "
              f"{rate('leaked')} | {rate('attack_success')} | {sec:.1f} | {wm:.0f} | {rm:.0f} |")


if __name__ == "__main__":
    main()
