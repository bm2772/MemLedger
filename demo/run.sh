#!/usr/bin/env bash
# Start the demo in offline mode: fake (fooled) agent model, lexical checkers, no Hugging Face or telemetry calls.
# It never depends on Wi-Fi. For a real model, start Ollama/vLLM and pick it in the sidebar.
set -euo pipefail
cd "$(dirname "$0")/.."
export MEMLEDGER_GUARD_BACKEND=${MEMLEDGER_GUARD_BACKEND:-lexical}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
exec "${PYTHON:-.venv/bin/python}" -m streamlit run demo/app.py --browser.gatherUsageStats false \
  --server.headless true --theme.base dark --theme.primaryColor "#2ea043" --client.toolbarMode viewer "$@"
