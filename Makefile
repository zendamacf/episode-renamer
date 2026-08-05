.PHONY: lint format typecheck test check release

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
