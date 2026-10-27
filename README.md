# MemLedger

**Provenance-governed memory for long-running AI agents.** AEGIS 2026 (Infosys × IISc × NVIDIA), problem statement
*Agent Memory Governance Evaluation*. Team **Prompt Stars**: Banaj Mahajan, Aditya Garg, Ahan Phatak, Omkaar Nerurkar.

AI agents that remember what they read can be poisoned: one malicious page can plant a false "fact" that later makes
the agent pay the wrong account or leak another team's data. MemLedger sits between the agent and its storage:

- **Provenance:** every memory records its source, what the agent saw, and which sources actually support each fact.
- **Trust:** trust comes from independent origins, maintained by a justification-based truth maintenance system (JTMS).
- **Write checks:** before anything is stored, it is checked for injection, hallucination, contradiction, poisoning
  and protected registry facts.
- **Retraction:** when a source turns out to be poisoned, exactly the memories that depended on it are quarantined.
- **Integrity:** direct database edits are detected on read (signed Merkle hash chain) and fail closed.
- **Actions:** risky tool parameters (accounts, recipients) come only from an Ed25519-signed registry, never from model text.

Slides: [`docs/MemLedger_presentation.pdf`](docs/MemLedger_presentation.pdf) · Results:
[`docs/results/final_numbers_v1.md`](docs/results/final_numbers_v1.md) · Interfaces: [`docs/interfaces.md`](docs/interfaces.md)

## Results (v1.0)

Test split: 2,299 episodes per version (AgentDojo, BIPIA, InjecAgent, MemEvoBench, MemShield-bench and 740 multi-team
scenario episodes, each attack with a harmless twin). 95% Wilson intervals are in [`docs/results.md`](docs/results.md).

| version | attack success | hijacked actions | leaks | tamper detected | harmless writes rejected | task accuracy |
|---|---|---|---|---|---|---|
| plain memory | 58.7% | 49.6% | 14.5% | 0/72 | 0% | 88.2% |
| **MemLedger (full)** | **4.2%** | **0/838** | **0/2299** | **72/72** | 5.6% | 84.0% |

Added latency: +25.5 ms per write, +0.8 ms per read. Known weak spots (MemEvoBench, BIPIA over-blocking, contradiction
false positives) are listed in the results doc.

## Try it (no GPU, about 2 minutes)

Requirements: Python 3.11, Node 18+ (for the console UI), `make`.

```bash
make setup          # .venv with the dev dependencies
make test           # ~540 tests
make web            # console on http://127.0.0.1:8000, then open http://127.0.0.1:8000/tour
```

The **"How it works" tour** (`/tour`) plays one story on plain memory and on MemLedger side by side, step by step:
- an injected page is screened out;
- poisoned writes are refused;
- flagging a source quarantines only what depended on it;
- new evidence restores a memory;
- a database edit is caught;
- an attacker's payment is blocked.

Every outcome is computed live by the real services; the default checkers are lightweight and offline.

Streamlit demo (alternative): `pip install -e ".[demo]" && bash demo/run.sh` (see [`demo/README.md`](demo/README.md)).

## Reproduce the evaluation

Data, models and weights are not in git. The `make` targets download them. The committed suite manifest
(`docs/results/suite_manifest.json`, counts and sha256 per split) ties a run to its exact episodes.

**Real checker models** (DeBERTa-v3 memshield and NLI, MiniCheck, Prompt Guard 2; Prompt Guard 2 is gated on Hugging
Face, so log in with `hf auth login` after access is granted):
```bash
make setup-models data suite      # extras + checker models, benchmarks into data/, attack suite + manifest
MEMLEDGER_GUARD_BACKEND=hf make web   # the console and tour with the real checkers
```

**GPU run on NVIDIA Brev** (one L40 or L40S; vLLM serves the agent model):
```bash
curl -fsSL https://raw.githubusercontent.com/bm2772/MemLedger/main/infra/brev_setup.sh -o brev_setup.sh
BRANCH=main MODEL=Qwen/Qwen3-8B bash brev_setup.sh     # = make setup-models data suite + vLLM on :8000
cd ~/workspace/MemLedger
export MEMLEDGER_NLI_MODEL=MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli
PYTHONPATH=. .venv/bin/python -u -m attacks.evaluate --split test --llm openai --model Qwen/Qwen3-8B \
    --base-url http://localhost:8000/v1 --guards hf --out results/attacks --run-id my-run --workers 16
PYTHONPATH=. .venv/bin/python -m eval.report results/attacks/my-run/summary.json --out docs/results.md
```

**NVIDIA Nemotron as the agent** (`nvidia/NVIDIA-Nemotron-Nano-9B-v2`). Serve it with NVIDIA's tool-call parser from the
model repo and the chat template in `infra/nemotron/`, which turns thinking off by default:
```bash
hf download nvidia/NVIDIA-Nemotron-Nano-9B-v2 nemotron_toolcall_parser_no_streaming.py --local-dir .
vllm serve nvidia/NVIDIA-Nemotron-Nano-9B-v2 --trust-remote-code --mamba_ssm_cache_dtype float32 \
    --max-model-len 16384 --enable-auto-tool-choice --tool-parser-plugin nemotron_toolcall_parser_no_streaming.py \
    --tool-call-parser nemotron_json --chat-template infra/nemotron/chat_template_nothink.jinja
```
Then run the same `attacks.evaluate` command with `--model nvidia/NVIDIA-Nemotron-Nano-9B-v2`.

**Rules for the numbers:**
- All tuning (thresholds, model choices) is done on the dev split; the test split is run once.
- InjecAgent and AgentDojo are test-only.
- Latency comes from a 1-worker run (`--workers 1 --limit-per-family 5`).

## Layout

| path | what |
|---|---|
| `memledger/core, store, retrieval` | the memory service: provenance graph, JTMS trust, hash chain, retrieval |
| `memledger/guards, policy, registry` | input screen, write checks, access control, action gate, signed registry |
| `memledger/agent` | tool-using agent loop that only touches memory through the service |
| `attacks/, bench/, scenarios/` | attack families, benchmark loaders, multi-team scenario generator, oracle |
| `eval/` | five-version runner (plain memory → full MemLedger), metrics, report |
| `web/` | MemLedger console (FastAPI + React) with the "How it works" tour |
| `demo/` | Streamlit demo |
| `infra/` | Brev setup, Docker, cost logger |
| `docs/` | slides, interfaces, results |
| `results/attacks/` | summaries of the reported runs (raw rows are not committed) |
