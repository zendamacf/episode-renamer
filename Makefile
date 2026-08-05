.PHONY: lint format typecheck test check

lint:
	ruff format --check .
	ruff check .

format:
	ruff format .
	ruff check .

typecheck:
	basedpyright .

test:
	pytest

check: lint typecheck
