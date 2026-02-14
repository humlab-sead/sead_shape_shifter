SHELL := /bin/bash

BACKEND_PORT ?= 8013
FRONTEND_PORT ?= 5173

.PHONY: csv excel
excel:
	@export PYTHONPATH=. && python src/arbodat/survey2excel.py \ 
		--env-file ./projects/.env \
		--sep ";" \
		--mode excel \
		--config-file ./projects/arbodat.yml \
		./projects/arbodat_mal_elena_input.csv \
		tmp/arbodat.xlsx

csv:
	@export PYTHONPATH=. && python src/arbodat/survey2excel.py \ 
		--env-file ./projects/.env \
		--sep ';' \
		--mode csv \
		--config-file ./projects/arbodat.yml \
		./projects/arbodat_mal_elena_input.csv \
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

.PHONY: profile
profile:
	@echo "Profiling test with py-spy..."
	@uv run py-spy record -o profile.svg --format speedscope -- pytest $(TEST) -v -s
	@echo "✓ Profile saved to profile.svg (open in browser or speedscope.app)"

.PHONY: profile-stats
profile-stats:
	@echo "Profiling test with cProfile..."
	@uv run python -m cProfile -o profile.stats -m pytest $(TEST) -v
	@uv run python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(30)"
	@echo "✓ Full stats saved to profile.stats"

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
# JSON Schema generation (for frontend Monaco editor autocomplete)
################################################################################

.PHONY: generate-schemas
generate-schemas:
	@echo "Generating JSON schemas from Pydantic models..."
	@PYTHONPATH=.:backend uv run python scripts/generate_schemas.py

.PHONY: check-schemas
check-schemas:
	@echo "Checking if JSON schemas are in sync with Pydantic models..."
	@PYTHONPATH=.:backend uv run python scripts/generate_schemas.py --check

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

# Serve backend with console + file logging
.PHONY: br-log
br-log: frontend-clear backend-kill backend-run-log

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

.PHONY: backend-run-log
backend-run-log:
	@echo "Starting backend server on http://localhost:$(BACKEND_PORT) (logs also saved to logs/backend.log)"
	@mkdir -p logs
	@PYTHONPATH=. uv run uvicorn backend.app.main:app \
		--log-level debug \
		--host 0.0.0.0 --port $(BACKEND_PORT) 2>&1 | tee logs/backend.log

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
		--reload-exclude 'projects' \
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

# Include Docker recipes from docker/Makefile
DOCKER_DIR := ./docker
export DOCKER_DIR
include docker/Makefile

.PHONY: docker-patch-frontend
docker-patch-frontend:
	@echo "Rebuilding frontend and patching running container..."
	@cd frontend && pnpm build:skip-check
	@docker cp frontend/dist/. shape-shifter:/app/frontend/dist/
	@echo "✓ Frontend patched in running container"

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
	@mdb-schema $(SCHEMA_OPTS) ./projects/ArchBotDaten.mdb $(BACKEND) > ./projects/ArchBotDaten_$(BACKEND)_schema.sql 

arbodat-lookup-schema:
	@mdb-schema $(SCHEMA_OPTS) ./projects/ArchBotStrukDat.mdb $(BACKEND) > ./projects/ArchBotStrukDat_$(BACKEND)_schema.sql 

arbodat-schema: arbodat-data-schema arbodat-lookup-schema
	@echo "✅ Schema extraction complete!"

################################################################################
# Presentation
################################################################################

PRESENTATION_FILE := docs/PRESENTATION_SEAD_WORKSHOP.md

.PHONY: presentation-pdf
presentation-pdf:
	@echo "Exporting presentation to PDF..."
	@npx -y @marp-team/marp-cli@latest $(PRESENTATION_FILE) --pdf -o docs/PRESENTATION_SEAD_WORKSHOP.pdf
	@echo "✓ PDF created: docs/PRESENTATION_SEAD_WORKSHOP.pdf"

.PHONY: presentation-html
presentation-html:
	@echo "Exporting presentation to HTML..."
	@npx -y @marp-team/marp-cli@latest $(PRESENTATION_FILE) --html -o docs/PRESENTATION_SEAD_WORKSHOP.html
	@echo "✓ HTML created: docs/PRESENTATION_SEAD_WORKSHOP.html"

.PHONY: presentation-pptx
presentation-pptx:
	@echo "Exporting presentation to PowerPoint..."
	@npx -y @marp-team/marp-cli@latest $(PRESENTATION_FILE) --pptx -o docs/PRESENTATION_SEAD_WORKSHOP.pptx
	@echo "✓ PPTX created: docs/PRESENTATION_SEAD_WORKSHOP.pptx"

.PHONY: presentation-watch
presentation-watch:
	@echo "Starting Marp watch mode (auto-reload in browser)..."
	@npx -y @marp-team/marp-cli@latest -w $(PRESENTATION_FILE)

.PHONY: presentation-all
presentation-all: presentation-pdf presentation-html presentation-pptx
	@echo "✓ All presentation formats exported"

################################################################################
# Diagrams
################################################################################

.PHONY: diagrams-extract
diagrams-extract:
	@echo "Extracting Mermaid diagrams from SYSTEM_DIAGRAMS.md..."
	@mkdir -p tmp/mermaid
	@python3 tmp/extract_mermaid.py 2>/dev/null || python3 -c " \
		import re, os; \
		content = open('docs/SYSTEM_DIAGRAMS.md').read(); \
		matches = re.findall(r'## (\d+)\.\s+([^\n]+)\n\n\`\`\`mermaid\n(.*?)\`\`\`', content, re.DOTALL); \
		os.makedirs('tmp/mermaid', exist_ok=True); \
		[open(f'tmp/mermaid/{num}-{re.sub(r\"[^\\w\\s-]\", \"\", title).strip().lower().replace(\" \", \"-\").replace(\"--\", \"-\")}.mmd', 'w').write(diagram.strip()) for num, title, diagram in matches]; \
		print(f'Extracted {len(matches)} diagrams to tmp/mermaid/')"
	@echo "✓ Diagrams extracted"

.PHONY: diagrams-to-svg
diagrams-to-svg: diagrams-extract
	@echo "Converting Mermaid diagrams to SVG (using mermaid.ink API)..."
	@mkdir -p docs/images/diagrams
	@python3 tmp/mermaid_to_svg_retry.py 2>/dev/null || python3 -c " \
		import base64, urllib.request, time; \
		from pathlib import Path; \
		mermaid_dir = Path('tmp/mermaid'); \
		output_dir = Path('docs/images/diagrams'); \
		output_dir.mkdir(parents=True, exist_ok=True); \
		[(print(f'Converting: {f.stem}'), \
		  (lambda code, out: \
		    (urllib.request.urlopen(f'https://mermaid.ink/svg/{base64.b64encode(code.encode()).decode()}', timeout=30).read() if True else None, \
		     open(out, 'wb').write(_) if _ else None, \
		     print(f'  ✓ Created {out.name}') if out.exists() else print(f'  ✗ Failed'), \
		     time.sleep(2))[-1] \
		  )(open(f).read(), output_dir / f'{f.stem}.svg')) \
		 for f in sorted(mermaid_dir.glob('*.mmd')) if not (output_dir / f'{f.stem}.svg').exists()]"
	@echo "✓ SVG diagrams created in docs/images/diagrams/"

.PHONY: diagrams-list
diagrams-list:
	@echo "SVG Diagrams:"
	@ls -1 docs/images/diagrams/*.svg 2>/dev/null | xargs -n1 basename || echo "No diagrams found"
