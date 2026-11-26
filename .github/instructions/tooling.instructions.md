---
description: "Use when changing scripts, the Makefile, GitHub Actions workflows, pre-commit hooks, or working with branch promotion."
applyTo: "scripts/**,Makefile,.github/workflows/**,.pre-commit-config.yaml"
---
# Scripts, Make Targets and CI

## Scripts

- Folders: `_shared/` (imports and environment files), `ci/` (checks used by `make`, hooks and workflows), `workflow/` (pull requests, promotion, releases), `project/` (project configuration and data), `target_model/`, `dev/` (diagnostics and local setup), `postgres/`, `tests/`.
- Add each new script to the Script Index in `scripts/README.md`.
- Run Python scripts from the repository root with `uv run python scripts/<folder>/<name>.py`. Do not edit `sys.path`.
- Get the repository root from `scripts._shared.paths.REPO_ROOT`, so a script still works after moving.
- `make ruff` and `make tidy` cover `scripts/`; `make pylint` does not.
- Scripts that change files, branches, GitHub or a database should offer a dry run or a check mode. Do not put credentials in command arguments or files.
- `scripts/ci/verify_promotion_provenance.sh` and `scripts/dev/sync_claude_rules.py` run without the project environment. Keep the second one standard library only.

## Makefile

- Declare targets `.PHONY` and put a short comment above any target whose effect is not clear from its name.
- Put logic of more than a few lines in a script.
- `make lint` changes files (`tidy`, `ruff --fix`) and then runs the checks.
- `make status` is read-only and offline; keep it that way.

## Generated Files

Change the source, run the generator, and commit both.

| Generated | Generator | Check |
|-----------|-----------|-------|
| `.claude/rules/` from `.github/instructions/` | `make claude-rules` | `make check-claude-rules` |
| `frontend/src/schemas/*.json` | `make generate-schemas` | `make check-schemas` (not part of `make lint`) |
| `docs/TARGET_MODEL_SCHEMA_REFERENCE.md` | `make generate-target-model-schema-reference` | `make check-target-model-schema-reference` |
| `docs/sead/SCHEMA.md` | `make sead-schema-docs` | `make sead-schema-check` |

## graphify

The root `AGENTS.md` says when to query the graph and how to check that it is usable. graphify is a uv tool (`~/.local/bin/graphify`), not part of the project `.venv`.

Rebuilding:

- The git hooks (installed by `make install-hooks`) rebuild the code part of the graph in the background after each commit, checkout, merge and rebase. The rebuild is AST-only and makes no LLM calls. Its log is `~/.cache/graphify-rebuild.log`.
- `make semantic-graphify` adds the LLM-based results (documents and community names).
- `make update-graphify` and `make semantic-graphify` also rebuild the wiki in graphify-out/wiki/. `make graphify-wiki` rebuilds only the wiki (local, about a second, no LLM).
- `GRAPHIFY_VIZ_NODE_LIMIT=0` blocks graph.html, which this project does not use.
- `make status` shows whether the graph, the LLM-based results, the community names or the wiki need a rebuild.

Reading:

- If a name matches several nodes, graphify lists them. Retry with `path/to/file.py::Symbol`, for example `graphify explain "backend/app/mappers/project_mapper.py::ProjectMapper"`.
- If `graphify path` finds no directed path, retry with `--undirected`.
- Use graphify-out/wiki/index.md, when it exists, for broad orientation. The git hooks do not rebuild the wiki, so it can lag behind recent commits. For specific questions, use `graphify query` or `graphify explain`, which read the current graph.
- Read graphify-out/GRAPH_REPORT.md only for a broad architecture review, or when queries do not give enough context.

## GitHub Actions

| Workflow | Runs on | Purpose |
|----------|---------|---------|
| `claude-rules-check.yml` | Pull requests that change rules or the generator | Rules match the instruction files |
| `instruction-references-check.yml` | All pull requests | Links and paths in the instruction files exist |
| `layer-imports-check.yml` | All pull requests | `src/` does not import `backend` |
| `promotion-guard.yml` | Pull requests into `staging` and `main` | Code commits arrived through pull requests |
| `release.yml` | Push to `main`, or manual | semantic-release |
| `container-release.yml` | Pull requests, and pushes to `container-release` | Checks and publishes the container bundle |

- No workflow runs the Python or frontend tests or `make lint`. Run them locally before merging.
- Give each job only the permissions it needs.
- `release.yml` pushes to `main` with the release bot token. Do not replace it with the workflow token.

## Branches and Promotion

- Changes flow `dev` to `staging` to `main`.
- Protected paths are `scripts/`, `src/`, `backend/`, `frontend/`, `ingesters/`, `tests/` and `.github/workflows/`. Changes to them must reach `dev` through a pull request, or promotion fails. The pre-commit hook blocks such commits on `dev`, `staging` and `main`.
- If you change the protected path list, update the script, the README section and this file together.
- To open a change pull request, use `scripts/workflow/create_change_pr.py`; start with `--dry-run`. It does not run checks, so `--default-validation` is only correct after you ran them.
- Promote with `make promote-dev-to-staging`. See `scripts/README.md`.
- Commit messages follow Conventional Commits. `semantic-release` reads them to choose the version. See `github-workflow.instructions.md`.
- Commit, push, open or merge pull requests, and promote only when the user asks.

## Tests

- Script tests are in `scripts/tests/` and `tests/`. Run them with `uv run pytest <path>`; `make test` does not include `scripts/tests/`.
