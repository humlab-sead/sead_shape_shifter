# Review of the Claude rules in `.claude/rules/`

Date: 2026-11-24. Branch: `claude-rules-sync`.

## Purpose

`.claude/rules/` is generated from `.github/instructions/` by `scripts/dev/sync_claude_rules.py` (`make claude-rules`). Each `applyTo` setting becomes a `paths:` list. This review checked whether the generated rules are correct, which rules cause problems, and what is missing.

How the review was done: all 27 rule files were read. Their `paths:` globs were matched against the repository, and the code names they mention were searched for in `src/` and `backend/app/`. The first pass did not check the long files `shapeshifter-configuration`, `graph`, `materialization`, `ingesters` and `specifications` claim by claim; see "Wrong claims found in the second pass".

## Summary

The rules are mostly correct, specific and consistent with `AGENTS.md`. Problems found:

- Some content was out of date (identity rule, renamed function, a file path that no longer exists).
- Some `paths:` globs matched no files, so those rules did not load for the files they were meant for.
- Several areas had no rule at all (mappers and directives, backend API, frontend stores and tests, tooling). Rules were added later; see "Added rules for G1–G5".

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
| G1 | No rule scoped to `backend/app/mappers/**` for the `ProjectMapper` and directive rules (`@include:`, `@value:`, `@load:` and `${ENV_VAR}` are resolved only in `ProjectMapper.to_core()`). Only one line in `python.md` mentions it. | Closed: `mappers` |
| G2 | No rule for backend API code: `backend/app/api/**`, `models/**`, `authorization/**`, `clients/**` (the `require_project` pattern, SIMS client and its environment variables). The `add-endpoint` prompt is not available to Claude. | Closed: `backend-api` |
| G3 | The frontend has one generic rule and `graph`. Nothing covers Pinia stores, the Monaco YAML editor or Vitest conventions. The `frontend-test` prompt is not available to Claude. | Closed: `frontend-stores`, `frontend-monaco`, `frontend-test` |
| G4 | General test conventions exist only inside `python.md`. `testing.md` covers writing `docs/TESTING.md`, not writing tests. | Closed: `test-writing` |
| G5 | No rule for `scripts/**`, the Makefile, `.github/workflows/` or branch promotion. | Closed: `tooling` |
| G6 | Four instruction files have no `applyTo` and are skipped by the generator: `writing-style`, `diagrams`, `github-workflow`, `phase-plan`. Claude reads them only when pointed at them. | Closed: `applyTo` added to three; `github-workflow` left skipped |
| G7 | The prompts in `.github/prompts/` and the agents in `.github/agents/` have no Claude version. Only three prompts are named in `AGENTS.md`. | Closed: prompts removed; custom agents unchanged |

### Behavior to verify

Question: does Claude Code load a `paths:` rule when a task only creates a matching file? Tested on 2026-11-26 in one live Claude Code session in the VS Code extension. Each case used rules that had not yet loaded in that session.

| Action | Rules that loaded |
|--------|-------------------|
| Read `docs/CLAUDE_RULES_REVIEW.md` | `diagrams`, `writing-style` |
| Create `frontend/src/stores/zzRuleLoadProbe.ts` with the Write tool | `frontend`, `frontend-stores`, after the file was written |
| Create `backend/tests/mappers/zz_rule_load_probe.py` with a shell command | None |
| Read `backend/tests/mappers/test_data_source_mapper.py` (control) | `mappers`, `python`, `test-writing` |

Result: reading a matching file loads its rules. Creating a file with the Write tool also loads them, but too late to affect the content of that write. Creating a file with a shell command did not load them. The instruction in `CLAUDE.md` to read the matching rule before creating a file is therefore still needed. The test files were deleted. Editing a file was not tested separately, and the Claude Code terminal was not tested.

### Copilot rule loading

Tested on 2026-11-26 in one Copilot session in VS Code (client `vscode-agent-host`, model GPT-6 Luna). The request was "Summarize this file." with a selection in `backend/app/mappers/project_mapper.py` attached. The results come from the session record, `~/.copilot/session-state/<session id>/events.jsonl`.

- The system prompt had a table with each rule's file pattern, path and description. It told the agent to read the listed files with the `view` tool before changing code.
- The text of `mappers.instructions.md` was not in the system prompt and did not appear after the agent read `project_mapper.py`. The agent did not open the rule file. The `python` and `test-writing` rules were not included in full either.
- The full text of `coding-practices`, `diagrams`, `writing-style`, `phase-plan` and `github-workflow` was in the system prompt. The record does not show why these were included.
- The table also listed the generated files in `.claude/rules/`, so rules appeared twice. The `.claude/rules/` rows checked had no description. The table also included instruction files from `sead_authority_service`, another folder in the workspace.

Second test, same day, client and model, in a new session: "In backend/app/mappers/project_mapper.py, improve the docstring of the ProjectMapper class." The request did not mention rules. The system prompt again had the table and not the `mappers` text. The agent opened `python.instructions.md` and `mappers.instructions.md` with the `view` tool, and then changed the file.

Result: in this session type, a matching `applyTo` pattern did not attach the `mappers` rule for the read-only request. For the edit request, the agent used the table and read both matching rules before the change. Other rules were not tested this way. The VS Code documentation describes automatic attachment by `applyTo` for Local sessions with `chat.includeApplyingInstructions` on; that was not tested.

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

### Added rules for G1–G5

- [x] `mappers` for `backend/app/mappers/**` and its tests (G1).
- [x] `backend-api` for the API, models, authorization and client code, with the endpoint steps and the SIMS client (G2).
- [x] `frontend-stores`, `frontend-monaco` and `frontend-test`, with the Vitest steps (G3).
- [x] `test-writing` for `tests/**`, `backend/tests/**` and `scripts/tests/**`; the test line moved out of `python` (G4).
- [x] `tooling` for `scripts/**`, `Makefile`, workflows and pre-commit, including branch promotion (G5).

How both tools get them: Copilot Chat reads the files in `.github/instructions/`; whether a matching file is attached automatically depends on the session type (see "Copilot rule loading"). Claude Code reads the generated files in `.claude/rules/`. `AGENTS.md` names the rules to read before creating new files.

The new globs were checked against the repository: each matches at least one file. For loading in a live Claude Code session, see "Behavior to verify". Loading in a live Copilot Chat session has not been tested.

### Found while writing the rules

These are code or workflow problems. No code was changed.

- `TaskService.initialize_task_list()` converts the project with `ProjectMapper.to_core()`, converts the resolved config back with `to_api_config()` and saves it. An in-memory test of the two conversions replaced `@value: entities.a.keys` with `['code']`. The save itself was not run. Resolved environment variable values could be written to the project file the same way. The frontend has no caller of this method, but the API route exists.
- `AGENTS.md`, `backend/AGENTS.md`, `backend/README.md`, `.github/copilot-instructions.md` and the `python` rule said that directives are resolved only in the mapper layer, which the code does not follow. **Fixed:** they now say not to add other places, and the `mappers` rule lists the existing ones.
- Some routes return `detail=str(e)` in 500 responses, for example in `endpoints/materialization.py`.
- `registerProjectCompletions()` registers a new completion provider each time a YAML editor mounts and never disposes it. This was read in the code; duplicate suggestions were not tested in a browser.
- No GitHub workflow runs tests or `make lint`.

### Open: decisions

- [x] Skipped instruction files (G6):
  - `phase-plan`: `docs/proposals/**/*_PHASE_PLAN.md`.
  - `writing-style`: `**/*.md`. Not `**/*`, because the generator would then load it for every Claude task. The main plain-language and docstring rules are already in `AGENTS.md`.
  - `diagrams`: `docs/**/*.md,**/*DIAGRAMS.md`. This misses Mermaid diagrams in other Markdown files outside `docs/`, such as `ingesters/sead_change_request/README.md`.
  - `github-workflow`: left without `applyTo`. It applies to commits and issues, not to files. `AGENTS.md` says when to read it. If that is not enough, make it a skill.
- [x] Prompts and agents (G7). Neither Copilot nor Claude Code uses a prompt file on its own: someone has to name it, or another file has to point to it. The maintainer does not use them, so `.github/prompts/` was removed instead of converted to skills.
  - `add-loader`, `add-validator` and `core-test`: file locations and test setup moved to the `features/loaders` and `features/validation` rules. Their code templates were not kept; the loader template had the wrong `load()` arguments, import path and logger.
  - `add-endpoint`, `backend-test` and `frontend-test`: covered by the `backend-api`, `test-writing` and `frontend-test` rules.
  - `yaml-review`, `entity-validation` and `dependency-check`: not kept. The `review-shapeshifter-configuration` skill covers this work.
  - `sead-database` and `sead-quick-ref`: not kept. `docs/sead/` is the schema reference. Their short explanation that analysis entities are virtual records was not moved.
  - The eight review and routing prompts and `docs/other/AI_AGENT_SETUP.md`, which described how to use them: not kept, and no skill replaces them.
  - The files in `.github/agents/` are Copilot custom agents. They were not changed and have no Claude version.
  - Removed files can be restored from git history.

### Open: verification

- [x] In a live Claude Code session, confirm that opening a matching file loads its rule, and that creating a new file does or does not (see "Behavior to verify"). Here "opening" means Claude reading the file; opening it in the editor did not load rules before the read.
- [x] In a live Copilot Chat session, confirm that the new instruction files are attached for matching files. They are not attached automatically in the session type tested; the agent read `mappers` and `python` before an edit. See "Copilot rule loading".
- [ ] Open the pull request for branch `claude-rules-sync` into `dev` and confirm the new `claude-rules-check` workflow runs and passes.
