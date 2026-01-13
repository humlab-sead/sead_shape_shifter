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

.PHONY: ruff
ruff:
	@uv run ruff check --fix --output-format concise src tests backend

.PHONY: tidy
tidy:
	@uv run isort src tests backend/app backend/tests
	@uv run black src tests backend/app backend/tests

.PHONY: lint
lint: tidy ruff pylint

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

# Serve backend without frontend (hence frontend-clear)
.PHONY: br
br: frontend-clear backend-kill backend-run

.PHONY: fr
fr: frontend-kill frontend-run

fr2: frontend-clear fr

# Serve frontend via backend (production mode)
# Builds frontend with .env.production (VITE_API_BASE_URL="") then serves via backend
.PHONY: br+fr
br+fr: frontend-kill frontend-build-fast backend-kill backend-run

.PHONY: run-all
run-all: backend-kill frontend-kill
	@echo "Starting backend and frontend servers..."
	@make -j2 backend-run frontend-run

################################################################################
# Backend recipes
################################################################################

.PHONY: kill
backend-kill: 
	@lsof -t -i ':$(BACKEND_PORT)' | xargs -r kill -9
	@echo "Killed all running servers."


.PHONY: backend-run
backend-run:
	@echo "Starting backend server on http://localhost:$(BACKEND_PORT)"
	@PYTHONPATH=. uv run uvicorn backend.app.main:app \
		--log-level debug \
		--host 0.0.0.0 --port $(BACKEND_PORT)

.PHONY: backend-run-with-hmr
backend-run-with-hmr:
	@echo "Starting backend server on http://localhost:$(BACKEND_PORT)"
	@PYTHONPATH=. uvicorn backend.app.main:app \
		--log-level debug \
		--reload \
		--reload-delay 2 \
		--reload-include '*.py' \
		--reload-exclude '.venv' \
		--reload-exclude '.git' \
		--reload-exclude 'frontend' \
		--reload-exclude 'input' \
		--reload-exclude 'backups' \
		--reload-exclude 'tmp' \
		--reload-exclude 'htmlcov' \
		--reload-exclude '.pytest_cache' \
		--reload-exclude 'tests' \
		--reload-exclude 'backend/tests' \
		--host 0.0.0.0 --port $(BACKEND_PORT)


.PHONY: backend-test
backend-test:
	@echo "Running backend tests..."
	@uv run pytest backend/tests -v

.PHONY: reconcile
reconcile:
	@echo "Running auto-reconciliation CLI..."
	@PYTHONPATH=.:backend uv run python scripts/auto_reconcile.py $(ARGS)

################################################################################
# Project Editor UI
################################################################################

.PHONY: ui-install
ui-install: install frontend-install
	@echo "✓ Full UI stack installed (core + api + frontend)"

frontend-kill: 
	@lsof -t -i ':$(FRONTEND_PORT)' | xargs -r kill -9
	@echo "Killed all running servers."

.PHONY: frontend-build
frontend-build:
	@cd frontend && rm -rf node_modules/.vite dist && pnpm dev 

.PHONY: frontend-build-fast
frontend-build-fast:
	@echo "Building frontend for production (skipping type check)..."
	@cd frontend && pnpm build:skip-check

frontend-clear:
	@rm -rf frontend/node_modules/.vite frontend/dist
	@echo "info: frontend dist and Vite cache cleared."

.PHONY: frontend-install
frontend-install:
	@echo "Installing frontend dependencies..."
	@cd frontend && pnpm install

.PHONY: frontend-lint
frontend-lint:
	@echo "Linting frontend code..."
	@cd frontend && pnpm lint

.PHONY: frontend-test
frontend-test:
	@echo "Running frontend tests..."
	@cd frontend && pnpm test:run

.PHONY: frontend-test-ui
frontend-test-ui:
	@echo "Running frontend tests with UI..."
	@cd frontend && pnpm test:ui

.PHONY: frontend-coverage
frontend-coverage:
	@echo "Running frontend tests with coverage..."
	@cd frontend && pnpm test:coverage

.PHONY: frontend-run
frontend-run:
	@echo "Starting frontend dev server on http://localhost:$(FRONTEND_PORT)"
	@cd frontend && pnpm dev

.PHONY: frontend-preview
frontend-preview:
	@echo "Preview production build on http://localhost:4173"
	@cd frontend && pnpm preview

################################################################################
# Docker
################################################################################

.PHONY: docker-build
docker-build:
	@echo "Building Docker image..."
	@docker compose -f docker/docker-compose.yml build

.PHONY: docker-build-no-cache
docker-build-no-cache:
	@echo "Building Docker image (no cache)..."
	@docker compose -f docker/docker-compose.yml build --no-cache

.PHONY: docker-up
docker-up:
	@echo "Starting Shape Shifter with Docker Compose..."
	@docker compose -f docker/docker-compose.yml up -d
	@echo "✓ Application started at http://localhost:8012"

.PHONY: docker-start
docker-start: docker-up

.PHONY: docker-down
docker-down:
	@echo "Stopping Shape Shifter containers..."
	@docker compose -f docker/docker-compose.yml down

.PHONY: docker-stop
docker-stop: docker-down

.PHONY: docker-logs
docker-logs:
	@docker compose -f docker/docker-compose.yml logs -f

.PHONY: docker-restart
docker-restart:
	@echo "Restarting Shape Shifter..."
	@docker compose -f docker/docker-compose.yml restart

.PHONY: docker-rebuild
docker-rebuild:
	@echo "Rebuilding and restarting Shape Shifter..."
	@docker compose -f docker/docker-compose.yml down
	@docker compose -f docker/docker-compose.yml up -d --build
	@echo "✓ Application rebuilt and started at http://localhost:8012"

.PHONY: docker-shell
docker-shell:
	@docker compose -f docker/docker-compose.yml exec shape-shifter /bin/bash

.PHONY: docker-clean
docker-clean:
	@echo "Cleaning up Docker resources..."
	@docker compose -f docker/docker-compose.yml down -v
	@docker image rm shape-shifter:latest 2>/dev/null || true
	@echo "✓ Cleanup complete"

.PHONY: docker-ps
docker-ps:
	@docker compose -f docker/docker-compose.yml ps

.PHONY: docker-health
docker-health:
	@echo "Checking application health..."
	@curl -sf http://localhost:8012/api/v1/health | jq . || echo "❌ Health check failed"

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
	@uv run vulture src backend

serve-coverage:
	@python -m http.server --directory htmlcov 8080
	

SCHEMA_OPTS = --no-drop-table --not-null --default-values --no-not_empty --comments --indexes --relations
BACKEND = postgres

arbodat-data-schema:
	@mdb-schema $(SCHEMA_OPTS) ./input/ArchBotDaten.mdb $(BACKEND) > ./input/ArchBotDaten_$(BACKEND)_schema.sql 

arbodat-lookup-schema:
	@mdb-schema $(SCHEMA_OPTS) ./input/ArchBotStrukDat.mdb $(BACKEND) > ./input/ArchBotStrukDat_$(BACKEND)_schema.sql 

arbodat-schema: arbodat-data-schema arbodat-lookup-schema
	@echo "✅ Schema extraction complete!"
