"""Model backends for the guards (slides 12, 13, 16). Every guard takes its model as an argument; tests use fakes.

No-arg constructors (used by the eval runner) pick the backend from $MEMLEDGER_GUARD_BACKEND:
    hf       (default) Hugging Face models, loaded lazily on first use. Needs the [models] extra. If transformers
             is not installed the constructor raises ImportError, so the runner records the component as missing
             instead of silently running a weaker check.
    lexical  the cheap code-only fallbacks in guards/text.py (CI, laptops, smoke runs).

Model ids can be overridden: $MEMLEDGER_MINICHECK_MODEL, $MEMLEDGER_NLI_MODEL, $MEMLEDGER_PROMPT_GUARD_MODEL,
$MEMLEDGER_MEMSHIELD_MODEL (path of the fine-tuned classifier), $MEMLEDGER_DEVICE (e.g. "cuda").
"""

from __future__ import annotations

import importlib.util
import os
import warnings
from collections.abc import Callable

PairScorer = Callable[[str, str], float]  # (document, claim) -> P(document supports claim)
NLIModel = Callable[[str, str], dict[str, float]]  # (premise, hypothesis) -> {entailment, neutral, contradiction}
TextClassifier = Callable[[str], float]  # text -> P(positive class: injected / manipulative)

MINICHECK = "lytang/MiniCheck-RoBERTa-Large"
# DeBERTa-v3-large NLI (MNLI, FEVER, ANLI, LingNLI, WANLI): on the 26 Oct Brev test run it removed all 15 harmless
# writes the base cross-encoder rejected as contradictions, with no change in attacks stopped. Override with
# $MEMLEDGER_NLI_MODEL (e.g. cross-encoder/nli-deberta-v3-base for the smaller model).
NLI = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
PROMPT_GUARD = "meta-llama/Llama-Prompt-Guard-2-86M"
PROTECTAI = "protectai/deberta-v3-base-prompt-injection-v2"  # ungated fallback when Prompt Guard 2 cannot load

# Injection-classifier cut-offs tuned on BIPIA's TRAIN split only (guards/train/tune_screen.py, 24 Oct 2026:
# 400 texts; highest recall with <= 5% false alarms on clean contexts). Below its cut-off a classifier score does
# not count. ProtectAI flags 56% of clean BIPIA emails at 0.8, so it only counts when near-certain.
# Prompt Guard 2 is not tuned yet (gated model): run the sweep before relying on it.
TUNED_CUTOFFS: dict[str, float] = {
    PROTECTAI: 0.99998,
}


def backend() -> str:
    b = os.environ.get("MEMLEDGER_GUARD_BACKEND", "hf").strip().lower()
    if b not in ("hf", "lexical"):
        raise ValueError(f"MEMLEDGER_GUARD_BACKEND must be 'hf' or 'lexical', got {b!r}")
    return b


def require_transformers() -> None:
    if importlib.util.find_spec("transformers") is None or importlib.util.find_spec("torch") is None:
        raise ImportError("transformers/torch not installed: pip install -e '.[models]' "
                          "or set MEMLEDGER_GUARD_BACKEND=lexical")


def _pick(id2label: dict[int, str], names: tuple[str, ...], default: int) -> int:
    for i, label in id2label.items():
        if any(n in label.lower() for n in names):
            return int(i)
    return default


def _float32() -> dict:
    """Load weights in float32 (F10): transformers 5 keeps the stored dtype, so deberta-v3 came up in fp16, which is
    ~20x slower on CPU and turns NaN when trained. transformers < 4.56 calls the argument torch_dtype."""
    import torch
    import transformers

    major, minor = (int(x) for x in transformers.__version__.split(".")[:2])
    return {"dtype" if (major, minor) >= (4, 56) else "torch_dtype": torch.float32}


class _HF:
    """Lazy sequence-classification model; loads on first call."""

    def __init__(self, model_id: str, max_length: int = 512, device: str | None = None) -> None:
        require_transformers()
        self.model_id, self.max_length = model_id, max_length
        self.device = device or os.environ.get("MEMLEDGER_DEVICE", "cpu")
        self._tok = self._model = None

    def _load(self) -> None:
        if self._model is None:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tok = AutoTokenizer.from_pretrained(self.model_id)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_id, **_float32()).to(self.device).eval()

    @property
    def id2label(self) -> dict[int, str]:
        self._load()
        return {int(k): v for k, v in self._model.config.id2label.items()}

    def probs(self, text: str, pair: str | None = None) -> list[float]:
        import torch

        self._load()
        enc = self._tok(text, pair, truncation=True, max_length=self.max_length, return_tensors="pt").to(self.device)
        with torch.no_grad():
            return torch.softmax(self._model(**enc).logits[0], dim=-1).tolist()

    def chunk_text(self, text: str) -> list[str]:
        """512-token chunks of text (slide 12: the classifier runs on 512-token chunks)."""
        self._load()
        ids = self._tok(text, add_special_tokens=False)["input_ids"]
        n = self.max_length - 2
        return [self._tok.decode(ids[i:i + n]) for i in range(0, max(len(ids), 1), n)]


class HFSupportScorer(_HF):
    """MiniCheck / AlignScore-style grounding: P(document supports claim)."""

    def __call__(self, document: str, claim: str) -> float:
        idx = _pick(self.id2label, ("support", "entail"), 1)
        return self.probs(document, claim)[idx]


class HFNLI(_HF):
    """DeBERTa-v3 MNLI cross-encoder -> {entailment, neutral, contradiction}."""

    def __call__(self, premise: str, hypothesis: str) -> dict[str, float]:
        p, labels = self.probs(premise, hypothesis), self.id2label
        out = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
        for i, label in labels.items():
            for k in out:
                if label.lower().startswith(k[:6]):
                    out[k] = p[i]
        return out


class HFTextClassifier(_HF):
    """Binary detector (Prompt Guard 2, ProtectAI, memshield): max P(positive) over 512-token chunks.
    `cutoff`: tuned score below which the input screen ignores this classifier (TUNED_CUTOFFS)."""

    POSITIVE = ("injection", "malicious", "jailbreak", "poison", "unsafe", "label_1")

    def __init__(self, model_id: str, max_length: int = 512, device: str | None = None,
                 cutoff: float | None = None, fallback: str | None = None) -> None:
        super().__init__(model_id, max_length, device)
        self._explicit_cutoff = cutoff
        self.cutoff = TUNED_CUTOFFS.get(model_id, 0.0) if cutoff is None else cutoff
        self.fallback = fallback  # model to use if this one cannot be loaded (gated, offline)

    def _load(self) -> None:
        try:
            super()._load()
        except (OSError, ValueError) as e:  # gated repo / no token / not cached
            if not self.fallback or self.fallback == self.model_id:
                raise
            warnings.warn(f"{self.model_id} could not be loaded ({type(e).__name__}); using {self.fallback}",
                          stacklevel=2)
            self.model_id, self.fallback, self._tok, self._model = self.fallback, None, None, None
            if self._explicit_cutoff is None:
                self.cutoff = TUNED_CUTOFFS.get(self.model_id, 0.0)
            super()._load()

    def __call__(self, text: str) -> float:
        idx = _pick(self.id2label, self.POSITIVE, 1)
        return max(self.probs(c)[idx] for c in self.chunk_text(text))


def default_support_scorer() -> PairScorer:
    if backend() == "lexical":
        from memledger.guards.text import lexical_support
        return lexical_support
    return HFSupportScorer(os.environ.get("MEMLEDGER_MINICHECK_MODEL", MINICHECK))


def default_nli() -> NLIModel:
    if backend() == "lexical":
        from memledger.guards.text import lexical_nli
        return lexical_nli
    return HFNLI(os.environ.get("MEMLEDGER_NLI_MODEL", NLI))


def default_injection_classifier() -> TextClassifier | None:
    """None in lexical mode: the screen then runs unhide + rules only (layers 1, 2).
    Default Prompt Guard 2; it is gated, so without access it falls back to ProtectAI (F11) with a warning
    instead of failing every episode. An explicit $MEMLEDGER_PROMPT_GUARD_MODEL gets no fallback."""
    if backend() == "lexical":
        return None
    if model := os.environ.get("MEMLEDGER_PROMPT_GUARD_MODEL"):
        return HFTextClassifier(model)
    return HFTextClassifier(PROMPT_GUARD, fallback=PROTECTAI)
