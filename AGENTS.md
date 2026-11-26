# Shape Shifter – Agent Guide

> Subsystem-specific rules live in `src/AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`, and `ingesters/AGENTS.md`. Read the relevant one when working in that subtree.

## Architecture

- Monorepo: Core (`src/`), Backend (`backend/app/`), Frontend (`frontend/`), Ingesters (`ingesters/`). One `.venv/` at repo root.
- Core pipeline (immutable order): **Extract → Filter → Link → Unnest → Translate → Store** — orchestrated by `ShapeShifter` (`src/normalizer.py`) via `ProcessState`.
- Backend: FastAPI; routers in `api/v1/endpoints/`, services in `services/`, Pydantic v2 models in `models/`.
- Frontend: Vue 3 `<script setup>` + Pinia stores + composables + Axios + Monaco YAML editor.

## Documentation and Code

- Use `docs/` for documented design, usage, and procedures.
- Current code, configuration, scripts, workflows, and generated artifacts decide how the system behaves. If a document disagrees with them, follow them and report the difference.
- Verify documentation claims against the source that implements or runs the described behavior. The exception is `docs/DESIGN.md`: follow "Sources to trust" in `.github/instructions/design.instructions.md`.
- `docs/archive/` is historical background only. It does not describe current practice.
- Proposals in `docs/proposals/` describe planned or past design work, not current behavior.

## Workflow Commands

- `make install` — full setup; `uv pip install -e ".[api]"` for Core+API only.
- `make backend-run` (FastAPI :8012), `make frontend-run` (Vue :5173).
- `make test` — full suite; `uv run pytest tests -v` (Core); `uv run pytest backend/tests -v` (backend).
- `make lint` / `make tidy` (Black + isort) before committing.
- `make status` — read-only check of graphify (hooks, graph and wiki freshness, community names), repository hooks, branch promotion and the SEAD schema reference; lists the command for each action needed.
- Run targeted tests for the changed area before finishing. Run broader tests when a change crosses layers.
- When completing work tracked by a task or phase plan, update its progress tracker, checklist, status, and deliverables in the same change. Do not leave completed work marked as not started.
- When drafting a pull request title or description, follow `.github/pr-description-instructions.md`. Use `.github/promotion_pr_template.md` for promotions (`dev` into `staging` or `staging` into `main`), and `.github/pull_request_template.md` for other pull requests.

## Documentation Vocabulary

- Use plain, concrete language in generated code, comments, docstrings, PR text, and documentation.
- Prefer words that name the actual thing, action, rule, input, output, or result directly.
- Do not treat any word as forbidden, but use abstract or overloaded terms carefully. If a technical term is necessary, define it nearby or pair it with a plain-language explanation.
- Use these terms carefully unless they are established project vocabulary: `evidence`, `boundary`, `framing`, `canonical`, `surface`, `facing`, `slice`, `signal`.
- Prefer explicit wording such as `data`, `result`, `source`, `check`, `validation result`, `limit`, `responsibility`, `allowed range`, `rule`, `purpose`, `reason`, `background`, `request details`, `standard`, `preferred`, `normalized`, `official`, `interface`, `page`, `endpoint`, `entry point`, `used by`, `shown to`, `exposed to`, `part`, `section`, `subset`, `step`, `indicator`, `warning`, `metric`, `status`, `input`, `output`, `error`, and `side effect`.
- Write for a mixed audience: junior developers, maintainers, testers, data managers, researchers, and non-technical stakeholders.
- The closer text is to code or user-visible behavior, the more concrete the vocabulary should be.
- Comments and docstrings should explain behavior, responsibility, assumptions, inputs, outputs, and side effects. Avoid metaphorical or fashion-driven wording when a simpler phrase is equally accurate.
- Write docstrings using concrete behavior-first wording. Prefer direct statements such as `Reads sample rows from a CSV file.`, `Returns validation errors for missing required fields.`, `Uses the site ID to find matching sample groups.`, and `Does not write changes to the database.` Avoid vague wording such as `Ingests artifacts across the import boundary.`, `Resolves canonical entities for downstream consumers.`, and `Emits signals for the review surface.`

## Cross-Cutting Rules

- **Absolute imports only**: `from src...` and `from backend.app...` — never relative across packages.
- **Layer boundary**: API models stay in `backend/app/models/`; domain logic stays in `src/`. Never import `backend.*` from `src/`. Put business logic in services and domain code, not in API models or route handlers.
- **Mapper**: API↔Core conversions go through the mappers in `backend/app/mappers/`; projects go through `ProjectMapper`. Never bypass them.
- **Directives** (`@include:`, `@value:`, `@load:`, `${ENV_VAR}`): API models and saved YAML keep them as written. `ProjectMapper.to_core()` resolves them when it converts a project. Do not add other places that resolve them, and never save a resolved config. Existing exceptions are listed in `.github/instructions/mappers.instructions.md`.
- **Registries**: use `@Validators.register(...)`, `@DataLoaders.register(...)`, `@get_ingester_registry().register(...)`, and the matching registry for filters and other extension types — never bypass a registry.
- **Circular imports**: use constructor injection, factory functions, or `TYPE_CHECKING` for type-only imports — never restructure imports as a workaround.
- **Async**: `ShapeShifter.normalize()` and all data loaders are async — await them and never call them with `asyncio.run()` inside a loader or service. Check where backend services call between sync and async code.

## Three-Tier Identity System

Core FK links use local `system_id` values. A change-request package can use an existing target ID only when the project declares `foreign_key_value_sources.<target>: public_id`. This applies only where the change-request ingester writes the package FK; the declaration does not create a Core link or dependency.

| Tier | Field | Purpose | FK values? |
|------|-------|---------|-----------|
| 1 | `system_id` | Local sequential integer | **Yes, for Core links** |
| 2 | `keys` | Business keys for deduplication | No |
| 3 | `public_id` | Target schema column name; holds SEAD IDs after mapping | No |

- `public_id` must end with `_id`. A Core FK child column uses the parent's `public_id` as its name and the parent's `system_id` as its value. The change-request package exception is project-specific and requires a target database lookup.

## Code Conventions

- Line length ≤ 140 characters; Black + isort.
- `loguru.logger` for logging; type hints on all functions and Pydantic models.
- Naming: `snake_case` entities, `_id` suffix for public IDs, `/api/v1/{resource}` (plural) for endpoints.
- `@pytest.mark.asyncio` for async tests. Backend routes protected by project authorization need the `authorized_client` fixture, not a plain `TestClient`; see `.github/instructions/test-writing.instructions.md`.

## Common Implementation Tasks

- **Backend endpoint**: router in `backend/app/api/v1/endpoints/`, models in `backend/app/models/`, service in `backend/app/services/`, register in `backend/app/api/v1/api.py`. Every route needs an authorization requirement and a row in the route inventory. Read `.github/instructions/backend-api.instructions.md`.
- **Constraint validator**: `@Validators.register(key=..., stage=...)` in `src/specifications/constraints.py`. Read `.github/instructions/features/validation.instructions.md`.
- **Data loader**: `@DataLoaders.register(key=...)` in `src/loaders/`, `ClassVar` schema on the class. Read `.github/instructions/features/loaders.instructions.md`.
- **Specification**: subclass `ProjectSpecification`, implement `is_satisfied_by()`, add to `CompositeProjectSpecification.get_default_specifications()`.
- **Ingester**: directory under `ingesters/<name>/`, implement `Ingester` protocol, `@get_ingester_registry().register(key="<name>")`. Read `.github/instructions/features/ingesters.instructions.md`.
- **New files**: Claude Code loads a path rule when it reads a matching file, which may not happen when a task only creates files. Before creating a mapper, API file, loader, validator, specification, ingester, frontend store, editor, test, script or workflow, read the matching file in `.github/instructions/`: `mappers`, `backend-api`, `features/loaders`, `features/validation`, `features/specifications`, `features/ingesters`, `frontend-stores`, `frontend-monaco`, `frontend-test`, `test-writing` or `tooling`.
- **Phase plan**: when asked to create or update a phased implementation plan, delivery sequencing document, or migration phase plan, use `.github/instructions/phase-plan.instructions.md`.
- **Task plan**: when asked to create or update a task plan for one development phase, use `.github/instructions/task-plan.instructions.md`.

## Key References

- Core models: `src/model.py`, `src/specifications/constraints.py`, `src/specifications/`.
- Backend entry: `backend/app/main.py`; validation: `backend/app/services/validation_service.py`.
- SIMS client: `backend/app/clients/sims_client.py`. Environment variables are listed in `.github/instructions/backend-api.instructions.md`.
- Docs: `docs/DESIGN.md`, `docs/CONFIGURATION_GUIDE.md`, `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md`, `docs/TESTING.md`.
- SEAD schema: `docs/sead/columns.csv` (current tables and columns with types, nullability, PKs and FK targets) and `docs/sead/SCHEMA.md` (the same per table, generated). Refresh with `make sead-schema`. The numbered `docs/sead/0*_*.sql` files are a stale historical dump; do not use them to decide tables or columns. See `docs/sead/README.md`.
- Scoped instructions: `.github/instructions/` is the source (VS Code Copilot uses the `applyTo` pattern to match rules to files; in some session types the agent gets only a list and has to read the rule itself). `.claude/rules/` is generated from it for Claude Code (`applyTo` becomes `paths`). Edit only the sources, then run `make claude-rules`; `make lint`, pre-commit and CI fail when the two differ. `github-workflow` has no `applyTo` because it applies to a task, not to files, so it is not converted: read it directly before creating an issue or preparing a commit. `writing-style` also applies to comments, docstrings, PR text and issues, which its `**/*.md` pattern does not cover: read it directly for those.
- UCanAccess setup: `scripts/dev/install-uncanccess.sh` (requires Java JRE).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships. The graph is built locally and is not committed: graphify-out/ is in `.gitignore`. graphify is a uv tool (`~/.local/bin/graphify`), not part of the project `.venv`.

How the graph is kept current:
- graphify git hooks (installed by `make install-hooks`) rebuild the code part of the graph in the background after each commit, checkout, merge and rebase. The rebuild is AST-only and makes no LLM calls; its log is `~/.cache/graphify-rebuild.log`.
- `make semantic-graphify` adds the LLM-based results (documents and community names). Run it only when the user asks.
- `make update-graphify` and `make semantic-graphify` also rebuild graphify-out/wiki/; `make graphify-wiki` rebuilds only the wiki (local, about a second, no LLM).
- `make status` shows whether the graph, the LLM-based results, the community names or the wiki need a rebuild.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If a name matches several nodes, graphify lists them; retry with `path/to/file.py::Symbol`, for example `graphify explain "backend/app/mappers/project_mapper.py::ProjectMapper"`. If `graphify path` finds no directed path, retry with `--undirected`.
- If graphify-out/wiki/index.md exists, use it for broad orientation instead of raw source browsing. The git hooks do not rebuild the wiki; only `make update-graphify`, `make semantic-graphify` and `make graphify-wiki` do, so it can lag behind recent commits. Use `graphify explain` or `graphify query` for anything specific, because they read the current graph.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- Before your first graph query in a session, check that the graph is usable:
  - If `graphify hook status` reports a hook as `not installed`, tell the user and suggest `make install-hooks`. Do not install hooks yourself.
  - If graphify-out/graph.json is missing, or older than the latest commit (compare its modification time with `git log -1 --format=%ct`), run `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .` first. A stale graph usually means the hooks are missing or a background rebuild failed; mention it to the user.
- Do not run `graphify update` after every edit; the hooks handle that at commit time. Run `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .` only when you changed code in this session and need to query the graph again before the change is committed. The variable blocks graph.html, which this project does not use.
- Treat the graph as a navigation aid, not the source of truth. If it conflicts with source or tests, trust the source.

## rtk (Token Optimization)

Prefix shell commands with `rtk` to compress output and reduce token usage (saves 60–90%), except for shell built-ins, interactive commands and commands where you need the raw output. If `rtk` fails, retry without it. Examples: `rtk uv run pytest`, `rtk make test`, `rtk git log -10`. Use `rtk gain` for analytics and `rtk proxy <cmd>` for raw output. See `RTK.md` for details.
