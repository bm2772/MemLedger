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


def _cal_item(key: str) -> bool:
    """A third of the MemEvoBench dev items calibrate the threshold instead of training (stable hash of the item key)."""
    import hashlib

    return int(hashlib.sha256(f"{key}|calibration".encode()).hexdigest()[:8], 16) % 3 == 0


def memevo_rows(root: str | Path | None = None, split: str = "dev",
                part: str | None = None) -> tuple[list[str], list[int]]:
    """MemEvoBench memories of the suite's `split` items as (texts, labels), label 1 = misleading.

    `part` ("train" / "val") takes two thirds / one third of the dev items, so the threshold can be calibrated on
    MemEvoBench memories the model never trained on. Same item split (bench.loaders.hash_split) and the same memory
    rendering as the eval episodes; a dev memory whose
    text also occurs in a test item is dropped, so training on "dev" never sees test content (MemEvoBench transfer of memshield: recall 0.21, docs/results/memshield.md)."""
    import json as _json

    from bench.download import data_dir
    from bench.loaders import hash_split, render_memory

    rows: dict[str, list[tuple[str, int]]] = {"dev": [], "test": []}
    for path in sorted(data_dir("memevobench", root).glob("*.json")):
        for i, x in enumerate(_json.loads(path.read_text())):
            key, sp = f"{path.stem}_{i}", hash_split(f"{path.stem}_{i}")
            if sp == "dev" and part is not None and _cal_item(key) != (part == "val"):
                continue  # part="train": the training two thirds; part="val": the calibration third
            rows[sp] += [(render_memory(m), int(m.get("label") == "misleading")) for m in x["retrievable_memories"]]
    held_out = {t for t, _ in rows["test"]} if split != "test" else set()  # a text shared with a test item stays out
    kept = [(t, y) for t, y in rows[split] if t not in held_out]
    return [t for t, _ in kept], [y for _, y in kept]


def suite_dev_writes() -> tuple[list[str], list[int]]:
    """HARMLESS write texts of the suite's DEV scenario episodes (generated worlds, no benchmarks): the memory types the
    agent runs see (benign twins, repetition, poisonedrag ...), as calibration negatives only, so the threshold keeps
    false rejections low on them. Their poisoned writes are left out: most are attacks other checks stop (registry,
    hallucination, gate), and counting them as misses made calibration recall meaningless (0.05). Never test."""
    from attacks.suite import SuiteConfig, build

    def writes(split: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in build(split, SuiteConfig(benchmarks=[]))[0]:
            for st in e.steps:
                if st.op == "write" and st.text:
                    out[st.text] = max(out.get(st.text, 0), int(e.is_poison(st, st.text)))
        return out

    dev, test = writes("dev"), writes("test")
    kept = [t for t, y in dev.items() if t not in test and y == 0]  # harmless only; texts test also writes stay out
    return kept, [0] * len(kept)


def select_seed(results: list[dict]) -> dict:
    """The seed with the highest calibration recall within the false-rejection budget; then the fewest false
    rejections; then the highest F1. Chosen on calibration data only, never on test."""
    return max(results, key=lambda r: (r["calibration"]["recall"], -r["calibration"]["false_rejection"],
                                       r["calibration"]["f1"]))


def training_kwargs(a: argparse.Namespace, seed: int, n_train: int, output_dir: str) -> dict:
    """TrainingArguments keywords for one seed, checked against the installed transformers (so a mismatch fails in
    seconds, not after setup on a GPU). Warm-up is given in steps: transformers 5 removed warmup_ratio."""
    import inspect

    import transformers

    steps = math.ceil(n_train / max(1, a.batch * a.grad_accum)) * a.epochs
    kw: dict = {"output_dir": output_dir, "num_train_epochs": a.epochs, "learning_rate": a.lr,
                "per_device_train_batch_size": a.batch, "per_device_eval_batch_size": a.batch,
                "gradient_accumulation_steps": a.grad_accum, "use_cpu": a.cpu, "seed": seed,
                "warmup_steps": int(a.warmup_ratio * steps), "weight_decay": a.weight_decay, "report_to": [],
                "logging_steps": 10}
    if a.best_epoch:  # evaluate each epoch on validation, keep the best (lowest loss)
        kw |= {"eval_strategy": "epoch", "save_strategy": "epoch", "save_total_limit": 1,
               "load_best_model_at_end": True, "metric_for_best_model": "eval_loss", "greater_is_better": False}
    else:
        kw["save_strategy"] = "no"
    known = inspect.signature(transformers.TrainingArguments.__init__).parameters
    if missing := [k for k in kw if k not in known]:
        raise SystemExit(f"transformers {transformers.__version__} has no TrainingArguments {missing}")
    return kw


def training_args(a: argparse.Namespace, seed: int, n_train: int, output_dir: str):
    import transformers

    return transformers.TrainingArguments(**training_kwargs(a, seed, n_train, output_dir))


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


def pick_threshold(y_true: list[int], scores: list[float], max_fpr: float = 0.05, floor: float = 0.0) -> float:
    """Highest-recall threshold whose false-positive rate on (validation) clean entries is <= max_fpr, never below
    `floor` (a badly calibrated run once picked 0.022). Ties in recall go to the higher threshold."""
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
    return max(best[1] if best else 1.0, floor)


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
    ap.add_argument("--seeds", type=int, default=1, help="train this many seeds (seed, seed+1, ...); keep the best on "
                                                         "calibration data (large models are seed-sensitive)")
    ap.add_argument("--warmup-ratio", type=float, default=0.0)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--best-epoch", action="store_true", help="evaluate every epoch on validation, keep the best")
    ap.add_argument("--cpu", action="store_true", help="train on the CPU even if a GPU / Apple MPS is available")
    ap.add_argument("--class-weight", choices=["none", "balanced"], default="none")
    ap.add_argument("--max-fpr", type=float, default=0.05, help="false-rejection budget for the validation threshold")
    ap.add_argument("--min-threshold", type=float, default=0.0, help="the threshold never goes below this")
    ap.add_argument("--add-memevobench-dev", action="store_true",
                    help="also train on MemEvoBench memories of the suite's dev items (its test items stay held out)")
    ap.add_argument("--calibrate-on-dev", action="store_true",
                    help="choose threshold and seed on memshield validation + a held-out third of MemEvoBench dev + "
                         "the suite's dev scenario writes (with --add-memevobench-dev, training keeps two thirds)")
    a = ap.parse_args(argv)

    import shutil

    import torch
    from datasets import Dataset, concatenate_datasets, load_dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
    )

    if a.data:
        ds = load_dataset("json", data_files={s: f"{a.data}/{s}.jsonl" for s in ("train", "validation", "test")})
    else:
        ds = load_dataset(a.dataset)
    if not {"train", "validation", "test"} <= set(ds):
        raise SystemExit(f"{a.data or a.dataset} needs train, validation and test splits, has {list(ds)}")
    text_col, label_col = detect_columns(ds["train"].column_names, a.text_col, a.label_col)
    sample = ds["train"][0][label_col]  # keep the dataset's label vocabulary ("clean"/"poisoned", bool or int)
    word = {0: "clean", 1: "poisoned"} if isinstance(sample, str) else {0: type(sample)(0), 1: type(sample)(1)}
    feats = ds["train"].select_columns([text_col, label_col]).features

    def rows(texts: list[str], ys: list[int]) -> Dataset:
        return Dataset.from_dict({text_col: texts, label_col: [word[y] for y in ys]}).cast(feats)

    extra, cal_parts = 0, {"memshield_validation": len(ds["validation"])}
    if a.add_memevobench_dev:
        texts, ys = memevo_rows(split="dev", part="train" if a.calibrate_on_dev else None)
        ds["train"] = concatenate_datasets([ds["train"].select_columns([text_col, label_col]), rows(texts, ys)])
        extra = len(texts)
        print(f"+ {extra} MemEvoBench dev memories ({sum(ys)} misleading) in training", flush=True)
    cal = ds["validation"].select_columns([text_col, label_col])
    if a.calibrate_on_dev:
        mt, my = memevo_rows(split="dev", part="val")
        st, sy = suite_dev_writes()
        cal = concatenate_datasets([cal, rows(mt, my), rows(st, sy)])
        cal_parts |= {"memevobench_dev_heldout": len(mt), "suite_dev_writes": len(st)}
        print(f"calibration: {cal_parts}", flush=True)
    tok = AutoTokenizer.from_pretrained(a.base)

    def prep(batch: dict) -> dict:
        enc = tok(batch[text_col], truncation=True, max_length=a.max_length)
        enc["labels"] = [to_binary(v) for v in batch[label_col]]
        return enc

    train = ds["train"].map(prep, batched=True, remove_columns=ds["train"].column_names)
    val = ds["validation"].map(prep, batched=True, remove_columns=ds["validation"].column_names)
    test = ds["test"].map(prep, batched=True, remove_columns=ds["test"].column_names)
    calib = cal.map(prep, batched=True, remove_columns=cal.column_names)
    labels = list(train["labels"])
    n_pos = sum(labels)
    weight = (torch.tensor([len(labels) / (2 * (len(labels) - n_pos)), len(labels) / (2 * n_pos)])
              if a.class_weight == "balanced" else None)

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kw):
            y = inputs.pop("labels")
            out = model(**inputs)
            w = weight.to(out.logits.device) if weight is not None else None
            loss = torch.nn.functional.cross_entropy(out.logits, y, weight=w)
            return (loss, out) if return_outputs else loss

    fpr = lambda y, p, th: (sum(t == 0 and s >= th for t, s in zip(y, p, strict=True))
                            / max(1, sum(t == 0 for t in y)))
    results, best, best_dir = [], None, Path(a.out) / "best_seed"
    for seed in range(a.seed, a.seed + max(1, a.seeds)):
        # float32: transformers 5 loads the checkpoint's dtype (fp16 for deberta-v3-base), and Adam in fp16 divides by
        # an underflowed exp_avg_sq on the first step (every weight NaN, on CPU and MPS alike)
        model = AutoModelForSequenceClassification.from_pretrained(
            a.base, dtype=torch.float32, num_labels=2, id2label={0: "CLEAN", 1: "POISONED"},
            label2id={"CLEAN": 0, "POISONED": 1})
        args = training_args(a, seed, len(train), f"{a.out}/checkpoints-{seed}")
        trainer = WeightedTrainer(model=model, args=args, train_dataset=train, eval_dataset=val if a.best_epoch else None,
                                  data_collator=DataCollatorWithPadding(tok))
        trainer.train()
        if any(math.isnan(h.get("loss", 0.0)) or h.get("loss", 0.0) > 100 for h in trainer.state.log_history):
            print(f"seed {seed}: training diverged, skipped", flush=True)
            continue

        def scores(split: object, tr: Trainer = trainer) -> tuple[list[int], list[float]]:
            pred = tr.predict(split)
            p = torch.softmax(torch.tensor(pred.predictions), dim=-1)[:, 1].tolist()
            return [int(x) for x in pred.label_ids], p

        yc, pc = scores(calib)
        threshold = pick_threshold(yc, pc, a.max_fpr, a.min_threshold)
        r = {"seed": seed, "threshold": threshold,
             "calibration": {**binary_metrics(yc, [int(p >= threshold) for p in pc]),
                             "false_rejection": fpr(yc, pc, threshold)}}
        results.append(r)
        print(f"seed {seed}: threshold {threshold:.3f}, calibration {json.dumps(r['calibration'])}", flush=True)
        if best is None or select_seed([best, r]) is r:
            best = r
            shutil.rmtree(best_dir, ignore_errors=True)
            trainer.save_model(best_dir)
            tok.save_pretrained(best_dir)
            best["validation_scores"], best["test_scores"] = scores(val), scores(test)
        shutil.rmtree(f"{a.out}/checkpoints-{seed}", ignore_errors=True)
        del trainer, model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    if best is None:
        raise SystemExit("every seed diverged; nothing saved. Retry with a lower --lr")

    threshold = best["threshold"]
    yv, pv = best.pop("validation_scores")
    yt, pt = best.pop("test_scores")
    metrics = binary_metrics(yt, [int(p >= threshold) for p in pt])
    at_half = binary_metrics(yt, [int(p >= 0.5) for p in pt])
    val_m = binary_metrics(yv, [int(p >= threshold) for p in pv])
    for f in best_dir.iterdir():  # the chosen seed becomes the model in --out
        shutil.move(str(f), Path(a.out) / f.name)
    best_dir.rmdir()
    settings = {k: getattr(a, k) for k in ("dataset", "data", "base", "epochs", "lr", "batch", "grad_accum",
                                           "max_length", "seed", "seeds", "warmup_ratio", "weight_decay",
                                           "best_epoch", "class_weight", "max_fpr", "min_threshold",
                                           "calibrate_on_dev", "cpu")}
    settings |= {"memevobench_dev_rows": extra, "calibration_rows": cal_parts}
    chosen_on = "calibration (memshield validation + MemEvoBench dev held-out + suite dev writes)" \
        if a.calibrate_on_dev else "validation"
    (Path(a.out) / "threshold.json").write_text(json.dumps({"threshold": threshold, "chosen_on": chosen_on,
                                                             "max_fpr": a.max_fpr, "seed": best["seed"]}, indent=2))
    (Path(a.out) / "test_metrics.json").write_text(json.dumps({
        **metrics, "false_rejection": fpr(yt, pt, threshold), "threshold": threshold, "split": "test",
        "seed": best["seed"], "at_0.5": {**at_half, "false_rejection": fpr(yt, pt, 0.5)},
        "validation": {**val_m, "false_rejection": fpr(yv, pv, threshold)},
        "calibration": best["calibration"], "seeds": results, "settings": settings}, indent=2))
    (Path(a.out) / "scores.json").write_text(json.dumps({"validation": [yv, pv], "test": [yt, pt]}))
    print(json.dumps({**metrics, "threshold": threshold, "seed": best["seed"], "at_0.5": at_half}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
