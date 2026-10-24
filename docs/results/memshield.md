# memshield classifier (slide 11, step 2) — status 25 Oct 2026

**Not trained yet. No precision/recall to report.** The eval runs use the lexical fallback (`guards/text.py`) until
this is done, and eval does not load the trained model yet anyway (audit finding F-M4-1).

| Attempt | Where | Result |
|---|---|---|
| DeBERTa-v3-base, 2 epochs, memshield train (824) / validation (175) | Mac M4, MPS | diverged: loss NaN, predicts "clean" for everything (test: precision 0, recall 0, accuracy 0.726 = share of clean items). Discarded. |
| same, `--cpu` | Mac M4, CPU | ~29 min per step (104 steps/epoch); stopped |

**To do on Brev (one L4, a few minutes; log it in infra/budget.csv):**
```bash
make memshield          # train split only; validation picks the best epoch; test metrics -> models/memshield/test_metrics.json
cat models/memshield/test_metrics.json   # copy precision / recall / F1 / n into this file
```
Weights stay in `models/` (gitignored). `make` exports `MEMLEDGER_MEMSHIELD_MODEL` automatically once
`models/memshield/config.json` exists.
