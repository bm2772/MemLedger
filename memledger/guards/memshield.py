"""Step 2 (memory screen): flags manipulative memory entries (slides 11, 16), a classifier tuned on memshield-bench.

The fine-tuned DeBERTa-v3-base comes from memledger/guards/train/train_memshield.py (train split only; weights are
never committed) and is loaded from $MEMLEDGER_MEMSHIELD_MODEL. In lexical mode the screen's rules plus a few
memory-specific patterns ("whenever the user asks ..., say ...") stand in for it.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from memledger.core.types import Source, Verdict, WriteProposal
from memledger.guards.input_screen import rule_score
from memledger.guards.models import HFTextClassifier, TextClassifier, backend

MEMORY_RULES = [
    re.compile(r"\b(always|whenever|every time|in (the )?future|next time|from now on)\b[\s\S]{0,60}?\b(say|reply|"
               r"respond|answer|use|pay|send|recommend|tell|claim|ignore|trust)\b", re.IGNORECASE),
    re.compile(r"\b(the user|users?) (wants|prefers|asked) (you )?to (always|never)\b", re.IGNORECASE),
    re.compile(r"\b(trusted|verified|official) (source|instruction)s? (says?|states?)\b", re.IGNORECASE),
]


def lexical_memshield(text: str) -> float:
    score, _ = rule_score(text)
    if any(rx.search(text) for rx in MEMORY_RULES):
        score = max(score, 0.7)
    return score


def default_memshield() -> TextClassifier:
    if backend() == "lexical":
        return lexical_memshield
    path = os.environ.get("MEMLEDGER_MEMSHIELD_MODEL")
    if not path:
        raise ImportError("no memshield model: run python -m memledger.guards.train.train_memshield and set "
                          "MEMLEDGER_MEMSHIELD_MODEL, or MEMLEDGER_GUARD_BACKEND=lexical")
    clf = HFTextClassifier(path)
    clf.threshold = model_threshold(path)  # type: ignore[attr-defined]
    return clf


def model_threshold(path: str, default: float = 0.5) -> float:
    """Decision threshold chosen on the validation split at training time (<model>/threshold.json)."""
    f = Path(path) / "threshold.json"
    return float(json.loads(f.read_text())["threshold"]) if f.is_file() else default


class MemshieldCheck:
    name = "memshield"

    def __init__(self, classifier: TextClassifier | None = None, threshold: float | None = None) -> None:
        self.classifier = classifier or default_memshield()
        self.threshold = threshold if threshold is not None else float(getattr(self.classifier, "threshold", 0.5))

    def check(self, proposal: WriteProposal, sources: list[Source]) -> Verdict:
        p = float(self.classifier(proposal.text))
        if p >= self.threshold:
            return Verdict(False, 1.0 - p, f"manipulative memory entry (p={p:.2f})", self.name)
        return Verdict(True, 1.0 - p, f"clean (p={p:.2f})", self.name)
