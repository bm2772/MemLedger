#!/usr/bin/env bash
# Brev GPU instance bootstrap (M4). Idempotent: safe to re-run after a restart.
#   1. clone/update the repo into /home/ubuntu/workspace/MemLedger
#   2. create a Python 3.11 venv with vLLM + transformers + sentence-transformers
#   3. start a vLLM OpenAI-compatible server for the 8-12B main model on :$PORT and wait until healthy
# Usage:  bash brev_setup.sh            (env: MODEL, PORT, MAX_MODEL_LEN, BRANCH, HF_TOKEN)
# Then:   export OPENAI_BASE_URL=http://localhost:8000/v1 OPENAI_API_KEY=EMPTY  and run eval/.
# STOP THE INSTANCE when done (see infra/README.md) and log the session with infra/cost_logger.py.
set -euo pipefail

WORKSPACE=/home/ubuntu/workspace
REPO_URL=${REPO_URL:-https://github.com/bm2772/MemLedger.git}
BRANCH=${BRANCH:-main}
MODEL=${MODEL:-Qwen/Qwen3-8B}
PORT=${PORT:-8000}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-16384}
VENV=$WORKSPACE/.venv
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
[ -x "$VENV/bin/python" ] || python3.11 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q "vllm>=0.6" "transformers>=4.44" sentence-transformers
"$VENV/bin/pip" install -q -e "$WORKSPACE/MemLedger[dev,store]"

if curl -sf "http://localhost:$PORT/health" >/dev/null; then
  echo "vLLM already running on :$PORT"
else
  echo "starting vLLM ($MODEL) on :$PORT, log: $LOG"
  nohup "$VENV/bin/vllm" serve "$MODEL" --host 0.0.0.0 --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" --served-model-name main >"$LOG" 2>&1 &
  for _ in $(seq 1 120); do  # weights download + load can take several minutes
    curl -sf "http://localhost:$PORT/health" >/dev/null && break
    sleep 10
  done
  curl -sf "http://localhost:$PORT/health" >/dev/null || { echo "vLLM did not come up; see $LOG"; exit 1; }
fi

nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv || true
echo "ready: OPENAI_BASE_URL=http://localhost:$PORT/v1 model=main"
echo "reminder: python infra/cost_logger.py session ... when done, then STOP the instance"
