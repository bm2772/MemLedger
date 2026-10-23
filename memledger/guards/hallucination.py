"""Step 2: hallucination check (slides 11, 13). A memory is hallucinated when its own sources do not support it.

The proposal is split into single facts; each is scored by a grounding model (MiniCheck or AlignScore; injectable)
against the text of the sources the model was shown, all sources together so multi-source conclusions can pass.
Long source text is checked in overlapping chunks and the best chunk counts. Flagged sources support nothing.
Verdict.score = the weakest fact's support, which the service uses as s in T = s * min parent trust (slide 7).
"""

from __future__ import annotations

from memledger.core.types import Source, Verdict, WriteProposal
from memledger.guards.models import PairScorer, default_support_scorer
from memledger.guards.text import chunks, split_facts


class HallucinationCheck:
    name = "hallucination"

    def __init__(self, scorer: PairScorer | None = None, threshold: float = 0.5, chunk_words: int = 350,
                 allow_unsupported: bool = False) -> None:
        self.scorer = scorer or default_support_scorer()
        self.threshold = threshold
        self.chunk_words = chunk_words
        self.allow_unsupported = allow_unsupported  # keep source-less memories as low-trust model knowledge

    def score_fact(self, fact: str, docs: list[str]) -> float:
        return max((float(self.scorer(d, fact)) for d in docs), default=0.0)

    def check(self, proposal: WriteProposal, sources: list[Source]) -> Verdict:
        facts = split_facts(proposal.text)
        if not facts:
            return Verdict(False, 0.0, "empty proposal", self.name)
        usable = [s for s in sources if not s.flagged and s.content.strip()]
        if not usable:
            if self.allow_unsupported:
                return Verdict(True, 0.0, "no sources: kept as model knowledge with zero support", self.name)
            return Verdict(False, 0.0, "no unflagged sources to support it", self.name)
        docs = chunks("\n\n".join(s.content for s in usable), self.chunk_words, self.chunk_words // 4)
        scored = [(f, self.score_fact(f, docs)) for f in facts]
        worst = min(s for _, s in scored)
        failing = [(f, s) for f, s in scored if s < self.threshold]
        if failing:
            detail = "; ".join(f"{f[:80]!r} ({s:.2f})" for f, s in failing)
            return Verdict(False, worst, f"unsupported by its sources: {detail}", self.name)
        return Verdict(True, worst, f"{len(facts)} fact(s) supported (min {worst:.2f})", self.name)
