SHELL := /bin/bash

BACKEND_PORT ?= 8012
FRONTEND_PORT ?= 5173

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
	@uv pip install -e ".[all]"
	@echo "✓ Installed shape-shifter with all dependencies (core + api + dev)"

.PHONY: install-core
install-core:
	@uv venv
	@uv pip install -e .
	@echo "✓ Installed shape-shifter core only"

.PHONY: install-api
install-api:
	@uv venv
	@uv pip install -e ".[api]"
	@echo "✓ Installed shape-shifter with API dependencies"

.PHONY: test
test:
	@uv run pytest tests backend/tests -v

.PHONY: publish
publish:
	@echo "Publishing Python package to PyPI"
	@uv publish

.PHONY: black
black:
	@uv run black src tests backend/app backend/tests

.PHONY: pylint
pylint:
	@uv run pylint src tests backend/app backend/tests

.PHONY: tidy
tidy:
	@uv run isort src tests backend/app backend/tests
	@uv run black src tests backend/app backend/tests

.PHONY: lint
lint: tidy pylint check-imports

.PHONY: check-imports
check-imports:
	@python scripts/check_imports.py

################################################################################
# Backend & frontend recipes
################################################################################

.PHONY: kill
kill: backend-kill frontend-kill

stop:
	@echo "Stopping all processes..."
	@lsof -ti:$(BACKEND_PORT) 2>/dev/null | xargs -r kill -9 || true
	@lsof -ti:$(FRONTEND_PORT) 2>/dev/null | xargs -r kill -9 || true
	@echo "Done."

.PHONY: br
br: backend-kill backend-run

.PHONY: fr
fr: frontend-kill frontend-run

.PHONY: fr2
fr2: frontend-kill frontend-build-fast frontend-run

################################################################################
# Backend recipes
################################################################################

.PHONY: kill
backend-kill: 
	@lsof -t -i ':$(BACKEND_PORT)' | xargs -r kill -9
	@echo "Killed all running servers."

RELOAD_EXCLUDE="./docs,output,input,*.pyc,__pycache__/*,*.pyo,*~,./frontend/*,.venv/*,dist/*,.tox/*,*sqlite*,./tests/*,,*.csv"

.PHONY: backend-run
backend-run:
	@echo "Starting backend server on http://localhost:$(BACKEND_PORT)"
	@if [ -z "$$CONFIG_FILE" ]; then \
		echo "Using default config: input/arbodat-database.yml"; \
		export CONFIG_FILE=$$(pwd)/input/arbodat-database.yml; \
	fi && \
	PYTHONPATH=. uvicorn backend.app.main:app \
		--reload --reload-exclude $(RELOAD_EXCLUDE) \
		--log-level debug \
		--host 0.0.0.0 --port $(BACKEND_PORT)

.PHONY: backend-test
backend-test:
	@echo "Running backend tests..."
	@uv run pytest backend/tests -v

################################################################################
# Configuration Editor UI
################################################################################

.PHONY: ui-install
ui-install: install frontend-install
	@echo "✓ Full UI stack installed (core + api + frontend)"

frontend-kill: 
	@lsof -t -i ':$(FRONTEND_PORT)' | xargs -r kill -9
	@echo "Killed all running servers."

.PHONY: frontend-install
frontend-install:
	@echo "Installing frontend dependencies..."
	@cd frontend && pnpm install

.PHONY: frontend-run
frontend-run:
	@echo "Starting frontend dev server on http://localhost:$(FRONTEND_PORT)"
	@cd frontend && pnpm dev

.PHONY: frontend-build-fast
frontend-build-fast:
	@echo "Building frontend (skipping type check)..."
	@cd frontend && pnpm build:skip-check

.PHONY: frontend-preview
frontend-preview:
	@echo "Preview production build on http://localhost:4173"
	@cd frontend && pnpm preview

.PHONY: frontend-build
frontend-build:
	@cd frontend && rm -rf node_modules/.vite dist && pnpm dev 

################################################################################
# Other stuff
################################################################################

.PHONY: fix-imports
fix-imports:
	@python scripts/fix_imports.py

isort:
	@uv run isort src tests backend/app backend/tests

requirements.txt: pyproject.toml
	@uv export -o requirements.txt

.PHONY: test-coverage
test-coverage:
	@uv run pytest tests backend/tests --cov=src --cov=backend/app --cov-report=html --cov-report=term

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
