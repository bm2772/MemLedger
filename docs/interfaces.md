# Interfaces (frozen 22 Oct; changes need M1 approval)

Code: `memledger/core/types.py`, `memledger/core/interfaces.py`, stand-in `memledger/core/mock.py`.

| Interface | Owner | Methods | Deck |
|---|---|---|---|
| `MemoryService` | M1 | `ingest(content, kind, session) -> Source`; `propose_write(WriteProposal) -> WriteResult`; `retrieve(query, session, k) -> [RetrievedMemory]`; `flag_source(id, reason) -> {quarantined, restored}`; `explain(claim_id) -> lineage` | slides 6, 7, 10, 14, 15 |
| `InputScreen` | M2 | `score(text) -> float` (high = injected) | slide 12 |
| `Check` | M2 | `check(proposal, sources) -> Verdict` — hallucination, contradiction, registry, memshield | slides 11, 13 |
| `ActionGate` | M2 | `allow(tool, params, context_claim_ids, session) -> Verdict` | slides 9, 11 |

## The five versions (eval flags, M4)
1. `baseline` — plain retrieval memory  2. `+provenance` — graph and trust  3. `+write_checks`  4. `full` — + access
control and action gate  5. `full_no_registry`.

## Step numbers (Figure 3)
1 screen input · 2 hallucination check (+ memshield) · 3 registry match · 4 contradiction + trust · 5 retrieve ·
6 read filter · 7 build context · 8 action gate.
