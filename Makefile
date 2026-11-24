SHELL := /bin/bash

BACKEND_PORT ?= 8025
FRONTEND_PORT ?= 5173

.PHONY: install
install:
	@uv venv
	@uv pip install -e ".[all]"
	@$(MAKE) install-hooks
	@echo "✓ Installed shape-shifter with all dependencies (core + api + dev)"

.PHONY: install-hooks
install-hooks:
	@uv run --extra all pre-commit install
	@$(MAKE) --no-print-directory install-graphify-hooks

# Installs graphify's post-commit, post-checkout, post-merge and post-rewrite hooks, which
# rebuild the local knowledge graph in graphify-out/ in the background (code only, no LLM).
# Skipped with a notice when graphify is not installed (see install-graphify).
# `graphify hook install` also writes a .gitattributes merge driver for graph.json. That only
# matters when graph.json is committed, and graphify-out/ is git-ignored here, so an untracked
# .gitattributes holding nothing but that line is removed again.
.PHONY: install-graphify-hooks
install-graphify-hooks:
	@if ! command -v graphify >/dev/null 2>&1; then \
		echo "graphify not found on PATH; skipping graphify git hooks (run make install-graphify)"; \
		exit 0; \
	fi; \
	graphify hook install; \
	if [ -f .gitattributes ] && ! git ls-files --error-unmatch .gitattributes >/dev/null 2>&1 \
		&& ! grep -qv 'merge=graphify' .gitattributes; then \
		rm -f .gitattributes; \
	fi

# Re-sync the shared .venv/ from uv.lock without pruning the api/dev extras.
# Plain `uv sync` syncs to base + dependency-group dev only and silently
# removes fastapi/uvicorn/pytest, which live in the optional "all" extra
# (= api + dev extras). The dependency-groups dev (pre-commit, pyinstrument)
# is included by uv sync automatically.
.PHONY: sync
sync:
	@uv sync --extra all
	@$(MAKE) install-hooks
	@echo "✓ Synced .venv/ (core + api + dev) from uv.lock"

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

.PHONY: test-validate
test-validate:
	@uv run python scripts/project/validate_project.py tests/test_data/projects/arbodat/shapeshifter.yml \
		--workflow all --log-level ERROR --ignore EMPTY_RESULT > validation_issues.csv 

.PHONY: profile-validate
profile-validate:
	@uv run pyinstrument scripts/project/validate_project.py tests/test_data/projects/arbodat/shapeshifter.yml --workflow all

.PHONY: profile
profile-test:
	@echo "Profiling test with py-spy..."
	@uv run py-spy record -o profile.svg --format speedscope -- pytest $(TEST) -v -s
	@echo "✓ Profile saved to profile.svg (open in browser or speedscope.app)"

.PHONY: profile-stats
profile-stats:
	@echo "Profiling test with cProfile..."
	@uv run python -m cProfile -o profile.stats -m pytest $(TEST) -v
	@uv run python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(30)"
	@echo "✓ Full stats saved to profile.stats"

.PHONY: profile-projects
profile-projects:
	@uv run python scripts/dev/profile_projects_listing.py

.PHONY: publish
publish:
	@echo "Publishing Python package to PyPI"
	@uv publish

.PHONY: black
black:
	@uv run black src tests backend/app backend/tests ingesters

.PHONY: pylint
pylint:
	@uv run pylint -j 0 src tests backend ingesters

# Lint only Python files changed against HEAD, including untracked files.
.PHONY: pylint-changed
pylint-changed:
	@{ git diff --name-only -z --diff-filter=d HEAD -- '*.py'; \
		git ls-files --others --exclude-standard -z -- '*.py'; } \
		| grep -zvE '^(\.venv|frontend|node_modules|docs|graphify-out)/' \
		| sort -zu \
		| xargs -0 -r uv run pylint -j 0

.PHONY: lint-changed
lint-changed: SHELL := /bin/bash
lint-changed:
	@mapfile -d '' candidates < <( \
		{ \
			git diff --name-only -z -- '*.py'; \
			git diff --cached --name-only -z -- '*.py'; \
			git ls-files --others --exclude-standard -z -- '*.py'; \
		} | sort -zu \
	); \
	files=(); \
	for file in "$${candidates[@]}"; do \
		[[ ! -f "$$file" ]] || files+=("./$$file"); \
	done; \
	if (( $${#files[@]} == 0 )); then \
		echo "No changed Python files."; \
		exit 0; \
	fi; \
	uv run isort --profile black "$${files[@]}" && \
	uv run black "$${files[@]}" && \
	uv run pylint "$${files[@]}"
	
.PHONY: pyright
pyright:
	@uv run pyright --threads 2 src backend ingesters

.PHONY: ruff
ruff:
	@uv run ruff check --fix --output-format concise src tests backend ingesters scripts

.PHONY: tidy
tidy:
	@uv run isort src tests backend ingesters scripts
	@uv run black src tests backend ingesters scripts

.PHONY: lint
lint: tidy ruff pylint check-target-model-schema-reference sead-schema-check check-doc-links

.PHONY: check-doc-links
check-doc-links:
	@scripts/ci/check_doc_links.sh

.PHONY: check-doc-links-lychee
check-doc-links-lychee:
	@echo "Checking documentation links with lychee..."
	@lychee --offline --no-progress --root-dir . --extensions md docs
	@echo "✓ Documentation links checked with lychee"

################################################################################
# Git related checks
################################################################################

.PHONY: branches-ahead
branches-ahead:
	@git for-each-ref --format='%(refname:short)' refs/heads | \
	while IFS= read -r branch; do \
		ahead=$$(git rev-list --count "dev..$$branch"); \
		if [ "$$ahead" -gt 0 ]; then \
			printf '%5s  %s\n' "$$ahead" "$$branch"; \
		fi; \
	done
	@echo "✓ Branches ahead of dev listed above"


target-model-csv:
	yq -o=csv '[.entities | to_entries[] | {"entity": .key, "role": .value.role, "required": .value.required, "description": .value.description, "domains": ((.value.domains // []) | join("; ")), "target_table": .value.target_table, "public_id": .value.public_id, "columns": ((.value.columns // {}) | keys | join("; ")), "unique_sets": ((.value.unique_sets // []) | map(join(" + ")) | join("; ")), "foreign_keys": ((.value.foreign_keys // []) | map(.entity) | join("; "))}]' resources/target_models/sead_standard_model.yml

################################################################################
# Development authorization for the current local resources. 
################################################################################

.PHONY: development-authorization
development-authorization:
	@echo "Setting up development authorization for local resources..."
	@SHAPE_SHIFTER_ENVIRONMENT=development \
	SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=false \
	SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID=local-developer \
	SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization-dev.sqlite3 \
	uv run sead-authorization dev-bootstrap

################################################################################
# JSON Schema generation (for frontend Monaco editor autocomplete)
################################################################################

.PHONY: generate-schemas
generate-schemas:
	@echo "Generating JSON schemas from Pydantic models..."
	@PYTHONPATH=.:backend uv run python scripts/project/generate_schemas.py

.PHONY: check-schemas
check-schemas:
	@echo "Checking if JSON schemas are in sync with Pydantic models..."
	@PYTHONPATH=.:backend uv run python scripts/project/generate_schemas.py --check

################################################################################
# Target-model schema reference generation
################################################################################

.PHONY: generate-target-model-schema-reference
generate-target-model-schema-reference:
	@echo "Generating target-model schema reference from Pydantic models..."
	@uv run python scripts/target_model/generate_target_model_schema_reference.py

.PHONY: check-target-model-schema-reference
check-target-model-schema-reference:
	@echo "Checking if target-model schema reference is in sync with Pydantic models..."
	@uv run python scripts/target_model/generate_target_model_schema_reference.py --check

################################################################################
# Target-model data export (Excel)
################################################################################

EXPORT_OUTPUT ?= output/sead_lookup_classifier_tables.xlsx
EXPORT_ROLES ?= lookup classifier

.PHONY: export-target-tables
export-target-tables:
	@echo "Exporting target-model tables (roles: $(EXPORT_ROLES)) to $(EXPORT_OUTPUT)..."
	@mkdir -p $(dir $(EXPORT_OUTPUT))
	@uv run python scripts/target_model/export_target_tables.py $(EXPORT_OUTPUT) $(addprefix --role ,$(EXPORT_ROLES))

################################################################################
# Target-model template generation
################################################################################

ARBODAT_TEMPLATE_OUTPUT ?= target_models/examples/generated/arbodat.generated.yml

.PHONY: generate-arbodat-yaml
generate-arbodat-yaml:
	@echo "Generating Arbodat starter project YAML at $(ARBODAT_TEMPLATE_OUTPUT)..."
	@mkdir -p $(dir $(ARBODAT_TEMPLATE_OUTPUT))
	@uv run python scripts/target_model/generate_project_template.py \
		--spec resources/target_models/sead_standard_model.yml \
		--project-name arbodat:generated-template \
		--domain abundance \
		--domain dating \
		--domain taxonomy \
		--domain contacts \
		--output $(ARBODAT_TEMPLATE_OUTPUT)
	@echo "✓ Arbodat starter project YAML written to $(ARBODAT_TEMPLATE_OUTPUT)"

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
		--host 127.0.0.1 --port $(BACKEND_PORT) \
		--timeout-keep-alive 120

.PHONY: backend-run-log
backend-run-log:
	@echo "Starting backend server on http://localhost:$(BACKEND_PORT) (logs also saved to logs/backend.log)"
	@mkdir -p logs
	@PYTHONPATH=. uv run uvicorn backend.app.main:app \
		--log-level debug \
		--host 127.0.0.1 --port $(BACKEND_PORT) \
		--timeout-keep-alive 120 2>&1 | tee logs/backend.log

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
		--timeout-keep-alive 120 \
		--reload-exclude 'tests' \
		--reload-exclude 'backend/tests' \
		--host 127.0.0.1 --port $(BACKEND_PORT)


.PHONY: backend-test
backend-test:
	@echo "Running backend tests..."
	@uv run pytest backend/tests -v

.PHONY: reconcile
reconcile:
	@echo "Running auto-reconciliation CLI..."
	@PYTHONPATH=.:backend uv run python scripts/project/auto_reconcile.py $(ARGS)

################################################################################
# AI Coding Assistants recipes
# Candidates: rtk, graphify, serena, snip, headroom
################################################################################

rtk-install:
	@echo "Installing RTK and setting up global configurations..."
	@if ! command -v rtk &> /dev/null; then \
		echo "RTK not found, installing..."; \
		brew install rtk; \
	else \
		brew upgrade rtk &> /dev/null; \
	fi
	@rtk init -g --copilot
	@rtk init -g --codex

# Rebuilds the code part of the local graph (AST only, no LLM). The git hooks normally do
# this after each commit, checkout, merge and rebase; graphify-out/ is not committed.
# graphify is a uv tool (~/.local/bin), not part of the project .venv.
# GRAPHIFY_VIZ_NODE_LIMIT=0 blocks graph.html generation and removes any stale
# file (graph is far above the 5000-node viz limit and the HTML is unused).
update-graphify:
	@GRAPHIFY_VIZ_NODE_LIMIT=0 GRAPHIFY_NO_BACKUP=1 graphify update $(CURDIR) --force
	@$(MAKE) --no-print-directory graphify-wiki

# Regenerates graphify-out/wiki/ (index.md plus one page per community and per highly
# connected node) from the current graph. Runs locally in about a second with no LLM calls,
# and removes pages for communities that no longer exist. The git hooks do not run it, so
# update-graphify and semantic-graphify call it at the end.
.PHONY: graphify-wiki
graphify-wiki:
	@graphify export wiki

# Rebuilds the graph including the LLM-based (semantic) results: document/paper/image
# extraction and community names. Code is still parsed locally (AST).
#
# Uses the same LLM settings as the repo scripts (scripts/workflow/*). Each value is
# taken from the environment if set, otherwise from its KEY = "value" line in .env:
#   REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE       must be "openai" (any server with the OpenAI chat API)
#   REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL   server base URL, usually ending in /v1
#   REPO_SCRIPTS_DEFAULT_MODEL               model id as the server names it
#   REPO_SCRIPTS_DEFAULT_PROVIDER_KEY        API key; "none" is sent if empty
# They are passed to graphify's "openai" backend as OPENAI_BASE_URL, GRAPHIFY_OPENAI_MODEL
# and OPENAI_API_KEY for these two commands only. The values are read by the shell at run
# time, so make never prints the API key, not even with make -n.
#
# Unchanged files are skipped via graphify's cache unless GRAPHIFY_REEXTRACT=1.
#   make semantic-graphify                          # incremental
#   make semantic-graphify GRAPHIFY_REEXTRACT=1     # re-extract everything, ignore the cache
#   make semantic-graphify GRAPHIFY_MODE=deep       # more aggressive inferred-edge extraction
#   make semantic-graphify GRAPHIFY_RELABEL=1       # rename all communities, not only unnamed ones
#   make semantic-graphify GRAPHIFY_CONCURRENCY=1   # parallel LLM requests (graphify default: 4)
# Make variable names avoid BACKEND (used further down in this Makefile) and names graphify
# itself reads from the environment (GRAPHIFY_FORCE, GRAPHIFY_LLM_*).
.PHONY: semantic-graphify
semantic-graphify:
	@set -e; \
	setting() { \
		v=$$(printenv "$$1" || true); \
		if [ -z "$$v" ] && [ -f .env ]; then \
			v=$$(sed -nE "s/^[[:space:]]*(export[[:space:]]+)?$$1[[:space:]]*=[[:space:]]*(.*)$$/\2/p" .env | tail -n 1); \
		fi; \
		printf '%s' "$$v" | sed -E 's/[[:space:]]+$$//; s/^"(.*)"$$/\1/'; \
	}; \
	provider=$$(setting REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE); \
	base_url=$$(setting REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL); \
	model=$$(setting REPO_SCRIPTS_DEFAULT_MODEL); \
	api_key=$$(setting REPO_SCRIPTS_DEFAULT_PROVIDER_KEY); \
	if [ "$$provider" != "openai" ]; then \
		echo "error: REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE is '$$provider'; semantic-graphify only supports 'openai'" >&2; exit 1; \
	fi; \
	if [ -z "$$base_url" ] || [ -z "$$model" ]; then \
		echo "error: set REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL and REPO_SCRIPTS_DEFAULT_MODEL (environment or .env)" >&2; exit 1; \
	fi; \
	export GRAPHIFY_VIZ_NODE_LIMIT=0 OPENAI_BASE_URL="$$base_url" GRAPHIFY_OPENAI_MODEL="$$model" \
		OPENAI_API_KEY="$${api_key:-none}"; \
	echo "Using $$model at $$base_url"; \
	graphify extract $(CURDIR) --backend openai $(if $(GRAPHIFY_CONCURRENCY),--max-concurrency $(GRAPHIFY_CONCURRENCY)) \
		$(if $(GRAPHIFY_MODE),--mode $(GRAPHIFY_MODE)) $(if $(GRAPHIFY_REEXTRACT),--force); \
	graphify label $(CURDIR) --backend openai $(if $(GRAPHIFY_CONCURRENCY),--max-concurrency $(GRAPHIFY_CONCURRENCY)) \
		$(if $(GRAPHIFY_RELABEL),,--missing-only); \
	graphify export wiki; \
	echo "✓ Semantic graph and wiki rebuilt in graphify-out/"

install-graphify:
	@uv tool install "graphifyy[all]" --force
	@$(MAKE) --no-print-directory install-graphify-hooks
	@graphify vscode install
	@graphify codex install
	@echo "✓ Graphify installed and git hooks set up"

################################################################################
# SEAD schema reference
################################################################################

# Exports the SEAD schema reference docs/sead/columns.csv (one row per column, with type,
# nullability, primary key and foreign-key target) by running docs/sead/columns.sql read-only,
# then regenerates docs/sead/SCHEMA.md. Connection settings are taken from the environment if
# set, otherwise from their KEY=value lines in .env: SEAD_HOST, SEAD_PORT, SEAD_USER, SEAD_DBNAME.
# psql never prompts (-w): put the password in ~/.pgpass or PGPASSWORD. The export is written to
# a temporary file first, so a failed run leaves the current columns.csv unchanged.
.PHONY: sead-schema
sead-schema:
	@set -e; \
	setting() { \
		v=$$(printenv "$$1" || true); \
		if [ -z "$$v" ] && [ -f .env ]; then \
			v=$$(sed -nE "s/^[[:space:]]*(export[[:space:]]+)?$$1[[:space:]]*=[[:space:]]*(.*)$$/\2/p" .env | tail -n 1); \
		fi; \
		printf '%s' "$$v" | sed -E 's/[[:space:]]+$$//; s/^"(.*)"$$/\1/'; \
	}; \
	host=$$(setting SEAD_HOST); port=$$(setting SEAD_PORT); user=$$(setting SEAD_USER); dbname=$$(setting SEAD_DBNAME); \
	if [ -z "$$host" ] || [ -z "$$port" ] || [ -z "$$user" ] || [ -z "$$dbname" ]; then \
		echo "error: set SEAD_HOST, SEAD_PORT, SEAD_USER and SEAD_DBNAME (environment or .env)" >&2; exit 1; \
	fi; \
	tmp=$$(mktemp docs/sead/.columns.csv.XXXXXX); trap 'rm -f "$$tmp"' EXIT; \
	echo "Exporting SEAD columns from $$dbname at $$host:$$port as $$user..."; \
	PGCONNECT_TIMEOUT=15 psql -h "$$host" -p "$$port" -U "$$user" -d "$$dbname" -X -w -q \
		--csv -P null=NULL -v ON_ERROR_STOP=1 -f docs/sead/columns.sql -o "$$tmp"; \
	chmod 644 "$$tmp"; mv "$$tmp" docs/sead/columns.csv; \
	echo "Wrote docs/sead/columns.csv ($$(($$(wc -l < docs/sead/columns.csv) - 1)) columns)"
	@$(MAKE) --no-print-directory sead-schema-docs

# Regenerates docs/sead/SCHEMA.md from docs/sead/columns.csv without a database connection.
# Use `make sead-schema-check` to verify that SCHEMA.md matches the CSV.
.PHONY: sead-schema-docs sead-schema-check
sead-schema-docs:
	@python3 scripts/target_model/generate_sead_schema_reference.py

sead-schema-check:
	@python3 scripts/target_model/generate_sead_schema_reference.py --check

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
# Other stuff
################################################################################

isort:
	@uv run isort src tests backend/app backend/tests ingesters

requirements.txt: pyproject.toml
	@uv export -o requirements.txt

.PHONY: test-coverage
test-coverage:
	@uv run pytest tests backend/tests --cov=src --cov=backend/app --cov-report=html --cov-report=term

################################################################################
# Disposable PostgreSQL (podman) for loopback integration tests
#
# These targets manage a throwaway PostgreSQL container that the
# SEAD_DISPOSABLE_POSTGRES_* integration tests create and drop schemas in.
# The container binds to loopback only and holds no real data.
################################################################################

.PHONY: pg-disposable-up
pg-disposable-up:
	@uv run python scripts/dev/spinup_disposable_postgres.py up

.PHONY: pg-disposable-env
pg-disposable-env:
	@echo 'Usage: eval $$(make pg-disposable-env)' >&2
	@uv run python scripts/dev/spinup_disposable_postgres.py env

.PHONY: pg-disposable-status
pg-disposable-status:
	@uv run python scripts/dev/spinup_disposable_postgres.py status

.PHONY: pg-disposable-down
pg-disposable-down:
	@uv run python scripts/dev/spinup_disposable_postgres.py down

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
# Release Notes
################################################################################

.PHONY: release-notes-list
release-notes-list:
	@echo "Available versions in CHANGELOG.md:"
	@uv run python scripts/workflow/generate_user_release_notes.py --list-versions

.PHONY: release-notes-missing
release-notes-missing:
	@echo "Generating release notes for all missing versions..."
	@uv run python scripts/workflow/generate_user_release_notes.py --generate-missing --force-heuristic

.PHONY: release-notes-missing-ai
release-notes-missing-ai:
	@echo "Generating release notes for all missing versions (with AI)..."
	@uv run python scripts/workflow/generate_user_release_notes.py --generate-missing

.PHONY: release-notes
release-notes:
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION not specified. Usage: make release-notes VERSION=1.26.0"; \
		exit 1; \
	fi
	@echo "Generating release notes for version $(VERSION)..."
	@uv run python scripts/workflow/generate_whats_new.py --version $(VERSION) --force-heuristic

.PHONY: release-notes-ai
release-notes-ai:
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION not specified. Usage: make release-notes-ai VERSION=1.26.0"; \
		exit 1; \
	fi
	@echo "Generating release notes for version $(VERSION) with AI..."
	@uv run python scripts/workflow/generate_whats_new.py --version $(VERSION)

# Create a draft dev-to-staging promotion PR and prepare its description.
.PHONY: promote-dev-to-staging
promote-dev-to-staging:
	@scripts/workflow/promote_dev_to_staging.sh prepare

# Fast-track: stage every pending change, let Copilot draft the commit subject and the PR
# description, and merge into dev. The commit type comes from the drafted subject, so review
# `make push-chore-pr-dry` first when the change is not purely housekeeping.
.PHONY: push-chore-pr
push-chore-pr:
	@echo "Creating a chore pull request from every pending change..."
	@uv run python scripts/workflow/create_change_pr.py --type chore \
		--generate-subject --all --generate-description --default-validation
	@echo "✓ Change pull request merged into dev"

.PHONY: push-fix-pr
push-fix-pr:
	@echo "Creating a fix pull request from every pending change..."
	@uv run python scripts/workflow/create_change_pr.py --type fix \
		--generate-subject --all --generate-description --default-validation
	@echo "✓ Change pull request merged into dev"

# Same workflow without creating anything: prints the drafted subject, file list, and body.
.PHONY: push-chore-pr-dry
push-chore-pr-dry:
	@uv run python scripts/workflow/create_change_pr.py \
		--generate-subject --all --generate-description --default-validation --dry-run



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
	@echo "Extracting Mermaid diagrams from DIAGRAMS.md..."
	@mkdir -p tmp/mermaid
	@python3 tmp/extract_mermaid.py 2>/dev/null || python3 -c " \
		import re, os; \
		content = open('docs/DIAGRAMS.md').read(); \
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
