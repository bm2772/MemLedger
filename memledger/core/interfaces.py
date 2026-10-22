"""Frozen interfaces between the four areas. Change only via a PR approved by M1."""

from __future__ import annotations

from typing import Protocol

from memledger.core.types import (
    RetrievedMemory,
    Session,
    Source,
    SourceKind,
    Verdict,
    WriteProposal,
    WriteResult,
)


class MemoryService(Protocol):
    """The only path to memory (slide 10). Owner: M1."""

    def ingest(self, content: str, kind: SourceKind, session: Session) -> Source: ...

    def propose_write(self, proposal: WriteProposal) -> WriteResult: ...

    def retrieve(self, query: str, session: Session, k: int = 8) -> list[RetrievedMemory]: ...

    def flag_source(self, source_id: str, reason: str) -> dict[str, list[str]]:
        """Returns {'quarantined': [...], 'restored': [...]} (JTMS retraction)."""
        ...

    def explain(self, claim_id: str) -> dict: ...


class Check(Protocol):
    """A guardrail check (slides 12-13). Owner: M2."""

    name: str

    def check(self, proposal: WriteProposal, sources: list[Source]) -> Verdict: ...


class InputScreen(Protocol):
    """Step 1 screening (slide 12). Owner: M2."""

    def score(self, text: str) -> float: ...


class ActionGate(Protocol):
    """Step 8 (slide 9). Owner: M2."""

    def allow(self, tool: str, params: dict, context_claim_ids: list[str], session: Session) -> Verdict: ...
