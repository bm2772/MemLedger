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
