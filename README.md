# MemLedger

Provenance-governed memory for long-running AI agents — AEGIS 2026 (Infosys × IISc × NVIDIA), problem statement
*Agent Memory Governance Evaluation*. Team **Prompt Stars**: Banaj Mahajan, Ahan Phatak, Omkaar Nerurkar, Aditya Garg.

MemLedger puts a memory service between an AI agent and its storage. It records where every memory came from,
scores trust with a justification-based truth maintenance system, checks new memories for hallucination,
contradictions and poisoning, enforces access and risky-action rules in code, and detects direct tampering
with a signed hash chain. It ships with an evaluation suite comparing five versions, from plain RAG memory to the full system.

- Design: [`docs/AEGIS2026_MemLedger.pdf`](docs/AEGIS2026_MemLedger.pdf)
- Plan: [`docs/TEAM_PLAN.md`](docs/TEAM_PLAN.md) · Prompts per member: [`docs/prompts/`](docs/prompts/) · Interfaces: [`docs/interfaces.md`](docs/interfaces.md)

## Quick start
```bash
make setup   # creates .venv and installs dev deps
make test
make web     # the MemLedger console on http://127.0.0.1:8000 (web/README.md)
```

## Layout
`memledger/` core, store, retrieval (M1) · guards, policy, registry (M2) · agent (M3) — `bench/ attacks/ scenarios/` (M3)
— `eval/ demo/ infra/` (M4) — `web/` console (M3) — `tests/` — `docs/`
