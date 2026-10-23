"""Fine-tune DeBERTa-v3-base on memshield-bench (npow/memshield-bench) as the write-time memory screen (slide 11).

    pip install -e '.[models]' datasets
    python -m memledger.guards.train.train_memshield --out models/memshield --epochs 2
    export MEMLEDGER_MEMSHIELD_MODEL=models/memshield

Trains on the dataset's train split only and reports precision/recall/F1 on its test split (written to
<out>/test_metrics.json; copy the numbers into results, not the weights). models/ is gitignored: never commit
weights. Run on a Brev GPU and log the hours in infra/budget.csv.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

TEXT_COLUMNS = ("text", "content", "memory", "entry", "memory_entry")
LABEL_COLUMNS = ("label", "is_poisoned", "poisoned", "malicious", "is_malicious")


def detect_columns(columns: list[str], text_col: str | None = None, label_col: str | None = None) -> tuple[str, str]:
    t = text_col or next((c for c in TEXT_COLUMNS if c in columns), None)
    lab = label_col or next((c for c in LABEL_COLUMNS if c in columns), None)
    if t is None or lab is None:
        raise ValueError(f"cannot find text/label columns in {columns}; pass --text-col/--label-col")
    return t, lab


def to_binary(v: object) -> int:
    """Labels may be bools, ints or strings such as 'poisoned'/'clean'."""
    if isinstance(v, str):
        return int(v.strip().lower() in ("1", "true", "poisoned", "malicious", "poison", "attack", "unsafe"))
    return int(bool(v))


def binary_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    tp = sum(t == p == 1 for t, p in zip(y_true, y_pred, strict=True))
    fp = sum(t == 0 and p == 1 for t, p in zip(y_true, y_pred, strict=True))
    fn = sum(t == 1 and p == 0 for t, p in zip(y_true, y_pred, strict=True))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = sum(t == p for t, p in zip(y_true, y_pred, strict=True)) / len(y_true) if y_true else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "accuracy": acc, "n": len(y_true)}


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs GPU, datasets and model downloads
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default="npow/memshield-bench")
    ap.add_argument("--base", default="microsoft/deberta-v3-base")
    ap.add_argument("--out", default="models/memshield")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--text-col")
    ap.add_argument("--label-col")
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args(argv)

    import numpy as np
    from datasets import load_dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
    )

    ds = load_dataset(a.dataset)
    if "train" not in ds or "test" not in ds:
        raise SystemExit(f"{a.dataset} needs train and test splits, has {list(ds)}")
    text_col, label_col = detect_columns(ds["train"].column_names, a.text_col, a.label_col)
    tok = AutoTokenizer.from_pretrained(a.base)

    def prep(batch: dict) -> dict:
        enc = tok(batch[text_col], truncation=True, max_length=a.max_length)
        enc["labels"] = [to_binary(v) for v in batch[label_col]]
        return enc

    train = ds["train"].map(prep, batched=True, remove_columns=ds["train"].column_names)
    test = ds["test"].map(prep, batched=True, remove_columns=ds["test"].column_names)
    model = AutoModelForSequenceClassification.from_pretrained(
        a.base, num_labels=2, id2label={0: "CLEAN", 1: "POISONED"}, label2id={"CLEAN": 0, "POISONED": 1})
    args = TrainingArguments(output_dir=f"{a.out}/checkpoints", num_train_epochs=a.epochs, learning_rate=a.lr,
                             per_device_train_batch_size=a.batch, per_device_eval_batch_size=a.batch,
                             seed=a.seed, save_strategy="no", report_to=[])
    trainer = Trainer(model=model, args=args, train_dataset=train, data_collator=DataCollatorWithPadding(tok))
    trainer.train()
    pred = trainer.predict(test)
    metrics = binary_metrics(list(pred.label_ids), list(np.argmax(pred.predictions, axis=-1)))
    Path(a.out).mkdir(parents=True, exist_ok=True)
    trainer.save_model(a.out)
    tok.save_pretrained(a.out)
    (Path(a.out) / "test_metrics.json").write_text(json.dumps({**metrics, "dataset": a.dataset, "base": a.base,
                                                                "split": "test"}, indent=2))
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
