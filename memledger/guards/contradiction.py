"""Step 4: contradiction check (slides 7, 11, 13). Uses a DeBERTa-v3 MNLI cross-encoder (injectable).

The proposal is compared with the k most similar existing memories of the same team (via the MemoryService, so
access rules apply). For each pair the NLI model gives P(contradiction), taken in both directions.
- If the old memory's validity interval has ended (valid_to set and passed), the intervals do not overlap: the new
  fact is an update, not a conflict.
- A real conflict is settled by trust: if the existing memory is more trusted than the proposal can be (its weakest
  unflagged source), the proposal is rejected; otherwise it is accepted and the conflict is reported in
  `last_conflicts` so the service can record it (LedgerService.record_contradiction) and mark the loser contested.
Nothing is deleted here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from memledger.core.types import Claim, Session, Source, Status, Verdict, WriteProposal, now
from memledger.guards.models import NLIModel, default_nli

Neighbours = Callable[[str, Session, int], list[Claim]]
AGENT_PRIOR = 0.5  # trust of a write with no sources (core/mock.py PRIORS[AGENT])


@dataclass(frozen=True)
class Conflict:
    claim_id: str
    text: str
    contradiction: float
    is_update: bool
    existing_trust: float


class ContradictionCheck:
    name = "contradiction"

    def __init__(self, nli: NLIModel | None = None, neighbours: Neighbours | None = None, k: int = 5,
                 threshold: float = 0.5) -> None:
        self.nli = nli or default_nli()
        self.neighbours = neighbours
        self.k = k
        self.threshold = threshold
        self.last_conflicts: list[Conflict] = []

    def attach(self, memory: object) -> ContradictionCheck:
        def neighbours(q: str, s: Session, k: int) -> list[Claim]:
            return [m.claim for m in memory.retrieve(q, s, k)]  # type: ignore[attr-defined]
        self.neighbours = neighbours
        return self

    def p_contradiction(self, a: str, b: str) -> float:
        return max(float(self.nli(a, b).get("contradiction", 0.0)), float(self.nli(b, a).get("contradiction", 0.0)))

    def conflicts(self, proposal: WriteProposal) -> list[Conflict]:
        if self.neighbours is None:
            raise RuntimeError("ContradictionCheck needs similar memories: call attach(memory) or pass neighbours")
        key, t, out = proposal.text.strip().lower(), now(), []
        for c in self.neighbours(proposal.text, proposal.session, self.k):
            if c.status in (Status.QUARANTINED, Status.SUPERSEDED) or c.text.strip().lower() == key:
                continue
            p = self.p_contradiction(c.text, proposal.text)
            if p >= self.threshold:
                ended = c.valid_to is not None and c.valid_to <= t
                out.append(Conflict(c.id, c.text, p, ended, c.trust))
        return out

    def check(self, proposal: WriteProposal, sources: list[Source]) -> Verdict:
        found = self.conflicts(proposal)
        self.last_conflicts = found
        usable = [s.prior_trust for s in sources if not s.flagged]
        ceiling = min(usable) if usable else AGENT_PRIOR  # T = s * min parent trust <= min parent trust
        real = [c for c in found if not c.is_update]
        stronger = [c for c in real if c.existing_trust > ceiling]
        if stronger:
            worst = max(stronger, key=lambda c: c.contradiction)
            return Verdict(False, 1.0 - worst.contradiction,
                           f"contradicts higher-trust memory {worst.claim_id} "
                           f"(trust {worst.existing_trust:.2f} > at most {ceiling:.2f})", self.name)
        parts = []
        if real:
            parts.append(f"conflicts with lower-trust {', '.join(c.claim_id for c in real)}")
        if updates := [c for c in found if c.is_update]:
            parts.append(f"update of {', '.join(c.claim_id for c in updates)}")
        return Verdict(True, 1.0, "; ".join(parts) or "no contradiction", self.name)
