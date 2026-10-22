# M1 — Core (memledger/core, store, retrieval). You are also repo admin.

## Day 1 (22 Oct) — branch m1/store
Read CLAUDE.md, docs/interfaces.md, memledger/core/types.py and interfaces.py, and slides 6, 7, 10, 14 of
docs/AEGIS2026_MemLedger.pdf. Implement memledger/store: a SQLite store (tables: sources, claims, derivations, edges
with type exposed_to|supported_by|contradicts|supersedes, status_log, hash_log) and a Chroma-backed vector index with
one collection per team. Append-only content; status changes only via status_log with reason and timestamp.
Write tests first (tests/store/). Keep to memledger/store. make test and make lint must pass. Commit and push.

## Day 2 (23 Oct) — branch m1/provenance
Implement memledger/core/service.py: class LedgerService implementing MemoryService. ingest() saves a Source with
SHA-256 hash and prior trust by SourceKind. propose_write() records a Derivation whose exposed_to = all context_ids
(recorded by the service, never by the model) and runs a pluggable list of Check objects (constructor argument; empty
list = baseline). Bi-temporal fields on claims. Hash chain: hash = SHA-256(content || recorded_at || sorted parent
hashes); after each write batch build a Merkle root of current hashes, sign it with an Ed25519 key passed in, append to
hash_log; verify on read (recompute + Merkle proof), quarantine on mismatch. explain(claim_id) returns the lineage
tree. Tests for every rule, including a direct-database-edit tamper test.

## Day 3 (24 Oct) — branch m1/trust-retrieval
Implement memledger/core/trust.py (JTMS, slide 7): starting trust per source kind; T = s * min(parent trust) with
s from supported_by scores; noisy-OR across derivations only when their origin sets (all ancestor sources) are
disjoint, merging same-origin copies; contested status when contradicted by higher trust (not an update);
flag_source() withdraws justifications using the source, quarantines claims with none left, restores the rest,
recomputes downstream. Then memledger/retrieval (slide 15): stage 1 = dense search (BGE-M3 via sentence-transformers,
injectable embedder, use a tiny fake in tests) + SQLite FTS5 keyword search in the user's team + shared only, exact
lookup for (subject, property, value) triples, one-hop graph links and newer versions; stage 2 = drop quarantined /
invalid / below-threshold, rank by relevance then trust, attach sources. Include the worked example on slide 7 as a
test (0.81, 0.56, 0.92, retraction to 0.56).

## Day 4 (25 Oct) — branch m1/integration
Integrate M2's checks and M3's agent with LedgerService end to end on one scenario (pull main first). Add the
"added delay" timing hooks M4 needs (per write/read, ms). Fix integration bugs; no new features. Integration freeze 18:00.

## Day 5–6 (26–27 Oct)
Fix bugs from M4's runs. On 27 Oct test M4's area (eval/, demo/) against the final checklist in docs/TEAM_PLAN.md and
file issues; tag v1.0 when all four sign off.
