import pytest

from eval.versions import VERSIONS, build, check_flags, load_guard_models, resolve_version
from memledger.registry import default_registry


def test_five_versions_each_add_one_layer_and_match_the_factory():
    assert list(VERSIONS) == ["baseline", "provenance", "write_checks", "full", "full_no_registry"]
    b, p, w, f, n = VERSIONS.values()
    assert not b.provenance and p.provenance and not p.write_checks
    assert w.write_checks and w.input_screen and not w.action_gate
    assert f.action_gate and f.access_control and f.registry and n.action_gate and not n.registry
    check_flags()


def test_aliases():
    assert resolve_version("+provenance").name == "provenance"
    with pytest.raises(KeyError):
        resolve_version("nope")


REG = {"Acme Ltd": {"account": "1234"}}


def test_baseline_has_nothing_switched_on():
    b = build("baseline", REG, backend="lexical")
    m = b.manifest
    assert m["service"] == "LedgerService" and m["checks"] == [] and not m["input_screen"]
    assert not m["action_gate"] and not m["registry"] and b.registry is None and default_registry() is None


def test_full_wires_everything_with_the_episode_registry():
    b = build("full", REG, backend="lexical")
    m = b.manifest
    assert m["input_screen"] and m["action_gate"] and m["access_control"] and m["registry"]
    assert "RegistryCheck" in m["checks"] and m["guard_backend"] == "lexical"
    assert b.registry.get("Acme Ltd", "account") == "1234" and default_registry() is b.registry


def test_full_no_registry_has_gate_but_no_registry():
    b = build("full_no_registry", REG, backend="lexical")
    assert b.manifest["action_gate"] and b.registry is None and "RegistryCheck" not in b.manifest["checks"]


def test_lexical_backend_loads_no_models():
    assert load_guard_models("lexical") == {}
