#!/usr/bin/env bash
# Brev GPU instance bootstrap (M4). Idempotent: safe to re-run after a restart.
#   1. clone/update the repo into $WORKSPACE/MemLedger (default ~/workspace: the login user differs per provider)
#   2. `make setup-models data suite`: Python 3.11 .venv with every extra (incl. vLLM), checker models in the HF
#      cache, benchmarks in data/, attack suite in data/attacks (same commands as on a Mac)
#   3. fine-tune the memshield write-time classifier if models/memshield is missing (`make memshield`, minutes on a GPU)
#   4. start a vLLM OpenAI-compatible server for the 8-12B main model on :$PORT and wait until healthy
# Usage:  bash brev_setup.sh            (env: MODEL, PORT, MAX_MODEL_LEN, GPU_UTIL, BRANCH, HF_TOKEN, MEMSHIELD_REPO)
# Then:   make eval-brev-smoke && make eval-brev        (infra/README.md "Final run")
# The checker models share the GPU with vLLM: GPU_UTIL (default 0.80) leaves them room; use a 40 GB+ GPU (L40S/A100).
# Qwen3: send {"think": false} / chat_template_kwargs {"enable_thinking": false} with every request; with thinking
# on, each call is ~30x slower (docs/testing/local_run_2026-10-23.md).
# STOP THE INSTANCE when done (see infra/README.md) and log the session with infra/cost_logger.py.
set -euo pipefail

WORKSPACE=${WORKSPACE:-$HOME/workspace}  # ubuntu on some providers, shadeform on massedcompute
REPO_URL=${REPO_URL:-https://github.com/bm2772/MemLedger.git}
BRANCH=${BRANCH:-integration/v1}  # the branch with every merged PR until v1.0 is on main
MODEL=${MODEL:-Qwen/Qwen3-8B}
PORT=${PORT:-8000}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-16384}
GPU_UTIL=${GPU_UTIL:-0.80}
REPO=$WORKSPACE/MemLedger
VENV=$REPO/.venv  # created by `make setup-models`
LOG=$WORKSPACE/vllm.log

mkdir -p "$WORKSPACE"
export HF_HOME=$WORKSPACE/hf-cache  # keep weights on the persistent disk, never in the repo

if [ -d "$WORKSPACE/MemLedger/.git" ]; then
  git -C "$WORKSPACE/MemLedger" fetch origin && git -C "$WORKSPACE/MemLedger" checkout "$BRANCH" \
    && git -C "$WORKSPACE/MemLedger" pull --ff-only
else
  git clone --branch "$BRANCH" "$REPO_URL" "$WORKSPACE/MemLedger"
fi

if ! command -v python3.11 >/dev/null; then
  sudo apt-get update && sudo apt-get install -y software-properties-common
  sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update
  sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
fi
make -C "$REPO" PY=python3.11 setup-models data suite
# prefer Ahan's model (docs/results/memshield.md): MEMSHIELD_REPO=<hf user>/<repo> downloads it from the Hugging Face
# Hub, or scp it to $REPO/models/memshield first (infra/README.md); otherwise fine-tune one here
if [ ! -f "$REPO/models/memshield/config.json" ] && [ -n "${MEMSHIELD_REPO:-}" ]; then
  "$VENV/bin/python" -c "from huggingface_hub import snapshot_download as d; d('$MEMSHIELD_REPO', local_dir='$REPO/models/memshield')"
fi
[ -f "$REPO/models/memshield/config.json" ] || make -C "$REPO" memshield  # data/memshield comes from `make data`

if curl -sf "http://localhost:$PORT/health" >/dev/null; then
  echo "vLLM already running on :$PORT"
else
  echo "starting vLLM ($MODEL) on :$PORT, log: $LOG"
  nohup "$VENV/bin/vllm" serve "$MODEL" --host 0.0.0.0 --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" --gpu-memory-utilization "$GPU_UTIL" --served-model-name main "$MODEL" \
    >"$LOG" 2>&1 &
  for _ in $(seq 1 120); do  # weights download + load can take several minutes
    curl -sf "http://localhost:$PORT/health" >/dev/null && break
    sleep 10
  done
  curl -sf "http://localhost:$PORT/health" >/dev/null || { echo "vLLM did not come up; see $LOG"; exit 1; }
fi

nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv || true
echo "ready: OPENAI_BASE_URL=http://localhost:$PORT/v1, model $MODEL (not 'main': the full qwen3 name switches thinking off)"
echo "memshield: $(cat "$REPO/models/memshield/test_metrics.json" 2>/dev/null | head -c 300)"
echo "next: export HF_HOME=$HF_HOME; cd $REPO && make eval-brev-smoke MODEL=$MODEL && make eval-brev MODEL=$MODEL"
echo "suite: $(cat "$REPO/docs/results/suite_manifest.json" | head -c 300)..."
echo "reminder: python infra/cost_logger.py session ... (appends to infra/budget.csv) when done, then STOP the instance"
echo "backstop: sudo shutdown -h +240   # never leave the GPU running idle"
