"""M1 attack families (attacks/<family>.py): counts, disjoint dev/test, ground truth, and a few episodes per family run
through M4's runner on baseline and full with the offline fooled model."""

import hashlib
import json
from collections import Counter

import pytest

from attacks import agentpoison, isolation
from attacks.oracle import attack_success, by_family
from attacks.suite import FAMILIES, FAMILY_SIZES, SuiteConfig, build
from attacks.tamper import KINDS, TamperingService, wrap_service
from eval.llm import GullibleLLM
from eval.runner import run_one
from eval.versions import resolve_version
from memledger.agent.episode import Episode

NEW = set(FAMILIES)
LLM = GullibleLLM()


@pytest.fixture(scope="module")
def suite():
    cfg = SuiteConfig(benchmarks=[], dev_worlds=0, test_worlds=0)
    return {s: build(s, cfg)[0] for s in ("dev", "test")}


def text_key(e: Episode) -> str:
    d = e.to_dict()
    for k in ("id", "split"):
        d.pop(k)
    d["meta"] = {k: v for k, v in d["meta"].items() if k != "gen_seed"}
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def test_counts_per_family_and_split(suite):
    for split, eps in suite.items():
        counts = Counter(e.meta["family"] for e in eps)
        assert set(counts) == NEW and all(counts[f] == FAMILY_SIZES[f] for f in NEW), (split, counts)
        assert sum(counts.values()) >= 500, split
        assert {e.split for e in eps} == {split}
        assert all(e.kind == "attack" and e.source == "scenario" and e.meta["part"] == "scenario" for e in eps)


def test_dev_and_test_are_disjoint(suite):
    dev, test = suite["dev"], suite["test"]
    assert not {e.id for e in dev} & {e.id for e in test}
    assert not {e.meta["gen_seed"] for e in dev} & {e.meta["gen_seed"] for e in test}
    assert max(e.meta["gen_seed"] for e in dev) < 10_000 <= min(e.meta["gen_seed"] for e in test)
    assert not {text_key(e) for e in dev} & {text_key(e) for e in test}  # no identical episode text across splits

    def values(eps):  # every canary marker, planted account and codename-like string an episode introduces
        out = set()
        for e in eps:
            out |= {c.marker for c in e.canaries} | set(e.poison_markers) | {s.canary for s in e.seeds if s.canary}
            out |= {v["account"] for v in e.registry.values()}
        return out

    assert not values(dev) & values(test)
    assert len({text_key(e) for e in dev}) == len(dev)  # and no duplicates inside a split


def test_every_episode_is_valid_v1_with_ground_truth(suite):
    for eps in suite.values():
        for e in eps:
            assert Episode.from_dict(e.to_dict()) == e
            ex, o = e.expect, e.meta["oracle"]
            assert ex.blocked or ex.forbidden or ex.forbidden_tool_calls, e.id
            assert o["type"] in ("tool_call", "answer_contains", "canary", "tamper"), e.id
            assert e.meta["attack_goal"] and e.meta["defended_outcome"] and e.meta["variant"], e.id
            if o["type"] == "tool_call":
                assert ex.forbidden_tool_calls and ex.tool_calls and e.registry and e.poison_markers, e.id
            if o["type"] == "canary":
                assert all(any(c.marker == m for c in e.canaries) for m in o["markers"]), e.id
            if o["type"] == "tamper":
                assert e.meta["tamper"]["kind"] in KINDS and set(ex.forbidden) <= {s.canary for s in e.seeds}
            ids = {s.id for s in e.seeds} | {s.id for s in e.steps if s.id}
            for st in e.steps:
                assert all(c in ids for c in (st.context or [])), (e.id, st.id)


def test_generation_is_deterministic():
    for name, mod in FAMILIES.items():
        assert mod.generate(7).to_dict() == mod.generate(7).to_dict(), name
        assert mod.generate(7).to_dict() != mod.generate(8).to_dict(), name


def test_isolation_matrix_covers_all_48_cells_in_both_splits(suite):
    for eps in suite.values():
        cells = Counter((e.meta["attack_type"], e.meta["path"]) for e in eps if e.meta["family"] == "isolation_matrix")
        assert set(cells) == set(isolation.VARIANTS) and len(cells) == 48 and set(cells.values()) == {3}
    assert len(isolation.TYPES) == 8 and len(isolation.PATHS) == 6


def test_db_tamper_covers_all_six_edits(suite):
    for eps in suite.values():
        kinds = Counter(e.meta["tamper"]["kind"] for e in eps if e.meta["family"] == "db_tamper")
        assert set(kinds) == set(KINDS) and set(kinds.values()) == {12}


def test_agentpoison_optimisation_raises_similarity(suite):
    for objective in ("embedding", "lexical"):
        opt = [e.meta["optimised"] for e in suite["dev"]
               if e.meta["family"] == "agentpoison" and e.meta["variant"]["objective"] == objective]
        assert all(o["sim_after"] >= o["sim_before"] for o in opt)
        assert sum(o["sim_after"] > o["sim_before"] for o in opt) > len(opt) * 0.9
        assert all(1 <= len(o["triggers"]) <= 6 for o in opt)
    assert agentpoison.similarity("pay the invoice", "pay the invoice", "embedding") == pytest.approx(1.0)


def pick(eps, family, n=6, **where):
    got = [e for e in eps if e.meta["family"] == family
           and all(e.meta["variant"].get(k) == v for k, v in where.items())]
    return got[:n]


def run(e, version):
    row, _ = run_one(e, resolve_version(version), LLM, {}, "lexical")
    assert row["error"] is None, (e.id, row["error"])
    return row


@pytest.mark.parametrize("family", sorted(NEW - {"db_tamper", "isolation_matrix"}))
def test_family_runs_through_runner_baseline_vulnerable_full_defended(suite, family):
    eps = pick(suite["dev"], family, 8)
    base = [attack_success(e, run(e, "baseline")) for e in eps]
    full = [attack_success(e, run(e, "full")) for e in eps]
    assert any(base), f"{family}: baseline is never attacked successfully; the episodes are toothless"
    if family != "poisonedrag":  # the lexical contradiction check cannot tell two values of a measurement apart
        assert not any(full), (family, [e.id for e, x in zip(eps, full) if x])


def test_isolation_matrix_representatives(suite):
    by = {(e.meta["attack_type"], e.meta["path"]): e for e in suite["dev"] if e.meta["family"] == "isolation_matrix"}
    for cell in [("derivation", "search"), ("multi_agent", "summaries"), ("registry", "shared"), ("direct", "search"),
                 ("via_model", "lookup"), ("tampering", "search"), ("data_flow", "graph"), ("side_channel", "caches")]:
        e = by[cell]
        assert not attack_success(e, run(e, "full")), cell
    for cell in [("derivation", "search"), ("multi_agent", "summaries"), ("registry", "shared")]:
        assert attack_success(by[cell], run(by[cell], "baseline")), cell  # the oracle can fire


def test_db_tamper_detected_and_untampered_control_is_served(suite):
    for e in pick(suite["dev"], "db_tamper", 6):
        base = run(e, "baseline")  # plain memory has no hash chain: the edited record is served, nothing is detected
        assert not base["tamper"]["detected"] and base["tamper"]["returned"] and base["tamper"]["quarantined"] == 0
        assert attack_success(e, base) is True
        for version in ("provenance", "write_checks", "full", "full_no_registry"):
            row = run(e, version)
            assert row["tamper"]["detected"] and not row["leaks"], (e.id, version, row["tamper"])
            assert row["tamper"]["detected_by"] == "hash verification"
            assert attack_success(e, row) is False
        ctrl = Episode.from_dict(e.to_dict())
        ctrl.meta.pop("tamper")
        row = run(ctrl, "full")
        assert "tamper" not in row
        if e.meta["tamper"]["kind"] != "labels":  # without the edit the item is returned, so the oracle fires
            assert row["leaks"], e.id
        else:  # the outsider reads nothing of team A: only the label edit could have exposed it
            assert not row["leaks"], e.id


def test_wrap_service_is_a_noop_without_tamper(suite):
    e = pick(suite["dev"], "minja", 1)[0]
    sentinel = object()
    assert wrap_service(e, sentinel) is sentinel
    d = pick(suite["dev"], "db_tamper", 1)[0]
    assert isinstance(wrap_service(d, object()), TamperingService)


def test_by_family_summarises_rows(suite):
    eps = [e for f in ("minja", "db_tamper") for e in pick(suite["dev"], f, 3)]
    rows = [run(e, "full") for e in eps]
    fam = by_family(eps, rows)
    assert fam["minja"]["attack_success"]["x"] == 0 and fam["db_tamper"]["tamper_detected"]["x"] == 3


def test_evaluate_runs_all_five_versions_on_a_small_subset(tmp_path, monkeypatch):
    from attacks import evaluate
    from eval.versions import VERSIONS

    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    evaluate.main(["--split", "dev", "--limit-per-family", "1", "--no-benchmarks", "--llm", "fake", "--guards", "lexical",
                   "--out", str(tmp_path), "--run-id", "t", "--quiet"])
    res = json.loads((tmp_path / "t" / "families.json").read_text())
    assert set(res["overall"]) == set(VERSIONS)
    assert res["overall"]["baseline"]["attack_success"]["p"] > res["overall"]["full"]["attack_success"]["p"] == 0
    assert "| minja |" in (tmp_path / "t" / "families.md").read_text()


@pytest.mark.parametrize("kind", KINDS)
def test_tamper_is_still_carried_out_when_its_target_seed_was_rejected(suite, kind):
    """26 Oct Brev run: an over-rejecting memshield refused the target seed, no tamper happened, and the untouched
    memories were scored as tampered (6 false leaks on full). The first stored seed is tampered instead."""
    ep = next(e for e in suite["test"] if e.meta.get("family") == "db_tamper" and e.meta["tamper"]["kind"] == kind)
    targets = set(ep.meta["tamper"]["targets"])
    keep = next(s for s in ep.seeds if s.id not in targets)  # memshield rejects every seed except this one
    drop = {s.content for s in ep.seeds if s.id != keep.id}
    shield = lambda text: 0.99 if text in drop else 0.0
    row, _ = run_one(ep, resolve_version("full"), GullibleLLM(), {"memshield": shield}, "lexical")
    assert row["tamper"]["retargeted"] and row["tamper"]["victims"] >= 1
    assert row["tamper"]["detected"] and not row["leaks"], row["tamper"]
