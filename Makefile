setup:
	python -m venv .venv && .venv/bin/pip install -e ".[dev]"
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check .
