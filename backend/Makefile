SHELL := /bin/bash

SOURCE_DIRS := app

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
	@uv run black $(SOURCE_DIRS)

.PHONY: tidy
tidy:
	@uv run isort $(SOURCE_DIRS)
	@uv run black $(SOURCE_DIRS)
	
.PHONY: pylint
pylint:
	@uv run pylint $(SOURCE_DIRS)

.PHONY: lint
lint: tidy pylint

