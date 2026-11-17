# Output Expectations Sidecar File

## Status

- Proposed change request
- Scope: Move output expectation declarations from `options.output_expectations` into a fixed-name file in the project folder.
- Goal: Keep full-run output checks separate from the project transformation config, and stop unrelated `options` edits from silently removing them.

Follows the shipped feature in [Output Dataset Expectations](../done/OUTPUT_DATASET_EXPECTATIONS/OUTPUT_DATASET_EXPECTATIONS.md) (PR #730). This proposal changes where the declaration lives, not what the checks measure.

## Summary

Declare output expectations in `shapeshifter.expectations.yml`, a fixed-name file next to `shapeshifter.yml`. Core loads it from the project folder, validates it with the existing declaration rules, and keeps the current evaluation, gating, and reporting behavior. Deprecate `options.output_expectations` for one release, then reject it.

The repository already uses this pattern three times: `shapeshifter.mapping.yml`, `shapeshifter.tasks.yml`, and `shapeshifter.layout.yml`. A fourth fixed-name sidecar follows an established convention instead of adding another key to `options`.

## Problem

Output expectations are declared at `options.output_expectations`, in the same section as `data_sources`, `validation`, `translations`, `ingesters`, `reconciliation`, `finally`, `fixed_entity_types`, and the deprecated `mappings`. Two failures follow from that placement.

First, the `options` section is written as a whole. `ProjectService.save_options_boundary` calls `YamlService.merge_boundary(file_path, "options", options)`, which replaces `doc["options"]` entirely. A client that sends a partial options mapping through `PUT /projects/{name}` therefore removes the expectation declarations without touching them. Nothing reports that the checks stopped running: a project with no expectations looks like a project that is correctly configured to have none.

Second, the declarations are hard to find and review. They are run-time checks on produced data, not project transformation settings, and they sit in a section that is edited for unrelated reasons. In the project folder they have no distinct artifact, unlike mappings, tasks, and layout.

This matters now because the feature is new and no editor for it exists, so the intended authoring surface is YAML. Moving the declaration while few projects use it costs less than after the key is established.

## Scope

- A fixed-name sidecar file: name, location, and schema.
- Loading and declaration validation for Core, backend execution, and project-table ingestion.
- Deprecation path for `options.output_expectations`.
- Minimal read and write endpoints for the sidecar content.
- Lifecycle behavior for project copy and sidecar deletion.

## Non-Goals

- Changing metrics, comparison rules, null-key handling, grouping rules, write gating, or result payloads.
- Adding an authoring form, file picker, or schema-driven editor for expectations.
- Moving other `options` groups into sidecars.
- Applying expectations to previews, samples, materialization, or partial-entity requests.
- Supporting more than one expectation file per project, or shared cross-project expectation files.
- Removing `options.output_expectations` in the same release that adds the sidecar.

## Current Behavior

Verified in the repository:

- Declarations live at `options.output_expectations`. `src/output_expectations.py` reads `project.options.get("output_expectations", [])`; `src/specifications/output_expectations.py` reads `project_cfg["options"]["output_expectations"]` and reports issues with field paths under `options.output_expectations[...]`.
- `src/workflow.py::normalize_project` evaluates only when `check_output_expectations` is true and the options key is non-empty. `workflow()` validates declarations before normalization, returns a failed evaluation before `store()`, and raises when output is incomplete.
- Declaration checks run on both full-run write paths even when optional pre-run validation is disabled (`ExecuteService.execute_workflow`, `ProjectIngesterService`).
- No dedicated endpoint, editor, or CLI flag exists for expectations. Writers use `PUT /projects/{name}` (boundary save that replaces `options`) or `PUT /projects/{name}/raw-yaml`.
- Three fixed-name sidecars already resolve from the project folder: `MappingManager` reads `shapeshifter.mapping.yml`, `TaskListSidecarManager` reads `shapeshifter.tasks.yml`, and `LayoutSidecarManager` reads `shapeshifter.layout.yml`.
- `options.mappings` is already deprecated with a warning that names the replacement sidecar (`src/normalizer.py`).
- `ProjectService.copy_project` copies the entire project directory, so a new sidecar file is copied without additional work.
- Superseded configuration still has to be resolved before validation: `ShapeShiftProject.from_file` resolves `@include:`, `@load:`, and `@value:` before the project object exists.

## Proposed Design

### File and schema

Add `shapeshifter.expectations.yml` in the project folder, beside `shapeshifter.yml`.

```yaml
version: 1
expectations:
  - name: site-count
    entity: site
    metric: row_count
    equals: 7
  - name: dataset-count
    entity: dataset
    metric: row_count
    min: 10
    max: 15
  - name: sites-per-project
    entity: site
    metric: grouped_row_count
    column: Projekt
    groups:
      "19_0013": { min: 1 }
      "19_0014": { min: 1 }
      null: { max: 0 }
```

- `version` must be the integer `1`. An unsupported value is a declaration error, so later schema changes can be rejected rather than misread.
- `expectations` is a list of the same declarations accepted today, with the same fields, metrics, comparisons, group rules, and uniqueness requirements.
- Unknown top-level keys are declaration errors. The file is a checked declaration, not a place for notes.
- No `@include`, `@load`, `@value`, or `${ENV}` resolution inside this file in the first version. The file is read as written, so what validation sees is what authors wrote.

### Resolution rule

Core resolves the sidecar from the directory containing the project file.

- `ShapeShiftProject` gained a filename at load time; the sidecar path is `Path(filename).parent / "shapeshifter.expectations.yml"`.
- When no project filename is available (in-memory or test projects), no sidecar is resolved and expectations are off. This keeps existing in-memory callers working unchanged.
- Because the name is fixed, nothing in `shapeshifter.yml` references the file. A project folder containing only `shapeshifter.yml` and the sidecar is a complete configuration.

### Loading and declaration validation

- A loader in `src/sidecars/` reads and parses the file, following the existing sidecar modules.
- `OutputExpectationsSpecification` validates the parsed declarations. The metric, limit, entity, column, key, and group-value rules do not change.
- Reported field paths change from `options.output_expectations[i]` to `shapeshifter.expectations.yml: expectations[i]`, so error messages name the file an author must edit.
- A sidecar that cannot be read or parsed (missing file is not an error; malformed YAML is) produces a declaration error before either write path, with the file name and the YAML problem. A silent "expectations off" result is not acceptable for a file that exists and is broken.
- Declaration checks keep running on both full-run write paths even when optional pre-run validation is disabled.

### Execution and reporting

Unchanged. Evaluation still runs on complete normalized tables before optional foreign-key removal and column translation. A failed check is still an execution validation failure that withholds dispatcher output and ingester writes. Response fields, `output_expectation_results`, CLI reporting, and the separation from `validation_passed` stay as shipped.

### Deprecation

- For one release, `options.output_expectations` continues to work. Its use logs a warning that names `shapeshifter.expectations.yml`.
- When both the sidecar and the options key are present, declaration validation fails and names both locations. This is intentional: a project mid-migration must not silently run one source while an author edits the other.
- After the deprecation release, `options.output_expectations` becomes a declaration error with a migration message.

### API surface

Follow the target-model YAML precedent, which is the closest existing case: a project-owned YAML file with read and write access and no editor form.

- `GET /projects/{name}/expectations-yaml` returns the sidecar content, or a documented "not configured" result when the file is absent.
- `PUT /projects/{name}/expectations-yaml` writes the content verbatim, validating YAML syntax first, and creates a backup. It requires project edit authorization.
- File resolution stays inside the project folder. Paths outside it are rejected.

Authoring in the project YAML editor is a separate decision; this proposal adds no frontend component.

### Lifecycle

- Copying a project copies the sidecar, because `copy_project` copies the directory.
- Deleting the sidecar disables the checks and leaves `shapeshifter.yml` untouched.
- `shapeshifter.yml` backups do not cover the sidecar; the sidecar write path takes its own backup.

## Alternatives Considered

- **`metadata.output_expectations` with a file picker.** Metadata already carries identity, provider binding, and target-model selection, and part of it is server-managed. Adding a run-time check there mixes two responsibilities. It also requires a new `ProjectMetadata` field, an allow-list entry in `ProjectMapper.to_core_dict` (that mapping drops unknown metadata keys), schema regeneration, a picker in `MetadataEditor.vue`, and an upload allow-list change: all to store one reference that a fixed filename avoids. Rejected.
- **A top-level `output_expectations:` section in `shapeshifter.yml`.** Simpler than metadata and avoids the `options` replacement problem, but still grows the main file and still shares a whole-file rewrite boundary. Deferred; the sidecar is the smaller surface.
- **Keep declarations in `options`.** Requires no work, but leaves the silent-loss failure and the placement problem in place.

## Risks And Tradeoffs

- **Silent disable when the file is renamed or deleted.** A missing sidecar means "no checks". Mitigate with an explicit "not configured" API result, a log line on every full run that reports whether expectations were configured, and documentation that names the file. Accepted because the same exposure already exists for the other three sidecars.
- **A second configuration file per project.** Authors must know the file exists. The fixed name and the declaration-error paths are the discovery mechanism.
- **Whole-section replacement no longer matters for expectations, but still matters for other options.** This proposal does not fix partial `options` writes for `data_sources`, `validation`, or `ingesters`.
- **Error-path churn.** Changing reported field paths touches existing tests that assert `options.output_expectations`.
- **Concurrent writers.** The sidecar needs its own read-modify-write lock, matching other project-file writers.

## Testing And Validation

- Sidecar declared, options absent: checks evaluate on both full-run paths, with results matching the current behavior for all three metrics.
- Neither source present: behavior identical to today, empty `output_expectation_results`.
- Both sources present: declaration error naming both locations; no output written.
- Options only: checks still run and the deprecation warning is logged.
- Malformed sidecar, unsupported `version`, unknown top-level key, unknown entity, invalid column, invalid limits, non-scalar group value, duplicate name: declaration errors before either write path, with the file named.
- Failed check and incomplete entity: no dispatcher output and no ingester writes, results reported for every configured check and group.
- Preview, sample, materialization, and partial-entity requests: no expectation evaluation.
- Project copy: the sidecar is present under the new project folder and resolves there.
- Reporting parity: API response fields and CLI output unchanged for the same declarations.

## Acceptance Criteria

- `P-AC-1` A project folder with `shapeshifter.yml` and `shapeshifter.expectations.yml`, and no `options.output_expectations`, evaluates every declared check in full dispatcher runs and full project-table ingestion runs, with unchanged metrics, comparisons, grouping, and null rules.
- `P-AC-2` A project with neither source behaves exactly as today: no evaluation, empty `output_expectation_results`, and no new errors or warnings.
- `P-AC-3` Declaration errors from the sidecar, including a malformed file, unsupported `version`, unknown top-level key, unknown entity, invalid grouping column, missing business keys, and invalid limits, prevent both full-run write paths and name `shapeshifter.expectations.yml` in the reported field path.
- `P-AC-4` `options.output_expectations` still evaluates checks and logs a deprecation warning that names `shapeshifter.expectations.yml`; when both sources declare expectations, validation fails with an error that names both.
- `P-AC-5` Expectation results keep their shipped shape and gating behavior: every configured check and group is reported, a failed check or incomplete entity withholds dispatcher output and ingester writes, and expectation status stays separate from `validation_passed`.
- `P-AC-6` Copying a project copies the sidecar, and deleting the sidecar disables the checks without editing `shapeshifter.yml`.
- `P-AC-7` The sidecar content is readable and writable through project endpoints with project read and edit authorization, and a resolved path outside the project folder is rejected.

## Planning Handoff

Confirmed decisions:

- Sidecar file, not metadata and not a top-level section. Fixed name `shapeshifter.expectations.yml`, no reference from `shapeshifter.yml`.
- Schema is `version: 1` plus `expectations`. Same declarations as today.
- No directive resolution inside the sidecar.
- Both sources present is an error, not a precedence rule.
- Evaluation, gating, and reporting behavior is unchanged.

Constraints and behavior to preserve:

- Expectation evaluation stays on complete normalized tables before optional foreign-key removal and column translation.
- Declaration checks run on both full-run write paths regardless of optional pre-run validation.
- No evaluation for previews, samples, materialization, validation-only requests, or partial-entity runs.
- Read-only SQL, project-folder containment, authorization, and backup behavior for project files stay as they are.
- `src/` must not import backend modules.

Expected validation outcomes:

- Parity between `options.output_expectations` and sidecar declarations for identical content.
- No dispatcher output and no ingester writes on any failed check.
- Reported field paths name the sidecar file.

Open questions and the phase that must resolve them:

- Whether the sidecar appears as a tab in the project YAML editor, and whether it is listed in the project file browser. Resolve in Phase 2.
- The deprecation removal release and its release-note wording. Resolve in Phase 3.

## Open Questions

- Should a shared or cross-project expectation file be supported later? Out of scope here; if it is wanted, the fixed-name rule is the thing to revisit.
- Should the sidecar be listed alongside `shapeshifter.mapping.yml` and `shapeshifter.tasks.yml` in project documentation as a first-class project artifact? Recommend yes, in the same change that ships the loader.

## Final Recommendation

Adopt `shapeshifter.expectations.yml` as the declaration source for output expectations and deprecate `options.output_expectations` over one release. The change is small, follows three existing sidecar precedents, removes the silent-loss failure caused by whole-section `options` writes, and keeps every measurement, gating, and reporting behavior already shipped.
