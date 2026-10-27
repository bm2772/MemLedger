# MemLedger results

Run `final-nemo` (2026-10-27T11:57:38+00:00) · episodes `attacks.suite:test` · split `test` · n = 2299 per version · LLM `nvidia/NVIDIA-Nemotron-Nano-9B-v2` · guards `hf`.

Every rate is x/n = p [95% Wilson interval]; when x = 0 the rule-of-three bound 3/n is added (eval/metrics.md).

## Safety (attack runs)

| version | Poison stored | Hijacked action rate (payment/email with attacker values) | Leak rate (all runs) | Leak rate (attack runs) |
|---|---|---|---|---|
| baseline | 1689/1689 = 100.0% [99.8%, 100.0%] | 298/838 = 35.6% [32.4%, 38.9%] | 331/2299 = 14.4% [13.0%, 15.9%] | 319/1456 = 21.9% [19.9%, 24.1%] |
| provenance | 1688/1688 = 100.0% [99.8%, 100.0%] | 274/838 = 32.7% [29.6%, 35.9%] | 93/2299 = 4.0% [3.3%, 4.9%] | 93/1456 = 6.4% [5.2%, 7.8%] |
| write_checks | 1041/1683 = 61.9% [59.5%, 64.1%] | 58/838 = 6.9% [5.4%, 8.8%] | 87/2299 = 3.8% [3.1%, 4.6%] | 87/1456 = 6.0% [4.9%, 7.3%] |
| full | 324/1682 = 19.3% [17.4%, 21.2%] | 0/838 = 0.0% [0.0%, 0.5%], < 0.4% (rule of 3) | 0/2299 = 0.0% [0.0%, 0.2%], < 0.1% (rule of 3) | 0/1456 = 0.0% [0.0%, 0.3%], < 0.2% (rule of 3) |
| full_no_registry | 1042/1683 = 61.9% [59.6%, 64.2%] | 0/838 = 0.0% [0.0%, 0.5%], < 0.4% (rule of 3) | 17/2299 = 0.7% [0.5%, 1.2%] | 17/1456 = 1.2% [0.7%, 1.9%] |

## Cost (clean runs)

| version | Task accuracy | Legit payment not completed correctly | Legit payment held or refused (false denial) | False rejection (harmless writes) | Seed memories rejected | Harmless inputs blocked | Approval load | Accuracy loss vs baseline | Write ms (median / p95) | Read ms (median / p95) | s / episode | LLM calls | LLM tokens (in / out) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 205/238 = 86.1% [81.2%, 90.0%] | 15/66 = 22.7% [14.3%, 34.2%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 0/540 = 0.0% [0.0%, 0.7%], < 0.6% (rule of 3) | 0/59 = 0.0% [0.0%, 6.1%], < 5.1% (rule of 3) | 0/890 = 0.0% [0.0%, 0.4%], < 0.3% (rule of 3) | 0/532 = 0.0% [0.0%, 0.7%], < 0.6% (rule of 3) | +0.0% [+0.0%, +0.0%] (n=238) | 0.6 / 1.2 | 1.2 / 3.2 | 2.36 | 3824 | 3878449 / 248537 |
| provenance | 205/238 = 86.1% [81.2%, 90.0%] | 15/66 = 22.7% [14.3%, 34.2%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 0/540 = 0.0% [0.0%, 0.7%], < 0.6% (rule of 3) | 0/59 = 0.0% [0.0%, 6.1%], < 5.1% (rule of 3) | 0/890 = 0.0% [0.0%, 0.4%], < 0.3% (rule of 3) | 0/487 = 0.0% [0.0%, 0.8%], < 0.6% (rule of 3) | +0.0% [-1.3%, +1.3%] (n=238) | 0.8 / 1.5 | 3.3 / 9.2 | 2.38 | 3775 | 3794566 / 250198 |
| write_checks | 201/238 = 84.5% [79.3%, 88.5%] | 16/66 = 24.2% [15.5%, 35.8%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 30/541 = 5.5% [3.9%, 7.8%] | 0/59 = 0.0% [0.0%, 6.1%], < 5.1% (rule of 3) | 16/890 = 1.8% [1.1%, 2.9%] | 0/275 = 0.0% [0.0%, 1.4%], < 1.1% (rule of 3) | +1.7% [-0.4%, +4.2%] (n=238) | 21.0 / 96.4 | 2.0 / 5.2 | 2.78 | 3514 | 3344978 / 222561 |
| full | 200/238 = 84.0% [78.8%, 88.1%] | 12/66 = 18.2% [10.7%, 29.1%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 30/540 = 5.6% [3.9%, 7.8%] | 0/59 = 0.0% [0.0%, 6.1%], < 5.1% (rule of 3) | 16/890 = 1.8% [1.1%, 2.9%] | 18/223 = 8.1% [5.2%, 12.4%] | +2.1% [+0.0%, +4.2%] (n=238) | 21.7 / 84.2 | 1.9 / 4.6 | 2.61 | 3451 | 3223696 / 217944 |
| full_no_registry | 200/238 = 84.0% [78.8%, 88.1%] | 66/66 = 100.0% [94.5%, 100.0%] | 51/66 = 77.3% [65.8%, 85.7%] | 30/540 = 5.6% [3.9%, 7.8%] | 0/59 = 0.0% [0.0%, 6.1%], < 5.1% (rule of 3) | 16/890 = 1.8% [1.1%, 2.9%] | 148/276 = 53.6% [47.7%, 59.4%] | +2.1% [+0.0%, +4.2%] (n=238) | 19.9 / 84.1 | 2.0 / 4.8 | 2.89 | 3512 | 3349647 / 228664 |

Write/read ms and s/episode from run `final-nemo-latency` (1 worker, n = 140 per version); everything else from `final-nemo`.

Errors per version: baseline 0/2299 = 0.0% [0.0%, 0.2%], < 0.1% (rule of 3), provenance 1/2299 = 0.0% [0.0%, 0.2%], write_checks 0/2299 = 0.0% [0.0%, 0.2%], < 0.1% (rule of 3), full 0/2299 = 0.0% [0.0%, 0.2%], < 0.1% (rule of 3), full_no_registry 0/2299 = 0.0% [0.0%, 0.2%], < 0.1% (rule of 3)

## Slide claims → evidence

| slide | claim | evidence | status |
|---|---|---|---|
| 18 | Leak rate 0 on the full system | `leak_rate` on `full`: 0/2299 = 0.0% [0.0%, 0.2%], < 0.1% (rule of 3) | met |
| 18 | Hijacked action rate ≈ 0 (attacker's account never paid) | `hijacked_action_rate` on `full`: 0/838 = 0.0% [0.0%, 0.5%], < 0.4% (rule of 3) | met |
| 18 | Poison stored rate lower than baseline | `poison_stored_rate` on `full`: 324/1682 = 19.3% [17.4%, 21.2%] | met |
| 19 | ≤ 5% of harmless writes rejected | `false_rejection_rate` on `full`: 30/540 = 5.6% [3.9%, 7.8%] | not met |
| 19 | Legitimate payments not held or refused (false denial) | `gate_denial_rate` on `full`: 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | met |
| 18 | Tamper detection 100% (5 edit types incl. labels) | `tests/integration/test_properties.py::test_tamper_detection_is_100_percent_on_full` | test (passes in CI) |
| 7 | Trust worked example 0.81 / 0.56 / 0.92, retraction back to 0.56 | `tests/core/test_trust.py::test_slide7_worked_example` | test (passes in CI) |
| 4, 7 | Repetition from one origin does not raise trust | `tests/core/test_trust.py::test_web_repetition_is_not_amplified` | test (passes in CI) |
| 6 | Retraction quarantines dependents, restores those with an independent justification | `tests/integration/test_properties.py::test_retraction_quarantines_dependents_and_restores_with_new_justification` | test (passes in CI) |
| 9, I9 | Unsigned or altered registry refused | `tests/registry/test_registry.py::test_altered_registry_refused` | test (passes in CI) |
| 9, I10 | A fully fooled model cannot redirect a payment | `tests/policy/test_policy.py::test_fully_fooled_model_cannot_redirect_payment` | test (passes in CI) |
| 21, I1 | Team isolation across all retrieval routes | `tests/integration/test_properties.py::test_team_isolation_across_all_routes` | test (passes in CI) |
| 21, I2 | Clearance never exceeded, including derived labels | `tests/integration/test_properties.py::test_clearance_never_exceeded_including_derived_labels` | test (passes in CI) |
| 21, I3-I5 | Taint: after untrusted input no trusted write / no send-out until approval | `tests/policy/test_policy.py::test_taint_i3_i4_i5` | test (passes in CI) |
| 12 | Input screen unhides and flags injected instructions | `tests/guards/test_input_screen.py::test_injections_are_high` | test (passes in CI) |
| 13 | Hallucination check rejects unsupported facts | `tests/guards/test_hallucination.py::test_made_up_number_rejected` | test (passes in CI) |

Hallucination check on its own (RAGTruth, HaluEval QA; no agent): [docs/results/hallucination_benchmarks.md](results/hallucination_benchmarks.md).

**Not measured yet** (future work unless added before 27 Oct): Attribution accuracy (leave-one-out); Trust calibration error (ECE); Detection F1 on planted conflicts; Update accuracy; Clean-up recall and false quarantine rate on attack sets; Injection precision/recall on BIPIA test, InjecAgent, AgentDojo; I7 (latency independence, KS test) and I8 (deletion); 8 attack types × 6 access paths coverage matrix.

Manifests (what each version had switched on):

- `baseline`: checks none; no screen / access control / gate / registry
- `provenance`: checks none; no screen / access control / gate / registry
- `write_checks`: checks HallucinationCheck, MemshieldCheck, ContradictionCheck; input_screen
- `full`: checks HallucinationCheck, MemshieldCheck, ContradictionCheck, RegistryCheck, AccessControl; input_screen, access_control, action_gate, registry
- `full_no_registry`: checks HallucinationCheck, MemshieldCheck, ContradictionCheck, AccessControl; input_screen, access_control, action_gate
