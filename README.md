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
make setup   # creates .venv and installs dev deps (enough for tests; see Reproduce for real runs)
make test
```

## Reproduce
Same make targets on a Mac and on Brev. Data, models and weights stay out of git (`data/`, `models/`, HF cache);
only the suite manifest (`docs/results/suite_manifest.json`: counts + sha256 per split) is committed, so a run can
be traced to the exact episodes.

**Mac (Ollama, CPU/MPS checkers)**
```bash
make setup-models          # .venv with [dev,models,store,demo] + checker models (vLLM is skipped on macOS)
make data suite            # benchmarks into data/, attack suite into data/attacks + manifest
make memshield             # optional: fine-tune the memshield screen into models/memshield (picked up automatically)
ollama pull qwen3:8b && ollama serve
make eval-local            # dev split, all 5 versions; the runner turns qwen3 thinking off ("think": false)
```

**Brev (vLLM on one L4/L40S)**
```bash
curl -fsSL https://raw.githubusercontent.com/bm2772/MemLedger/main/infra/brev_setup.sh -o brev_setup.sh
BRANCH=main MODEL=Qwen/Qwen3-8B bash brev_setup.sh     # = make setup-models data suite + vLLM on :8000
cd /home/ubuntu/workspace/MemLedger
PYTHONPATH=. .venv/bin/python -u -m attacks.evaluate --split test --llm openai --model Qwen/Qwen3-8B \
    --base-url http://localhost:8000/v1 --guards hf --out results/attacks --run-id brev-final
python infra/cost_logger.py session ...   # then STOP the instance (infra/README.md)
```
The final test run uses `--split test` once, after all tuning on dev is finished. Check that
`docs/results/suite_manifest.json` matches the manifest printed by `make suite` before reporting numbers.

## Layout
`memledger/` core, store, retrieval (M1) · guards, policy, registry (M2) · agent (M3) — `bench/ attacks/ scenarios/` (M3)
— `eval/ demo/ infra/` (M4) — `tests/` — `docs/`
