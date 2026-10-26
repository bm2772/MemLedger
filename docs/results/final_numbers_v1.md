# Final numbers for v1.0 (run `final2`, 26 Oct 2026)

**Setup:**
- Brev L40, agent Qwen3-8B served with vLLM.
- Test split from PR #25 (bigger samples): **2299 episodes per version**, suite manifest `suite_manifest_final2.json` (sha256 `65d51e3532dc0149…`).
- Checkers:
  - base memshield (Ahan's DeBERTa-v3-base);
  - DeBERTa-v3-large NLI;
  - MiniCheck;
  - **Prompt Guard 2 86M** input screen, chosen on dev (see below).
- Code: branch `run/brev-final-2`, i.e. #21–#25, #27, #28 merged for the run only.
- `docs/results.md` is generated from `results/attacks/final2`.

## Test split, all versions

| version | attack success (oracle) | hijacked actions | leak rate | tamper detected | benign task accuracy | legit payments refused | harmless writes rejected |
|---|---|---|---|---|---|---|---|
| baseline (plain memory) | 854/1455 = 58.7% | 416/838 = 49.6% | 333/2299 = 14.5% | 0/72 | 210/238 = 88.2% | 0/66 | 0/540 |
| provenance | 607/1456 = 41.7% | 376/838 = 44.9% | 112/2299 = 4.9% | 72/72 | 206/238 = 86.6% | 0/66 | 0/540 |
| write checks | 286/1455 = 19.7% | 138/838 = 16.5% | 107/2299 = 4.7% | 72/72 | 201/238 = 84.5% | 0/66 | 30/540 = 5.6% |
| **full MemLedger** | **61/1456 = 4.2%** [3.3, 5.3] | **0/838** | **0/2299** | **72/72** | 200/238 = 84.0% | **0/66** | 30/540 = 5.6% [3.9, 7.8] |
| full, no registry | 58/1455 = 4.0% | 0/838 | 18/2299 = 0.8% | 72/72 | 203/238 = 85.3% | 66/66 | 30/540 = 5.6% |

**Notes on the table:**
- **One errored episode:** `bipia_test_email_45` timed out (LLM call > 300 s) in baseline, write_checks and full_no_registry. It has no verdict there, which is why the denominators differ by one.
- **Legit payments refused:** `full_no_registry` holds every legitimate payment because, without the registry, the gate cannot bind the account.

## Per benchmark, plain memory → full

| benchmark (test items) | attack success | harmless writes rejected (full) | clean inputs quarantined (full) |
|---|---|---|---|
| AgentDojo (230 = 23 injection tasks × 10 user tasks) | 45.2% → **0%** (0/23 tasks) | – | – |
| InjecAgent (300 attacks) | 1.0% → **0%** | – | 0/300 |
| MemShield-bench (179) | 98.0% → **10.2%** | 4/130 = 3.1% | 1/130 |
| BIPIA (300) | 16.8% → 11.3% | – | **13/150 = 8.7%** |
| MemEvoBench (166) | 42.2% → **41.0%** | **21/166 = 12.7%** | 2/166 |

## Weak spots (stated as they are)
1. **MemEvoBench is not defended.** Misleading memories pass every check (41% vs 42.2% on plain memory), and 12.7% of its clean memories are rejected. The large memshield did better on the earlier 40-item sample, but that model is not the headline (`final_run_2026-10-26.md`).
2. **Prompt Guard 2's low cut-off over-blocks BIPIA.** 8.7% of clean BIPIA emails are quarantined, and BIPIA clean-task accuracy falls from 77.4% to 69.4%. That is most of the 4.2-point overall accuracy cost (88.2% → 84.0%). The cut-off (0.006, PR #28) was tuned on BIPIA train for ≤ 5% false alarms; on the test emails it gives 8.7%.
3. **Harmless writes rejected: 5.6%,** just over the 5% target (slide 19: not met).

## Prompt Guard 2 vs ProtectAI (dev split, `full`; chosen on dev only)

| | ProtectAI | Prompt Guard 2 |
|---|---|---|
| attack success (oracle) | 26/749 = 3.5% | **20/749 = 2.7%** |
| harmless writes rejected | 2.7% | 2.7% |
| clean inputs wrongly blocked | 0.8% | 0.4% |
| benign task accuracy | 95.7% | 95.0% |

The run's gate script compared the deprecated hijack alias (0 for both) instead of the oracle rate. The oracle rate gives the same choice, and the script is fixed.

## Latency (1 worker, 5 episodes per family)
Run `final2-latency` (same code and checkers, Prompt Guard 2, 1 worker, 5 episodes per family): **+25.5 ms per write and +0.8 ms per read** on `full` (write checks alone: +23.2 ms; provenance: +0.2 ms / +1.9 ms).

## Earlier runs
`final_run_2026-10-26.md` covers the 1159-episode suite: base vs large memshield, the dev NLI check, and the memshield stabilisation. Those numbers are not comparable row for row with this suite.
