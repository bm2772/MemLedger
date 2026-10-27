"""Stress-test checks: independent recomputation of the tables, determinism under
re-ordering, oracle edge cases."""

import json
import random

from attacks import recompute
from attacks.evaluate import main as evaluate
from attacks.stress import family_sample, verdicts
from eval.metrics import wilson


def test_wilson_matches_eval_metrics():
    for x, n in [(0, 5), (1, 45), (42, 45), (14, 14), (3, 74)]:
        assert recompute.wilson(x, n) == wilson(x, n) or all(
            abs(a - b) < 1e-12 for a, b in zip(recompute.wilson(x, n), wilson(x, n), strict=True))


def test_recomputed_tables_match_and_catch_a_wrong_count(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    evaluate(["--split", "dev", "--limit-per-family", "1", "--benign-per-family", "1", "--no-benchmarks",
              "--versions", "baseline,full", "--out", str(tmp_path), "--run-id", "r", "--quiet"])
    from attacks.benign import benign_twin
    from attacks.suite import SuiteConfig, build
    eps, _ = build("dev", SuiteConfig(benchmarks=[]))
    eps += [t for e in eps if (t := benign_twin(e)) is not None]
    meta = {e.id: e.meta for e in eps}
    assert recompute.compare(tmp_path / "r", tmp_path / "raw" / "r", meta) == []
    f = tmp_path / "r" / "families.json"
    d = json.loads(f.read_text())
    d["overall"]["full"]["oracle_attack_success"]["x"] += 1
    f.write_text(json.dumps(d))
    assert any("full oracle_attack_success" in m for m in recompute.compare(tmp_path / "r", tmp_path / "raw" / "r", meta))


def test_verdicts_do_not_depend_on_episode_or_version_order(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    from eval.runner import make_llm
    eps = family_sample(48 * 500, 2)
    vs = ["baseline", "full"]
    a = verdicts(eps, vs, make_llm("fake"))
    shuffled = eps[:]
    random.Random(3).shuffle(shuffled)
    b = verdicts(shuffled, vs[::-1], make_llm("fake"))
    assert a == b


def test_errored_versions_are_reported():
    from attacks.evaluate import error_warnings
    rows = {"baseline": [{"error": None}], "full": [{"error": "OSError: gated repo\nmore"}, {"error": None}]}
    assert error_warnings(rows) == ["WARNING: 1/2 episodes errored in full; most common (1x): OSError: gated repo"]
