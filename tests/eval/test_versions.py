import pytest

from eval.versions import VERSIONS, MissingComponent, build_stack, resolve_version
from memledger.core.mock import MockMemoryService
from memledger.core.types import Verdict


class PassCheck:
    name = "pass"

    def check(self, proposal, sources):
        return Verdict(True, 1.0, check=self.name)


class Gate:
    def allow(self, tool, params, context_claim_ids, session):
        return Verdict(False, 0.0, "needs approval", "gate")


class Screen:
    def score(self, text):
        return 0.0


class FakeLedger:
    def __init__(self, checks=None):
        self.checks = checks or []


def comps(**over):
    c = {"baseline_service": "memledger.core.mock:MockMemoryService",
         "service": "tests_eval_fakes:FakeLedger",
         "checks": {"support": "tests_eval_fakes:PassCheck"},
         "registry_check": "tests_eval_fakes:PassCheck",
         "input_screen": "tests_eval_fakes:Screen",
         "action_gate": "tests_eval_fakes:Gate",
         "registry_binder": None,
         "access_control": None}
    c.update(over)
    return c


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    import sys
    import types
    m = types.ModuleType("tests_eval_fakes")
    m.FakeLedger, m.PassCheck, m.Gate, m.Screen = FakeLedger, PassCheck, Gate, Screen
    monkeypatch.setitem(sys.modules, "tests_eval_fakes", m)


def test_five_versions_each_add_one_layer():
    assert list(VERSIONS) == ["baseline", "provenance", "write_checks", "full", "full_no_registry"]
    b, p, w, f, n = VERSIONS.values()
    assert not b.provenance and p.provenance and not p.write_checks
    assert w.write_checks and not w.action_gate
    assert f.action_gate and f.access_control and f.registry
    assert n.action_gate and not n.registry


def test_aliases():
    assert resolve_version("+provenance").name == "provenance"
    assert resolve_version("+write_checks").name == "write_checks"
    with pytest.raises(KeyError):
        resolve_version("nope")


def test_baseline_is_plain_mock_without_guards():
    s = build_stack("baseline", comps())
    assert isinstance(s.service, MockMemoryService)
    assert s.screen is None and s.gate is None and s.binder is None
    assert s.manifest["service"] == "MockMemoryService" and s.manifest["missing"] == []


def test_full_wires_checks_screen_gate_and_registry_check():
    s = build_stack("full", comps())
    assert isinstance(s.service, FakeLedger)
    assert [type(c).__name__ for c in s.service.checks] == ["PassCheck", "PassCheck"]
    assert s.screen is not None and s.gate is not None
    assert {"checks.support", "registry_check", "input_screen", "action_gate"} <= set(s.manifest["active"])


def test_full_no_registry_drops_registry_check():
    s = build_stack("full_no_registry", comps())
    assert len(s.service.checks) == 1 and "registry_check" not in s.manifest["active"]


def test_missing_components_are_recorded_not_faked():
    s = build_stack("full", comps(action_gate="memledger.nowhere:Gate", registry_binder=None))
    assert s.gate is None
    assert "action_gate" in s.manifest["missing"] and "registry_binder" in s.manifest["missing"]
    assert s.manifest["degraded"] is True


def test_strict_raises_on_missing():
    with pytest.raises(MissingComponent):
        build_stack("full", comps(action_gate="memledger.nowhere:Gate"), strict=True)


def test_missing_provenance_service_falls_back_to_mock_and_says_so():
    s = build_stack("provenance", comps(service="memledger.nowhere:LedgerService"))
    assert isinstance(s.service, MockMemoryService)
    assert "service" in s.manifest["missing"] and s.manifest["degraded"]
