"""memledger.guards: input screen (step 1) and write checks (steps 2-4), slides 11-13. Owner: M2.

Default paths used by the eval runner (eval/versions.py):
    guards.screen:InputScreen  guards.hallucination:HallucinationCheck  guards.memshield:MemshieldCheck
    guards.contradiction:ContradictionCheck  guards.registry_match:RegistryCheck
Checks that need the memory service (contradiction: similar memories; registry: flag the bad source) and the
policy objects (gate, access control) get it through attach(memory); attach_all() does it for a list.
"""

from __future__ import annotations

from collections.abc import Iterable


def attach_all(components: Iterable[object], memory: object) -> None:
    for c in components:
        if hasattr(c, "attach"):
            c.attach(memory)
