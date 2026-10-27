# Hallucination check on RAGTruth and HaluEval (test split)

Check: `HallucinationCheck` with scorer `lytang/MiniCheck-RoBERTa-Large`, threshold 0.5, chunks of 350 words (production settings, nothing tuned on test). Sample: all items per dataset, seed 0. Positive class = hallucinated. 95% Wilson intervals.

| dataset | n (halluc.) | precision | recall | F1 | false rejection | AUROC | median ms |
|---|---|---|---|---|---|---|---|
| ragtruth | 2700 (943) | 905/1990 = 45.5% [43.3%, 47.7%] | 905/943 = 96.0% [94.5%, 97.1%] | 0.617 | 1085/1757 = 61.8% [59.5%, 64.0%] | 0.812 | 1907.9 |
| ragtruth / Data2txt | 900 (579) | 577/893 = 64.6% [61.4%, 67.7%] | 577/579 = 99.7% [98.7%, 99.9%] | 0.784 | 316/321 = 98.4% [96.4%, 99.3%] |  |  |
| ragtruth / QA | 900 (160) | 154/587 = 26.2% [22.8%, 29.9%] | 154/160 = 96.2% [92.1%, 98.3%] | 0.412 | 433/740 = 58.5% [54.9%, 62.0%] |  |  |
| ragtruth / Summary | 900 (204) | 174/510 = 34.1% [30.1%, 38.3%] | 174/204 = 85.3% [79.8%, 89.5%] | 0.487 | 336/696 = 48.3% [44.6%, 52.0%] |  |  |
| ragtruth, threshold 0.25 (best F1 on 600 dev items) | 2700 (943) | 852/1616 = 52.7% [50.3%, 55.1%] | 852/943 = 90.3% [88.3%, 92.1%] | 0.666 | 764/1757 = 43.5% [41.2%, 45.8%] |  |  |
| halueval | 13914 (6957) | 5821/10446 = 55.7% [54.8%, 56.7%] | 5821/6957 = 83.7% [82.8%, 84.5%] | 0.669 | 4625/6957 = 66.5% [65.4%, 67.6%] | 0.747 | 78.8 |
| halueval, threshold 0.15 (best F1 on 6086 dev items) | 13914 (6957) | 4650/6105 = 76.2% [75.1%, 77.2%] | 4650/6957 = 66.8% [65.7%, 67.9%] | 0.712 | 1455/6957 = 20.9% [20.0%, 21.9%] |  |  |

## How this was run

`MEMLEDGER_DEVICE=mps python -m bench.hallucination_eval --split test --dev-rows <dev rows>` on an Apple-silicon Mac, about 133 minutes. Per-item times are for MPS; the run was resumed from its row log after a stall. RAGTruth uses its official `test` split; each response is one item, labelled hallucinated if it has any annotated span. HaluEval QA has no official split, so items go to dev or test by the loader's stable hash (30/70), and each question gives two items, the right answer and the hallucinated one.

Choices made on dev only:
- **HaluEval item format.** Three formats were tried on 200 dev items: "Q: … A: …" as the memory (F1 0.629, false rejection 96%), the question as a context document with the answer alone as the memory (F1 0.656, 70%), and one merged claim (F1 0.634, 94%). The second is used.
- **The "threshold t" rows.** t is the best-F1 threshold on that dataset's dev rows (grid 0.05–0.95), applied once to test. Production stays at 0.5. These rows show what a different threshold would do; they are not the headline.

## What it shows

- **Hallucinations are caught.** At 0.5, recall is 96% on RAGTruth and 84% on HaluEval.
- **Most supported text is rejected too.** About 62% on RAGTruth and 67% on HaluEval, and 98% on RAGTruth Data2txt. The check rejects when any single fact scores below the threshold. Long outputs with many facts nearly always contain one fact MiniCheck is unsure of, so the weakest fact decides.
- **The score carries signal.** AUROC is 0.81 on RAGTruth and 0.75 on HaluEval. A lower threshold chosen on dev cuts false rejection from 66.5% to 20.9% on HaluEval (recall 84% to 67%), and from 61.8% to 43.5% on RAGTruth (recall 96% to 90%).
- **These benchmark items are longer and denser than most agent memories.** The false-rejection rate in the agent runs is measured separately (`false_rejection_rate` in the eval report) and should not be read off this table. The threshold, and whether the weakest fact should decide, are for the guard's owner to revisit on dev data.
