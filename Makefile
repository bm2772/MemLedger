PY ?= $(shell command -v python3.11 || command -v python3 || command -v python)
DATA_SETS = memshield memevobench bipia injecagent agentdojo
MEMSHIELD_DIR ?= models/memshield
# use the fine-tuned memshield classifier once `make memshield` has produced it (models/ is gitignored)
# Prompt Guard 2 is gated: without HF_TOKEN use the ungated ProtectAI classifier (tuned cut-off in guards/models.py)
export MEMLEDGER_PROMPT_GUARD_MODEL ?= $(if $(HF_TOKEN),meta-llama/Llama-Prompt-Guard-2-86M,protectai/deberta-v3-base-prompt-injection-v2)
export MEMLEDGER_MEMSHIELD_MODEL ?= $(if $(wildcard $(MEMSHIELD_DIR)/config.json),$(abspath $(MEMSHIELD_DIR)))

.PHONY: setup setup-models data suite memshield test lint eval-local

setup:
	$(PY) -m venv .venv && .venv/bin/pip install -e ".[dev]"
setup-models:  # everything for real runs: extras + checker models in the HF cache (vLLM only on Linux)
	[ -x .venv/bin/python ] || $(PY) -m venv .venv
	.venv/bin/pip install -q --upgrade pip
	.venv/bin/pip install -e ".[dev,models,store,demo]" agentdojo certifi
	.venv/bin/python -m bench.fetch_models
data:  # published benchmarks into data/ (gitignored); skips what is offline or gated
	.venv/bin/python -m bench.download $(DATA_SETS)
suite:  # dev/test attack suite incl. downloaded benchmarks; only the manifest is committed
	PYTHONPATH=. .venv/bin/python -m attacks.suite --out data/attacks --manifest docs/results/suite_manifest.json
memshield:  # fine-tune the write-time memory screen on memshield TRAIN (validation for early stopping)
	.venv/bin/python -m memledger.guards.train.train_memshield --data-dir data/memshield --out $(MEMSHIELD_DIR)
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check .
eval-local:  # dev split, all 5 versions, qwen3:8b on local Ollama (thinking off), HF checkers if installed
	PYTHONPATH=. .venv/bin/python -u -m attacks.evaluate --split dev --llm openai --model qwen3:8b \
		--base-url http://localhost:11434/v1 --guards auto --out results/attacks --run-id local-$$(date +%Y%m%d-%H%M)
