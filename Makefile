PY ?= $(shell command -v python3.11 || command -v python3 || command -v python)
DATA_SETS = memshield memevobench bipia injecagent agentdojo
MEMSHIELD_DIR ?= models/memshield
# Prompt Guard 2 is gated: without HF_TOKEN use the ungated ProtectAI classifier (tuned cut-off in guards/models.py)
export MEMLEDGER_PROMPT_GUARD_MODEL ?= $(if $(HF_TOKEN),meta-llama/Llama-Prompt-Guard-2-86M,protectai/deberta-v3-base-prompt-injection-v2)
# use the fine-tuned memshield classifier once `make memshield` has produced it (models/ is gitignored)
export MEMLEDGER_MEMSHIELD_MODEL ?= $(if $(wildcard $(MEMSHIELD_DIR)/config.json),$(abspath $(MEMSHIELD_DIR)))

.PHONY: setup setup-models data suite memshield memshield-large test lint eval-local eval-brev-smoke eval-brev eval-latency

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
memshield-large:  # Brev GPU: DeBERTa-v3-large + MemEvoBench dev memories (its test items held out) -> models/memshield-large
	.venv/bin/python -m memledger.guards.train.train_memshield --data data/memshield --base microsoft/deberta-v3-large \
		--out models/memshield-large --epochs 3 --lr 1e-5 --batch 8 --grad-accum 2 --max-length 512 --add-memevobench-dev
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check .
eval-local:  # dev split, all 5 versions, qwen3:8b on local Ollama (thinking off), HF checkers if installed
	PYTHONPATH=. .venv/bin/python -u -m attacks.evaluate --split dev --llm openai --model qwen3:8b \
		--base-url http://localhost:11434/v1 --guards auto --out results/attacks --run-id local-$$(date +%Y%m%d-%H%M)
# Final run on Brev (infra/README.md "Final run"): vLLM serves MODEL on LLM_URL (infra/brev_setup.sh), checkers on the
# GPU. MODEL must be the full name (contains "qwen3"): that is what switches thinking off; the alias "main" would not.
MODEL ?= Qwen/Qwen3-8B
LLM_URL ?= http://localhost:8000/v1
WORKERS ?= 16
RUN_ID ?= brev-test
# HF_HOME: the checker weights brev_setup.sh downloaded (a new shell would otherwise fetch them again into ~/.cache)
BREV_EVAL = HF_HOME=$${HF_HOME:-$$HOME/workspace/hf-cache} MEMLEDGER_DEVICE=cuda PYTHONPATH=. \
	.venv/bin/python -u -m attacks.evaluate --split test --llm openai \
	--model $(MODEL) --base-url $(LLM_URL) --guards hf --out results/attacks
eval-brev-smoke:  # 1 episode per family on all 5 versions (~5 min): every model loads, no episode errors
	$(BREV_EVAL) --limit-per-family 1 --workers 4 --run-id $(RUN_ID)-smoke
# eval-brev again after a crash resumes: errored versions are played again; a different MODEL/checkers/suite under the
# same RUN_ID is refused (pass RUN_ID=...)
eval-brev:  # the final run: test split x 5 versions
	$(BREV_EVAL) --workers $(WORKERS) --resume --run-id $(RUN_ID)
eval-latency:  # "added ms" without contention from parallel episodes: 1 worker, 5 episodes per family
	$(BREV_EVAL) --limit-per-family 5 --workers 1 --run-id $(RUN_ID)-latency
web-build:  # the console UI (web/ui) -> web/ui/dist, served by the API server
	cd web/ui && npm ci --no-audit --no-fund && npm run build
web: web-build  # console on http://127.0.0.1:8000 (open mode: local only; set MEMLEDGER_USERS to deploy)
	.venv/bin/python -m pip install -q -e ".[web]"
	.venv/bin/python -m web
web-dev:  # API on :8000 + Vite dev server with hot reload on :5173
	.venv/bin/python -m web & cd web/ui && npm run dev
