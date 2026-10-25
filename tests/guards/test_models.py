"""HF checker loading (F10 float32, F11 Prompt Guard fallback) without downloading any model."""

import sys
import types

import pytest

from memledger.guards import models


@pytest.fixture
def fake_transformers(monkeypatch):
    torch = pytest.importorskip("torch")
    calls = []

    class Model:
        config = types.SimpleNamespace(id2label={0: "SAFE", 1: "INJECTION"})

        def to(self, device):
            return self

        def eval(self):
            return self

    class Auto:
        @staticmethod
        def from_pretrained(model_id, **kw):
            calls.append((model_id, kw))
            if "Prompt-Guard" in model_id:
                raise OSError("gated repo")
            return Model()

    fake = types.SimpleNamespace(AutoModelForSequenceClassification=Auto, AutoTokenizer=Auto,
                                 __version__="5.0.0")
    monkeypatch.setitem(sys.modules, "transformers", fake)
    monkeypatch.setattr(models, "require_transformers", lambda: None)
    return calls, torch


def test_checkers_load_in_float32_f10(fake_transformers):
    calls, torch = fake_transformers
    models.HFSupportScorer(models.MINICHECK)._load()
    model_calls = [kw for _, kw in calls if kw]
    assert model_calls == [{"dtype": torch.float32}]


def test_gated_prompt_guard_falls_back_to_protectai_f11(fake_transformers, monkeypatch):
    monkeypatch.delenv("MEMLEDGER_PROMPT_GUARD_MODEL", raising=False)
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "hf")
    clf = models.default_injection_classifier()
    with pytest.warns(UserWarning, match="ProtectAI|protectai"):
        clf._load()
    assert clf.model_id == models.PROTECTAI and clf.cutoff == models.TUNED_CUTOFFS[models.PROTECTAI]


def test_explicit_model_gets_no_fallback(fake_transformers, monkeypatch):
    monkeypatch.setenv("MEMLEDGER_PROMPT_GUARD_MODEL", models.PROMPT_GUARD)
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "hf")
    with pytest.raises(OSError):
        models.default_injection_classifier()._load()
