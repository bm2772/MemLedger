"""Resolve context ids to their labels, trust and status, and decide integrity (slides 11, 12, 21).

Works with M1's LedgerService (memory.store.get_source / get_claim) and with MockMemoryService (.sources/.claims).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from memledger.core.types import Claim, Integrity, Labels, Source, SourceKind, Status

UNTRUSTED_KINDS = frozenset({SourceKind.WEB, SourceKind.MODEL_PARAMETRIC})
BAD_STATUS = frozenset({Status.QUARANTINED, Status.CONTESTED, Status.SUPERSEDED})


@dataclass(frozen=True)
class Item:
    id: str
    is_source: bool
    labels: Labels
    trust: float
    text: str
    kind: SourceKind | None = None  # sources only
    status: Status | None = None  # claims only
    flagged: bool = False

    @classmethod
    def of(cls, x: Source | Claim) -> Item:
        if isinstance(x, Source):
            return cls(x.id, True, x.labels, x.prior_trust, x.content, kind=x.kind, flagged=x.flagged)
        return cls(x.id, False, x.labels, x.trust, x.text, status=x.status)


Resolver = Callable[[str], Item | None]


def integrity_of(item: Item, untrusted_below: float = 0.4) -> Integrity:
    """Untrusted: web/model-parametric or flagged sources, quarantined/contested/superseded or low-trust claims,
    and anything labelled untrusted (e.g. mid-band screen). Trusted: registry sources or a TRUSTED label."""
    if item.labels.integrity == Integrity.UNTRUSTED or item.flagged:
        return Integrity.UNTRUSTED
    if item.is_source:
        if item.kind in UNTRUSTED_KINDS:
            return Integrity.UNTRUSTED
        if item.kind == SourceKind.REGISTRY:
            return Integrity.TRUSTED
        return item.labels.integrity
    if item.status in BAD_STATUS or item.trust < untrusted_below:
        return Integrity.UNTRUSTED
    return item.labels.integrity


def resolver(memory: object) -> Resolver:
    store = getattr(memory, "store", None)
    if store is not None and hasattr(store, "get_source") and hasattr(store, "get_claim"):
        def get(i: str) -> Source | Claim | None:
            return store.get_source(i) or store.get_claim(i)
    elif hasattr(memory, "sources") and hasattr(memory, "claims"):
        def get(i: str) -> Source | Claim | None:
            return memory.sources.get(i) or memory.claims.get(i)
    else:
        raise TypeError(f"cannot resolve ids on {type(memory).__name__}")

    def resolve(i: str) -> Item | None:
        x = get(i)
        return Item.of(x) if x is not None else None

    return resolve
