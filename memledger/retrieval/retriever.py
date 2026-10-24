"""Slide 15: two-stage retrieval. Stage 1 gathers candidates over four routes; stage 2 filters by trust."""

from __future__ import annotations

from memledger.core.trust import TrustEngine
from memledger.core.types import RetrievedMemory, Session, Status, now
from memledger.store.index import VectorIndex
from memledger.store.sqlite import SQLiteStore


class Retriever:
    def __init__(self, store: SQLiteStore, index: VectorIndex, trust_threshold: float = 0.0) -> None:
        self.store = store
        self.index = index
        self.trust_threshold = trust_threshold
        self.engine = TrustEngine(store)
        self.last_routes: dict[str, set[str]] = {}  # claim id -> routes that made it a candidate (tests, attacks/)

    def _candidates(self, query: str, teams: list[str], k: int) -> dict[str, float]:
        rel: dict[str, float] = {}
        routes: dict[str, set[str]] = {}
        self.last_routes = routes

        def bump(cid: str, r: float, route: str) -> None:
            routes.setdefault(cid, set()).add(route)
            if r > rel.get(cid, -1.0):
                rel[cid] = r

        for cid, score in self.index.query(teams, query, k * 3):
            bump(cid, score, "index")
        kw = self.store.keyword_search(teams, query, k * 3)
        top = max((s for _, s in kw), default=0.0)
        for cid, score in kw:
            bump(cid, score / top if top > 0 else 1.0, "keyword")
        q = query.lower()
        for subject in self.store.triple_subjects():
            if subject and subject in q:
                for cid in self.store.lookup_triples(subject):
                    bump(cid, 1.0, "triple")
        # one hop: parents, children (x0.5) and newer versions (x0.9) of stage-1 claims
        for cid, r in list(rel.items()):
            for e in self.store.edges(dst=cid, type="supported_by"):
                bump(e["src"], r * 0.5, "graph")
            for e in self.store.edges(src=cid, type="supported_by"):
                bump(e["dst"], r * 0.5, "graph")
            for e in self.store.edges(dst=cid, type="supersedes"):
                bump(e["src"], r * 0.9, "graph")
        return rel

    def search(self, query: str, session: Session, k: int = 8, scoped: bool = True) -> list[RetrievedMemory]:
        """scoped=False is the plain-RAG baseline: one global index, every team's claims are candidates."""
        teams = [session.team, "shared"] if scoped else self.store.teams()
        t_now = now()
        out = []
        for cid, r in self._candidates(query, teams, k).items():
            claim = self.store.get_claim(cid)  # parents may be sources: get_claim is None, skipped
            if claim is None or claim.labels.team not in teams:
                continue
            if claim.status in (Status.QUARANTINED, Status.SUPERSEDED):
                continue
            if claim.valid_to is not None and claim.valid_to < t_now:
                continue
            if claim.trust < self.trust_threshold:
                continue
            out.append((r, claim))
        out.sort(key=lambda x: (-x[0], -x[1].trust))
        return [RetrievedMemory(c, sorted(self.engine.claim_origins(c.id)), r) for r, c in out[:k]]
