#!/usr/bin/env bash
# Start the chat demo on the real models: the agent LLM served by vLLM (infra/brev_setup.sh starts it on :8000) and
# the Hugging Face checker models on the GPU. Run it on the Brev instance and open it through a port-forward:
#   (laptop) ssh -L 8501:localhost:8501 <instance>    then http://localhost:8501
set -euo pipefail
cd "$(dirname "$0")/.."
export MEMLEDGER_GUARD_BACKEND=${MEMLEDGER_GUARD_BACKEND:-hf}
export MEMLEDGER_DEVICE=${MEMLEDGER_DEVICE:-cuda}
export MEMLEDGER_LLM_URL=${MEMLEDGER_LLM_URL:-http://localhost:8000/v1}
export MEMLEDGER_LLM_MODEL=${MEMLEDGER_LLM_MODEL:-Qwen/Qwen3-8B}  # full name: the eval client turns qwen3 thinking off
export MEMLEDGER_LLM_KEY=${MEMLEDGER_LLM_KEY:-EMPTY}
if [ -z "${MEMLEDGER_MEMSHIELD_MODEL:-}" ] && [ -d models/memshield ]; then
  export MEMLEDGER_MEMSHIELD_MODEL=models/memshield  # Ahan's fine-tuned classifier, if setup downloaded it
fi
curl -sf "$MEMLEDGER_LLM_URL/models" >/dev/null || { echo "no LLM at $MEMLEDGER_LLM_URL: start vLLM first" >&2; exit 1; }
exec "${PYTHON:-.venv/bin/python}" -m streamlit run demo/app.py --browser.gatherUsageStats false \
  --server.headless true --theme.base dark --theme.primaryColor "#2ea043" --client.toolbarMode viewer "$@"
