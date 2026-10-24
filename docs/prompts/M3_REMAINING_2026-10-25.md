# M3 (Ahan) — remaining setup, consistency audit and front-end check (25–26 Oct)

Base for everything: branch `integration/v1` (all member work merged; 340 tests; 7 new attack families). Work on
branches cut from it: `git fetch && git checkout -b <branch> origin/integration/v1`, then paste the block into Claude
Code. Changes in other members' areas only with a note in the PR listing every change (CLAUDE.md rule).

## 1. Setup still missing — branch `m3/setup-final`
```
Read CLAUDE.md, docs/TEAM_PLAN.md, docs/prompts/NEXT_STEPS_2026-10-24.md and attacks/suite.py.
Make the project reproducible from a fresh clone on the Mac AND on Brev:
a) `make setup-models`: create .venv, install extras [dev,models,store,demo], download the checker models
   (lytang/MiniCheck-RoBERTa-Large incl. pytorch_model.bin, cross-encoder/nli-deberta-v3-base,
   protectai/deberta-v3-base-prompt-injection-v2, BAAI/bge-m3; meta-llama/Llama-Prompt-Guard-2-86M only if HF_TOKEN
   is set and the licence was accepted) into the HF cache. Never commit weights.
b) `make data`: run `python -m bench.download` for memshield-bench, MemEvoBench, BIPIA (train/test), InjecAgent,
   AgentDojo into data/ (gitignored); print sizes and licences; skip gracefully if offline.
c) `make suite`: build data/attacks/{dev,test}.jsonl + manifest.json (attacks.suite) INCLUDING the downloaded
   benchmarks; commit only the manifest (counts + sha256) as docs/results/suite_manifest.json so runs are traceable.
d) memshield classifier: run memledger/guards/train/train_memshield.py on the memshield TRAIN split (validation for
   early stopping), report test-split precision/recall in docs/results/memshield.md, save weights outside git
   (models/memshield/) and set $MEMLEDGER_MEMSHIELD_MODEL in the Makefile targets.
e) infra/brev_setup.sh: clone, `make setup-models data suite`, start vLLM (Qwen3-8B or Llama-3.1-8B) with an
   OpenAI-compatible server; document "think": false for qwen3 (30x faster); cost logger to infra/budget.csv;
   stop-instance reminder.
f) README "Reproduce" section: Mac (Ollama) and Brev (vLLM) commands for `make eval-local` and the final test run.
make test + make lint green; push; report the compare URL and the suite manifest counts.
```

## 2. Consistency audit (everything ties up) — branch `m3/consistency-audit`
```
Audit integration/v1 end to end and write docs/testing/consistency_audit.md. Fix only what is in M3's area; list
everything else as findings with file:line and owner (M1/M2/M4). Check:
1. Interfaces: every class implementing MemoryService / Check / InputScreen / ActionGate matches
   memledger/core/interfaces.py; exactly one Episode, Session, Verdict type; no module imports another member's
   internals instead of the interface.
2. One source of truth: version flags (memledger/core/factory.py FLAGS vs eval/versions.py vs docs/interfaces.md),
   step numbers 1-8 (Figure 3) in docstrings, source priors (core/mock.py vs core/trust.py vs deck slide 7:
   0.95/0.9/0.7/0.3), thresholds (one config place), model ids (guards/models.py vs Makefile vs infra/ vs README).
3. Data flow: run one episode of every attack family through all 5 versions with the fake LLM and assert: every
   write goes through MemoryService; exposed_to recorded; trust computed; hash chain verifies; labels set; and
   attacks/oracle.py agrees with eval/metrics.py (same episode -> same verdict).
4. Splits: no episode, canary, vendor account or benchmark item in both dev and test (hash-compare
   data/attacks/dev.jsonl vs test.jsonl); BIPIA train only for tuning; InjecAgent/AgentDojo only in test.
5. Deck vs code: for each claim in docs/AEGIS2026_MemLedger.pdf (slides 4-19, appendix A1-A3) name the file/test
   that implements or measures it; mark NOT IMPLEMENTED where missing. Put this traceability table in the doc.
6. Hygiene: no secrets/keys/weights/data in git history (search `git log --all -p` for PRIVATE KEY, .env,
   .safetensors, .bin), no dead modules, no TODO/FIXME, CI matches Makefile targets, code runs on Python 3.11 (CI)
   even though Macs run 3.14, *.egg-info not tracked.
Add tests for every rule you can automate (tests/test_consistency.py). make test + make lint green; push.
```

## 3. Front end (owner M4; M3 tests it) — branch `m3/demo-check`, findings only
Current demo: `streamlit run demo/app.py` — tabs: Acme side-by-side (slide 5), Lineage (explain), Clean-up
(flag -> quarantine/restore), Tamper, Results (reads docs/results.md).
```
Start the demo from a fresh clone (`make setup-models`, then `streamlit run demo/app.py`) and test every tab with
the fake LLM and with Ollama qwen3:8b. Write docs/testing/demo_check.md: steps, screenshots, timings, failures.
Do not edit demo/; list findings for M4, at least:
- add an Isolation tab (team A writes, team B asks; withheld result, canary never shown);
- add a "Run attack family" panel that plays one episode per family from data/attacks/dev.jsonl on baseline vs full;
- Results tab: read docs/results.md from eval.report, with a clear message if it is missing;
- offline mode: fake LLM + lexical checkers so the demo never depends on Wi-Fi on 30 Oct;
- a 3-minute scripted demo path and a screen recording as fallback.
```

## Deadlines
1 and 2 by Sun 26 Oct 12:00 (M4 then runs the final Brev test on a reproducible setup); 3 by Sun 26 Oct 18:00.
Mon 27 Oct: test M2's area (guards/policy/registry) per docs/TEAM_PLAN.md.
