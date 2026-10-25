# Next steps from 24 Oct (status at 23 Oct evening)

**Status.** M1 days 1–6 done (`m1/hardening`, 275 tests, tamper incl. labels 100%). `m1/integration` already merges
M2 #5, M3 #3/#4, M4 #1/#2. Shared Episode v1 is on `m3/episode-v1`. First real-model local run:
`testing/local-run-2026-10-23` (`docs/testing/local_run_2026-10-23.md`) — full MemLedger: 0/36 leaks, 0/2 payment
attacks, but **4/4 legitimate payments wrongly held** (two M2 issues below).

**Merge order (today, reviewers: anyone not the author):**
`m1/store` → `m1/provenance` → `m1/trust-retrieval` → #5 (M2) → #3 (M3) → `m3/episode-v1` → #4 (M3) → #1, #2 (M4)
→ `m1/integration` → `m1/hardening`. Integration freeze **Sat 25 Oct 18:00**.

Paste the prompt for your role into Claude Code after `git pull`.

## M2 — Aditya (branch `m2/fix-false-denials`, from `m1/hardening`)
```
Read docs/testing/local_run_2026-10-23.md, CLAUDE.md and slides 9 and 13 of the deck. Fix the two issues:
1) memledger/guards/contradiction.py: only run NLI on claim pairs that share a subject (named entity / project
   codename / vendor, or the (subject, property) of an extracted triple); require P(contradiction) >= 0.9 and a margin
   over P(entailment). Add the three pairs from the doc as tests (different projects = no conflict; same project,
   different value = conflict; changed bank account = conflict or update).
2) memledger/policy/gate.py: Ctx(a) = only the claims that supplied the call's parameter values (none when every
   high-risk parameter is registry-bound). Keep the taint rule for model-supplied parameters. Tests: contested but
   irrelevant memories + registry-bound payment -> allowed; attacker account taken from memory -> blocked.
Then re-run docs/testing/local_bench.py with --checkers hf on the dev split (or the lexical backend if no models)
and report legit-payment ok, leak rate and attack success per version. Then tune cut-offs on the BIPIA TRAIN split
only. make test + make lint green; push and report the compare URL.
```

## M3 — Ahan (branch `m3/attacks`, from `m3/episode-v1`)
```
Read CLAUDE.md, docs/prompts/M3_attacks_data.md (Day 3) and docs/proposals/episode-format.md. attacks/ is still empty.
Implement the Day 3 attack library emitting Episode v1: AgentPoison-style optimised record and PoisonedRAG-style
planted documents, MINJA-style query-only injection, fake-fact poison (Acme account), summary laundering, repetition
flooding, direct DB tampering (content, timestamps, links, labels, deletion) and the 8 isolation attack types x 6 access
paths (slide 22). Every episode has ground truth (blocked / forbidden / forbidden_tool_calls) and a fixed seed;
dev/test split fixed. Then generate the final test set (do not tune on it) and a dev set >= 150 episodes, and update
the benchmark loaders' small subsets to Episode v1. make test + make lint green; push and report.
```

## M4 — Omkaar (branch `m4/runner-v1`, from `m1/hardening` after `m3/episode-v1` merges)
```
Read CLAUDE.md, docs/proposals/episode-format.md, docs/testing/local_run_2026-10-23.md and docs/prompts/M4_eval_demo.md.
1) Switch eval/ to memledger.agent.episode (Episode v1): delete eval/episode.py, map attacker_goal ->
   expect.forbidden_tool_calls, ingest seeds first, support the `task` op by calling memledger.agent.runner.run_episode
   with OpenAICompatLLM (send {"think": false} for qwen3 on Ollama/vLLM; otherwise each call is ~30x slower).
2) Add per-episode wall time and LLM token counts to results; keep the cost logger for Brev.
3) Run all 5 versions on M3's dev set locally (qwen3:8b) then on Brev (L4/L40S, stop the instance after);
   produce docs/results.md with 95% Wilson intervals and the rule-of-three bound for zero leaks.
4) Start demo/app.py (Streamlit): slide-5 Acme scenario side by side (plain vs MemLedger), lineage view via
   explain(), flag source -> quarantine/restore, tamper detection. Demo is due Sun 26 Oct.
make test + make lint green; push and report the compare URL.
```
