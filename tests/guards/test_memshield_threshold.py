"""memshield decision threshold: chosen on validation at training time, read back by MemshieldCheck (slide 11)."""

import json

import pytest

from memledger.guards.memshield import MemshieldCheck, model_threshold
from memledger.guards.train.train_memshield import pick_threshold


def test_pick_threshold_max_recall_within_false_rejection_budget():
    y = [0] * 20 + [1] * 5
    s = [i / 100 for i in range(20)] + [0.9, 0.8, 0.185, 0.1, 0.05]
    # one clean entry above 0.185 is 1/20 = 5% false rejections: allowed; 0.1 would add more
    assert pick_threshold(y, s, max_fpr=0.05) == 0.185
    assert pick_threshold(y, s, max_fpr=0.0) == 0.8


def test_pick_threshold_without_clean_entries_takes_lowest():
    assert pick_threshold([1, 1], [0.3, 0.7]) == 0.3


def test_model_threshold_file(tmp_path):
    assert model_threshold(str(tmp_path)) == 0.5
    (tmp_path / "threshold.json").write_text(json.dumps({"threshold": 0.12}))
    assert model_threshold(str(tmp_path)) == 0.12


def test_check_uses_classifier_threshold():
    def clf(text: str) -> float:
        return 0.2
    assert MemshieldCheck(classifier=clf).threshold == 0.5
    clf.threshold = 0.1  # type: ignore[attr-defined]
    assert MemshieldCheck(classifier=clf).threshold == 0.1
    assert MemshieldCheck(classifier=clf, threshold=0.3).threshold == 0.3


def test_pick_threshold_rejects_nan_scores():
    import pytest
    with pytest.raises(ValueError, match="NaN"):
        pick_threshold([0, 1], [float("nan"), 0.9])


def test_threshold_floor_and_seed_selection_on_calibration_data():
    from memledger.guards.train.train_memshield import select_seed

    y, s = [0, 0, 0, 1, 1], [0.001, 0.002, 0.003, 0.0025, 0.0028]  # badly calibrated: everything near 0
    assert pick_threshold(y, s, max_fpr=0.4) < 0.5 and pick_threshold(y, s, max_fpr=0.4, floor=0.5) == 0.5
    runs = [{"seed": 13, "calibration": {"recall": 0.90, "false_rejection": 0.04, "f1": 0.8}},
            {"seed": 14, "calibration": {"recall": 0.95, "false_rejection": 0.05, "f1": 0.7}},
            {"seed": 15, "calibration": {"recall": 0.95, "false_rejection": 0.02, "f1": 0.6}}]
    assert select_seed(runs)["seed"] == 15  # recall first, then fewer false rejections


def test_training_args_build_and_train_with_best_epoch(tmp_path):
    """The exact TrainingArguments the Brev run uses, on the installed transformers (26 Oct: warmup_ratio no longer
    exists in transformers 5 and the GPU run failed on it). A tiny random DeBERTa trains 2 epochs with per-epoch
    evaluation and keeps the best."""
    import argparse

    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    from memledger.guards.train.train_memshield import training_args, training_kwargs

    a = argparse.Namespace(batch=4, grad_accum=1, epochs=2, lr=1e-4, cpu=True, warmup_ratio=0.1, weight_decay=0.01,
                           best_epoch=True)
    kw = training_kwargs(a, seed=13, n_train=16, output_dir=str(tmp_path / "ck"))  # checked against this transformers
    assert kw["warmup_steps"] == int(0.1 * 8) and kw["load_best_model_at_end"]  # 16 texts / 4 per step x 2 epochs
    pytest.importorskip("accelerate")  # TrainingArguments/Trainer need it (the models extra installs it, e.g. on Brev)
    args = training_args(a, seed=13, n_train=16, output_dir=str(tmp_path / "ck"))

    cfg = transformers.DebertaV2Config(vocab_size=50, hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
                                       intermediate_size=32, max_position_embeddings=32, num_labels=2)
    model = transformers.AutoModelForSequenceClassification.from_config(cfg)
    g = torch.Generator().manual_seed(0)
    data = [{"input_ids": torch.randint(0, 50, (8,), generator=g), "attention_mask": torch.ones(8, dtype=torch.long),
             "labels": torch.tensor(i % 2)} for i in range(16)]
    trainer = transformers.Trainer(model=model, args=args, train_dataset=data, eval_dataset=data[:8])
    trainer.train()
    assert trainer.state.best_model_checkpoint and trainer.state.epoch == 2
    plain = training_args(argparse.Namespace(**{**vars(a), "best_epoch": False}), 13, 16, str(tmp_path / "p"))
    assert not plain.load_best_model_at_end
