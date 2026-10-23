"""Step 3: registry match (slides 5, 8, 11, 13). Protected facts must equal the signed registry exactly.

For each sentence that names a registry subject (e.g. "Acme Ltd", also "Acme" / "Acme's") and a protected field
("account", "IBAN", "email", ...), the value given for that field is extracted as a (subject, field, value) triple
and compared with the registry. A mismatch rejects the write and flags the sources that carry the wrong value.
The extractor is rule-based and injectable; its error rate is measured with the other checks (slide 13).
Reasons never contain the registry value (it may be above the user's clearance).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from memledger.core.types import Source, SourceKind, Verdict, WriteProposal
from memledger.guards.text import normalise, split_facts
from memledger.registry.binding import default_registry
from memledger.registry.registry import Registry, RegistryError
from memledger.registry.schema import Entry

FIELD_WORDS: dict[str, tuple[str, ...]] = {
    "account": ("bank account", "account number", "account no", "account", "acct", "a/c", "iban", "bank details"),
    "email": ("email address", "e-mail", "email", "mail address", "contact address", "contact"),
    "contact": ("contact", "email", "e-mail", "phone"),
    "phone": ("phone number", "telephone", "phone", "mobile", "tel"),
    "limit": ("approval limit", "spending limit", "limit", "threshold", "cap"),
}
_EMAIL = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
VALUE_RX: dict[str, re.Pattern[str]] = {
    "account": re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,4})?\b|\b\d(?:[\d-]*\d)?\b"),
    "email": re.compile(_EMAIL),
    "contact": re.compile(_EMAIL + r"|\+?\d[\d\s()-]{6,}\d"),
    "phone": re.compile(r"\+?\d[\d\s()-]{6,}\d"),
    "limit": re.compile(r"[$€£₹]?\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|usd|eur|inr|gbp)?\b", re.IGNORECASE),
}
_GENERIC = re.compile(_EMAIL + r"|\b[A-Z0-9]*\d[A-Z0-9-]*\b")
_SUFFIX = re.compile(r"\b(ltd|limited|inc|llc|corp|corporation|plc|co|gmbh|pvt|private|company)\b\.?", re.IGNORECASE)


@dataclass(frozen=True)
class Triple:
    entry: Entry
    value: str
    sentence: str

    @property
    def matches(self) -> bool:
        return norm_value(self.value) == norm_value(self.entry.value)


def norm_value(v: str) -> str:
    return re.sub(r"[\s\-()]", "", v).lower()


def _subject_rx(subject: str) -> re.Pattern[str]:
    full = re.escape(" ".join(subject.split()))
    core = " ".join(_SUFFIX.sub(" ", subject).split())
    names = [full] + ([re.escape(core)] if core and core.lower() != subject.lower() and len(core) >= 3 else [])
    return re.compile(r"\b(?:" + "|".join(names) + r")(?:['’]s)?\b", re.IGNORECASE)


def extract(text: str, entries: list[Entry]) -> list[Triple]:
    """(subject, field, value) triples for registry subjects/fields mentioned in text."""
    out: list[Triple] = []
    for sent in split_facts(text) or [text]:
        s = normalise(sent)
        for e in entries:
            subj = _subject_rx(e.subject).search(s)
            if not subj:
                continue
            words = FIELD_WORDS.get(e.field.lower(), (e.field.replace("_", " "),))
            hit = next((m for w in words if (m := re.search(r"\b" + re.escape(w) + r"\b", s, re.IGNORECASE))), None)
            if not hit:
                continue
            rx = VALUE_RX.get(e.field.lower(), _GENERIC)
            subject_span = range(subj.start(), subj.end())
            values = [m for m in rx.finditer(s) if m.start() not in subject_span and m.group().strip()]
            after = [m for m in values if m.start() >= hit.end()]
            before = [m for m in values if m.end() <= hit.start()]
            chosen = after[0] if after else (before[-1] if before else None)
            if chosen is not None:
                out.append(Triple(e, chosen.group().strip(), sent))
    return out


Extractor = Callable[[str, list[Entry]], list[Triple]]


class RegistryCheck:
    name = "registry"

    def __init__(self, registry: Registry | None = None, extractor: Extractor = extract,
                 on_mismatch: Callable[[str, str], object] | None = None) -> None:
        self.registry = registry
        self.extractor = extractor
        self.on_mismatch = on_mismatch  # e.g. memory.flag_source(source_id, reason)

    def attach(self, memory: object) -> RegistryCheck:
        self.on_mismatch = memory.flag_source  # type: ignore[attr-defined]
        return self

    def check(self, proposal: WriteProposal, sources: list[Source]) -> Verdict:
        reg = self.registry or default_registry()
        if reg is None:
            raise RegistryError("RegistryCheck has no registry: pass one, set_default_registry() or $MEMLEDGER_REGISTRY")
        triples = self.extractor(proposal.text, reg.current())
        bad = [t for t in triples if not t.matches]
        if bad:
            keys = sorted({t.entry.key for t in bad})
            reason = f"protected fact {', '.join(keys)} does not match the signed registry"
            carriers = [s for s in sources if s.kind != SourceKind.REGISTRY
                        and any(norm_value(t.value) in norm_value(s.content) for t in bad)]
            if self.on_mismatch is not None:
                for s in carriers:
                    self.on_mismatch(s.id, f"registry mismatch: {', '.join(keys)}")
            return Verdict(False, 0.0, reason, self.name)
        if triples:
            return Verdict(True, 1.0, f"matches registry: {', '.join(sorted({t.entry.key for t in triples}))}",
                           self.name)
        return Verdict(True, 1.0, "no protected facts", self.name)
