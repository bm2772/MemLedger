"""Step 2: hallucination check (slides 11, 13). A memory is hallucinated when its own sources do not support it.

The proposal is split into single facts; each is scored by a grounding model (MiniCheck or AlignScore; injectable)
against the text of the sources and parent memories the model was shown (a memory may be grounded on earlier
memories, slide 7), all together so multi-source conclusions can pass. Long text is checked in overlapping chunks and
the best chunk counts. Flagged sources and quarantined, contested or superseded memories ground nothing.
A proposal or fact that appears in its sources as whole sentence(s) or whole line(s) (whitespace-normalised, e.g. a
copied code snippet) scores 1.0 without the model: MiniCheck rejected an identical code snippet in the stress test.
A clause inside a longer sentence does not count ("It is false that X", "Scammers claim X" do not support X; nor
does "98" inside "9876"): those go to the model. Verdict.score = the weakest fact's support, which the service uses
as s in T = s * min parent trust (slide 7).

attribute() then says which context items support which fact of an accepted memory: a parent (source or memory)
supports a fact when it does so on its own (verbatim, or its best chunk reaches the threshold). A fact no single
parent supports passed on the parents together, so all of them support it (joint). The service records these as
supported_by, so retraction and trust follow the parents of the facts, not everything that was in the context.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from memledger.core.types import Claim, FactSupport, Source, Status, Verdict, WriteProposal
from memledger.guards.models import PairScorer, default_support_scorer
from memledger.guards.text import chunks, normalise, split_facts

GROUNDING = frozenset({Status.ACTIVE, Status.RESTORED})  # memories that may ground a new one

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
        self._memo: dict[tuple[str, str], float] = {}  # (document, fact) -> score, for the proposal being checked

    def _score(self, doc: str, fact: str) -> float:
        if (doc, fact) not in self._memo:  # attribute() re-scores the same pairs as check() for a single source
            self._memo[doc, fact] = float(self.scorer(doc, fact))
        return self._memo[doc, fact]

    def score_fact(self, fact: str, docs: list[str]) -> float:
        return max((self._score(d, fact) for d in docs), default=0.0)

    @staticmethod
    def _parents(sources: list[Source], claims: Sequence[Claim]) -> tuple[dict[str, str], dict[str, str]]:
        """({source id: text}, {memory id: text}) of the context items that may ground or support a memory."""
        return ({s.id: s.content for s in sources if not s.flagged and s.content.strip()},
                {c.id: c.text for c in claims if c.status in GROUNDING and c.text.strip()})

    def check(self, proposal: WriteProposal, sources: list[Source], claims: Sequence[Claim] = ()) -> Verdict:
        self._memo = {}
        facts = split_facts(proposal.text)
        if not facts:
            return Verdict(False, 0.0, "empty proposal", self.name)
        usable = [t for d in self._parents(sources, claims) for t in d.values()]
        if not usable:
            if self.allow_unsupported:
                return Verdict(True, 0.0, "no sources: kept as model knowledge with zero support", self.name)
            return Verdict(False, 0.0, "no unflagged sources or usable memories to support it", self.name)
        docs = chunks("\n\n".join(usable), self.chunk_words, self.chunk_words // 4)
        full = _squash("\n".join(usable))
        if _verbatim(_squash(proposal.text), full):
            return Verdict(True, 1.0, "copied verbatim from its sources", self.name)
        scored = [(f, 1.0 if _verbatim(_squash(f), full) else self.score_fact(f, docs)) for f in facts]
        worst = min(s for _, s in scored)
        failing = [(f, s) for f, s in scored if s < self.threshold]
        if failing:
            detail = "; ".join(f"{f[:80]!r} ({s:.2f})" for f, s in failing)
            return Verdict(False, worst, f"unsupported by its sources: {detail}", self.name)
        return Verdict(True, worst, f"{len(facts)} fact(s) supported (min {worst:.2f})", self.name)

    def attribute(self, proposal: WriteProposal, sources: list[Source],
                  claims: Sequence[Claim] = ()) -> list[FactSupport]:
        """Per fact of an accepted proposal, the parents that support it (see the module docstring). Flagged sources
        and quarantined, contested or superseded memories support nothing."""
        srcs, mems = self._parents(sources, claims)
        parents = {**srcs, **mems}
        squashed = {pid: _squash(text) for pid, text in parents.items()}
        out = []
        for fact in split_facts(proposal.text):
            sq = _squash(fact)
            scores = {pid: 1.0 if _verbatim(sq, squashed[pid]) else self.score_fact(
                fact, chunks(text, self.chunk_words, self.chunk_words // 4)) for pid, text in parents.items()}
            own = {pid: sc for pid, sc in scores.items() if sc >= self.threshold}
            joint = not own and bool(parents)
            out.append(FactSupport(fact, own or scores, joint))
        return out
