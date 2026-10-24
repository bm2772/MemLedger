setup:
	python -m venv .venv && .venv/bin/pip install -e ".[dev]"
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
