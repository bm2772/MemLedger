"""Fine-tune DeBERTa-v3-base on memshield-bench (npow/memshield-bench) as the write-time memory screen (slide 11).

    pip install -e '.[models]' datasets
    python -m memledger.guards.train.train_memshield --out models/memshield --epochs 3 [--data data/memshield]
    export MEMLEDGER_MEMSHIELD_MODEL=models/memshield

Trains on the dataset's train split only. The decision threshold is chosen on the validation split (highest recall
with at most --max-fpr false rejections of clean entries) and saved to <out>/threshold.json, which MemshieldCheck
reads. The test split is scored once, at that threshold and at 0.5, into <out>/test_metrics.json (copy the numbers
into results, not the weights). --class-weight balanced reweights the loss for the 602 clean / 222 poisoned train
split. models/ is gitignored: never commit weights. Log the hours in infra/budget.csv.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

TEXT_COLUMNS = ("text", "content", "memory", "entry", "memory_entry")
LABEL_COLUMNS = ("label", "is_poisoned", "poisoned", "malicious", "is_malicious")


def detect_columns(columns: list[str], text_col: str | None = None, label_col: str | None = None) -> tuple[str, str]:
    t = text_col or next((c for c in TEXT_COLUMNS if c in columns), None)
    lab = label_col or next((c for c in LABEL_COLUMNS if c in columns), None)
    if t is None or lab is None:
        raise ValueError(f"cannot find text/label columns in {columns}; pass --text-col/--label-col")
    return t, lab


def memevo_rows(root: str | Path | None = None, split: str = "dev") -> tuple[list[str], list[int]]:
    """MemEvoBench memories of the suite's `split` items as (texts, labels), label 1 = misleading.

    Same item split (bench.loaders.hash_split) and the same memory rendering as the eval episodes; a dev memory whose
    text also occurs in a test item is dropped, so training on "dev" never sees test content (MemEvoBench transfer of memshield: recall 0.21, docs/results/memshield.md)."""
    import json as _json

    from bench.download import data_dir
    from bench.loaders import hash_split, render_memory

    rows: dict[str, list[tuple[str, int]]] = {"dev": [], "test": []}
    for path in sorted(data_dir("memevobench", root).glob("*.json")):
        for i, x in enumerate(_json.loads(path.read_text())):
            rows[hash_split(f"{path.stem}_{i}")] += [(render_memory(m), int(m.get("label") == "misleading"))
                                                     for m in x["retrievable_memories"]]
    held_out = {t for t, _ in rows["test"]} if split != "test" else set()  # a text shared with a test item stays out
    kept = [(t, y) for t, y in rows[split] if t not in held_out]
    return [t for t, _ in kept], [y for _, y in kept]


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


def pick_threshold(y_true: list[int], scores: list[float], max_fpr: float = 0.05) -> float:
    """Highest-recall threshold whose false-positive rate on (validation) clean entries is <= max_fpr.
    Ties in recall go to the higher threshold (fewer false rejections)."""
    if any(math.isnan(s) for s in scores):  # NaN: the model diverged
        raise ValueError("NaN scores: training diverged; retrain with a lower --lr")
    neg = sum(1 for t in y_true if t == 0)
    best: tuple[float, float] | None = None  # (recall, threshold)
    for th in sorted(set(scores), reverse=True):
        pred = [int(s >= th) for s in scores]
        fp = sum(1 for t, p in zip(y_true, pred, strict=True) if t == 0 and p == 1)
        if neg and fp / neg > max_fpr:
            break  # lower thresholds only add false positives
        rec = binary_metrics(y_true, pred)["recall"]
        if best is None or rec > best[0]:
            best = (rec, th)
    return best[1] if best else 1.0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs GPU, datasets and model downloads
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default="npow/memshield-bench")
    ap.add_argument("--data", help="local dir with {train,validation,test}.jsonl (bench.download) instead of the hub")
    ap.add_argument("--base", default="microsoft/deberta-v3-base")
    ap.add_argument("--out", default="models/memshield")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--grad-accum", type=int, default=1, help="e.g. --batch 8 --grad-accum 2 on a 16 GB Mac")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--text-col")
    ap.add_argument("--label-col")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--cpu", action="store_true", help="train on the CPU even if a GPU / Apple MPS is available")
    ap.add_argument("--class-weight", choices=["none", "balanced"], default="none")
    ap.add_argument("--max-fpr", type=float, default=0.05, help="false-rejection budget for the validation threshold")
    ap.add_argument("--add-memevobench-dev", action="store_true",
                    help="also train on MemEvoBench memories of the suite's dev items (its test items stay held out)")
    a = ap.parse_args(argv)

    import torch
    from datasets import load_dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
    )

    if a.data:
        ds = load_dataset("json", data_files={s: f"{a.data}/{s}.jsonl" for s in ("train", "validation", "test")})
    else:
        ds = load_dataset(a.dataset)
    if not {"train", "validation", "test"} <= set(ds):
        raise SystemExit(f"{a.data or a.dataset} needs train, validation and test splits, has {list(ds)}")
    text_col, label_col = detect_columns(ds["train"].column_names, a.text_col, a.label_col)
    extra = 0
    if a.add_memevobench_dev:
        from datasets import Dataset, concatenate_datasets

        texts, ys = memevo_rows(split="dev")
        sample = ds["train"][0][label_col]  # keep the dataset's label vocabulary ("clean"/"poisoned", bool or int)
        word = {0: "clean", 1: "poisoned"} if isinstance(sample, str) else {0: type(sample)(0), 1: type(sample)(1)}
        cols = {text_col: texts, label_col: [word[y] for y in ys]}
        extra_ds = Dataset.from_dict(cols).cast(ds["train"].select_columns([text_col, label_col]).features)
        ds["train"] = concatenate_datasets([ds["train"].select_columns([text_col, label_col]), extra_ds])
        extra = len(texts)
        print(f"+ {extra} MemEvoBench dev memories ({sum(ys)} misleading) in training", flush=True)
    tok = AutoTokenizer.from_pretrained(a.base)

    def prep(batch: dict) -> dict:
        enc = tok(batch[text_col], truncation=True, max_length=a.max_length)
        enc["labels"] = [to_binary(v) for v in batch[label_col]]
        return enc

    train = ds["train"].map(prep, batched=True, remove_columns=ds["train"].column_names)
    val = ds["validation"].map(prep, batched=True, remove_columns=ds["validation"].column_names)
    test = ds["test"].map(prep, batched=True, remove_columns=ds["test"].column_names)
    labels = list(train["labels"])
    n_pos = sum(labels)
    weight = (torch.tensor([len(labels) / (2 * (len(labels) - n_pos)), len(labels) / (2 * n_pos)])
              if a.class_weight == "balanced" else None)
    # float32: transformers 5 loads the checkpoint's dtype (fp16 for deberta-v3-base), and Adam in fp16 divides by an
    # underflowed exp_avg_sq on the first step (every weight NaN, on CPU and MPS alike)
    model = AutoModelForSequenceClassification.from_pretrained(
        a.base, dtype=torch.float32, num_labels=2, id2label={0: "CLEAN", 1: "POISONED"}, label2id={"CLEAN": 0, "POISONED": 1})
    args = TrainingArguments(output_dir=f"{a.out}/checkpoints", num_train_epochs=a.epochs, learning_rate=a.lr,
                             per_device_train_batch_size=a.batch, per_device_eval_batch_size=a.batch,
                             gradient_accumulation_steps=a.grad_accum, use_cpu=a.cpu, seed=a.seed,
                             save_strategy="no", report_to=[], logging_steps=10)

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kw):
            y = inputs.pop("labels")
            out = model(**inputs)
            w = weight.to(out.logits.device) if weight is not None else None
            loss = torch.nn.functional.cross_entropy(out.logits, y, weight=w)
            return (loss, out) if return_outputs else loss

    trainer = WeightedTrainer(model=model, args=args, train_dataset=train, data_collator=DataCollatorWithPadding(tok))
    trainer.train()
    if any(math.isnan(h.get("loss", 0.0)) or h.get("loss", 0.0) > 100 for h in trainer.state.log_history):
        raise SystemExit("training loss diverged (NaN or > 100); nothing saved. Retry with a lower --lr")

    def scores(split: object) -> tuple[list[int], list[float]]:
        pred = trainer.predict(split)
        p = torch.softmax(torch.tensor(pred.predictions), dim=-1)[:, 1].tolist()
        return [int(x) for x in pred.label_ids], p

    yv, pv = scores(val)
    threshold = pick_threshold(yv, pv, a.max_fpr)
    yt, pt = scores(test)
    metrics = binary_metrics(yt, [int(p >= threshold) for p in pt])
    at_half = binary_metrics(yt, [int(p >= 0.5) for p in pt])
    val_m = binary_metrics(yv, [int(p >= threshold) for p in pv])
    fpr = lambda y, p, th: (sum(t == 0 and s >= th for t, s in zip(y, p, strict=True))
                            / max(1, sum(t == 0 for t in y)))
    Path(a.out).mkdir(parents=True, exist_ok=True)
    trainer.save_model(a.out)
    tok.save_pretrained(a.out)
    settings = {k: getattr(a, k) for k in ("dataset", "data", "base", "epochs", "lr", "batch", "grad_accum",
                                           "max_length", "seed", "class_weight", "max_fpr", "cpu")}
    settings["memevobench_dev_rows"] = extra
    (Path(a.out) / "threshold.json").write_text(json.dumps({"threshold": threshold, "chosen_on": "validation",
                                                             "max_fpr": a.max_fpr}, indent=2))
    (Path(a.out) / "test_metrics.json").write_text(json.dumps({
        **metrics, "false_rejection": fpr(yt, pt, threshold), "threshold": threshold, "split": "test",
        "at_0.5": {**at_half, "false_rejection": fpr(yt, pt, 0.5)},
        "validation": {**val_m, "false_rejection": fpr(yv, pv, threshold)}, "settings": settings}, indent=2))
    (Path(a.out) / "scores.json").write_text(json.dumps({"validation": [yv, pv], "test": [yt, pt]}))
    metrics = {**metrics, "threshold": threshold, "at_0.5": at_half}
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
