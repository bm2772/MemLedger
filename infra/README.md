# infra/ — Brev GPU ops (owner: M4)

| File | What |
|---|---|
| `Dockerfile` | Python 3.11 + vLLM + transformers + sentence-transformers; default CMD serves the main model |
| `brev_setup.sh` | Idempotent bootstrap: clone repo into `/home/ubuntu/workspace`, venv, data, suite, memshield fine-tune, start vLLM on `:8000` |
| `cost_logger.py` | Appends one row per GPU session to `budget.csv`; `TokenMeter` counts tokens from responses |
| `budget.csv` | The ledger of every Brev session (committed; no secrets in it) |

## Start a session
```bash
# on the Brev instance (any 24 GB+ GPU fits an 8B model in bf16; L4/A10G is enough for dev runs)
curl -fsSL https://raw.githubusercontent.com/bm2772/MemLedger/main/infra/brev_setup.sh -o brev_setup.sh
MODEL=Qwen/Qwen3-8B bash brev_setup.sh          # gated models (Llama) also need HF_TOKEN in the env
export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY   # served model name: "main"
```
Docker instead: `docker build -f infra/Dockerfile -t memledger:gpu . && docker run --gpus all -p 8000:8000 memledger:gpu`.

## Final run (test split, all 5 versions)
```bash
# 1. GPU: 40 GB+ (L40S 48 GB or A100) - vLLM gets 80% (GPU_UTIL), the checker models the rest
curl -fsSL https://raw.githubusercontent.com/bm2772/MemLedger/integration/v1/infra/brev_setup.sh -o brev_setup.sh
sudo shutdown -h +300                              # backstop: never leave the GPU running
MODEL=Qwen/Qwen3-8B BRANCH=integration/v1 bash brev_setup.sh   # setup, data, suite, memshield fine-tune, vLLM
export HF_HOME=/home/ubuntu/workspace/hf-cache && cd /home/ubuntu/workspace/MemLedger
# 2. smoke: 1 episode per family x 5 versions; must print no "WARNING: ... episodes errored"
make eval-brev-smoke
# 3. the run (16 parallel episodes, resumable: re-run the same command after a crash)
make eval-brev                                     # -> results/attacks/brev-test/{summary,families}.json/.md
make eval-latency                                  # 1 worker: the "added ms" numbers without contention
# 4. export, log, stop
python -m eval.report results/attacks/brev-test/summary.json   # docs/results.md
rsync results/attacks/raw/ <somewhere off the box>             # raw rows are gitignored
python infra/cost_logger.py session --member M4 --instance <name> --gpu L40S --hours <h> --rate <$/h> \
    --purpose "final test run" --from-summary results/attacks/brev-test/summary.json
git add results/attacks/brev-test results/attacks/brev-test-latency docs/results.md infra/budget.csv  # then commit, push
sudo shutdown -h now
```
- Use the full model name (`MODEL=Qwen/Qwen3-8B`): the eval client switches qwen3 thinking off by name; the vLLM
  alias `main` would leave it on (~30x slower).
- `make eval-brev` sets `MEMLEDGER_DEVICE=cuda`; without it the checkers run on the CPU.
- Results from `--workers 16` are identical to a 1-worker run (checked on the offline test split); only the per-episode
  wall time and the added-ms latencies include contention, hence `make eval-latency`.

## Stop-the-instance rules (non-negotiable — the budget is $1,000 for the whole team)
1. **Stop the instance the moment a job finishes.** No idle GPUs overnight, over meals or "in case".
2. **Never start a GPU for something that runs on CPU** (unit tests, the mock baseline, metrics, report, demo dev).
3. **Export results before stopping**: `results/` summaries go into git; raw JSONL is copied off the box
   (`scp`/`rsync`) — it is gitignored. Model weights stay in `/home/ubuntu/workspace/hf-cache`, never in git.
4. **Log every session immediately after stopping**, even short ones:
   `python infra/cost_logger.py session --member M4 --instance <name> --gpu <type> --hours <h> --rate <$/h> --purpose "<job>"`
   then `python infra/cost_logger.py summary`. Tokens come from the runner's `TokenMeter` totals.
5. **Set a hard stop**: before a long job, schedule `sudo shutdown -h +<minutes>` as a backstop.
6. **Ask M4 before** anything over 4 GPU-hours or any GPU larger than a single A100/H100 (e.g. the optional 70B run).
7. **Planned spend** (TEAM_PLAN.md): dev ~$40 · calibration/fine-tune ~$20 · main runs ~$80 · optional larger model
   ~$100 · demo ~$30 → ~$270; the rest is reserve. If `summary` shows >$300 spent, stop and re-plan with the team.
8. No secrets on disk in the repo: `HF_TOKEN` and API keys only as environment variables.
