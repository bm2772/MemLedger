"""Build a LedgerService for one of the five evaluated versions (docs/interfaces.md, slide 17).

    baseline          no checks, screen, access control or gate (plain retrieval, no provenance-based filtering)
    provenance        LedgerService with trust and hash chain, no guards
    write_checks      + input screen, hallucination, memshield, contradiction, registry match
    full              + access control and action gate
    full_no_registry  full without registry match (the gate keeps no registry either, so nothing is bound)

The flags mirror eval/versions.py (a test keeps them in sync). `fakes` replaces the models behind the guards so
tests and smoke runs need no downloads: scorer, nli, memshield, injection (callables), registry, store, index,
on_timing. Defaults are the code-only lexical fallbacks from guards/text.py.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from memledger.core.service import LedgerService

# name -> (write_checks, input_screen, access_control, action_gate, registry)
FLAGS: dict[str, tuple[bool, bool, bool, bool, bool]] = {
    "baseline": (False, False, False, False, False),
    "provenance": (False, False, False, False, False),
    "write_checks": (True, True, False, False, False),
    "full": (True, True, True, True, True),
    "full_no_registry": (True, True, True, True, False),
}


def build_service(version: str, *, registry: Any | None = None, on_timing: Callable[[str, float], None] | None = None,
                  screen_threshold: float = 0.5, **fakes: Any) -> LedgerService:
    key = version.lstrip("+")
    if key not in FLAGS:
        raise KeyError(f"unknown version {version!r}; choose from {list(FLAGS)}")
    checks_on, screen_on, access_on, gate_on, registry_on = FLAGS[key]
    # guards are imported lazily so baseline/provenance never need them
    from memledger.guards import attach_all
    from memledger.guards.contradiction import ContradictionCheck
    from memledger.guards.hallucination import HallucinationCheck
    from memledger.guards.input_screen import InputScreen
    from memledger.guards.memshield import MemshieldCheck, lexical_memshield
    from memledger.guards.registry_match import RegistryCheck
    from memledger.guards.text import lexical_nli, lexical_support
    from memledger.policy.access import AccessControl
    from memledger.policy.gate import ActionGate

    checks: list[Any] = []
    if checks_on:
        checks += [HallucinationCheck(scorer=fakes.get("scorer", lexical_support)),
                   MemshieldCheck(classifier=fakes.get("memshield", lexical_memshield)),
                   ContradictionCheck(nli=fakes.get("nli", lexical_nli))]
        if registry_on:
            checks.append(RegistryCheck(registry))
    access = AccessControl() if access_on else None
    gate = ActionGate(registry=registry if registry_on else None, access=access) if gate_on else None
    screen = InputScreen(classifier=fakes.get("injection")) if screen_on else None
    svc = LedgerService(store=fakes.get("store"), index=fakes.get("index"), checks=checks, input_screen=screen,
                        screen_threshold=screen_threshold, access=access, gate=gate, on_timing=on_timing,
                        version=key)
    attach_all([*svc.checks, *([gate] if gate else [])], svc)
    return svc
