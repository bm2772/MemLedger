"""Slide 7: JTMS trust. Plain code, no model.

A claim holds if at least one derivation (justification) is valid. Each derivation has trust
s * min(parent trust); derivations that share an origin source are one group (max, never
noisy-OR'd, so repeating one web page ten times adds nothing); independent groups combine by
noisy-OR: T = 1 - prod(1 - group value).

Exposure: a claim that saw a flagged source (in exposed_to) without resting on it (in no supported_by) may still
have been steered by it, so it is CONTESTED (reason "exposure: ...", trust unchanged) rather than quarantined; so is a
claim whose every valid justification rests on an exposure-contested claim. One clean justification keeps it active.
Validity is well-founded: support that loops back to the claim itself does not count. It is computed as a least
fixed point (the standard JTMS labelling, polynomial; review of #17), not by walking every path.
It is restored when the cause goes (source unflagged, parent cleared), like a JTMS-quarantined claim.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from memledger.core.mock import PRIORS
from memledger.core.types import Derivation, SourceKind, Status
from memledger.store.sqlite import SQLiteStore

EPS = 1e-9
EXPOSURE = "exposure: "  # status reason prefix of exposure-contested claims (vs. contradiction-contested)


class TrustEngine:
    def __init__(self, store: SQLiteStore, priors: dict[SourceKind, float] = PRIORS) -> None:
        self.store = store
        self.priors = priors
        self._lab: _Labels | None = None

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
        """Well-founded support (Doyle's JTMS): no flagged source, and every parent claim holds without leaning on d's
        own claim, directly or through other claims. So a memory re-stated from itself, or a loop m1 -> m2 -> m1,
        cannot keep itself up once its real source is gone (review of #17)."""
        with self._labelling() as lab:
            return lab.valid(d)

    @contextmanager
    def _labelling(self) -> Iterator[_Labels]:
        """One well-founded labelling shared by everything inside a recompute / claim_trust call (re-entrant). Only
        the derivation graph, source flags and integrity quarantines go into it, and none of them change inside."""
        outer = self._lab is None
        if outer:
            self._lab = _Labels(self)
        try:
            yield self._lab
        finally:
            if outer:
                self._lab = None

    def derivation_trust(self, d: Derivation) -> float:
        trusts = [t for p in d.supported_by if (t := self._parent_trust(p)) is not None]
        if not trusts:
            return self.priors[SourceKind.AGENT]
        return min(d.supported_by.values()) * min(trusts)

    def origins(self, d: Derivation, _seen: frozenset[str] = frozenset()) -> set[str]:
        """The sources d rests on, through valid derivations of its parent claims (never back through `_seen`).
        One walk with a visited set: the set of reachable sources does not depend on the path, so this equals the
        union over all paths without enumerating them (that was exponential in deep memory chains; review of #17)."""
        with self._labelling() as lab:
            out: set[str] = set()
            visited, todo = set(_seen), [d]
            while todo:
                for pid in todo.pop().supported_by:
                    kind = lab.kind(pid)
                    if kind == "source":
                        out.add(pid)
                    elif kind == "claim" and pid not in visited:
                        visited.add(pid)
                        todo += [pd for pd in lab.ders(pid) if lab.valid(pd)]
            return out

    def claim_origins(self, claim_id: str) -> set[str]:
        with self._labelling():
            return self._claim_origins(claim_id)

    def _claim_origins(self, claim_id: str) -> set[str]:
        out: set[str] = set()
        for d in self.store.derivations_for(claim_id):
            if self.is_valid(d):
                out |= self.origins(d, frozenset({claim_id}))
        return out

    # ---- claim trust
    def claim_trust(self, claim_id: str) -> float | None:
        with self._labelling():
            return self._claim_trust(claim_id)

    def _claim_trust(self, claim_id: str) -> float | None:
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

    def _exposure(self, d: Derivation, supporters: set[str]) -> str | None:
        """Why a (valid) derivation is exposed: a flagged source it saw that supported none of the claim's facts
        (`supporters` = every derivation's parents; a supporter that is flagged just invalidates its own derivation,
        slide 6 D1), or an exposure-contested parent claim. None when clean."""
        for pid in d.exposed_to:
            if pid not in supporters and (s := self.store.get_source(pid)) is not None and s.flagged:
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
        ders = self.store.derivations_for(claim_id)
        supporters = {pid for d in ders for pid in d.supported_by}
        why = [self._exposure(d, supporters) for d in ders if self.is_valid(d)]
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
        with self._labelling():
            return self._recompute(claim_ids)

    def _recompute(self, claim_ids: list[str] | None) -> dict[str, list[str]]:
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


class _Labels:
    """Well-founded support as least fixed points (Doyle's JTMS labelling), computed over the ancestors of what is asked.

    A claim is grounded if it has a derivation whose sources are unflagged and whose parent claims are grounded. The
    labelling starts with nothing grounded and adds claims until nothing changes, so nothing on a loop can enter first
    (loops never ground themselves); integrity-quarantined claims never enter. A derivation of C is valid if its
    parents are grounded *without C* (C cannot feed its own trust); that second labelling runs only when C is among
    the parents' ancestors. Each fixed point covers only the ancestors of the claims asked about, and answers are
    cached for the scope, so the cost is polynomial (derivations x passes) and local to the part of the graph used.
    """

    def __init__(self, engine: TrustEngine) -> None:
        self.engine, self.store = engine, engine.store
        self._ders: dict[str, list[Derivation]] = {}
        self._kind: dict[str, str | None] = {}  # id -> "source" | "claim" | None (unknown)
        self._flagged: dict[str, bool] = {}
        self._excluded: dict[str, bool] = {}
        self._known: dict[str | None, dict[str, bool]] = {}  # without -> claim id -> grounded

    def ders(self, cid: str) -> list[Derivation]:
        if cid not in self._ders:
            self._ders[cid] = self.store.derivations_for(cid)
        return self._ders[cid]

    def kind(self, pid: str) -> str | None:
        if pid not in self._kind:
            s = self.store.get_source(pid)
            if s is not None:
                self._kind[pid], self._flagged[pid] = "source", s.flagged
            else:
                self._kind[pid] = "claim" if self.store.get_claim(pid) is not None else None
        return self._kind[pid]

    def excluded(self, cid: str) -> bool:
        if cid not in self._excluded:
            c = self.store.get_claim(cid)
            self._excluded[cid] = c.status == Status.QUARANTINED and not self.engine._jtms_quarantined(cid)
        return self._excluded[cid]

    def ancestors(self, roots: list[str]) -> set[str]:
        """The claims among roots and everything their derivations rest on, transitively."""
        seen, todo = set(roots), list(roots)
        while todo:
            for d in self.ders(todo.pop()):
                for pid in d.supported_by:
                    if pid not in seen and self.kind(pid) == "claim":
                        seen.add(pid)
                        todo.append(pid)
        return seen

    def _parents_in(self, d: Derivation, good: set[str]) -> bool:
        for pid in d.supported_by:
            k = self.kind(pid)
            if (k == "source" and self._flagged[pid]) or (k == "claim" and pid not in good):
                return False
        return True  # unknown ids are ignored, as before

    def grounded(self, cid: str, without: str | None = None) -> bool:
        known = self._known.setdefault(without, {})
        if cid not in known:
            todo = [c for c in self.ancestors([cid]) if c not in known]
            good = {c for c, g in known.items() if g}
            changed = True
            while changed:
                changed = False
                for c in todo:
                    if c not in good and c != without and not self.excluded(c) and \
                            any(self._parents_in(d, good) for d in self.ders(c)):
                        good.add(c)
                        changed = True
            known.update({c: c in good for c in todo})
        return known[cid]

    def valid(self, d: Derivation) -> bool:
        claims = []
        for pid in d.supported_by:
            k = self.kind(pid)
            if k == "source" and self._flagged[pid]:
                return False
            if k == "claim":
                claims.append(pid)
        if not all(self.grounded(p) for p in claims):
            return False
        if d.claim_id not in self.ancestors(claims):
            return True
        return all(self.grounded(p, without=d.claim_id) for p in claims)
