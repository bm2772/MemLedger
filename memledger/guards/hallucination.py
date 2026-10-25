"""Step 2: hallucination check (slides 11, 13). A memory is hallucinated when its own sources do not support it.

The proposal is split into single facts; each is scored by a grounding model (MiniCheck or AlignScore; injectable)
against the text of the sources the model was shown, all sources together so multi-source conclusions can pass.
Long source text is checked in overlapping chunks and the best chunk counts. Flagged sources support nothing.
A proposal or fact that appears in its sources as whole sentence(s) or whole line(s) (whitespace-normalised, e.g. a
copied code snippet) scores 1.0 without the model: MiniCheck rejected an identical code snippet in the stress test.
A clause inside a longer sentence does not count ("It is false that X", "Scammers claim X" do not support X; nor
does "98" inside "9876"): those go to the model. Verdict.score = the weakest fact's support, which the service uses
as s in T = s * min parent trust (slide 7).
"""

from __future__ import annotations

import re

from memledger.core.types import Source, Verdict, WriteProposal
from memledger.guards.models import PairScorer, default_support_scorer
from memledger.guards.text import chunks, normalise, split_facts

_START = r"(?:\A|(?<=\n)|(?<=[.!?;:] ))"  # text or line start, or right after a sentence end / label colon
_END = r"[.!?;]?(?=\n|\Z)|[.!?;](?= )"  # line or text end, or a sentence end


def _verbatim(needle: str, haystack: str) -> bool:
    """needle occurs in haystack as whole sentence(s) or whole line(s), across line breaks (both via _squash)."""
    tokens = needle.rstrip(".!?;").split()
    if not tokens:
        return False
    body = r"[ \n]".join(re.escape(t) for t in tokens)
    return re.search(_START + body + r"(?:" + _END + r")", haystack) is not None


def _squash(text: str) -> str:
    """Lower-cased, NFKC, whitespace collapsed within lines; line breaks kept (they bound sentences and code lines)."""
    lines = (" ".join(line.split()) for line in normalise(text).lower().splitlines())
    return "\n".join(line for line in lines if line)


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
        full = _squash("\n".join(s.content for s in usable))
        if _verbatim(_squash(proposal.text), full):
            return Verdict(True, 1.0, "copied verbatim from its sources", self.name)
        scored = [(f, 1.0 if _verbatim(_squash(f), full) else self.score_fact(f, docs)) for f in facts]
        worst = min(s for _, s in scored)
        failing = [(f, s) for f, s in scored if s < self.threshold]
        if failing:
            detail = "; ".join(f"{f[:80]!r} ({s:.2f})" for f, s in failing)
            return Verdict(False, worst, f"unsupported by its sources: {detail}", self.name)
        return Verdict(True, worst, f"{len(facts)} fact(s) supported (min {worst:.2f})", self.name)
