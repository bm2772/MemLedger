"""Small text utilities shared by the guards, plus the cheap lexical backends (no model).

The lexical backends are a transparent fallback for laptops and CI ($MEMLEDGER_GUARD_BACKEND=lexical). They are
weaker than the models on slides 13 and 16 and are reported as their own backend, never as MiniCheck or DeBERTa.
"""

from __future__ import annotations

import re
import unicodedata

STOPWORDS = frozenset({
    "a", "an", "the", "of", "to", "in", "on", "at", "by", "for", "from", "with", "and", "or", "but", "is",
    "are", "was", "were", "be", "been", "being", "it", "its", "this", "that", "these", "those", "as", "has",
    "have", "had", "do", "does", "did", "so", "than", "then", "there", "here", "which", "who", "whom",
    "whose", "what", "when", "where", "why", "how", "not", "no", "nor", "into", "onto", "about", "over",
    "under", "after", "before", "also", "just", "very", "can", "could", "should", "would", "may", "might",
    "will", "shall", "must", "our", "your", "their", "his", "her", "we", "you", "they", "he", "she", "i",
    "me", "my", "us", "them", "s"
})
NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "isn't",
                       "aren't", "wasn't", "weren't", "doesn't", "don't", "didn't", "won't", "hasn't", "haven't"})

_WORD = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")
_NUMBER = re.compile(r"\d[\d,.\-/ ]*\d|\d")
_SENT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9\"'(])|\n\s*[-*•]\s+|\n{2,}|;\s+")


def normalise(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def words(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(normalise(text).lower()):
        w = re.sub(r"['’]s$", "", w)  # possessive: "acme's" -> "acme"
        out.append(w)
    return out


def _stem(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def content_words(text: str) -> set[str]:
    return {_stem(w) for w in words(text) if w not in STOPWORDS and w not in NEGATIONS}


def numbers(text: str) -> set[str]:
    return {re.sub(r"[,\- ]", "", n) for n in _NUMBER.findall(normalise(text))}


def has_negation(text: str) -> bool:
    return any(w in NEGATIONS for w in normalise(text).lower().split())


def split_facts(text: str) -> list[str]:
    """Split a proposed memory into single facts: sentences, semicolon clauses and bullet items."""
    parts = _SENT.split(normalise(text).strip())
    return [p.strip(" \t-*•") for p in parts if p and p.strip(" \t-*•.") and content_words(p)]


def chunks(text: str, size: int, overlap: int) -> list[str]:
    """Word windows of `size` words, overlapping by `overlap` (long sources are checked in chunks, slide 13)."""
    ws = text.split()
    if len(ws) <= size:
        return [text]
    step = max(1, size - overlap)
    return [" ".join(ws[i:i + size]) for i in range(0, len(ws) - overlap, step)]


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


# ---- lexical backends -------------------------------------------------------------------------------------------
def lexical_support(document: str, claim: str) -> float:
    """P(document supports claim), approximated: every number must appear; then share of content words covered."""
    need = content_words(claim)
    if not need:
        return 1.0
    if not numbers(claim) <= numbers(document):
        return 0.0
    if has_negation(claim) != has_negation(document) and has_negation(claim):
        return 0.0
    have = content_words(document)
    return len(need & have) / len(need)


def lexical_nli(premise: str, hypothesis: str) -> dict[str, float]:
    """Crude NLI: same topic with different numbers or flipped negation = contradiction."""
    p, h = content_words(premise), content_words(hypothesis)
    pn, hn = numbers(premise), numbers(hypothesis)
    topic = jaccard(p - pn, h - hn)
    if topic >= 0.5 and pn and hn and pn != hn and not (hn <= pn):
        return {"contradiction": 0.9, "neutral": 0.05, "entailment": 0.05}
    if topic >= 0.6 and has_negation(premise) != has_negation(hypothesis):
        return {"contradiction": 0.8, "neutral": 0.1, "entailment": 0.1}
    support = lexical_support(premise, hypothesis)
    if support >= 0.9:
        return {"contradiction": 0.02, "neutral": 0.08, "entailment": 0.9}
    return {"contradiction": 0.05, "neutral": 0.9, "entailment": 0.05}
