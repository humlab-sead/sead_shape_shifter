SHELL := /bin/bash

UVICORN_PORT := 8000

.PHONY: csv excel
excel:
	@export PYTHONPATH=. && python src/arbodat/survey2excel.py \ 
		--env-file src/arbodat/input/.env \
		--sep ";" \
		--mode excel \
		--config-file src/arbodat/input/arbodat.yml \
		src/arbodat/input/arbodat_mal_elena_input.csv \
		tmp/arbodat.xlsx

csv:
	@export PYTHONPATH=. && python src/arbodat/survey2excel.py \ 
		--env-file src/arbodat/input/.env \
		--sep ';' \
		--mode csv \
		--config-file src/arbodat/input/arbodat.yml \
		src/arbodat/input/arbodat_mal_elena_input.csv \
		tmp/arbodat

.PHONY: dev-serve
dev-serve: dev-kill
	@echo "Starting uvicorn on port $(UVICORN_PORT)..."
	@nohup uv run uvicorn main:app --host 0.0.0.0 --port $(UVICORN_PORT) --reload &> uvicorn.log & echo $$! > uvicorn.pid
	@echo "Starting OpenRefine..."
	@nohup ./bin/openrefine-3.9.5/refine -i 127.0.0.1 -p 3333 &> refine.log & echo $$! > refine.pid
	@echo "✅ Development servers started!"
	@echo "   - Uvicorn: PID $$(cat uvicorn.pid), log → uvicorn.log"
	@echo "   - OpenRefine: PID $$(cat refine.pid), log → refine.log"

dev-stop:
	@if [ -f uvicorn.pid ]; then kill -TERM `cat uvicorn.pid`; fi
	@if [ -f refine.pid ]; then kill -TERM `cat refine.pid`; fi
	@rm -f uvicorn.pid refine.pid
	@echo "✅ Servers stopped."

dev-kill:
	@pkill -f '[u]vicorn main:app' 2>/dev/null || true
	@pkill -f '[r]efine' 2>/dev/null || true
	@rm -f uvicorn.pid refine.pid
	@echo "✅ Servers killed."

.PHONY: serve
serve:       
	@uv run uvicorn main:app --host 0.0.0.0 --port $(UVICORN_PORT) --reload
	
debug-serve:       
	@uv run uvicorn main:app --host 0.0.0.0 --port $(UVICORN_PORT) --reload --log-level debug

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
	@uv run black src tests main.py

.PHONY: pylint
pylint:
	@uv run pylint src tests main.py

.PHONY: lint
lint: tidy pylint check-imports

.PHONY: check-imports
check-imports:
	@python scripts/check_imports.py

.PHONY: fix-imports
fix-imports:
	@python scripts/fix_imports.py

isort:
	@uv run isort src tests main.py

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

.PHONY: generate-schema
generate-schema:
	@echo "Generating entity schema files from templates..."
	@uv run python src/scripts/generate_entity_schema.py --all
	@echo "✅ Schema generation complete!"

.PHONY: generate-schema-force
generate-schema-force:
	@echo "Regenerating all entity schema files..."
	@uv run python src/scripts/generate_entity_schema.py --all --force
	@echo "✅ Schema regeneration complete!"
	

SCHEMA_OPTS = --no-drop-table --not-null --default-values --no-not_empty --comments --indexes --relations
BACKEND = postgres

arbodat-data-schema:
	@mdb-schema $(SCHEMA_OPTS) src/arbodat/input/ArchBotDaten.mdb $(BACKEND) > src/arbodat/input/ArchBotDaten_$(BACKEND)_schema.sql 

arbodat-lookup-schema:
	@mdb-schema $(SCHEMA_OPTS) src/arbodat/input/ArchBotStrukDat.mdb $(BACKEND) > src/arbodat/input/ArchBotStrukDat_$(BACKEND)_schema.sql 

arbodat-schema: arbodat-data-schema arbodat-lookup-schema
	@echo "✅ Schema extraction complete!"
