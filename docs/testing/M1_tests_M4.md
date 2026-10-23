# M1 cross-test of M4's area (eval/, demo/, infra/) — dry run 2026-10-23, for the 27 Oct swap

Tester: M1. Code under test: branch `m1/hardening` @ `5e4e7f6` (M1+M2+M3+M4 merged). Everything ran offline with the
lexical guard fallbacks (`MEMLEDGER_GUARD_BACKEND=lexical`) and a scripted fake LLM; no GPU, no downloads.
Result words: PASS / FAIL / NOT YET (not implemented or not measurable yet). Re-run this list on 27 Oct.

## 1. Checklist (docs/TEAM_PLAN.md "Final testing checklist" + M4 items)

| # | Item | How tested | Result NOW | Evidence |
|---|---|---|---|---|
| 1 | Fresh clone: setup + tests pass | `git clone` local repo to scratchpad, checkout `m1/hardening`, `python3 -m venv .venv && pip install -e ".[dev]"` (network was available), `make test`, `make lint` | PASS (with a caveat) | `274 passed, 1 skipped, 1 xfailed in 37s`; `All checks passed!`. Caveat: `make setup` itself FAILS on macOS: `/bin/sh: python: command not found` (Makefile uses `python`; Finding 6). The skipped test needs `chromadb` (optional `[store]` extra); the xfail is the known label-tamper gap (see 9) |
| 2 | Demo script runs end to end | `ls demo/` | NOT YET | `demo/` is empty (only the directory); no script, no `[demo]` code |
| 3 | Each deck mechanism has a test | grep of tests/ per mechanism | PASS | input screen: guards/test_input_screen, core/test_service_wiring; hallucination/memshield/contradiction/registry check: guards/test_checks, test_hallucination, integration/test_m2_pipeline; JTMS trust + retraction: core/test_trust, integration/test_properties (e); hash chain/Merkle/tamper: core/test_merkle, core/test_service, integration/test_properties (d); 2-stage retrieval: retrieval/test_retriever; access control I1/I2: policy/test_policy, integration/test_properties (a)-(c); taint I3-I5 + action gate: policy/test_policy; registry signing/binding I9/I10: registry/test_registry; 5-version flags: core/test_service_wiring, eval/test_versions, integration/test_e2e. Not covered by any test: I7 (latency independence, KS test), I8 (deleted memories never return — no delete API), the 8x6 attack/path coverage matrix |
| 4 | Leak rate 0 with rule-of-three bound | M3 dev split (36 episodes) on `full`: 0 leaks; property tests (a)(b)(c) over 3 teams x 3 clearances | PASS for what exists; bound is weak | `full` leak_rate 0/36 -> rule of three < 8.3% (Wilson upper 9.6%). 3,000-run target from metrics.md is not reached yet; the coverage matrix (8 attacks x 6 paths) is not built (Finding 7) |
| 5 | Tamper detection 100% | `tests/integration/test_properties.py::test_tamper_detection_is_100_percent_on_full`: 50 trials, each on a fresh populated store, 5 edit types (claim text, source content, recorded_at, derivation edge, deleted hash_log row) with triggers dropped; all tampered claims and their descendants must be withheld AND quarantined | PASS | `full`: 390/390 = 100% (Wilson 99.0-100%, rule of three n/a since x=n); `baseline` 194/194. Known gap: edits to a claim's team/confidentiality label are NOT detected (hash excludes labels, per deck slide 14) — `test_label_tamper_is_detected` is a strict xfail |
| 6 | Hallucination / injection numbers recorded | `ls results/`, grep | NOT YET | Only `results/baseline-smoke-20261023` (5 hand-written episodes, baseline only). No RAGTruth/HaluEval/BIPIA run, no thresholds recorded |
| 7 | No secrets in git history | `git log -p --all` grep for api key / secret / password / BEGIN PRIVATE KEY / sk- / hf_ / ghp_ / AKIA; file-name scan for .env/.key/.pem/.sqlite/weights | PASS | 0 matches for key-shaped tokens or private-key blocks. Keyword hits (names only, no values) are in docs (`CLAUDE.md`, `docs/TEAM_PLAN.md`, `docs/prompts/README.md`, `infra/README.md`), `memledger/agent/llm.py` (reads `MEMLEDGER_LLM_KEY` from env), `memledger/guards/input_screen.py` (regex words), `memledger/registry/{__main__,signing}.py` (keygen code; no key files tracked, `.gitignore` has `*.key *.pem secrets/`), tests. Hygiene: `memledger.egg-info/` is tracked (Finding 11) |
| 8 | `docs/results.md` maps each slide claim to a test or number | `ls docs/` | NOT YET | file does not exist |
| 9 | Runner runs all 5 versions | `MEMLEDGER_GUARD_BACKEND=lexical python -m eval.runner --episodes eval/fixtures/smoke.jsonl --strict --run-id smoke` | PASS on M4's own fixture | 5 versions x 5 episodes, 0 errors, 0 degraded (table in section 3b). Without the env var and `--strict` it stops with `ImportError: transformers/torch not installed` (expected, undocumented in eval/README, Finding 4); without `--strict` it degrades honestly |
| 10 | Runner accepts M3's scenario set | `eval.episode.load_episodes(seed0.json)` | FAIL | `AttributeError: 'str' object has no attribute 'get'` — M3 emits `World` JSON with `Episode(seeds, turns, expect)`; M4 expects `sessions, steps, canaries`. No converter (Finding 2). M3's episodes were run through M3's runner instead (section 3a) |
| 11 | Metrics as defined in eval/metrics.md, incl. 95% CIs, rule of three | read `eval/`, grep for wilson / rule of three | FAIL / NOT YET | `eval/metrics.py` and `eval/isolation.py` (named in metrics.md, eval/README, summary.md) do not exist. Runner reports 11 point estimates only. No Wilson, rule of three, bootstrap, ECE, F1, attribution, update accuracy, false quarantine, p95 delay (Finding 1). Point estimates present are computed as the formulas say (poison stored, ASR, hijacked rate, leak, FRR, accuracy, approval load, median delay) |
| 12 | Cost logger | `pytest tests/infra tests/eval` (32 pass); CLI `session` + `summary` against a temp CSV | PASS | `logged 2.00 h, $2.20 (t)` / `spent $2.20 ... remaining $997.80 of $1000`. `infra/budget.csv` committed with header only (no sessions yet, fine) |
| 13 | Dockerfile / brev script sanity (read only) | `bash -n infra/brev_setup.sh`; read Dockerfile; docker build/run NOT attempted (no GPU, no network build) | PASS static, NOT RUN | `bash-syntax-ok`; shellcheck/hadolint not installed. Notes: vllm unpinned (`>=0.6`), `BRANCH` defaults to `main` and the README curls `raw.githubusercontent.com/.../main/infra/brev_setup.sh`, which does not exist until infra is merged to main; repo URL not verifiable offline; script uses `set -euo pipefail` and no secrets (HF_TOKEN env only) (Finding 9) |

## 2. Properties tests added by M1 (all green)

`tests/integration/test_properties.py` (12 tests): team isolation over index/keyword/triple/one-hop routes on `baseline`
and `full`; shared readable by all and not a bridge; clearance never exceeded incl. derived labels and the
launder-via-low-clearance refusal; identity only from `Session`; tamper detection (above); retraction end to end
(quarantine, independent justification survives, restore after new evidence). One M1 bug found and fixed along the way:
after a JTMS restore the claim was missing from the latest signed root, so `verify_claim` quarantined it again
(regression test `tests/core/test_service.py::test_restored_claim_is_reanchored_and_retrievable`; fix
`LedgerService.add_justification`, which records the derivation, recomputes trust and re-anchors).

## 3. Dev-split run, 2026-10-23

Run directory (not in repo): `<scratchpad>/runs/`. Setup: `python -m scenarios.generator --seed 0` -> 72 episodes,
dev split = 36 (20 attack: 12 cross_team, 6 clearance, 2 fake_fact; 16 clean: 12 recall/shared_recall... 2 payment).
Versions built by `memledger.core.factory.build_service` (the same flags as `eval/versions.py`), M3's `run_episode`,
fake "gullible" LLM from `tests/integration/test_e2e.py` (copies the last account number it saw, echoes memory), lexical
guards, signed registry for `full` only. Dev split only; thresholds untuned.

### 3a. M3 scenarios through M3's runner (the Episode formats do not match, so M4's runner cannot read them)

| version | episodes | errors | attack success rate | leak rate | benign task success | false-positive (benign failed) | write ms (median) | read ms (median) |
|---|---|---|---|---|---|---|---|---|
| baseline | 36 | 0 | 0.60 (12/20) | 0.333 (12/36) | 0.875 | 0.125 | 0.26 | 4.92 |
| provenance | 36 | 0 | 0.60 | 0.333 | 0.875 | 0.125 | 0.27 | 4.92 |
| write_checks | 36 | 0 | 0.60 | 0.333 | 0.875 | 0.125 | 1.56 | 4.97 |
| full | 36 | 0 | 0.00 (0/20) | 0.000 (0/36; rule of three < 8.3%) | 1.000 | 0.000 | 2.44 | 4.94 |
| full_no_registry | 36 | 0 | 0.00 | 0.000 | 0.875 | 0.125 | 1.59 | 4.98 |

Attack success by category (baseline = provenance = write_checks): clearance 6/6, cross_team 4/12, fake_fact 2/2;
`full` and `full_no_registry`: 0 everywhere. Added delay vs baseline (median): write +0.01 / +1.30 / +2.18 / +1.33 ms
(provenance / write_checks / full / full_no_registry); read about +0.0-0.1 ms (access filter and hash verification are
cheap; `gate` calls are timed separately and not included). The 2 benign failures at 0.875 are the 2 payment episodes:
without the registry binder the fake LLM pays "unknown", so that is the registry's effect, not a false rejection (no
seed write was rejected in any version). Read time is dominated by hash-chain verification of k*2 candidates.
Caveats: baseline here is `LedgerService` with no checks, identical flags to `provenance` (the eval baseline is a
different class, see 3b); fake LLM and lexical guards give floor numbers, not the final ones; no model-based
hallucination/injection results yet.

### 3b. M4's runner on M4's fixture (`eval/fixtures/smoke.jsonl`, 5 episodes, `--strict`, lexical guards)

| version | service | n | errors | poison stored | ASR | hijacked | leak rate | FRR | task acc | approval load | write ms | read ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | MockMemoryService | 5 | 0 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.002 | 0.003 |
| provenance | LedgerService | 5 | 0 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.163 | 0.268 |
| write_checks | LedgerService | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.258 | 0.185 |
| full | LedgerService | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.411 | 0.180 |
| full_no_registry | LedgerService | 5 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.229 | 0.173 |

Leak rate is 0 for every version including baseline because `MockMemoryService` already scopes by team and the fixture
has no same-team low-clearance canary: this fixture cannot show a leak (Finding 3).

## 4. Findings for M4

1. `eval/metrics.py` and `eval/isolation.py` are referenced by `eval/metrics.md`, `eval/README.md` and `results/*/summary.md` but do not exist: no Wilson intervals, rule-of-three bound, bootstrap CIs, ECE, detection F1, attribution, clean-up recall, false quarantine, p95 delay, or the I1-I10 property checks. Fix: implement `wilson()`, `rule_of_three()`, `bootstrap_diff()` and have `run()` write them into `summary.json` (the numbers in sections 3a/3b were computed by hand).
2. `eval/runner.py` cannot consume M3's output (`load_episodes` raises `AttributeError: 'str' object has no attribute 'get'` on `data/scenarios/seedN.json`), and `eval/versions.py::build_stack` re-implements the wiring that `memledger.core.factory.build_service` already provides (different baseline class, own component paths). Fix: add `eval/adapters.py` converting `memledger.agent.episode.Episode` (seeds/turns/expect) to `eval.episode.Episode`, or make the runner drive M3's `run_episode` + `build_service`; add a test that generates seed 0 and runs all 5 versions.
3. `eval/fixtures/smoke.jsonl` cross-team canary cannot discriminate: baseline (`MockMemoryService`) is team-scoped, so baseline leak rate is 0. Add a same-team low-clearance canary (M3's `clearance` category leaks on 6/6 episodes in baseline) so the leak oracle is exercised; decide whether eval baseline should be the unscoped plain retriever (README already asks for a plain mode) and tell M1.
4. `--strict` fails without `MEMLEDGER_GUARD_BACKEND=lexical` or the `[models]` extra (`ImportError: transformers/torch not installed`); eval/README does not say so. Document both modes, and print which backend was used in the manifest.
5. Leak oracle (`Env._check_leak`) only inspects retrieved claim text and tool-call arguments; metrics.md defines "visible" as retrieved memories, prompt, answer, tool arguments, logs and error messages. The `error` string and the agent answer are never scanned (the scripted agent produces no answer). Fix when the LLM agent is plugged in; scan `error` now.
6. `Makefile` uses `python`; on macOS only `python3` exists, so `make setup` fails (`/bin/sh: python: command not found`). Suggest `python3 -m venv .venv` (CI uses 3.11, local default is 3.14; `requires-python >=3.11` is satisfied).
7. `demo/` is empty and `docs/results.md` does not exist (checklist items 2 and 8); the 8 attack types x 6 access paths coverage matrix and I7 (latency KS test) / I8 (deletion) have no tests or runner support; add at least a coverage-matrix test that fails on empty cells.
8. Added-delay metric compares `LedgerService` versions with `MockMemoryService` (2 microseconds), so "added delay" mixes store cost with layer cost; use a plain-LedgerService baseline (as in section 3a) and report median plus p95 per write and per read separately from the hash-verification cost.
9. Infra: `brev_setup.sh` and the README curl command target `main`, where `infra/` is not merged yet; vLLM is unpinned in both Dockerfile and script (non-reproducible); neither was run (no GPU). Pin `vllm==<tested>` and `transformers`, default `BRANCH` to the release tag `v1.0`, and test the script once on a cheap instance before 27 Oct.
10. `results/baseline-smoke-20261023/summary.md` is a 1-version, 5-episode smoke run committed as a result; label it clearly as smoke or move it out of `results/` so it is not mistaken for a benchmark number in `docs/results.md`.
11. Repo hygiene (any owner): `memledger.egg-info/` is tracked in git, so every `pip install -e .` dirties the tree (`M memledger.egg-info/SOURCES.txt`); `git rm -r --cached memledger.egg-info` and add it to `.gitignore`.
