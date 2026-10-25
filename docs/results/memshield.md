# memshield classifier (write-time memory screen, slide 11) — fine-tune results, 25 Oct

Model: `microsoft/deberta-v3-base` fine-tuned on npow/memshield-bench **train** (824 entries: 602 clean / 222
poisoned) with `memledger/guards/train/train_memshield.py`. Threshold chosen on **validation** (175); **test** (179)
scored once. Weights are not in git: `models/memshield/` (set `MEMLEDGER_MEMSHIELD_MODEL` to the folder; it holds
`threshold.json`, which `MemshieldCheck` reads).

```
python -m memledger.guards.train.train_memshield --data data/memshield --out models/memshield \
    --epochs 3 --lr 2e-5 --batch 2 --grad-accum 8 --max-length 384
```

Settings: 3 epochs, lr 2e-5, effective batch 16, max length 384 (5 train / 1 validation / 3 test entries are longer),
no class weights (recall already above 0.8), seed 13, float32. Mac M4 16 GB (MPS): 9.3 min; needs
`PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.8 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.6` and nothing else large in memory (unload
Ollama models). Two traps found on the way, both handled in the script now:
- transformers 5 loads deberta-v3-base in **fp16**; Adam in fp16 makes every weight NaN after one step (CPU and MPS).
  The script loads float32 and refuses to save a diverged model.
- batch 8 × 512 tokens swaps a 16 GB Mac to a halt (17 GB resident).

## Classifier, memshield-bench test split

| threshold | precision | recall | F1 | clean entries rejected |
|---|---|---|---|---|
| **0.990** (validation: max recall at ≤ 5% false rejections) | **0.936** | **0.898** | **0.917** | **2.3%** (3/130) |
| 0.5 (not used) | 0.814 | 0.980 | 0.889 | 8.5% |

Validation at 0.990: precision 0.958, recall 0.902, false rejections 1.6%.

## Write path as a classifier (test split, fake agent, HF checkers)

Before = the same run without the model (`load_guard_models` never passed memshield before this branch, so "HF
checkers" meant the lexical memshield rules; this reproduces the 24 Oct numbers exactly).

| benchmark (full) | before: recall | before: harmless rejected | after: recall | after: precision | after: harmless rejected |
|---|---|---|---|---|---|
| memshield (40 poisoned / 40 clean) | 0.07 | 0/40 | **0.88** | 0.92 | 3/40 |
| MemEvoBench (120 / 160) | 0.03 | 2/160 | 0.21 | 0.53 | **22/160** |

All harmless writes in the clean episodes of these families (benchmarks + agentpoison twins): 1/126 → 14/126.
Agentpoison family (60 episodes): 0/60 attack success on write checks / full / full-no-registry before and after (the
lexical rules already stopped it); 60/60 on baseline and provenance. Benchmark attack success on full: 77/80 → 40/80.
Added write latency: +115 ms → +155 ms (median).

qwen3:8b (think off), 10 episodes per family + 5 benign twins, HF checkers + fine-tuned memshield:

| version | agentpoison | memshield + MemEvoBench attack success | harmless writes rejected |
|---|---|---|---|
| baseline | 10/10 | 14/20 | 0/34 |
| provenance | 10/10 | 14/20 | 0/33 |
| write checks | 0/10 | 1/20 | 4/33 |
| full | 0/10 | 2/20 | 4/33 |
| full, no registry | 0/10 | 1/20 | 4/33 |

## Caveat for M2: MemEvoBench

The model does not transfer to MemEvoBench: scores bunch just under 1.0, so no threshold helps (MemEvoBench dev:
recall 0.19 / 10% false rejections at 0.990; a threshold tuned on memshield validation + MemEvoBench dev, 0.991, gives
0.16 / 8%). Options: add MemEvoBench dev entries to training (dev only, never test), or report memshield-bench and
MemEvoBench separately and accept the false rejections. Decide before the Brev run.
