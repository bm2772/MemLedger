PY ?= $(shell command -v python3.11 || command -v python3 || command -v python)
DATA_SETS = memshield memevobench bipia injecagent agentdojo
MEMSHIELD_DIR ?= models/memshield
# Prompt Guard 2 is gated: without HF_TOKEN use the ungated ProtectAI classifier (tuned cut-off in guards/models.py)
export MEMLEDGER_PROMPT_GUARD_MODEL ?= $(if $(HF_TOKEN),meta-llama/Llama-Prompt-Guard-2-86M,protectai/deberta-v3-base-prompt-injection-v2)
# use the fine-tuned memshield classifier once `make memshield` has produced it (models/ is gitignored)
export MEMLEDGER_MEMSHIELD_MODEL ?= $(if $(wildcard $(MEMSHIELD_DIR)/config.json),$(abspath $(MEMSHIELD_DIR)))

.PHONY: setup setup-models data suite memshield test lint eval-local

# never re-create an existing .venv with another Python (that mixes site-packages); delete .venv to change Python
VENV = [ -x .venv/bin/python ] || $(PY) -m venv .venv

setup:
	$(VENV)
	.venv/bin/python -m pip install -e ".[dev]"
setup-models:  # everything for real runs: extras + checker models in the HF cache (vLLM only on Linux)
	$(VENV)
	.venv/bin/python -m pip install -q --upgrade pip
	.venv/bin/python -m pip install -e ".[dev,models,store,demo]" agentdojo certifi
	.venv/bin/python -m bench.fetch_models
data:  # published benchmarks into data/ (gitignored); skips what is offline or gated
	.venv/bin/python -m bench.download $(DATA_SETS)
suite:  # dev/test attack suite incl. downloaded benchmarks; only the manifest is committed
	PYTHONPATH=. .venv/bin/python -m attacks.suite --out data/attacks --manifest docs/results/suite_manifest.json
memshield:  # fine-tune the write-time memory screen on memshield TRAIN (threshold picked on validation)
	# float32 works on MPS (~9 min on an M4, see docs/results/memshield.md); unload Ollama models first
	PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.8 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.6 \
	.venv/bin/python -m memledger.guards.train.train_memshield --data data/memshield --out $(MEMSHIELD_DIR) \
		--epochs 3 --lr 2e-5 --batch 2 --grad-accum 8 --max-length 384
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check .
eval-local:  # dev split, all 5 versions, qwen3:8b on local Ollama (thinking off), HF checkers if installed
	PYTHONPATH=. .venv/bin/python -u -m attacks.evaluate --split dev --llm openai --model qwen3:8b \
		--base-url http://localhost:11434/v1 --guards auto --out results/attacks --run-id local-$$(date +%Y%m%d-%H%M)
web-build:  # the console UI (web/ui) -> web/ui/dist, served by the API server
	cd web/ui && npm ci --no-audit --no-fund && npm run build
web: web-build  # console on http://127.0.0.1:8000 (open mode: local only; set MEMLEDGER_USERS to deploy)
	.venv/bin/python -m pip install -q -e ".[web]"
	.venv/bin/python -m web
web-dev:  # API on :8000 + Vite dev server with hot reload on :5173
	.venv/bin/python -m web & cd web/ui && npm run dev
