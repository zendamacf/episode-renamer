.PHONY: install install.dev lint format typecheck test check ci release

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

install.dev:
	python -m pip install --upgrade pip
	pip install -r requirements-dev.txt

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

release:
ifndef VERSION
	$(error VERSION is required, e.g. make release VERSION=0.2.1)
endif
	./scripts/prep_release.py $(VERSION)

check: lint typecheck

ci: check test
