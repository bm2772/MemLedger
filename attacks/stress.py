"""Stress tests for the attack-suite results (docs/testing/stress_test_report.md, RESULTS_AND_REVIEW section D.4).

    python -m attacks.stress seeds   [--per-family 12] [--llm fake|openai --model qwen3:8b]
    python -m attacks.stress order   [--per-family 6]
    python -m attacks.stress scale   [--per-family 50]
    python -m attacks.stress robust

seeds   every generated family at three disjoint generator seed ranges (and three scenario worlds): per-family attack
        success per version, so a rate that moves a lot between seeds is visible
order   the same episodes in the suite order, shuffled, and with the versions run in reverse: every per-episode
        verdict must be identical (no state leaks between episodes or versions)
scale   N episodes per family on the lexical backend: wall time and peak RSS
robust  malformed / empty / huge / unicode / concurrent inputs straight against build_service and run_one
"""

from __future__ import annotations

import argparse
import json
import random
import resource
import sys
import threading
import time
from collections import defaultdict

from attacks.oracle import attack_success
from attacks.suite import FAMILIES, SuiteConfig, scenario_episodes
from eval.runner import make_llm, run_one
from eval.versions import VERSIONS, load_guard_models, resolve_version
from memledger.agent.episode import Episode

SEED_RANGES = (48 * 500, 48 * 700, 48 * 900)  # disjoint from dev (0..) and test (10_000..) generator seeds; multiples
# of 48 so --per-family 48 covers every variant of every family (variant = seed % len(VARIANTS), all divide 48)


def family_sample(base: int, per_family: int) -> list[Episode]:
    out = []
    for name, fam in FAMILIES.items():
        for i in range(per_family):
            e = fam.generate(base + i)
            e.meta = {**e.meta, "family": name}
            out.append(e)
    return out


def verdicts(eps: list[Episode], versions: list[str], llm, backend: str = "lexical") -> dict[str, dict[str, object]]:
    models = load_guard_models(backend)
    out: dict[str, dict[str, object]] = {}
    for name in versions:
        v = resolve_version(name)
        out[name] = {}
        for e in eps:
            row, _ = run_one(e, v, llm, models, backend)
            out[name][e.id] = (attack_success(e, row) if e.kind == "attack" else row["correct"], row["error"])
    return out


def rates(eps: list[Episode], ver: dict[str, dict[str, object]]) -> dict[str, dict[str, str]]:
    fam_of = {e.id: e.meta["family"] for e in eps if e.kind == "attack"}
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for v, res in ver.items():
        cnt: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for eid, (ok, _err) in res.items():
            if eid in fam_of and ok is not None:
                cnt[fam_of[eid]][0] += bool(ok)
                cnt[fam_of[eid]][1] += 1
        for f, (x, n) in cnt.items():
            out[f][v] = f"{x}/{n}"
    return dict(out)


def cmd_seeds(a: argparse.Namespace) -> dict:
    llm = make_llm(a.llm, a.model, a.base_url)
    res = {}
    for k, base in enumerate(SEED_RANGES):
        eps = family_sample(base, a.per_family)
        eps += [e for e in scenario_episodes("dev", SuiteConfig(dev_worlds=1, seed=base + k))
                if e.kind == "attack"][: a.per_family * 3]
        for e in eps:
            e.meta.setdefault("family", e.category)
        res[f"seed{base}"] = rates(eps, verdicts(eps, a.versions, llm))
    return res


def cmd_order(a: argparse.Namespace) -> dict:
    llm = make_llm("fake")
    eps = family_sample(SEED_RANGES[0], a.per_family)
    eps += scenario_episodes("dev", SuiteConfig(dev_worlds=1, seed=SEED_RANGES[0]))[: a.per_family * 6]
    first = verdicts(eps, a.versions, llm)
    shuffled = eps[:]
    random.Random(7).shuffle(shuffled)
    second = verdicts(shuffled, list(reversed(a.versions)), make_llm("fake"))
    diffs = [(v, eid, first[v][eid], second[v][eid]) for v in a.versions for eid in first[v]
             if first[v][eid] != second[v][eid]]
    return {"episodes": len(eps), "versions": a.versions, "differences": diffs[:20], "n_differences": len(diffs)}


def cmd_scale(a: argparse.Namespace) -> dict:
    llm = make_llm("fake")
    eps = family_sample(SEED_RANGES[1], a.per_family)
    out = {}
    for name in a.versions:
        t0 = time.perf_counter()
        ver = verdicts(eps, [name], llm)
        errs = sum(1 for _ok, err in ver[name].values() if err)
        out[name] = {"episodes": len(eps), "wall_s": round(time.perf_counter() - t0, 1), "errors": errs}
    out["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 1)  # bytes on macOS
    return out


def cmd_robust(a: argparse.Namespace) -> dict:
    from memledger.agent.episode import Episode as Ep
    from memledger.core.factory import build_service
    from memledger.core.types import Session, SourceKind, WriteProposal
    from memledger.registry.registry import Registry

    s = Session("u", "team_a", "researcher", 1)
    res: dict[str, str] = {}

    def case(name: str, fn) -> None:
        try:
            res[name] = f"ok: {fn()}"
        except Exception as e:  # noqa: BLE001 - every case reports its own outcome
            res[name] = f"{type(e).__name__}: {str(e)[:160]}"

    for v in ("baseline", "full"):
        reg = Registry.from_mapping({}) if v == "full" else None

        def svc(v=v, reg=reg):
            return build_service(v, registry=reg)
        case(f"{v}: empty memory retrieve", lambda svc=svc: len(svc().retrieve("anything", s)))

        def empty(svc=svc):
            m = svc()
            return m.propose_write(WriteProposal("", [m.ingest("", SourceKind.WEB, s).id], s)).accepted
        case(f"{v}: empty string ingest+write", empty)
        big = "lorem ipsum dolor sit amet " * 4000  # ~108k chars

        def huge(svc=svc, big=big):
            m = svc()
            t0 = time.perf_counter()
            src = m.ingest(big, SourceKind.WEB, s)
            w = m.propose_write(WriteProposal(big[:2000], [src.id], s))
            return f"accepted={w.accepted} {time.perf_counter() - t0:.2f}s"
        case(f"{v}: 108k-char document", huge)
        uni = "Ünïcødé 数据 🚀 " + chr(0x202E) + "RTL" + chr(0x202C) + " zero" + chr(0x200B) + "width"

        def unicode(svc=svc, uni=uni):
            m = svc()
            src = m.ingest(uni, SourceKind.INTERNAL, s)
            w = m.propose_write(WriteProposal(uni, [src.id], s))
            hits = m.retrieve("数据", s)
            return f"accepted={w.accepted} hits={len(hits)} chain={m._chain_ok() if hasattr(m, '_chain_ok') else '?'}"
        case(f"{v}: unicode / bidi / zero-width", unicode)

        def concurrent(svc=svc):
            m = svc()
            src = m.ingest("The pump runs at 40 rpm.", SourceKind.INTERNAL, s)
            errs: list[str] = []

            def w(i: int) -> None:
                try:
                    m.propose_write(WriteProposal(f"The pump runs at 40 rpm (note {i}).", [src.id], s))
                except Exception as e:  # noqa: BLE001
                    errs.append(type(e).__name__)
            ts = [threading.Thread(target=w, args=(i,)) for i in range(16)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            return f"errors={errs[:3]} n_err={len(errs)} chain_ok={m._chain_ok() if hasattr(m, '_chain_ok') else '?'}"
        case(f"{v}: 16 concurrent writes", concurrent)
    for bad in ({}, {"id": "x"}, {"id": "x", "steps": [{"op": "nope"}]}, {"id": "x", "steps": "notalist"}):
        case(f"malformed episode {json.dumps(bad)[:40]}", lambda bad=bad: Ep.from_dict(bad).id)
    case("run_one on an episode with no steps", lambda: run_one(
        Ep.from_dict({"id": "empty", "kind": "clean", "steps": []}), resolve_version("full"), make_llm("fake"), {},
        "lexical")[0]["error"])
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["seeds", "order", "scale", "robust"])
    ap.add_argument("--per-family", type=int, default=48)
    ap.add_argument("--versions", default=",".join(VERSIONS))
    ap.add_argument("--llm", choices=["fake", "openai"], default="fake")
    ap.add_argument("--model")
    ap.add_argument("--base-url")
    a = ap.parse_args(argv)
    a.versions = [v for v in a.versions.split(",") if v]
    import os
    os.environ.setdefault("MEMLEDGER_GUARD_BACKEND", "lexical")
    out = {"seeds": cmd_seeds, "order": cmd_order, "scale": cmd_scale, "robust": cmd_robust}[a.cmd](a)
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
