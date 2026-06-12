PYTHON := uv run python
ENTRY  := pac-man.py
CONFIG := config.json

.PHONY: install run debug lint lint-strict test docs clean clean-all

install:
	uv sync

run:
	$(PYTHON) $(ENTRY) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(ENTRY) $(CONFIG)

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy --strict .

test:
	uv run pytest

docs:
	@if ! command -v dot >/dev/null 2>&1; then \
		echo "graphviz not found — install it with: sudo apt install graphviz"; \
	else \
		dot -Tsvg docs/architecture.dot  -o docs/architecture.svg; \
		dot -Tpng docs/architecture.dot  -o docs/architecture.png; \
		dot -Tsvg docs/state-machine.dot -o docs/state-machine.svg; \
		dot -Tpng docs/state-machine.dot -o docs/state-machine.png; \
		echo "Diagrams regenerated in docs/"; \
	fi

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .ruff_cache .coverage htmlcov
	find . -type f -name '*.py[co]' -delete

clean-all: clean
	rm -rf .venv
