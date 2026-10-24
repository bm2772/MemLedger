"""In-memory stand-in for MemoryService so M2-M4 can build before M1's real service lands.

Behaves like the plain-RAG baseline: no checks, keyword-overlap retrieval, team scoping only
(`scoped=False`: no scoping at all, a global store).
"""

from __future__ import annotations

import hashlib
import itertools

from memledger.core.types import (
    Claim,
    Labels,
    RetrievedMemory,
    Session,
    Source,
    SourceKind,
    WriteProposal,
    WriteResult,
)

PRIORS = {
    SourceKind.REGISTRY: 0.95,
    SourceKind.PAPER: 0.95,
    SourceKind.INTERNAL: 0.9,
    SourceKind.USER: 0.7,
    SourceKind.TOOL: 0.8,
    SourceKind.WEB: 0.3,
    SourceKind.AGENT: 0.5,
    SourceKind.MODEL_PARAMETRIC: 0.2,
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class MockMemoryService:
    def __init__(self, scoped: bool = True) -> None:
        self.scoped = scoped  # False = plain RAG over one global store (the eval baseline)
        self._ids = itertools.count(1)
        self.sources: dict[str, Source] = {}
        self.claims: dict[str, Claim] = {}

    def _id(self, prefix: str) -> str:
        return f"{prefix}{next(self._ids)}"

    def ingest(self, content: str, kind: SourceKind, session: Session) -> Source:
        src = Source(self._id("s"), kind, content, Labels(session.team), PRIORS[kind], sha(content))
        self.sources[src.id] = src
        return src

    def propose_write(self, proposal: WriteProposal) -> WriteResult:
        claim = Claim(self._id("c"), proposal.text, Labels(proposal.session.team), trust=0.5,
                      content_hash=sha(proposal.text))
        self.claims[claim.id] = claim
        return WriteResult(True, [claim.id], [])

    def retrieve(self, query: str, session: Session, k: int = 8) -> list[RetrievedMemory]:
        words = set(query.lower().split())
        hits = []
        for c in self.claims.values():
            if self.scoped and c.labels.team not in (session.team, "shared"):
                continue
            overlap = len(words & set(c.text.lower().split()))
            if overlap:
                hits.append(RetrievedMemory(c, [], float(overlap)))
        return sorted(hits, key=lambda h: -h.relevance)[:k]

    def flag_source(self, source_id: str, reason: str) -> dict[str, list[str]]:
        if source_id in self.sources:
            self.sources[source_id].flagged = True
        return {"quarantined": [], "restored": []}

    def explain(self, claim_id: str) -> dict:
        return {"claim": claim_id, "lineage": []}
