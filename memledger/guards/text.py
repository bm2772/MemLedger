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
        return {"contradiction": 0.9, "neutral": 0.05, "entailment": 0.05}
    support = lexical_support(premise, hypothesis)
    if support >= 0.9:
        return {"contradiction": 0.02, "neutral": 0.08, "entailment": 0.9}
    return {"contradiction": 0.05, "neutral": 0.9, "entailment": 0.05}


# ---- subjects (who/what a fact is about) ------------------------------------------------------------------------
_LABEL_PREFIX = re.compile(r"^\s*(?:[A-Z][\w ]{0,40}:\s+)+")  # "Note: ", "Vendor master record: "
_TOKEN = re.compile(r"[A-Za-z0-9][\w&\-]*(?:\.\d+)*(?:['’]s\b)?")
_CORP = frozenset({"ltd", "limited", "inc", "llc", "corp", "corporation", "plc", "co", "gmbh", "pvt", "company"})


def _is_name(tok: str) -> bool:
    return tok[:1].isupper() and tok.lower() not in STOPWORDS


def proper_nouns(text: str) -> set[str]:
    """Capitalised words (names, codenames, vendors), lower-cased, possessives and corporate suffixes dropped."""
    out = set()
    for tok in _TOKEN.findall(_LABEL_PREFIX.sub("", normalise(text))):
        w = re.sub(r"['’]s$", "", tok)
        if _is_name(w) and w.lower() not in _CORP:
            out.add(w.lower())
    return out


def subject_key(text: str) -> str | None:
    """The first named phrase of a fact, e.g. 'Project Vorliooru measured ...' -> 'project vorliooru',
    "Note: Acme Ltd's account ..." -> 'acme'. None if the fact names nothing."""
    toks = _TOKEN.findall(_LABEL_PREFIX.sub("", normalise(text)))
    start = next((i for i, t in enumerate(toks) if _is_name(t)), None)
    if start is None:
        return None
    phrase = []
    for t in toks[start:]:
        possessive = bool(re.search(r"['’]s$", t))
        w = re.sub(r"['’]s$", "", t)
        if not (_is_name(w) or (phrase and (w.isdigit() or (len(w) == 1 and w.isupper())))):  # Server A, Ticket 42
            break
        phrase.append(w.lower())
        if possessive:
            break
    words_ = [w for w in phrase if w not in _CORP] or phrase
    return " ".join(words_)


def same_subject(a: str, b: str, min_overlap: float = 0.5) -> bool:
    """True if two facts are about the same subject: equal (or nested) subject keys; without a key on one side,
    shared proper nouns (if any) and overlapping topic words."""
    ka, kb = subject_key(a), subject_key(b)
    if ka and kb:
        sa, sb = set(ka.split()), set(kb.split())
        return sa <= sb or sb <= sa
    pa, pb = proper_nouns(a), proper_nouns(b)
    if (pa or pb) and not pa & pb:
        return False
    topic = jaccard(content_words(a) - numbers(a), content_words(b) - numbers(b))
    return topic >= (min_overlap if pa & pb else 0.6)
