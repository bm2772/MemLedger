"""The five versions compared on slide 17 (Figure 6), as config flags over one service.

baseline          plain retrieval memory (MockMemoryService until M1 ships a plain mode of LedgerService)
provenance        + provenance graph and JTMS trust (LedgerService, no checks)
write_checks      + input screen (step 1) and write checks: hallucination, contradiction, memshield, registry match
full              + access control and action gate, high-risk params bound from the registry
full_no_registry  full without registry match and registry binding, to isolate the registry's effect

Components are resolved lazily from "module:attr" paths so the runner works before M1/M2 code lands. A component a
version asks for but that cannot be imported is recorded in the manifest as missing (never silently faked);
--strict turns that into an error. Override paths with a JSON file (see DEFAULT_COMPONENTS).
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from memledger.core.interfaces import ActionGate, InputScreen, MemoryService


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

# Paths M1/M2 are expected to provide; agree exact names with them and override via --components until merged.
DEFAULT_COMPONENTS: dict[str, Any] = {
    "baseline_service": "memledger.core.mock:MockMemoryService",
    "service": "memledger.core.service:LedgerService",
    "checks": {
        "hallucination": "memledger.guards.hallucination:HallucinationCheck",
        "memshield": "memledger.guards.memshield:MemshieldCheck",
        "contradiction": "memledger.guards.contradiction:ContradictionCheck",
    },
    "registry_check": "memledger.guards.registry_match:RegistryCheck",
    "input_screen": "memledger.guards.screen:InputScreen",
    "access_control": "memledger.policy.access:AccessControl",
    "action_gate": "memledger.policy.gate:ActionGate",
    "registry_binder": "memledger.registry.binding:bind_params",  # (tool, params, session) -> params
}

Binder = Callable[[str, dict, Any], dict]


class MissingComponent(RuntimeError):
    pass


@dataclass
class Stack:
    service: MemoryService
    screen: InputScreen | None
    gate: ActionGate | None
    binder: Binder | None
    manifest: dict


def resolve_version(name: str) -> Version:
    key = name.lstrip("+")
    if key not in VERSIONS:
        raise KeyError(f"unknown version {name!r}; choose from {list(VERSIONS)}")
    return VERSIONS[key]


def _load(path: str | None) -> Any:
    if not path:
        raise ImportError("no path configured")
    mod, _, attr = path.partition(":")
    return getattr(importlib.import_module(mod), attr)


def _instance(obj: Any) -> Any:
    """Classes are instantiated with no args; functions/instances are used as-is."""
    return obj() if inspect.isclass(obj) else obj


def build_stack(version: str | Version, components: dict | None = None, strict: bool = False) -> Stack:
    """Fresh service + guards for one episode (episodes never share memory)."""
    v = version if isinstance(version, Version) else resolve_version(version)
    comps = {**DEFAULT_COMPONENTS, **(components or {})}
    active: list[str] = []
    missing: list[str] = []

    def get(key: str, path: str | None) -> Any:
        try:
            obj = _instance(_load(path))
        except (ImportError, AttributeError) as e:
            if strict:
                raise MissingComponent(f"{v.name}: {key} ({path}) unavailable: {e}") from e
            missing.append(key)
            return None
        active.append(key)
        return obj

    checks = []
    if v.write_checks:
        for name, path in comps["checks"].items():
            if (c := get(f"checks.{name}", path)) is not None:
                checks.append(c)
    if v.registry and v.write_checks and (c := get("registry_check", comps["registry_check"])) is not None:
        checks.append(c)

    service = None
    if v.provenance:
        try:
            cls = _load(comps["service"])
        except (ImportError, AttributeError) as e:
            if strict:
                raise MissingComponent(f"{v.name}: service unavailable: {e}") from e
            missing.append("service")
        else:
            accepts_checks = "checks" in inspect.signature(cls).parameters
            service = cls(checks=checks) if accepts_checks else cls()
            active.append("service")
    if service is None:
        service = _instance(_load(comps["baseline_service"]))

    screen = get("input_screen", comps["input_screen"]) if v.input_screen else None
    gate = get("action_gate", comps["action_gate"]) if v.action_gate else None
    binder = get("registry_binder", comps["registry_binder"]) if v.registry and v.action_gate else None
    if v.access_control:
        get("access_control", comps["access_control"])  # enforced inside the service; recorded for the manifest

    manifest = {"version": v.name, "service": type(service).__name__, "checks": [type(c).__name__ for c in checks],
                "active": active, "missing": missing, "degraded": bool(missing)}
    return Stack(service, screen, gate, binder, manifest)
