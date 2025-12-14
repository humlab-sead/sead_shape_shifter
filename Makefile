SHELL := /bin/bash

.PHONY: csv excel
excel:
	@export PYTHONPATH=. && python src/arbodat/survey2excel.py \ 
		--env-file ./input/.env \
		--sep ";" \
		--mode excel \
		--config-file ./input/arbodat.yml \
		./input/arbodat_mal_elena_input.csv \
		tmp/arbodat.xlsx

csv:
	@export PYTHONPATH=. && python src/arbodat/survey2excel.py \ 
		--env-file ./input/.env \
		--sep ';' \
		--mode csv \
		--config-file ./input/arbodat.yml \
		./input/arbodat_mal_elena_input.csv \
		tmp/arbodat

.PHONY: install
install:
	@uv venv
	@uv pip install -e .

.PHONY: test
test:
	@uv run pytest tests -v

.PHONY: publish
publish:
	@echo "Publishing Python package to PyPI"
	@uv publish

.PHONY: black
black:
	@uv run black src tests

.PHONY: pylint
pylint:
	@uv run pylint src tests

.PHONY: lint
lint: tidy pylint check-imports

.PHONY: check-imports
check-imports:
	@python scripts/check_imports.py


# ============================================================================
# Backend recipes
# ============================================================================

backend-pylint:
	@pushd backend && (uv run pylint app tests || true) && popd

backend-black:
	@pushd backend && uv run black app tests && popd

backend-tidy: backend-black
	@pushd backend && uv run isort app tests && popd

backend-lint: backend-tidy backend-pylint
	@echo "✓ Backend linting complete"

# backend-test:
# 	@pushd backend && uv run pytest tests -v && popd	

# ============================================================================
# Configuration Editor UI
# ============================================================================

.PHONY: ui-install
ui-install: install backend-install frontend-install

.PHONY: backend-install
backend-install:
	@echo "Installing main package (shape-shifter) in editable mode..."
	@uv pip install -e . 2>&1 | grep -E '(Installed|Uninstalled|Built|shape-shifter)' || true
	@echo "Installing backend dependencies..."
	@cd backend && uv pip install -e ".[dev]" 2>&1 | grep -E '(Installed|Uninstalled|Built|shape-shifter-editor-backend)' || true
	@echo "✓ Backend installation complete"

.PHONY: backend-run
backend-run:
	@echo "Starting backend server on http://localhost:8000"
	@if [ -z "$$CONFIG_FILE" ]; then \
		echo "Using default config: input/arbodat-database.yml"; \
		export CONFIG_FILE=$$(pwd)/input/arbodat-database.yml; \
	fi && \
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: backend-test
backend-test:
	@echo "Running backend tests..."
	@cd backend && uv run python -m pytest -v

.PHONY: frontend-install
frontend-install:
	@echo "Installing frontend dependencies..."
	@cd frontend && pnpm install

.PHONY: frontend-run
frontend-run:
	@echo "Starting frontend dev server on http://localhost:5173"
	@cd frontend && pnpm dev

.PHONY: fix-imports
fix-imports:
	@python scripts/fix_imports.py

isort:
	@uv run isort src tests

.PHONY: tidy
tidy: black isort

requirements.txt: pyproject.toml
	@uv export -o requirements.txt

.PHONY: test-coverage
test-coverage:
	@uv run pytest test_main.py --cov=main --cov-report=html --cov-report=term

.PHONY: dead-code
dead-code:
	@uv run vulture src tests main.py



SCHEMA_OPTS = --no-drop-table --not-null --default-values --no-not_empty --comments --indexes --relations
BACKEND = postgres

arbodat-data-schema:
	@mdb-schema $(SCHEMA_OPTS) ./input/ArchBotDaten.mdb $(BACKEND) > ./input/ArchBotDaten_$(BACKEND)_schema.sql 

arbodat-lookup-schema:
	@mdb-schema $(SCHEMA_OPTS) ./input/ArchBotStrukDat.mdb $(BACKEND) > ./input/ArchBotStrukDat_$(BACKEND)_schema.sql 

arbodat-schema: arbodat-data-schema arbodat-lookup-schema
	@echo "✅ Schema extraction complete!"
