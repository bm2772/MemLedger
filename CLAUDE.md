# MemLedger — instructions for every Claude Code session

Project: provenance-governed memory for long-running AI agents (AEGIS 2026, team Prompt Stars).
Spec: `docs/AEGIS2026_MemLedger.pdf` (the deck). Plan and deadlines: `docs/TEAM_PLAN.md` (v1.0 on 27 Oct 2026).
Interfaces: `docs/interfaces.md` + `memledger/core/{types,interfaces}.py` (frozen; changes need M1 approval).

## Ownership (only edit your own area)
- M1 Core: memledger/core, memledger/store, memledger/retrieval
- M2 Guardrails: memledger/guards, memledger/policy, memledger/registry
- M3 Attacks & data: memledger/agent, bench/, attacks/, scenarios/
- M4 Eval & demo: eval/, demo/, infra/
If you need a change outside your area, open an issue or ask the owner; do not edit it.

## Architecture rules (from the deck — do not violate)
- The agent never touches storage: every read/write goes through MemoryService.
- Identity (team, role, clearance) comes from `Session`, never from model output or tool arguments.
- Provenance edges are recorded by the service: `exposed_to` = everything in the context window; `supported_by` = verifier-confirmed.
- Trust (JTMS): T = s * min(parent trust); noisy-OR only across derivations with disjoint origins; retraction quarantines
  claims with no valid justification left and restores the rest. The JTMS is plain code, no model.
- Content is append-only; status changes go to an audited log; hash = SHA-256(content || record time || sorted parent hashes);
  signed Merkle root appended to the hash log after each write batch.
- Registry facts (accounts, contacts, limits) come only from the Ed25519-signed registry; high-risk tool parameters are
  bound from the registry, never from model text.
- Training/tuning data never overlaps test data (BIPIA train split only for tuning; InjecAgent, AgentDojo test only).

## Conventions
- Python 3.11, type hints, dataclasses from memledger/core/types.py. Small modules, docstrings say which slide they implement.
- Tests first; `make test` and `make lint` must pass before every commit. Use MockMemoryService to work in parallel.
- Never commit secrets, .env, keys, model weights or datasets (download scripts only). Models run via vLLM/Ollama/HF.
- Branch `m<N>/<task>`, small PRs, 1 review from another member. Pull before each session.
