# Review of the Claude rules in `.claude/rules/`

Date: 2026-11-24. Branch: `claude-rules-sync`.

## Purpose

`.claude/rules/` is generated from `.github/instructions/` by `scripts/dev/sync_claude_rules.py` (`make claude-rules`). Each `applyTo` setting becomes a `paths:` list. This review checked whether the generated rules are correct, which rules cause problems, and what is missing.

How the review was done: all 27 rule files were read. Their `paths:` globs were matched against the repository, and the code names they mention were searched for in `src/` and `backend/app/`. The first pass did not check the long files `shapeshifter-configuration`, `graph`, `materialization`, `ingesters` and `specifications` claim by claim; see "Wrong claims found in the second pass".

## Summary

The rules are mostly correct, specific and consistent with `AGENTS.md`. Problems found:

- Some content was out of date (identity rule, renamed function, a file path that no longer exists).
- Some `paths:` globs matched no files, so those rules did not load for the files they were meant for.
- Several areas have no rule at all (mappers and directives, backend API, frontend stores and tests, tooling).

## Findings

### Problems in existing rules

| # | Finding | Status |
|---|---------|--------|
| P1 | `features/entities` said Core FK values are always `system_id` and that external IDs as FK values are a mistake. `AGENTS.md` allows one exception: a change-request package FK declared with `foreign_key_value_sources.<target>: public_id`. | Fixed |
| P2 | `features/execution` and `features/loaders` named `_resolve_project_local_file_options()`. The current function is `apply_local_file_options()` in `src/normalizer.py`. | Fixed |
| P3 | References such as `features/loaders.instructions.md` did not exist under `.claude/rules/`. The generator now rewrites them. | Fixed |
| P4 | `frontend` contained the text `lang=\"ts\"` with stray backslashes (the source file had them too). | Fixed |
| P5 | `src/constraints.py` does not exist. The file is `src/specifications/constraints.py`. The wrong path was in the `validation` instruction, `AGENTS.md` and `.github/prompts/add-validator.prompt.md`. | Fixed |
| P6 | Three classes were named `ValidationIssue`. They are now `ConstraintIssue` (`src/specifications/constraints.py`), `DataValidationIssue` (`src/validators/data_validators.py`) and `TestRunIssue` (`backend/app/models/test_run.py`; the first version of this review missed this one). | Fixed (renamed) |
| P7 | `features/transforms` says extra columns are evaluated before linking. `features/execution` lists them under the Translate stage, and its column table omits them. The deferral rules in both are correct; the summaries disagree. | Fixed |
| P8 | Some instruction text still mentions Copilot (`proposal-writing-guide`: "Copilot workflow"; `phase-plan`: "Copilot Instructions"). | Fixed |
| P9 | One directory can load two rules: `src/specifications/**` loads `entities` and `specifications`. `tests/process/**` loads `execution` and `transforms`. This costs extra context and the two rules can drift apart. | Fixed |

### Wrong claims found in the second pass

The first review checked names and paths. These problems appeared when the described behavior was compared with the code. All are fixed. A wider search then found more copies of C1, C3, C5, C6, C8 and C9 in prompts, `docs/DESIGN.md`, `docs/DEVELOPMENT.md`, a presentation, a code comment and docstrings; those are fixed too. Earlier release notes, `CHANGELOG.md`, proposals and the archive were not changed.

| # | Where | Claim | What the code does |
|---|-------|-------|--------------------|
| C1 | `transforms`, `src/AGENTS.md`, `extra_columns.py` docstring | A short list of DSL functions, presented as complete (`transforms` and `src/AGENTS.md` added "no others") | `DEFAULT_FUNCTIONS` registers more functions. The texts now point to it instead of copying names |
| C2 | `execution` | Translate applies `replacements`, evaluates `extra_columns` and maps `public_id`; Store writes to `table_store` | Replacements run during extraction; Translate renames columns; Store writes the output target |
| C3 | `execution`, `transforms`, `src/AGENTS.md` | Filters always run before linking | Filters run at `extract`, `after_link` or `after_unnest` |
| C4 | `execution` | `DeferredLinkingTracker.retry()` runs after the main loop | There is no such method. `retry_linking()` runs after each entity and again after the loop |
| C5 | `materialization`, `backend/AGENTS.md` | The entity `type` does not change; the path is stored in `materialized.path`; unmaterialization deletes the sidecar file | The type becomes `fixed`; the path is only in the `@load:` value; the file is not deleted |
| C6 | `ingesters`, `AGENTS.md`, `ingesters/AGENTS.md`, two ingester READMEs, `docs/DEVELOPMENT.md`, `ingesters/__init__.py` | Register with `@Ingesters.register(...)` | `Ingesters` does not exist. Use `@get_ingester_registry().register(...)` |
| C7 | `specifications`, `AGENTS.md`, `src/AGENTS.md` | Add new specs to `CompositeProjectSpecification.__init__()` | The list is in `get_default_specifications()` |
| C8 | `validation`, add-validator prompt | Constraint validators return lists of dictionaries; conformance validators are constraint validators | Constraint validators implement `is_applicable()` and `validate(context)`; conformance validators are separate |
| C9 | `loaders`, `entities`, `execution` | `UCanAccessLoader`, `_process_merged_branch()` | `UCanAccessSqlLoader`, `process_merged_branch()` |
| C10 | `target-model` | A table listing the conformance validators; the bridge check starts with a source-to-bridge FK | The table was incomplete. The code checks that the bridge entity exists; the source has no FK to it |
| C11 | `validation` | A list of the current data validators | The list was incomplete. The text now points to the file |
| C12 | `design` instruction | Use the `proposal-implementation-plan` prompt | No such prompt exists in `.github/prompts/` |

How much was checked in the long rules: `materialization`, `graph`, `specifications` and `ingesters` were compared with the main source files they describe. For `shapeshifter-configuration`, only claims that can be tested directly were checked (constraint fields, fixed column types, filter names and stages, append inheritance, API entity types, environment variable settings, materialized entity layout). No error was found in those. The rest was checked later; see "Review of `shapeshifter-configuration`".

### Review of `shapeshifter-configuration`

Method: claims were tested with small project configurations run through `CompositeProjectSpecification`, `ShapeShifter.normalize()`, the validation CLI and the backend conformance service, or compared with the source code. The instruction file now describes the current behavior.

Wrong statements, now corrected:

| # | The rule said | What the code does |
|---|---------------|--------------------|
| S1 | Structural validation may accept an unknown constraint name or unsupported cardinality | It rejects both |
| S2 | A missing `@load:` target model can validate as an empty or skipped valid result (two places) | The backend reports an error. The CLI marks conformance `Skipped` |
| S3 | Saves on a bound project reject changes to established `keys` | Keys are not locked. SIMS rejects a changed key list on the next Change Request run |

Incomplete or misleading statements, now clarified: structural validation does not check `system_id` positivity, uniqueness or nulls in full rows with data-only `columns`; a missing parent `public_id` is only a warning and the FK is skipped at linking; FK cycles pass structural validation; overlapping `id_vars`/`value_vars` give a warning, not an error; every CLI workflow runs structural validation first; `surrogate_id` is not read by Core `TableConfig.public_id`; fields read only for extraction can remain in the output.

Statements in the rule that the code does not enforce. These may be defects, but each needs a decision. No code was changed. Each has an issue:

| # | Behavior | How it was shown |
|---|----------|------------------|
| D1 | Normalization drops `system_id` and `public_id` values from full fixed rows when `columns` lists data fields only (the format the rule recommends). `system_id` is renumbered and `public_id` is empty unless the mapping sidecar supplies it. `docs/CONFIGURATION_GUIDE.md` says `system_id` values are preserved Child values that refer to a parent's saved `system_id` can then match no row. [Issue #814](https://github.com/humlab-sead/sead_shape_shifter/issues/814) | A YAML project loaded through the CLI resolver and through `ProjectMapper`; `SubsetService.get_subset()` drops both columns from the loader output. A scan of local project files found 4 fixed entities, in 4 project files, with non-empty public IDs in this format. Their sidecar mappings were not checked |
| D2 | `append_mode: distinct` removes no rows; the code that would apply it is commented out in `src/normalizer.py` Turned off on purpose in the fix for #180; its test is skipped. [Issue #811](https://github.com/humlab-sead/sead_shape_shifter/issues/811) | Normalization run |
| D3 | `validate_project.py` exits 0 when findings have errors. `execute()` returns 1, but `main()` is a Click command and the return value is discarded An existing test expects exit code 0 for a report with an error. [Issue #812](https://github.com/humlab-sead/sead_shape_shifter/issues/812) | CLI run |
| D4 | Equal `var_name` and `value_name` pass validation and lose the melted values [Issue #813](https://github.com/humlab-sead/sead_shape_shifter/issues/813) | Validation and normalization runs |

Not verified: SIMS behavior (the HTTP 409 statement comes from the code's docstring), whether external databases contain provider rows, and guidance about how to review or report, which does not describe code behavior.

### Paths that matched no files

| Rule | Glob | Status |
|------|------|--------|
| validation | `tests/test_constraints*`, `backend/tests/test_validation*` | Replaced with `tests/validators/**`, `tests/specifications/test_constraints.py`, `backend/tests/validators/**` |
| specifications | `tests/test_constraints*` | Replaced with `tests/specifications/**` |
| materialization | `backend/tests/test_materialization*` | Replaced with `backend/tests/specifications/test_materialization*` and `tests/specifications/test_materialize.py` |
| semantic-rules | `backend/app/**/rules/**/*.yml`, `backend/app/**/validation/**/*.py` | Removed |
| whats-new-release-notes | `docs/whats-new/????-??-v*.md` | Removed |
| shapeshifter-configuration | `**/shapeshifter.yaml`, `data/projects/**/*.yaml` | Left in place. No `.yaml` files exist today, so it does no harm. |

### Gaps

| # | Gap | Status |
|---|-----|--------|
| G1 | No rule scoped to `backend/app/mappers/**` for the `ProjectMapper` and directive rules (`@include:`, `@value:`, `@load:` and `${ENV_VAR}` are resolved only in `ProjectMapper.to_core()`). Only one line in `python.md` mentions it. | Open |
| G2 | No rule for backend API code: `backend/app/api/**`, `models/**`, `authorization/**`, `clients/**` (the `require_project` pattern, SIMS client and its environment variables). The `add-endpoint` prompt is not available to Claude. | Open |
| G3 | The frontend has one generic rule and `graph`. Nothing covers Pinia stores, the Monaco YAML editor or Vitest conventions. The `frontend-test` prompt is not available to Claude. | Open |
| G4 | General test conventions exist only inside `python.md`. `testing.md` covers writing `docs/TESTING.md`, not writing tests. | Open |
| G5 | No rule for `scripts/**`, the Makefile, `.github/workflows/` or branch promotion. | Open |
| G6 | Four instruction files have no `applyTo` and are skipped by the generator: `writing-style`, `diagrams`, `github-workflow`, `phase-plan`. Claude reads them only when pointed at them. | Decision needed |
| G7 | The prompts in `.github/prompts/` and the agents in `.github/agents/` have no Claude version. Only three prompts are named in `AGENTS.md`. | Open |

### Behavior to verify

- As far as I know, Claude Code loads a `paths:` rule when it reads a matching file, not when it only creates a new file. A task that only creates files may not load the rule. This was not verified in a live session. Test it, and if it holds, put the most important rules in `AGENTS.md` or make them always-on.

## Checklist of suggested actions

### Done

- [x] Add the `foreign_key_value_sources` exception to `features/entities` and `features/execution`.
- [x] Use `apply_local_file_options()` in `features/execution` and `features/loaders`.
- [x] Rewrite references to other instruction files in the generator.
- [x] Fix the `\"` typo in the frontend instruction.
- [x] Replace or remove globs that matched no files.
- [x] Use `src/specifications/constraints.py` in the validation instruction, `AGENTS.md` and the add-validator prompt.
- [x] Explain the two `ValidationIssue` classes in the validation instruction.

- [x] Describe the real stage order in `features/execution` and `features/transforms` (P7, C2, C3, C4).
- [x] Remove Copilot-specific wording from the instruction files (P8).
- [x] Remove the overlapping globs: `src/specifications/**` from `entities`, `tests/process/**` from `transforms` (P9). `src/specifications/constraints.py` still loads both `specifications` and `validation`, on purpose.
- [x] Check `graph`, `materialization`, `ingesters` and `specifications` against the source, and the testable claims in `shapeshifter-configuration` (C1–C12).
- [x] Rename the three `ValidationIssue` classes (P6).

### Open: follow-up from the second pass

- [ ] **Deferred:** Decide whether unmaterialization should delete the sidecar data file ([issue #810](https://github.com/humlab-sead/sead_shape_shifter/issues/810)). The code keeps it, and the docstrings now say so.
- [x] Check the remaining behavior statements in `shapeshifter-configuration` (see "Review of `shapeshifter-configuration`").
- [x] Fix the 2 failing tests in `backend/tests/authorization/test_route_authentication.py`. Three reconciliation `selection/*` routes are missing from the authorization route metadata. They failed before the rename.

### Open: add rules (new files in `.github/instructions/`, then `make claude-rules`)

- [ ] Mapper and directive rule for `backend/app/mappers/**` (G1).
- [ ] Backend API rule for `backend/app/api/**`, `models/**`, `authorization/**`, `clients/**` (G2). Include the `add-endpoint` steps and the SIMS client.
- [ ] Frontend rules for stores, the Monaco editor and Vitest tests (G3). Include the `frontend-test` steps.
- [ ] Test-writing rule for `tests/**` and `backend/tests/**`, moved out of `python.md` (G4).
- [ ] Tooling rule for `scripts/**`, `Makefile` and `.github/workflows/`, including branch promotion (G5).

### Open: decisions

- [ ] For each skipped instruction file (`writing-style`, `diagrams`, `github-workflow`, `phase-plan`), choose: leave skipped, make always-on, or give it an `applyTo` (G6). Together they are about 15 KB, so always-on has a cost.
- [ ] Decide how to give Claude the prompts and agents from `.github/` (G7). Options: convert them to skills, convert them to `.claude/agents/`, or list them in `AGENTS.md`.

### Open: verification

- [ ] In a live Claude Code session, confirm that opening a matching file loads its rule, and that creating a new file does or does not (see "Behavior to verify").
- [ ] Open the pull request for branch `claude-rules-sync` into `dev` and confirm the new `claude-rules-check` workflow runs and passes.
