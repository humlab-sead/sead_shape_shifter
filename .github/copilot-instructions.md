# Shape Shifter - AI Coding Instructions

Keep this file small and always-on. Use `.github/instructions/*.instructions.md` for task-specific guidance.

## Documentation scope

- Use `docs/` as the source of truth.
- Ignore `docs/archive/`.
- Treat `docs/features/` as backlog, not authoritative implementation guidance, unless the user asks about roadmap or planned features.

## Repository structure

- `src/`: core Python transformation engine
- `backend/app/`: FastAPI backend
- `frontend/`: Vue 3 frontend
- `ingesters/`: pluggable ingester implementations
- Python uses the root `.venv/`

Core pipeline order matters: Extract → Filter → Link → Unnest → Translate → Store.

## Always-on architecture rules

- Keep API models in `backend/app/models/` and domain logic in `src/`.
- Convert API and core models with mappers.
- Resolve environment variables and directives only at the mapper boundary.
- Do not put business logic in API DTOs.
- Do not import API-layer models into `src/`.
- Prefer constructor injection or factory functions when services depend on each other.
- Use `TYPE_CHECKING` imports for type hints.
- Validators in `src/validators/` must receive data and config; they do not fetch data.
- Return domain validation issues, not API DTOs.
- Use local `system_id` values for relationships.
- `keys` are business keys for matching and deduplication.
- `public_id` names target and export identity columns and should end with `_id`.
- Do not use external IDs as internal foreign-key values.
- Directives such as `@include:`, `@load:`, and `@value:` belong in YAML and API-layer models; core models should receive resolved values.
- Use the registry pattern for validators, loaders, filters, and ingesters.
- Loader schemas belong on loader classes as `schema: ClassVar[DriverSchema]`.
- Use absolute imports only: `from src...` and `from backend.app...`.
- Await loaders and check sync/async service boundaries carefully.

## Workflow expectations

- Use the unified environment at `.venv/` for Python work.
- Run targeted tests for the changed area before finishing.
- Run broader tests when a change crosses layers.
- When touching project YAML, validate against `.github/instructions/shapeshifter-configuration.instructions.md`.

## Task-specific instructions

Use the focused files under `.github/instructions/` for detailed guidance:

- `python.instructions.md` - Python code, loaders, validators, and tests
- `frontend.instructions.md` - Vue, Pinia, and frontend API conventions
- `project-config.instructions.md` - `shapeshifter.yml` and config validation
- `shapeshifter-configuration.instructions.md` - YAML rules, identity system, and FK patterns
- `github-workflow.instructions.md` - issue, commit, and handoff workflow
- `ingesters.instructions.md` - ingester structure, discovery, and testing
- `diagrams.instructions.md` - Mermaid diagram style and conventions
- `operations.instructions.md` - writing and maintaining `docs/OPERATIONS.md`
- `user-guide.instructions.md` - writing and maintaining `docs/USER_GUIDE.md`
- `phase-plan.instructions.md` - phased implementation and delivery sequencing
- `task-plan.instructions.md` - task plans for individual implementation phases
- `writing-style.instructions.md` - concrete wording for docs, comments, and PR text
- `simplify-docs` - rewrite documents in simpler, more direct language while keeping structure and meaning the same
- `testing.instructions.md` - testing strategy, test levels, and validation guidance
- `development.instructions.md` - local setup, workflow, and development practices

## graphify

For repo architecture or relationship questions, follow the graphify quick start in `AGENTS.md`.

<!-- rtk-instructions v2 -->
**rtk** is a CLI proxy that filters and compresses command outputs, saving 60-90% tokens.

Use `rtk` for shell commands unless raw output, shell built-ins, or interactive commands require otherwise.

Examples:
```bash
rtk uv run pytest
rtk make test
rtk pylint src/
rtk git status
rtk git log -10
rtk cat docs/proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md
```

If `rtk` fails, retry without it.

Meta: `rtk gain`, `rtk gain --history`, `rtk discover`, `rtk proxy <cmd>`
<!-- /rtk-instructions -->
