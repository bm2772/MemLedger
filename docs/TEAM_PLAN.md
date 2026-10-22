# MemLedger: team build plan (22 → 27 Oct 2026; presentation 30 Oct)

Repo: https://github.com/bm2772/MemLedger · All code is written by Claude Code. Members drive Claude, review its output,
run experiments and make decisions. Spec = the deck (`AEGIS2026_MemLedger.pdf`).

**5 days is tight → build an MVP that demonstrates every mechanism, measured on a reduced test set.**
Must-have (in deck, demoable): memory service, provenance graph + JTMS trust + retraction, hash chain, write checks
(hallucination, contradiction, registry), input screen, access control + action gate, 2-stage retrieval, 5-version
comparison on a subset, demo. Cut if late (say so on slides as "future work"): larger 70B model, full benchmark coverage,
garak/PyRIT adaptive attacks, SSO (use a stub), long-context study.

## Roles

| Member | Area | Owns |
|---|---|---|
| **M1 — Core** (repo admin) | Memory service, provenance graph, JTMS trust, hashing, storage, retrieval | `memledger/core`, `store`, `retrieval` |
| **M2 — Guardrails** | Input screen, write checks, registry (signed JSON), access control, action gate | `memledger/guards`, `policy`, `registry` |
| **M3 — Attacks & data** | Agent harness, two-team scenario generator, attack library, benchmark loaders (subsets) | `memledger/agent`, `bench/`, `attacks/`, `scenarios/` |
| **M4 — Eval & demo** | 5-version runner, metrics + stats, Brev GPU ops & budget, Streamlit demo, results into slides | `eval/`, `demo/`, `infra/` |

## Repo rules (M1, first 2 hours of day 1)
- Create repo, invite 3 members, protect `main` (PR + 1 review + CI: pytest, ruff), `.gitignore` (no `.env`, keys,
  weights, datasets). Layout: `memledger/{core,store,retrieval,guards,policy,registry,agent}`, `bench/ attacks/
  scenarios/ eval/ demo/ infra/ tests/ docs/`.
- Root `CLAUDE.md`: architecture, interfaces, "only edit your own package; interface changes need M1's approval".
- `docs/interfaces.md` frozen by end of day 1 (MemoryService: `ingest, propose_write, retrieve, flag_source, explain`;
  Claim/Source/Derivation schema; `check(proposal) -> Verdict`; labels). Everyone codes against mocks meanwhile.

## Working with Claude Code (every member)
1. `git pull`, branch `m<N>/<task>`, open Claude Code in the repo.
2. Prompt: task, slide it implements, interface to satisfy, "tests first, run pytest, stay in my package".
3. Read the diff before committing; you are accountable. Push small PRs often; review a teammate's PR within 2 hours.
4. Merge to `main` at least twice a day; pull before starting each session.
5. Log every Brev session (hours, $) in `infra/budget.csv`. Stop instances when idle.

## Day-by-day

| Day | M1 Core | M2 Guardrails | M3 Attacks & data | M4 Eval & demo |
|---|---|---|---|---|
| **Wed 22** | Repo, CI, CLAUDE.md, interfaces; SQLite + Chroma store | Check interface, registry schema + Ed25519 sign/verify | Agent loop on local Ollama via MemoryService; scenario spec | Brev setup, vLLM + verifier Docker image, cost logger; metrics spec |
| **Thu 23** | Provenance graph (edges, bi-temporal), hash chain + signed root, `explain()` | Input screen (unhide, rules, Prompt Guard 2, spotlighting); hallucination check (MiniCheck) | Scenario generator (2 teams, canaries, ground truth); loaders: LongMemEval/LoCoMo subsets, BIPIA, memshield | Runner with 5 versions as flags; baseline (plain RAG) run |
| **Fri 24** | JTMS trust + retraction/restore; 2-stage retrieval | Contradiction (DeBERTa NLI), registry match, memshield classifier, access control, action gate + approval queue | Attacks: poisoning (AgentPoison/PoisonedRAG-style, MINJA-style), fake-fact, tampering, 8 isolation attacks | Isolation harness (I1–I10, canary oracles), metrics code |
| **Sat 25** | **Integration freeze 18:00** — end-to-end on one scenario; bug fixes | Integration + fixes; cut-off sweep on dev set | Integration; build test set | First full GPU run (small model, subset) |
| **Sun 26** | Fixes from runs; delay metric | Fixes; calibration | Extra attack runs; benchmark subsets | Final test-set run, results tables + 95% CIs; demo |
| **Mon 27** | **Final testing (swap: M1 tests M4, M2 tests M1, M3 tests M2, M4 tests M3)** · tag `v1.0` by 23:59 | | | |

**Final testing checklist (27 Oct):** fresh clone → setup + tests pass; demo script runs end to end; each deck mechanism
has a test; leak rate 0 (with rule-of-three bound); tamper detection 100%; hallucination/injection numbers recorded;
no secrets in git history; `docs/results.md` maps each slide claim to a test or number.

**28–29 Oct:** update slides with real numbers (mark targets that were not reached), rehearse. **30 Oct:** present.

## Budget ($1,000 Brev; M4 owns)
Dev ~$40 · calibration/fine-tune ~$20 · main runs ~$80 · optional larger model ~$100 · demo ~$30 → ~$270; rest is
reserve. Stop instances after every job; keep data in `/home/ubuntu/workspace`; export results after each run.
