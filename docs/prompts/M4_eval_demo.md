# M4 — Eval & demo (eval/, demo/, infra/). You own the Brev budget.

## Day 1 (22 Oct) — branch m4/infra
Read CLAUDE.md, docs/TEAM_PLAN.md and slides 17-19 of the deck. infra/: Dockerfile (Python 3.11, vLLM, transformers,
sentence-transformers), brev_setup.sh (clone repo into /home/ubuntu/workspace, start vLLM OpenAI server for an 8-12B
model), a token + dollar logger appending to infra/budget.csv, and a README with stop-the-instance rules. eval/metrics.md:
every metric on slides 18-19 with its exact formula.

## Day 2 (23 Oct) — branch m4/runner
eval/runner.py: runs Episodes (from M3) through the agent with one of 5 versions (baseline, +provenance, +write_checks,
full, full_no_registry) built as config flags on M1's LedgerService (MockMemoryService = baseline until then). Saves
per-episode JSONL results under results/ (gitignored raw, committed summaries). First baseline run on a small subset.

## Day 3 (24 Oct) — branch m4/metrics
eval/metrics.py: all safety and cost metrics (slides 18-19) with 95% Wilson intervals and the rule-of-three bound for
zero events; eval/isolation.py: properties I1-I10 with canary oracles and the differential I7 test (fixed seed,
temperature 0, KS test on latency with Holm correction). Unit tests on synthetic results.

## Day 4 (25 Oct) — branch m4/gpu-runs
On Brev: run all 5 versions on the dev subset; threshold sweep support for M2 (pick setting: most attacks blocked with
<=5% harmless rejections). Log cost. Stop the instance after each run.

## Day 5 (26 Oct) — branch m4/results-demo
Final test-set run (no tuning after this). eval/report.py -> docs/results.md with tables per version and a slide-claim
traceability table. demo/app.py (Streamlit): the slide 5 Acme scenario side by side (plain vs MemLedger), lineage view
(explain), flag source -> quarantine/restore, tamper detection.

## Day 6 (27 Oct)
Test M3's area (agent, bench, attacks, scenarios) against the checklist; update numbers for the slides; v1.0 sign-off.

## Next (24 Oct)
See docs/prompts/NEXT_STEPS_2026-10-24.md — it supersedes the remaining days above where they differ.
