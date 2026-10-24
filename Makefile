setup:
	python -m venv .venv && .venv/bin/pip install -e ".[dev]"
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check .
eval-local:  # dev split, all 5 versions, qwen3:8b on local Ollama (thinking off), HF checkers if installed
	PYTHONPATH=. .venv/bin/python -u -m attacks.evaluate --split dev --llm openai --model qwen3:8b \
		--base-url http://localhost:11434/v1 --guards auto --out results/attacks --run-id local-$$(date +%Y%m%d-%H%M)
