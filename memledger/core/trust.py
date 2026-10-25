"""Slide 7: JTMS trust. Plain code, no model.

A claim holds if at least one derivation (justification) is valid. Each derivation has trust
s * min(parent trust); derivations that share an origin source are one group (max, never
noisy-OR'd, so repeating one web page ten times adds nothing); independent groups combine by
noisy-OR: T = 1 - prod(1 - group value).

Exposure: a claim that saw a flagged source (in exposed_to) without resting on it (not in supported_by) may still
have been steered by it, so it is CONTESTED (reason "exposure: ...", trust unchanged) rather than quarantined; so is a
claim whose every valid justification rests on an exposure-contested claim. One clean justification keeps it active.
It is restored when the cause goes (source unflagged, parent cleared), like a JTMS-quarantined claim.
"""

from __future__ import annotations

from memledger.core.mock import PRIORS
from memledger.core.types import Derivation, SourceKind, Status
from memledger.store.sqlite import SQLiteStore

EPS = 1e-9
EXPOSURE = "exposure: "  # status reason prefix of exposure-contested claims (vs. contradiction-contested)


class TrustEngine:
    def __init__(self, store: SQLiteStore, priors: dict[SourceKind, float] = PRIORS) -> None:
        self.store = store
        self.priors = priors

    # ---- per-parent helpers
    def source_trust(self, source) -> float:
        return 0.0 if source.flagged else self.priors[source.kind]

    def _parent_trust(self, pid: str) -> float | None:
        """Trust of a parent, or None if it is unknown or invalidates the derivation."""
        if (s := self.store.get_source(pid)) is not None:
            return None if s.flagged else self.source_trust(s)
        if (c := self.store.get_claim(pid)) is not None:
            return None if c.status == Status.QUARANTINED else c.trust
        return None

    def _known(self, pid: str) -> bool:
        return self.store.get_source(pid) is not None or self.store.get_claim(pid) is not None

    def is_valid(self, d: Derivation) -> bool:
        return all(self._parent_trust(p) is not None for p in d.supported_by if self._known(p))

    def derivation_trust(self, d: Derivation) -> float:
        trusts = [t for p in d.supported_by if (t := self._parent_trust(p)) is not None]
        if not trusts:
            return self.priors[SourceKind.AGENT]
        return min(d.supported_by.values()) * min(trusts)

    def origins(self, d: Derivation, _seen: frozenset[str] = frozenset()) -> set[str]:
        out: set[str] = set()
        for pid in d.supported_by:
            if self.store.get_source(pid) is not None:
                out.add(pid)
            elif self.store.get_claim(pid) is not None and pid not in _seen:
                for pd in self.store.derivations_for(pid):
                    if self.is_valid(pd):
                        out |= self.origins(pd, _seen | {pid})
        return out

    def claim_origins(self, claim_id: str) -> set[str]:
        out: set[str] = set()
        for d in self.store.derivations_for(claim_id):
            if self.is_valid(d):
                out |= self.origins(d, frozenset({claim_id}))
        return out

    # ---- claim trust
    def claim_trust(self, claim_id: str) -> float | None:
        valid = [d for d in self.store.derivations_for(claim_id) if self.is_valid(d)]
        if not valid:
            return None
        parent = list(range(len(valid)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        orig = [self.origins(d, frozenset({claim_id})) for d in valid]
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                if orig[i] & orig[j]:
                    parent[find(i)] = find(j)
        best: dict[int, float] = {}
        for i, d in enumerate(valid):
            g = find(i)
            best[g] = max(best.get(g, 0.0), self.derivation_trust(d))
        miss = 1.0
        for v in best.values():
            miss *= 1.0 - v
        return 1.0 - miss

    # ---- recompute
    def _topo(self, claim_ids: list[str]) -> list[str]:
        order: list[str] = []
        done: set[str] = set()
        want = set(claim_ids)

        def visit(cid: str, stack: frozenset[str]) -> None:
            if cid in done or cid in stack:
                return
            for d in self.store.derivations_for(cid):
                for p in d.supported_by:
                    if p in want:
                        visit(p, stack | {cid})
            done.add(cid)
            order.append(cid)

        for cid in claim_ids:
            visit(cid, frozenset())
        return order

    def exposure_contested(self, claim_id: str) -> bool:
        """The claim's current CONTESTED status was set by exposure (not by a contradiction)."""
        for row in reversed(self.store.status_history(claim_id)):
            if row["reason"] == "jtms: trust recomputed":  # trust-only update, status carried over
                continue
            return row["status"] == Status.CONTESTED.value and row["reason"].startswith(EXPOSURE)
        return False

    def _exposure(self, d: Derivation) -> str | None:
        """Why a (valid) derivation is exposed: a flagged source it saw but does not rest on, or an exposure-contested
        parent claim. None when clean."""
        for pid in d.exposed_to:
            if pid not in d.supported_by and (s := self.store.get_source(pid)) is not None and s.flagged:
                return f"flagged source {pid}"
        for pid in d.supported_by:
            c = self.store.get_claim(pid)
            if c is not None and c.status == Status.CONTESTED and self.exposure_contested(pid):
                return f"rests on contested memory {pid}"
        return None

    def _update_exposure(self, claim_id: str, res: dict[str, list[str]]) -> None:
        claim = self.store.get_claim(claim_id)
        if claim is None or claim.status in (Status.QUARANTINED, Status.SUPERSEDED):
            return
        why = [self._exposure(d) for d in self.store.derivations_for(claim_id) if self.is_valid(d)]
        exposed = bool(why) and all(why)
        if exposed and claim.status in (Status.ACTIVE, Status.RESTORED):
            self.store.set_status(claim_id, Status.CONTESTED.value, EXPOSURE + str(why[0]), claim.trust)
            res["contested"].append(claim_id)
        elif not exposed and self.exposure_contested(claim_id):
            self.store.set_status(claim_id, Status.RESTORED.value, EXPOSURE + "cleared", claim.trust)
            res["restored"].append(claim_id)

    def _jtms_quarantined(self, claim_id: str) -> bool:
        for row in reversed(self.store.status_history(claim_id)):
            if row["status"] == Status.QUARANTINED.value:
                return row["reason"].startswith("jtms")
        return False

    def recompute(self, claim_ids: list[str] | None = None) -> dict[str, list[str]]:
        ids = claim_ids if claim_ids is not None else [c.id for c in self.store.list_claims()]
        res: dict[str, list[str]] = {"quarantined": [], "restored": [], "contested": [], "updated": []}
        for cid in self._topo(ids):
            claim = self.store.get_claim(cid)
            if claim is None:
                continue
            t = self.claim_trust(cid)
            quarantined = claim.status == Status.QUARANTINED
            if t is None:
                if not quarantined:
                    self.store.set_status(cid, Status.QUARANTINED.value, "jtms: no valid justification", 0.0)
                    res["quarantined"].append(cid)
            elif quarantined:
                if self._jtms_quarantined(cid):
                    self.store.set_status(cid, Status.RESTORED.value, "jtms: justification restored", t)
                    res["restored"].append(cid)
            elif abs(t - claim.trust) > EPS:
                self.store.set_status(cid, claim.status.value, "jtms: trust recomputed", t)
                res["updated"].append(cid)
            self._update_exposure(cid, res)  # in dependency order, so parents are settled first
        return res

    # ---- contradictions
    def contest(self, claim_a: str, claim_b: str, is_update: bool = False) -> None:
        a, b = self.store.get_claim(claim_a), self.store.get_claim(claim_b)
        if a is None or b is None:
            raise KeyError("unknown claim")
        if is_update:
            new, old = (a, b) if a.recorded_at >= b.recorded_at else (b, a)
            self.store.add_edge(new.id, old.id, "supersedes")
            self.store.set_status(old.id, Status.SUPERSEDED.value, f"superseded by {new.id}")
            return
        self.store.add_edge(a.id, b.id, "contradicts")
        if abs(a.trust - b.trust) <= EPS:
            return
        lo, hi = (a, b) if a.trust < b.trust else (b, a)
        self.store.set_status(lo.id, Status.CONTESTED.value, f"contradicted by higher-trust {hi.id}")
