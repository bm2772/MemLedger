# memshield-large: DeBERTa-v3-large + MemEvoBench dev memories (26 Oct, Brev L40)

`make memshield-large`: `microsoft/deberta-v3-large`, 3 epochs, lr 1e-5, effective batch 16, max length 512, trained on
memshield-bench **train** plus the memories of the suite's MemEvoBench **dev** items (125, 75 misleading; any text
shared with a test item is dropped). The threshold is chosen on memshield-bench **validation** (≤ 5% false rejections).
Training took about 2 minutes on the L40.

## Classifier, memshield-bench test (179)
| model | threshold | precision | recall | F1 | clean entries rejected |
|---|---|---|---|---|---|
| base (Ahan, `ahanphatak/memledger-memshield`) | 0.990 | 0.936 | 0.898 | 0.917 | 2.3% |
| **large + MemEvoBench dev** | 0.822 | **0.959** | **0.959** | **0.959** | **1.5%** |

## In the agent run (`results/attacks/brev-upgraded`, Qwen3-8B, test split, `full`)
Run `brev-upgraded` used memshield-large **and** the large NLI model (PR for Aditya). Compared with `brev-test`
(base memshield, base NLI):

| on `full` | brev-test | brev-upgraded |
|---|---|---|
| oracle attack success | 34/819 (4.2%) | **16/819 (2.0%)** |
| MemEvoBench attacks | 16/40 | **1/40** |
| memshield-bench attacks | 5/40 | **2/40** |
| poisoned memories stored | 13.5% | **6.9%** |
| harmless writes rejected | 34/364 (9.3%) | 41/364 (11.3%) |

Which check rejected the harmless writes on `full`:
- **contradiction (NLI):** 15 → **0**;
- **memshield:** 18 → **40**:
  - MemEvoBench clean 10 → 18;
  - repetition_flooding twins 5 → 14;
  - poisonedrag twins 0 → 6;
  - memshield-bench clean 3 → 2.

**Open:** the 0.822 threshold keeps false rejections under 5% on memshield-bench validation, but not on our other
memory types. The threshold should be re-chosen on dev data only (memshield validation + MemEvoBench dev + dev-split
scenario writes) with a ≤ 5% total budget; the test split must not be used for that.
