"""The five versions compared on slide 17 (Figure 6), built by M1's memledger.core.factory.build_service.

baseline          plain RAG: one global store (no team scoping), no hash-chain verification on read, no JTMS
                  retraction, no guards; the service still stores the same rows so the tamper edits can be applied
provenance        + team-scoped lookup, provenance graph, JTMS trust and hash-chain verification on every read
write_checks      + input screen (step 1) and write checks: hallucination, memshield, contradiction
full              + registry match, access control and action gate; high-risk params bound from the registry (I10)
full_no_registry  full without the registry, to isolate its effect

Guards use the backend named by $MEMLEDGER_GUARD_BACKEND: "lexical" (code-only fallbacks, CI and laptops) or "hf"
(the real models; needs the [models] extra). The HF models are loaded once per run and shared by all episodes.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from memledger.core.factory import FLAGS, build_service
from memledger.core.service import LedgerService
from memledger.registry import Registry, set_default_registry


@dataclass(frozen=True)
class Version:
    name: str
    provenance: bool = False
    write_checks: bool = False
    input_screen: bool = False
    access_control: bool = False
    action_gate: bool = False
    registry: bool = False


VERSIONS: dict[str, Version] = {
    "baseline": Version("baseline"),
    "provenance": Version("provenance", provenance=True),
    "write_checks": Version("write_checks", provenance=True, write_checks=True, input_screen=True),
    "full": Version("full", True, True, True, True, True, True),
    "full_no_registry": Version("full_no_registry", True, True, True, True, True, False),
}


def resolve_version(name: str) -> Version:
    key = name.lstrip("+")
    if key not in VERSIONS:
        raise KeyError(f"unknown version {name!r}; choose from {list(VERSIONS)}")
    return VERSIONS[key]


def guard_backend() -> str:
    return os.environ.get("MEMLEDGER_GUARD_BACKEND", "hf").strip().lower()


def load_guard_models(backend: str | None = None) -> dict[str, Any]:
    """Model callables for the factory's `fakes` slots; {} = the factory's lexical defaults."""
    if (backend or guard_backend()) != "hf":
        return {}
    from memledger.guards.models import default_injection_classifier, default_nli, default_support_scorer

    models = {"scorer": default_support_scorer(), "nli": default_nli(), "injection": default_injection_classifier()}
    if os.environ.get("MEMLEDGER_MEMSHIELD_MODEL"):  # otherwise the factory's lexical memshield rules
        from memledger.guards.memshield import default_memshield
        models["memshield"] = default_memshield()
    return models


@dataclass
class Built:
    service: LedgerService
    registry: Registry | None  # also the lookup send_payment binds from (I10); None = model-supplied params
    manifest: dict


def build(version: str | Version, episode_registry: dict, models: dict[str, Any] | None = None,
          on_timing: Callable[[str, float], None] | None = None, backend: str | None = None) -> Built:
    """Fresh service for one episode (episodes never share memory), with that episode's signed registry."""
    v = version if isinstance(version, Version) else resolve_version(version)
    reg = Registry.from_mapping(episode_registry) if v.registry else None
    set_default_registry(reg)  # bind_params' default: never a previous episode's registry
    svc = build_service(v.name, registry=reg, on_timing=on_timing, **(models or {}))
    manifest = {"version": v.name, "service": type(svc).__name__, "checks": [type(c).__name__ for c in svc.checks],
                "input_screen": svc.input_screen is not None, "action_gate": svc.gate is not None,
                "access_control": svc.access is not None, "registry": reg is not None,
                "hash_verify": svc.verify_hashes, "team_scoped": svc.scoped, "jtms": svc.jtms,
                "guard_backend": backend or guard_backend(),
                "memshield": "memshield" in (models or {}) and os.environ.get("MEMLEDGER_MEMSHIELD_MODEL") or "lexical",
                "missing": []}
    return Built(svc, reg, manifest)


def check_flags() -> None:
    """The eval flags and M1's factory must describe the same five versions."""
    assert set(FLAGS) == set(VERSIONS)
    for name, v in VERSIONS.items():
        assert FLAGS[name] == (v.write_checks, v.input_screen, v.access_control, v.action_gate, v.registry), name
