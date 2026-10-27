"""Registry-bound tool parameters (slides 5, 9; property I10).

High-risk tools take protected parameters from the registry, never from model text: send_payment(vendor) gets the
vendor's account from the registry whatever account the model asked for. Binding never raises; when no registry
value exists the parameter is set to None, which the ActionGate refuses (fail closed).

The default registry is the one installed with set_default_registry() (eval runner: one per episode), else the
files named by $MEMLEDGER_REGISTRY and $MEMLEDGER_REGISTRY_PUBKEY.
"""

from __future__ import annotations

import os

from memledger.core.types import Session
from memledger.registry.registry import Registry

# tool -> protected param -> (param that names the registry subject, registry field)
BINDINGS: dict[str, dict[str, tuple[str, str]]] = {
    "send_payment": {"account": ("vendor", "account")},
}

_default: Registry | None = None


def set_default_registry(registry: Registry | None) -> None:
    global _default
    _default = registry


def default_registry() -> Registry | None:
    global _default
    if _default is None and (path := os.environ.get("MEMLEDGER_REGISTRY")):
        _default = Registry.load(path, os.environ["MEMLEDGER_REGISTRY_PUBKEY"])
    return _default


def protected_params(tool: str) -> dict[str, tuple[str, str]]:
    return BINDINGS.get(tool, {})


def registry_value(tool: str, param: str, params: dict, registry: Registry | None) -> str | None:
    """The registry value a protected parameter must have, or None if there is none."""
    subject_param, field = BINDINGS[tool][param]
    subject = params.get(subject_param)
    if registry is None or not isinstance(subject, str) or not subject:
        return None
    return registry.get(subject, field)


def bind_params(tool: str, params: dict, session: Session | None = None, registry: Registry | None = None) -> dict:
    """Returns a copy of params with every protected parameter replaced by its registry value (or None)."""
    reg = registry or default_registry()
    out = dict(params)
    for param in protected_params(tool):
        out[param] = registry_value(tool, param, params, reg)
    return out
