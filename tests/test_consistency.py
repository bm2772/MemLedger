"""Consistency audit rules that can be automated (docs/testing/consistency_audit.md).

Interfaces, one source of truth, data flow through all five versions, disjoint splits and repo hygiene.
"""

from __future__ import annotations

import ast
import inspect
import re
import subprocess
from pathlib import Path

import pytest

from attacks.oracle import attack_success
from attacks.suite import SuiteConfig, build
from memledger.agent.runner import run_episode
from memledger.core import interfaces
from memledger.core.types import SourceKind
from tests.test_bench import root  # noqa: F401  (tiny on-disk benchmark fixtures)

ROOT = Path(__file__).resolve().parents[1]
CODE_DIRS = ["memledger", "eval", "attacks", "bench", "scenarios", "demo", "infra"]


def py_files():
    for d in CODE_DIRS:
        yield from (ROOT / d).rglob("*.py")


# ------------------------------------------------------------------------------------------------ 1. interfaces
def _params(fn) -> list[str]:
    return [p for p in inspect.signature(fn).parameters if p != "self"]


def _conforms(cls, proto) -> None:
    for name, fn in vars(proto).items():
        if callable(fn) and not name.startswith("_"):
            assert _params(getattr(cls, name))[:len(_params(fn))] == _params(fn), f"{cls.__name__}.{name}"


def test_implementations_match_frozen_interfaces():
    from memledger.core.mock import MockMemoryService
    from memledger.core.service import LedgerService
    from memledger.guards.contradiction import ContradictionCheck
    from memledger.guards.hallucination import HallucinationCheck
    from memledger.guards.input_screen import InputScreen
    from memledger.guards.memshield import MemshieldCheck
    from memledger.guards.registry_match import RegistryCheck
    from memledger.policy.gate import ActionGate

    for cls in (LedgerService, MockMemoryService):
        _conforms(cls, interfaces.MemoryService)
    for cls in (ContradictionCheck, HallucinationCheck, MemshieldCheck, RegistryCheck):
        _conforms(cls, interfaces.Check)
    _conforms(InputScreen, interfaces.InputScreen)
    _conforms(ActionGate, interfaces.ActionGate)


def test_one_definition_of_the_shared_types():
    defs: dict[str, list[str]] = {}
    for f in py_files():
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.ClassDef) and node.name in ("Episode", "Session", "Verdict", "Seed", "Step"):
                defs.setdefault(node.name, []).append(str(f.relative_to(ROOT)))
    assert {k: len(v) for k, v in defs.items()} == {k: 1 for k in defs}, defs


# ------------------------------------------------------------------------------------------ 2. one source of truth
def test_version_flags_agree_everywhere():
    from eval.versions import VERSIONS, check_flags
    from memledger.core.factory import FLAGS

    check_flags()
    doc = (ROOT / "docs/interfaces.md").read_text()
    assert set(FLAGS) == set(VERSIONS) and all(v in doc for v in FLAGS)


def test_source_priors_match_slide_7():
    from memledger.core import mock, service, trust

    deck = {SourceKind.PAPER: 0.95, SourceKind.REGISTRY: 0.95, SourceKind.INTERNAL: 0.9, SourceKind.USER: 0.7,
            SourceKind.WEB: 0.3}
    assert service.PRIORS is mock.PRIORS and inspect.signature(trust.TrustEngine).parameters["priors"].default \
        is mock.PRIORS
    assert {k: mock.PRIORS[k] for k in deck} == deck


def test_checker_model_ids_have_one_home():
    """guards/models.py owns the ids; the fetch script downloads exactly those (plus the embedder)."""
    from bench.fetch_models import MODELS
    from memledger.guards import models

    fetched = {m for m, _, _ in MODELS}
    assert {models.MINICHECK, models.NLI, models.PROMPT_GUARD, *models.TUNED_CUTOFFS} <= fetched


# ------------------------------------------------------------------------------------------------- 3. data flow
FAMILY_SIZES = {"agentpoison": 1, "poisonedrag": 1, "minja": 1, "summary_laundering": 1, "repetition_flooding": 1,
                "db_tamper": 1, "isolation_matrix": 8}


@pytest.fixture(scope="module")
def one_per_family():
    eps, _ = build("dev", SuiteConfig(dev_worlds=1, benchmarks=[], family_sizes=FAMILY_SIZES))
    out = {}
    for e in eps:
        out.setdefault((e.meta["family"], e.kind), e)
    return list(out.values())


def test_every_attack_is_graded_by_a_known_oracle(one_per_family, root):  # noqa: F811
    eps = one_per_family + build("test", SuiteConfig(test_worlds=1, family_sizes=FAMILY_SIZES), root=root)[0]
    for e in eps:
        if e.kind == "attack":
            assert e.meta.get("oracle", {}).get("type") in ("tool_call", "answer_contains", "canary", "tamper", "goal",
                                                            "blocked"), e.id


@pytest.mark.parametrize("version", ["baseline", "provenance", "write_checks", "full", "full_no_registry"])
def test_one_episode_per_family_flows_through_every_version(version, one_per_family, monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    from attacks.tamper import wrap_service
    from eval.llm import GullibleLLM
    from eval.runner import record
    from eval.versions import build as build_version

    for e in one_per_family:
        built = build_version(version, e.registry)
        svc = built.service
        memory = wrap_service(e, svc)
        res = run_episode(e, memory, GullibleLLM(), registry_lookup=built.registry.get if built.registry else None,
                          gate=svc.gate)
        row = record(e, version, res, svc, None)
        if hasattr(memory, "report"):
            row["side_channel" if hasattr(memory, "calls") else "tamper"] = memory.report()
        claims = svc.store.list_claims()
        # every write went through the service: each claim has a derivation with what the model saw (exposed_to)
        for c in claims:
            ds = svc.store.derivations_for(c.id)
            assert ds and all(d.exposed_to for d in ds), (e.id, c.id)
            assert c.labels.team and c.content_hash, (e.id, c.id)
        if e.meta["family"] != "db_tamper" and version != "baseline":  # the chain verifies when nobody edited it
            assert all(svc.verify_claim(c.id) for c in claims if c.status.value == "active"), e.id
        # the per-episode oracle agrees with what eval/metrics.py counts for the same row
        verdict = attack_success(e, row)
        kind = e.meta.get("oracle", {}).get("type")
        if kind == "tool_call":
            assert verdict == bool(row["hijacked"]), e.id
        if kind == "canary" and not row.get("side_channel"):
            assert verdict == bool(row["leaks"]), e.id


# ----------------------------------------------------------------------------------------------------- 4. splits
def _keys(eps):
    accounts = {f.get("account") for e in eps for f in e.registry.values() if isinstance(f, dict)} - {None}
    # benchmark content: ingested/written texts and the documents the stub tools return (BIPIA, InjecAgent, AgentDojo
    # keep theirs there). Task questions are left out: they are our template (bench/loaders.py), so two entries with
    # the same topic in dev and test ask the same question without sharing any benchmark item.
    bench = [e for e in eps if e.meta["part"] == "benchmark"]
    texts = {s.content or s.text for e in bench for s in e.steps if s.op != "task"}
    texts |= {t["response"] for e in bench for t in e.meta.get("stub_tools", []) if t.get("response")}
    texts -= {"", None}
    return {"ids": {e.id for e in eps}, "canaries": {c.marker for e in eps for c in e.canaries},
            "accounts": accounts, "benchmark items": texts}


def test_dev_and_test_share_no_ids_canaries_or_accounts(root):  # noqa: F811
    cfg = SuiteConfig(dev_worlds=1, test_worlds=1, family_sizes={k: 2 for k in FAMILY_SIZES})
    dev, test = _keys(build("dev", cfg, root=root)[0]), _keys(build("test", cfg, root=root)[0])
    for name in ("ids", "canaries", "accounts"):
        assert not dev[name] & test[name], (name, sorted(dev[name] & test[name])[:3])


def test_dev_and_test_share_no_benchmark_items_on_real_data():
    """The fixtures reuse texts across splits, so this runs on the downloaded data (make data)."""
    from bench.download import data_dir

    if not (data_dir("memshield") / "test.jsonl").exists():
        pytest.skip("benchmarks not downloaded")
    cfg = SuiteConfig(dev_worlds=0, test_worlds=0, family_sizes={})
    dev, test = build("dev", cfg)[0], build("test", cfg)[0]
    shared = _keys(dev)["benchmark items"] & _keys(test)["benchmark items"]
    assert not shared, sorted(shared)[:3]
    assert not {e.source for e in dev} & {"injecagent", "agentdojo"}


def test_bipia_dev_is_the_train_split(root):  # noqa: F811
    from bench import load

    assert all("_train_" in e.id for e in load("bipia", "dev", root=root))


# ---------------------------------------------------------------------------------------------------- 6. hygiene
def _tracked() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return out.splitlines()


def test_no_generated_or_secret_files_tracked():
    bad = re.compile(r"(\.egg-info/|(^|/)\.env|\.key$|\.pem$|\.safetensors$|\.bin$|\.gguf$|\.sqlite$|^data/|^models/)")
    assert not [f for f in _tracked() if bad.search(f)]


def test_no_todo_markers_in_code():
    hits = [f"{f.relative_to(ROOT)}:{i}" for f in py_files()
            for i, line in enumerate(f.read_text().splitlines(), 1) if re.search(r"\b(TODO|FIXME|XXX)\b", line)]
    assert not hits, hits


def test_ci_runs_the_makefile_checks():
    ci = "\n".join(p.read_text() for p in (ROOT / ".github/workflows").glob("*.yml"))
    make = (ROOT / "Makefile").read_text()
    assert "python-version: \"3.11\"" in ci  # CI is the 3.11 floor of pyproject's requires-python
    for cmd in ("ruff check .", "pytest -q"):
        assert cmd in ci and cmd in make, cmd


def test_code_uses_no_syntax_newer_than_3_11():
    """ast with feature_version=(3, 11) rejects 3.12+ syntax (PEP 695 type params, `type X = ...`)."""
    for f in py_files():
        ast.parse(f.read_text(), filename=str(f), feature_version=(3, 11))
