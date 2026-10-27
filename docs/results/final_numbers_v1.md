# Final numbers for v1.0 (agent: NVIDIA Nemotron Nano 9B v2, run `final-nemo`, 27 Oct 2026)

**Setup:**
- Brev L40; the agent model, `nvidia/NVIDIA-Nemotron-Nano-9B-v2`, is served with vLLM using NVIDIA's tool-call parser
  (ported to vLLM 0.32, `infra/nemotron/`) and its chat template with thinking off.
- Test split: **2299 episodes per version**, the same suite as run `final2` below.
- Checkers:
  - base memshield (DeBERTa-v3-base);
  - DeBERTa-v3-large NLI;
  - MiniCheck;
  - Prompt Guard 2 (chosen on dev).
- Code: `v1.0` with all PRs merged. `docs/results.md` is generated from `results/attacks/final-nemo`.

## Test split, all versions

| version | attack success (oracle) | hijacked actions | leak rate | tamper detected | benign task accuracy | legit payments not completed | harmless writes rejected |
|---|---|---|---|---|---|---|---|
| baseline (plain memory) | 712/1456 = 48.9% | 298/838 = 35.6% | 331/2299 = 14.4% | 0/72 = 0.0% | 205/238 = 86.1% | 15/66 = 22.7% | 0/540 = 0.0% |
| provenance | 467/1455 = 32.1% | 274/838 = 32.7% | 93/2299 = 4.0% | 72/72 = 100.0% | 205/238 = 86.1% | 15/66 = 22.7% | 0/540 = 0.0% |
| write checks | 187/1456 = 12.8% | 58/838 = 6.9% | 87/2299 = 3.8% | 72/72 = 100.0% | 201/238 = 84.5% | 16/66 = 24.2% | 30/541 = 5.5% |
| **full MemLedger** | **57/1456 = 3.9%** | **0/838 = 0.0%** | **0/2299 = 0.0%** | **72/72 = 100.0%** | 200/238 = 84.0% | 12/66 = 18.2% | 30/540 = 5.6% |
| full, no registry | 58/1456 = 4.0% | 0/838 = 0.0% | 17/2299 = 0.7% | 72/72 = 100.0% | 200/238 = 84.0% | 66/66 = 100.0% | 30/540 = 5.6% |

Latency (run `final-nemo-latency`, 1 worker, 5 episodes per family): **+21.1 ms per write, +0.7 ms per read** on `full`.

## Per benchmark, plain memory → full

| benchmark | attack success | harmless writes rejected (full) | clean inputs quarantined (full) |
|---|---|---|---|
| AgentDojo (230) | 43.0% → **0.0%** | – | – |
| InjecAgent (300 attacks) | 0.7% → **0.0%** | – | 0/300 = 0.0% |
| MemShield-bench (179) | 93.9% → **10.2%** | 4/130 = 3.1% | 1/130 = 0.8% |
| BIPIA (300) | 13.3% → **10.0%** | – | 13/150 = 8.7% |
| MemEvoBench (166) | 21.7% → **13.3%** | 21/166 = 12.7% | 2/166 = 1.2% |

The model comparison (Nemotron vs Qwen3-8B on this suite, and Qwen3-8B vs Qwen3-32B on the earlier suite) is in the slides (Table 12). The mechanism benchmarks (clean-up recall, false quarantine, contradiction F1) are in `mechanisms.md`.

---

# Same suite with Qwen3-8B as the agent (run `final2`, 26 Oct 2026)

**Setup:**
- Brev L40, agent Qwen3-8B served with vLLM.
- Test split from PR #25 (bigger samples): **2299 episodes per version**, suite manifest `suite_manifest_final2.json` (sha256 `65d51e3532dc0149…`).
- Checkers:
  - base memshield (Ahan's DeBERTa-v3-base);
  - DeBERTa-v3-large NLI;
  - MiniCheck;
  - **Prompt Guard 2 86M** input screen, chosen on dev (see below).
- Code: branch `run/brev-final-2`, i.e. #21–#25, #27, #28 merged for the run only.

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
4. **Contradiction detection can flag unrelated facts about the same subject.** Both NLI models give P(contradiction) ≈ 0.99 to pairs such as "Kestrel reaches 91% recall on Saltmarsh" vs "Kestrel runs on the Orion cluster". `same_subject` matches only the subject, and the check takes the direction with the higher score. Planned after v1.0 (M2, on dev): require both directions to pass, and add a same-attribute match.
5. **Prompt Guard 2's cut-off is kept at 0.006 as tuned.** It was chosen on BIPIA train for ≤ 5% false alarms and gives 8.7% on BIPIA test. Re-tuning it because of the test result would be tuning on test, so the gap is reported as it is. A likely fix after v1.0: use the screen's mid band ("allowed but untrusted"). Today every input scoring ≥ 0.5 is quarantined (`LedgerService.ingest`).

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
