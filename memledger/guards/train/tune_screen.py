"""Tune the input screen's cut-offs on BIPIA's TRAIN split only (slides 12, 19). Never InjecAgent/AgentDojo/test.

    git clone --depth 1 https://github.com/microsoft/BIPIA.git /tmp/bipia      # data is not committed
    python -m memledger.guards.train.tune_screen /tmp/bipia/benchmark --classifier protectai --out results/screen

Negatives: the train contexts (email, code, table). Positives: the same contexts with a train attack inserted at
the start, middle or end, as BIPIA builds its attacked prompts. For each layer setting the sweep picks the cut-off
that blocks the most attacks while flagging at most `max_fpr` (5%) of clean contexts, and reports both.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

TASKS = {"email": "text", "table": "text", "code": "code"}  # task -> which train attack file it uses


def load_train(root: str | Path, per_task: int = 100, seed: int = 13) -> list[tuple[str, int]]:
    """(text, label) pairs from BIPIA train files only; label 1 = injected."""
    root, rng = Path(root), random.Random(seed)
    out: list[tuple[str, int]] = []
    for task, kind in TASKS.items():
        path = root / task / "train.jsonl"
        if not path.exists():
            continue
        contexts = [_text(json.loads(line)["context"]) for line in path.read_text().splitlines() if line.strip()]
        contexts = rng.sample(contexts, min(per_task, len(contexts)))
        attacks = [a for group in json.loads((root / f"{kind}_attack_train.json").read_text()).values() for a in group]
        for ctx in contexts:
            out.append((ctx, 0))
            attack, where = rng.choice(attacks), rng.choice(("start", "middle", "end"))
            out.append((insert(ctx, attack, where), 1))
    if not out:
        raise FileNotFoundError(f"no BIPIA train files under {root}")
    return out


def _text(context: str | list[str]) -> str:
    return "\n".join(context) if isinstance(context, list) else context  # code contexts are lists of lines


def insert(context: str, attack: str, where: str) -> str:
    if where == "start":
        return f"{attack}\n{context}"
    if where == "end":
        return f"{context}\n{attack}"
    words = context.split(" ")
    mid = len(words) // 2
    return " ".join(words[:mid] + [attack] + words[mid:])


def sweep(scores: list[float], labels: list[int], max_fpr: float = 0.05) -> dict:
    """Best cut-off: highest recall with false-positive rate <= max_fpr (ties -> higher cut-off)."""
    neg = sum(1 for y in labels if y == 0) or 1
    pos = sum(labels) or 1
    best = {"threshold": 1.01, "recall": 0.0, "fpr": 0.0}
    for t in sorted(set(scores) | {1.01}, reverse=True):
        fp = sum(1 for s, y in zip(scores, labels, strict=True) if y == 0 and s >= t)
        tp = sum(1 for s, y in zip(scores, labels, strict=True) if y == 1 and s >= t)
        rec, fpr = tp / pos, fp / neg
        if fpr <= max_fpr and rec > best["recall"]:
            best = {"threshold": t, "recall": rec, "fpr": fpr}
    return best


def rates(scores: list[float], labels: list[int], t: float) -> dict:
    neg = sum(1 for y in labels if y == 0) or 1
    pos = sum(labels) or 1
    return {"threshold": t,
            "recall": sum(1 for s, y in zip(scores, labels, strict=True) if y == 1 and s >= t) / pos,
            "fpr": sum(1 for s, y in zip(scores, labels, strict=True) if y == 0 and s >= t) / neg}


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs BIPIA and (optionally) models
    from memledger.guards.input_screen import InputScreen
    from memledger.guards.models import HFTextClassifier

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bipia_benchmark")
    ap.add_argument("--classifier", choices=["none", "protectai", "promptguard"], default="none")
    ap.add_argument("--per-task", type=int, default=100)
    ap.add_argument("--max-fpr", type=float, default=0.05)
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)

    data = load_train(a.bipia_benchmark, a.per_task)
    model = {"none": None, "protectai": "protectai/deberta-v3-base-prompt-injection-v2",
             "promptguard": "meta-llama/Llama-Prompt-Guard-2-86M"}[a.classifier]
    screen = InputScreen(classifier=HFTextClassifier(model) if model else None)
    results = [screen.assess(text) for text, _ in data]
    labels = [y for _, y in data]
    report = {"split": "BIPIA train", "n": len(data), "positives": sum(labels), "classifier": model or "none",
              "max_fpr": a.max_fpr, "layers": {}}
    for layer in ["rules", "classifier", "max"]:
        scores = [r.score if layer == "max" else r.layers.get(layer, 0.0) for r in results]
        if layer == "classifier" and not model:
            continue
        report["layers"][layer] = {"best": sweep(scores, labels, a.max_fpr),
                                   "at_default_high_0.8": rates(scores, labels, 0.8),
                                   "at_default_mid_0.5": rates(scores, labels, 0.5)}
    print(json.dumps(report, indent=2))
    if a.out:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / f"tune_screen_{a.classifier}.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
