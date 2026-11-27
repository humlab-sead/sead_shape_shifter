# Bootstrap A Project From A Curated Excel Workbook: Phase Plan

Source: [Bootstrap A Project From A Curated Excel Workbook](BOOTSTRAP_PROJECT_FROM_EXCEL.md). The proposal was a draft for review when this plan was written. If review changes a design rule or a `P-AC-*` criterion, update this plan.

## Summary

The work is delivered in two phases. Phase 1 reads a workbook and reports every blocking error. Phase 2 writes the project from a workbook that passes those checks and adds the command.

The split lets the checks be tested against the current, uncorrected example workbook before any project output exists. The delivery ends with a project that loads and normalizes. It does not make a dataset ready for ingestion.

## Problem

Shape Shifter cannot create a project from a curated workbook with one sheet per table. Setting up the example workbook by hand means about 25 entities and thousands of rows. The workbook also breaks identity and foreign key rules that must be reported before a project can be created from it.

## Scope

In scope:

- workbook reading, the options file and all blocking checks
- project output: `shapeshifter.yml`, Parquet sidecar files, foreign key declarations and the created `submission` and `data_provider` entities
- a command under `scripts/project/`, with the conversion logic in `src/`
- the validation needed to meet `P-AC-1` to `P-AC-12`

Out of scope: the proposal's [Non-Goals](BOOTSTRAP_PROJECT_FROM_EXCEL.md#non-goals) and [Needed Before Ingestion](BOOTSTRAP_PROJECT_FROM_EXCEL.md#needed-before-ingestion) items, including [#829](https://github.com/humlab-sead/sead_shape_shifter/issues/829) and [#830](https://github.com/humlab-sead/sead_shape_shifter/issues/830). Neither issue blocks this plan. Repairing the example workbook is the curator's work.

## Current Position

Verified in the repository:

- No command creates a project from a workbook.
- Core has a `fixed` loader. `@load:` reads Parquet files, and `column_types` accepts `int`, `string`, `float`, `bool` and `date`.
- Code that infers column types for materialized entities is in the backend. Code in `src/` cannot import it.
- The standard target model marks columns as `required` and `generated`. No two of its entities share a `target_table` or a `public_id`, so each sheet naming rule matches at most one entity.
- Projects in the repository reference the standard model as `@load: ${GLOBAL_TARGET_MODEL_DIR}/sead_standard_model.yml`.
- With the three sheet mappings in the proposal, all 25 sheets in the example workbook match a target model entity or table. Sheets outside the model can only be covered by test workbooks.
- The example workbook is under `data/`, which Git ignores. Automated tests cannot depend on it.

External dependency: the curator has to correct the example workbook. `P-AC-12` cannot be closed before that.

## Phase Plan

### Phase 1: Workbook Reading And Checks

**Goal**

Read a workbook and its options file, and return either the content needed to write a project or the complete list of blocking errors.

**Focus**

- sheet matching, entity names and public ID names
- rows, headers, columns, identities and formulas
- foreign key checks against sheets in the workbook
- collecting errors across all sheets in one run

**Depends On**

- The proposal's Sheets, Options File, Rows, Columns And Identities, and Foreign Keys sections.

**Outputs**

- A checked description of each sheet for Phase 2: entity name, public ID name, columns, row values unchanged, and the references between columns and entities.
- A list of all blocking errors. When the list is not empty, Phase 2 writes nothing.
- Test workbooks that Phase 2 can reuse.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`) Each sheet gets its entity name and public ID name from the first matching rule under Sheets. The four blocking errors listed there are reported. A missing public ID name for a sheet outside the target model suggests adding a sheet mapping.
- `PH1-AC-2` (from `P-AC-4`) Every column with a header is read. An empty column without a header is skipped.
- `PH1-AC-3` (from `P-AC-5`) Each of these blocks the run: data after an empty row, data in a column without a header, repeated headers in a sheet, a repeated non-blank public ID in a sheet, a missing, non-positive or repeated `system_id`, a non-integer identity or foreign key value, and a formula without a saved result. No value is assigned or changed.
- `PH1-AC-4` (from `P-AC-6`) Every non-null value in a checked column that references a sheet in the workbook must match a `system_id` in that sheet. Checked columns are direct target model foreign keys and other columns named after another entity's public ID, including references to and from sheets outside the model. No option disables the check.
- `PH1-AC-5` (from `P-AC-7`) One run reports all detectable errors from all sheets. Each unmatched reference reports the sheet, column, referenced sheet, all Excel row numbers without truncation, and whether the value matches a public ID in the referenced sheet. Errors for empty rows, headers and public IDs include the details required by the proposal. Only checks that cannot run because of another error are skipped, as the proposal describes.

**Validation Milestones**

- `VM-1` Unit tests with small workbooks pass for every naming rule and blocking error (`PH1-AC-1` to `PH1-AC-4`).
- `VM-2` A test with errors in several sheets returns all of them in one run (`PH1-AC-5`).
- `VM-3` A run on the uncorrected example workbook, with the three sheet mappings, reports the six foreign key columns and the identity problems in the proposal's Problem section. Row counts match the proposal, or each difference is explained and the proposal is corrected. Any additional error is checked against the workbook (`PH1-AC-3` to `PH1-AC-5`).

**Task-Plan Handoff**

- Source criteria: `P-AC-3` to `P-AC-7`.
- Check headers as written in the sheet. pandas renames repeated headers.
- Data after an empty row is reported, and other checks skip those rows.
- A referenced entity that is not in the workbook is not looked up. An entity that Phase 2 creates counts as not in the workbook.
- ID columns not covered by a foreign key rule are loaded without a check.
- Report only blocking errors. Do not add warnings to the report.
- No command or project output in this phase.
- Blocking questions: none.

**Readiness**

Ready for a task plan.

### Phase 2: Project Output And Command

**Goal**

Create a project that loads and normalizes with unchanged identities, through a command that writes nothing when the run is blocked.

**Focus**

- `fixed` entities, `column_types`, added columns and Parquet sidecar files
- foreign key declarations and the `submission` and `data_provider` entities
- command arguments, error report, exit status and output directory protection
- round-trip validation and user documentation

**Depends On**

- Phase 1's checked sheet description, error list and test workbooks.

**Outputs**

- The command under `scripts/project/`.
- A new project directory with `shapeshifter.yml` and one `materialized/<entity>.parquet` file per entity.
- Documentation of the command, its options file and what remains before ingestion.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`) Each sheet becomes a `fixed` entity with a Parquet sidecar file and empty `keys`. The only other entities are a missing `submission` or `data_provider`. The project references the standard target model.
- `PH2-AC-2` (from `P-AC-4`) The only columns added to a sheet are a missing public ID column and, when every row has a public ID, missing non-generated required columns. Added columns are empty.
- `PH2-AC-3` (from `P-AC-2`) Without circular links, the project loads and normalizes with all `system_id`, public ID and foreign key values unchanged. This includes empty columns, mixed-type columns written as text, and columns where Core skips the link because the child already has the parent's public ID column.
- `PH2-AC-4` (from `P-AC-8`) `foreign_keys` and `foreign_key_value_sources` follow the proposal's Foreign Keys section. No `public_id` value source is declared for `submission`, `data_provider` or `submission_state`.
- `PH2-AC-5` (from `P-AC-10`) A missing `submission` or `data_provider` is created as described under Submission And Data Provider, with no rows or invented values.
- `PH2-AC-6` (from `P-AC-11`) The command requires `--data-provider-code` and `--provider-schema` and writes both values to the project metadata without checking them as a pair.
- `PH2-AC-7` (from `P-AC-9`) A blocked run reports only the blocking errors in a form that can be saved, exits with a non-zero status and writes no project files. The command never writes into a non-empty directory.
- `PH2-AC-8` (from `P-AC-12`) The corrected example workbook produces a project that satisfies `PH2-AC-3`.

**Validation Milestones**

- `VM-4` Round-trip tests bootstrap, load, normalize and compare values. They cover empty and mixed-type columns, sheets outside the model, skipped links, and a workbook exported by the `xlsx` dispatcher (`PH2-AC-1` to `PH2-AC-3`).
- `VM-5` Tests confirm the declarations, the created entities and the metadata values (`PH2-AC-4` to `PH2-AC-6`).
- `VM-6` Tests run the command on a blocked workbook and against a non-empty directory. Both leave the file system unchanged apart from a saved error report, and the exit status is non-zero (`PH2-AC-7`).
- `VM-7` A run on the corrected example workbook loads, normalizes and preserves identity and foreign key values. Remaining validation errors are recorded (`PH2-AC-8`).

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-2`, `P-AC-4` and `P-AC-8` to `P-AC-12`.
- Keep conversion logic in `src/`, with no imports from `backend`.
- Confirm early that values survive the path from Parquet through `@load:`, the `fixed` loader and type coercion. Check in particular nulls in integer columns and non-integer values in columns whose names end in `_id` but are not identity or foreign key columns.
- Required columns are not added to a sheet with any new row, so that conformance validation reports missing and misnamed columns.
- Validation errors in a created project are expected. A change request is not part of validation.
- A project with circular links is outside `PH2-AC-3`. Do not remove or defer links to avoid a cycle.
- `VM-7` needs the corrected workbook. Implementation and `VM-4` to `VM-6` can proceed without it. The phase stays open until `VM-7` passes.
- Blocking questions: none.

**Readiness**

Ready for a task plan after Phase 1 is complete.

## Cross-Phase Rules

- Never assign, infer or rewrite a `system_id`, public ID or foreign key value, and do not repair workbooks.
- The options file maps sheet names and supplies public ID names for sheets outside the model. It cannot exclude sheets or disable checks.
- A workbook rule that fails a real workbook is changed in the proposal first, not relaxed in code.
- Do not change the target model, existing-row validation or the change request ingester as part of this work.
- Keep curated workbooks out of Git. Build test workbooks from small made-up data.

## Validation Strategy

| Level | Phase | Milestones | Expected result |
|---|---|---|---|
| Unit tests per rule | 1 | `VM-1`, `VM-2` | Each rule passes valid input and reports invalid input, in one complete list |
| Uncorrected example run | 1 | `VM-3` | Reported errors agree with the proposal and the workbook |
| Round-trip and output tests | 2 | `VM-4`, `VM-5` | Values are unchanged and declarations match the design |
| Command tests | 2 | `VM-6` | Blocked runs create no project files |
| Corrected example run | 2 | `VM-7` | The project loads and normalizes; remaining validation errors are recorded |

`VM-3` and `VM-7` are run by hand, because the workbook is not in Git. Record their results in the phase task plans. Exact commands, test files and assertions belong there too.

## Final Recommendation

Start the task plan for Phase 1. Send the `VM-3` error report to the curator when it is available, so the workbook can be corrected while Phase 2 is implemented.
