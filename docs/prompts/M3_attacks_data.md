# M3 — Attacks & data (memledger/agent, bench/, attacks/, scenarios/)

## Day 1 (22 Oct) — branch m3/agent
Read CLAUDE.md, docs/interfaces.md, core/types.py and slides 5, 10, 21-23 of the deck. Implement memledger/agent: a
minimal tool-using agent loop whose ONLY memory access is a MemoryService (use MockMemoryService now). LLM backend is
injectable: OpenAI-compatible client (works with local Ollama and vLLM on Brev) plus a deterministic fake for tests.
Tools: search_docs, read_web, send_email, send_payment(vendor) (stubs that record calls). Tests with the fake LLM.

## Day 2 (23 Oct) — branch m3/scenarios-bench
scenarios/: generator for the two-team research-lab world (slide 21): >=3 teams for isolation tests, two clearance
levels, every memory with a 128-bit canary and a made-up canary fact, registry facts, known ground truth, attack and
clean sessions, JSON output with dev/test split fixed by seed. bench/: download+loader scripts (data never committed,
stored under data/) for LongMemEval (s subset), LoCoMo, BIPIA (train/test), InjecAgent, AgentDojo, memshield-bench,
MemEvoBench, RAGTruth, HaluEval, LLM-AggreFact — each returns a common Episode format; small default subsets.

## Day 3 (24 Oct) — branch m3/attacks
attacks/: poisoning (AgentPoison-style optimised record and PoisonedRAG-style planted docs on our store), MINJA-style
query-only injection, fake-fact poison (the Acme bank account example), summary laundering, repetition flooding,
direct DB tampering (content, timestamps, links, deletion), and the 8 isolation attack types x 6 access paths (slide
22). Each attack yields Episodes with ground-truth labels of what should be blocked. Optional if time: garak/PyRIT
wrappers using an attacker LLM.

## Day 4 (25 Oct) — branch m3/integration
Run the agent against M1's real service with M2's checks on the scenario set; fix loaders/attacks. Freeze 18:00.

## Day 5–6 (26–27 Oct)
Generate the final test set (no peeking during tuning). On 27 Oct test M2's area (guards/policy/registry) and file issues.

## Next (24 Oct)
See docs/prompts/NEXT_STEPS_2026-10-24.md — it supersedes the remaining days above where they differ.

## Remaining (25-26 Oct)
See docs/prompts/M3_REMAINING_2026-10-25.md (setup, consistency audit, demo check).

## Review and stress test (24-25 Oct)
See docs/testing/RESULTS_AND_REVIEW_2026-10-24.md, section D.

## To do: fine-tune the memshield classifier (25 Oct) — branch `m3/memshield-finetune` from origin/integration/v1
Paste into Claude Code:
```
Read docs/testing/RESULTS_AND_REVIEW_2026-10-24.md section E and memledger/guards/train/train_memshield.py.
1. pip install -e '.[models]' datasets
2. python -m memledger.guards.train.train_memshield --out models/memshield --epochs 3 --lr 2e-5 --batch 16 --max-length 512
   (train split only; models/ is gitignored - never commit weights; log GPU/Mac time in infra/budget.csv)
3. If test recall < 0.8: add class weights or oversample poisoned entries (602 clean / 222 poisoned in train) and pick
   the decision threshold on the VALIDATION split (max recall with <= 5% false rejections). Never tune on test.
4. export MEMLEDGER_MEMSHIELD_MODEL=models/memshield and rerun: the write-path-as-classifier test (memshield and
   MemEvoBench, test split) and the agentpoison family on all 5 versions (fake agent + HF checkers, then qwen3:8b with
   think:false on 10 episodes per family).
5. Write docs/results/memshield.md: training settings, validation threshold, test precision/recall/F1, before/after
   recall of the write path (was 0.07 memshield / 0.03 MemEvoBench) and any change in harmless writes rejected.
6. Tell Aditya (M2) the model path and threshold so the default config uses them. make test + make lint green; push.
```
Due: Sun 26 Oct 12:00 (before the final Brev run).
