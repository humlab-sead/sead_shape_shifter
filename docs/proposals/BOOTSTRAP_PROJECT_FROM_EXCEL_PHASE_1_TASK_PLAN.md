# Bootstrap A Project From A Curated Excel Workbook: Phase 1 Task Plan

## Phase Summary

**Phase:** 1, Workbook Reading And Checks.

**Goal:** Read a workbook and its options file, and return either the content needed to write a project or the complete list of blocking errors.

**Readiness:** Validated. Cases where the proposal is silent are settled under [Decisions Where The Proposal Is Silent](#decisions-where-the-proposal-is-silent).

**Sources:** [proposal](BOOTSTRAP_PROJECT_FROM_EXCEL.md) (`P-AC-3` to `P-AC-7`) and [phase plan](BOOTSTRAP_PROJECT_FROM_EXCEL_PHASE_PLAN.md) (`PH1-AC-1` to `PH1-AC-5`, `VM-1` to `VM-3`). The proposal was a draft for review when this plan was written.

**Constraints:**

- No command, project output or user documentation. These belong to Phase 2.
- Never assign, change or infer a `system_id`, public ID or foreign key value. Do not write to the workbook.
- No option disables a check. The error list contains only blocking errors.
- Code in `src/` does not import `backend`.
- Tests use small made-up workbooks. Do not add curated workbooks to Git.
- If the repository or the workbook disagrees with this plan, stop and report what differs. Do not redesign or widen the scope.

**Acceptance criteria** (full wording in the phase plan):

- [ ] `PH1-AC-1` (`P-AC-3`) Entity names, public ID names and the four naming errors follow the proposal's Sheets rules.
- [ ] `PH1-AC-2` (`P-AC-4`) Every column with a header is read. An empty column without a header is skipped.
- [ ] `PH1-AC-3` (`P-AC-5`) Invalid rows, headers, identities, foreign key values and unsaved formulas block the run. No value is assigned or changed.
- [ ] `PH1-AC-4` (`P-AC-6`) Every non-null reference to a sheet in the workbook matches a `system_id` there, with no override.
- [ ] `PH1-AC-5` (`P-AC-7`) One run reports all detectable errors with the required details.

## Repository Findings

**Repository basis:** branch `bootstrap-project-from-excel`, commit `e2833142`, 2026-11-26. The working tree also held uncommitted changes to `src/model.py`, `src/extract.py`, two Core test files and two documents (inherited `extra_columns` on append branches), and the untracked phase plan. Phase 1 does not touch those files.

| Source | Finding | Planning implication |
|---|---|---|
| `src/` | No code creates a project from a workbook. `src/excel_bootstrap/` and `tests/excel_bootstrap/` do not exist. | Phase 1 adds new files and changes no existing code. |
| `src/target_model/models.py::TargetModel` | `EntitySpec` has `target_table`, `public_id` and `foreign_keys`. `ForeignKeySpec` has `entity` and `via`, and no column name. | The column of a direct foreign key is the referenced entity's `public_id`. |
| `tests/target_model/test_spec_files.py` | The standard model loads with `TargetModel.model_validate(yaml.safe_load(...))`. | The checker receives a `TargetModel` instance and does not load model files. |
| `resources/target_models/sead_standard_model.yml` | Every entity has a `public_id`. Table names and public ID names are unique. `value_class` and `dataset` reference themselves. `site` has two `via` foreign keys. | Naming lookups are unambiguous. A self-reference would use the entity's own public ID column, so it is not a reference column. |
| `src/issues.py::CoreIssue` | Core issue type with `severity`, `message`, `entity`, `column`, `code` and `metadata`. | Use it for blocking errors. |
| `src/types/fixed_entity_types.py::is_missing_fixed_entity_value` | `None` and whitespace-only text count as missing. Core never treats booleans as integers. | Use the same function for blank cells, and reject booleans in ID columns. |
| `openpyxl`, tried during planning | A formula written by `openpyxl` has `data_type == "f"` in a normal load and no value in a `data_only=True` load. The sheet XML holds `<f>1+1</f><v />`. | Load each workbook both ways. A test of a saved formula result has to add the result to the sheet XML. |
| Example workbook | 25 sheets, no formulas, one merged range in `tbl_value_classes`. Populated `_id` cells hold integers. Some columns without a header are empty. `tbl_physical_samples` has empty-text cells. | Treat empty text as blank. Do not fail on empty columns without a header. |
| Read-only prototype of the reference rules on the example | The six foreign key columns and row counts match the proposal. No other reference is unmatched. | `VM-3` has a known expected result (`V-5`). The prototype is not a deliverable. |
| Same prototype, identity values | `tbl_value_types` has `system_id` 0 to 10 above the empty rows and 0 to 10 again below them. `tbl_value_classes` lacks `system_id` on 23 of 24 rows. `tbl_value_qualifiers` has no `system_id` column. | The repeats in `tbl_value_types` are not reported, because rows after the gap are skipped. This explains the difference from the proposal's Problem section. A missing `system_id` column is reported like blank values. |
| Example workbook headers | Some headers are not usable names, for example `value type`, and a tuple-like text header in `tbl_value_classes` and `tbl_value_qualifiers`. | Phase 1 reads them as written. Phase 2 has to confirm that a project accepts them. |

## Scope

**In scope:** a new package `src/excel_bootstrap/` with the options file, workbook reading, naming rules, blocking checks and the checked result, and its tests in `tests/excel_bootstrap/`.

**Out of scope:** the command under `scripts/project/`, `column_types`, added columns, Parquet files, `shapeshifter.yml`, foreign key declarations, created `submission` and `data_provider` entities, workbook repairs, and target model or ingester changes.

**Affected contracts:** none that exist today. Phase 2 will use `check_workbook` and `CheckResult`.

### Interface

```python
check_workbook(workbook_path: Path, target_model: TargetModel, options_path: Path | None = None) -> CheckResult
```

- `CheckResult.errors`: list of `CoreIssue` with `severity="error"`. `CheckResult.is_blocked` is true when the list is not empty.
- `CheckResult.sheets`: one `CheckedSheet` per sheet, in workbook order. It is empty when the run is blocked.
- `CheckedSheet`: `sheet_name`, `entity_name`, `public_id`, `in_target_model`, `columns` (headers as written, in sheet order), `rows` (saved cell values, unchanged), `row_numbers` (Excel row numbers) and `references`. `columns` does not include columns that Phase 2 adds.
- `ColumnReference`: `column`, `referenced_entity`, `in_workbook` and `kind` (`direct_foreign_key` or `public_id_name`).
- Each issue sets `code`, `entity` when known, `column` when one applies, and a `message` that can be read on its own. `metadata` holds the details: `sheet`, `rows`, `column_letters`, `value`, `referenced_sheet` and `matches_public_id`, as they apply. Row lists are never truncated, in `metadata` or in `message`.

### Reference Rules

For each column of a sheet except `system_id` and the sheet's own public ID column, use the first match:

1. The sheet's entity is in the target model, and the column is the `public_id` of a direct foreign key target (no `via`) other than itself: reference that entity, `direct_foreign_key`.
2. The column is another entity's public ID name: reference that entity, `public_id_name`. A sheet in the workbook that uses the name is chosen before a target model entity that is not in the workbook.
3. Otherwise the column is not checked.

Every referenced column must hold integers or blanks. When the referenced entity is a sheet in the workbook, every non-blank value must also equal a `system_id` in that sheet.

### Error Codes

| Code | Reported as |
|---|---|
| `WORKBOOK_UNREADABLE`, `OPTIONS_INVALID` | One issue; the run returns only this issue. When both files fail, both are returned. |
| `OPTIONS_UNKNOWN_SHEET`, `OPTIONS_UNUSED_PUBLIC_ID` | One per options entry |
| `MAPPED_TABLE_UNKNOWN`, `PUBLIC_ID_NAME_MISSING`, `PUBLIC_ID_NAME_INVALID` | One per sheet |
| `DUPLICATE_ENTITY_NAME`, `DUPLICATE_PUBLIC_ID_NAME` | One per repeated name, listing the sheets |
| `HEADER_ROW_MISSING` | One per sheet |
| `DATA_AFTER_EMPTY_ROW` | One per sheet, with all rows that hold data after the first empty row |
| `DATA_WITHOUT_HEADER` | One per column, with the column letter and rows |
| `DUPLICATE_HEADER` | One per sheet and header, with all column letters |
| `FORMULA_WITHOUT_VALUE` | One per sheet and column, with the rows |
| `SYSTEM_ID_MISSING`, `SYSTEM_ID_INVALID` | One per sheet, with the rows; `INVALID` covers non-integer and non-positive values |
| `SYSTEM_ID_DUPLICATE`, `PUBLIC_ID_DUPLICATE` | One per sheet and value, with all rows |
| `ID_VALUE_NOT_INTEGER` | One per sheet and column (public ID or reference), with the rows |
| `REFERENCE_UNMATCHED` | One per sheet, column and value, with the referenced sheet, all rows and `matches_public_id` |

### Decisions Where The Proposal Is Silent

These apply to this phase. Raise a disagreement before implementation starts.

| Case | Decision |
|---|---|
| Blank cell | `None` or whitespace-only text, as in `is_missing_fixed_entity_value`. A row is empty when all its cells are blank. A cell with a formula is never blank. |
| Integer value | An integer, or a decimal number with no fraction. Text such as `"5"`, booleans and dates are not integers. |
| Positive value | Required for `system_id` only. |
| Options file shape | Only `sheets` and `public_ids`, each a map of text to text. Unreadable YAML, an unknown key or a wrong type gives `OPTIONS_INVALID`. An empty file or no file means no mappings. |
| Options entry for a sheet not in the workbook | Blocks (`OPTIONS_UNKNOWN_SHEET`), so a misspelled sheet name is not ignored. |
| `public_ids` entry for a sheet that matches the target model | Blocks (`OPTIONS_UNUSED_PUBLIC_ID`). The model's name applies. |
| `system_id` given as a public ID name | `PUBLIC_ID_NAME_INVALID`. |
| Header row | Row 1. If it is blank, including in an empty sheet, report `HEADER_ROW_MISSING` and skip the sheet's value checks. |
| Header text | Compared exactly, without trimming or case changes. A non-text header is read as its text form. A whitespace-only header counts as no header. |
| Sheet with a header and no rows | Allowed. No `system_id` error. |
| Hidden sheets and merged cells | Hidden sheets are loaded. A merged range keeps its value in the first cell only, as `openpyxl` reads it. |
| Invalid value in a reference column | Report `ID_VALUE_NOT_INTEGER` only, not also `REFERENCE_UNMATCHED`. |

**Skipped checks.** Only these checks are skipped:

- Rows after the first empty row: all value checks. Their data is reported by `DATA_AFTER_EMPTY_ROW`. Their `system_id` values do not satisfy references.
- A sheet with `MAPPED_TABLE_UNKNOWN`: checks that need its entity name or public ID name. Do not also report `PUBLIC_ID_NAME_MISSING`.
- A sheet with `PUBLIC_ID_NAME_MISSING`: public ID value checks, and references that would be found through the missing name. References to its entity name from direct foreign keys are still checked.
- A repeated entity name or public ID name: references that could mean either sheet.
- A repeated header: value checks on that column name, and references that need it from the referenced sheet.
- A cell reported by `FORMULA_WITHOUT_VALUE`: other value checks on that cell. If it is in a referenced sheet's `system_id` column, references to that sheet are still checked.

A referenced sheet with no `system_id` column or only blank values is not skipped. All references to it are unmatched.

## Work Breakdown

### Area 1: Add Result Types, Options And Workbook Reading

**Objective:** The package reads the options file and every sheet without changing values, and tests can build workbooks for each case.

**Affected code:** `src/excel_bootstrap/__init__.py` `NEW`, `models.py` `NEW`, `options.py` `NEW`, `reader.py` `NEW`; `tests/excel_bootstrap/__init__.py` `NEW`, `workbook_builder.py` `NEW`, `test_options.py` `NEW`, `test_reader.py` `NEW`.

**Dependencies:** None.

**Tasks:**

* [ ] `T1.1` **Change:** Define the result types.
  * **Target:** `src/excel_bootstrap/models.py` `NEW`.
  * **Current → required:** No types exist → `CheckResult`, `CheckedSheet` and `ColumnReference` as listed under Interface.
  * **Implementation:** Use dataclasses with type hints. Use `CoreIssue` for errors; do not add a second issue type.
  * **Validation:** `V-4` asserts the fields of a successful result and the empty `sheets` of a blocked one.
* [ ] `T1.2` **Change:** Load and validate the options file.
  * **Target:** `src/excel_bootstrap/options.py` `NEW`.
  * **Current → required:** No options loader exists → A Pydantic model with `sheets` and `public_ids`, both empty by default, with `extra="forbid"`; a loader that returns the options or an `OPTIONS_INVALID` issue.
  * **Implementation:** Read the file with `yaml.safe_load`. Do not resolve directives or environment variables. Entry checks that need sheet names belong to `T2.1`.
  * **Validation:** `V-1`: no file, empty file, valid file, bad YAML, a top level that is not a map, an unknown key such as `skip`, a non-text value, a missing file path.
* [ ] `T1.3` **Change:** Read the sheets from the workbook.
  * **Target:** `src/excel_bootstrap/reader.py` `NEW`.
  * **Current → required:** No reader exists → For each worksheet, return its name, header cells with Excel column letters, rows with Excel row numbers and saved values, and the positions of formulas without a saved result.
  * **Implementation:** Use `openpyxl`, not pandas, because pandas renames repeated headers. Load once with `data_only=False` to find formulas, including array formulas, and once with `data_only=True` for saved values. Do not use `read_only=True`. Trailing empty rows and empty columns without a header produce no rows or columns. Return `WORKBOOK_UNREADABLE` for a missing or invalid file. Never save the workbook.
  * **Constraints:** Keep values and their types as `openpyxl` returns them.
  * **Validation:** `V-1`: header order and letters; integers, decimals, text, dates and booleans unchanged; repeated headers kept as written; styled trailing rows and columns ignored; hidden sheet read; formula with and without a saved result; a row whose only content is an unsaved formula is not empty; unreadable file; file bytes unchanged after reading.
* [ ] `T1.4` **Change:** Add a helper that builds test workbooks.
  * **Target:** `tests/excel_bootstrap/workbook_builder.py` `NEW`.
  * **Current → required:** No helper exists → A function writes a workbook into `tmp_path` from a map of sheet names to rows. A second function adds a saved result to a formula cell by rewriting the sheet XML. Phase 2 tests can import both.
  * **Implementation:** Use `openpyxl` to write. Keep a small inline target model, as a dict passed to `TargetModel.model_validate`, in this module. Include a direct foreign key, a `via` foreign key, a self-reference and an entity left out of the test workbooks.
  * **Validation:** `V-1` uses both functions.

**Completion evidence:** `V-1` passes.

### Area 2: Resolve Entity Names And Public ID Names

**Objective:** Every sheet gets the names set by the proposal's Sheets rules, or a blocking error.

**Affected code:** `src/excel_bootstrap/naming.py` `NEW`; `tests/excel_bootstrap/test_naming.py` `NEW`.

**Dependencies:** `T1.1`, `T1.2`, `T1.4`.

**Tasks:**

* [ ] `T2.1` **Change:** Apply the naming rules and report naming and options entry errors.
  * **Target:** `src/excel_bootstrap/naming.py` `NEW`.
  * **Current → required:** No naming rules exist → For each sheet, apply in order: options mapping to a `target_table`; sheet name equals a model entity name; sheet name equals a `target_table`; outside the model.
  * **Implementation:** Return resolved names and all issues; do not stop at the first. The `PUBLIC_ID_NAME_MISSING` message suggests adding a `sheets` mapping if the name is an altered SEAD table name. Check the `_id` suffix. Find repeated entity names and public ID names across all sheets, including an options-supplied name that repeats a model name used by another sheet. Do not guess a public ID name. Report `OPTIONS_UNKNOWN_SHEET` and `OPTIONS_UNUSED_PUBLIC_ID`.
  * **Validation:** `V-2`: each of the four rules and their order; mapping to an unknown table; missing, badly suffixed and `system_id` public ID names; both kinds of repeat; both options entry errors; several naming errors in one result. One test loads the standard model and asserts that the proposal's three mapped sheets resolve to entities with those `target_table` values.

**Completion evidence:** `V-2` passes.

### Area 3: Check Rows, Headers And Identity Values

**Objective:** Each sheet's structure and identity values are checked, and all errors are collected.

**Affected code:** `src/excel_bootstrap/checks.py` `NEW`; `tests/excel_bootstrap/test_sheet_checks.py` `NEW`.

**Dependencies:** `T1.3`, `T2.1`.

**Tasks:**

* [ ] `T3.1` **Change:** Check the layout of each sheet.
  * **Target:** `src/excel_bootstrap/checks.py` `NEW`.
  * **Current → required:** No layout checks exist → Report `HEADER_ROW_MISSING`, `DATA_AFTER_EMPTY_ROW`, `DATA_WITHOUT_HEADER`, `DUPLICATE_HEADER` and `FORMULA_WITHOUT_VALUE`; pass only the first data block and named columns to value checks.
  * **Implementation:** A repeated header is reported even when one of its columns is empty. A column without a header is skipped only when all its cells are blank, including cells after the gap.
  * **Validation:** `V-3`: each code, with row numbers and column letters; one and several empty rows before extra data; trailing empty rows without extra data; empty and non-empty columns without a header; a repeated header with one empty column; header-only sheet; blank row 1.
* [ ] `T3.2` **Change:** Check `system_id` and public ID values.
  * **Target:** `src/excel_bootstrap/checks.py` `NEW`.
  * **Current → required:** No identity checks exist → Report `SYSTEM_ID_MISSING`, `SYSTEM_ID_INVALID`, `SYSTEM_ID_DUPLICATE`, `PUBLIC_ID_DUPLICATE` and non-integer public ID values.
  * **Implementation:** Put the blank and integer tests in one function each and reuse them in `T4.1`. A missing `system_id` column in a sheet with rows gives `SYSTEM_ID_MISSING` with all rows. A missing public ID column is not an error.
  * **Constraints:** Compare converted integers, and leave the stored cell value unchanged.
  * **Validation:** `V-3`: missing column, blank and empty-text values, 0, negative, text, boolean, date, 1.5 and 2.0; repeated values with all rows, including 2 and 2.0; repeated public IDs; repeated blanks in the public ID column are allowed; no value in the sheet data is changed.

**Completion evidence:** `V-3` passes.

### Area 4: Check References And Return The Result

**Objective:** `check_workbook` returns the checked sheets or the complete error list.

**Affected code:** `src/excel_bootstrap/checks.py` `NEW`, `checker.py` `NEW`, `__init__.py` `NEW`; `tests/excel_bootstrap/test_reference_checks.py` `NEW`, `test_check_workbook.py` `NEW`.

**Dependencies:** `T2.1`, `T3.1`, `T3.2`.

**Tasks:**

* [ ] `T4.1` **Change:** Find reference columns and check their values.
  * **Target:** `src/excel_bootstrap/checks.py` `NEW`.
  * **Current → required:** No reference checks exist → Apply the Reference Rules; report `ID_VALUE_NOT_INTEGER` and `REFERENCE_UNMATCHED`; return `ColumnReference` entries.
  * **Implementation:** Collect the valid `system_id` and public ID values of all sheets before checking any reference, so sheet order does not matter. Set `matches_public_id` when the unmatched value is a public ID in the referenced sheet; it is false when that sheet has no public ID column. The message gives the sheet, column, referenced sheet, value, all Excel rows and the public ID result. Do not look up entities that are not in the workbook, including `submission` and `data_provider`.
  * **Validation:** `V-3`: direct foreign key, matched and unmatched; column named after another entity's public ID, to and from a sheet outside the model; `via` target column in a sheet; self-reference through the own public ID column and an unlisted column such as `parent_id` are not checked; value that matches only a public ID; null values; referenced entity not in the workbook, with an integer and a text value; referenced sheet without `system_id` values; referenced sheet listed after the referencing sheet; more than 100 unmatched rows, all listed.
* [ ] `T4.2` **Change:** Add `check_workbook` and apply the skip rules.
  * **Target:** `src/excel_bootstrap/checker.py` `NEW`; export it and the result types from `src/excel_bootstrap/__init__.py` `NEW`.
  * **Current → required:** No entry point exists → Run options loading, reading, naming, layout, identity and reference checks, and collect all issues.
  * **Implementation:** Return early only for `WORKBOOK_UNREADABLE` and `OPTIONS_INVALID`. Apply only the checks listed under Skipped checks. Order issues by workbook sheet order, with options issues first, so two runs give the same list. Return `sheets` only when there are no errors. Do not write files.
  * **Validation:** `V-4`: one workbook with naming, layout, identity and reference errors in several sheets returns all of them; each skip rule has a case showing the dependent check is skipped and an unrelated error on the same sheet is still reported; a valid workbook returns every sheet with unchanged values and expected references; two runs return the same list; `tmp_path` contains no new files.

**Completion evidence:** `V-3` and `V-4` pass.

### Area 5: Validate Against The Example Workbook

**Objective:** The result on the uncorrected example agrees with the proposal and the workbook.

**Affected code:** this task plan.

**Dependencies:** Area 4.

**Tasks:**

* [ ] `T5.1` **Change:** Run `V-5`, compare the result and record it.
  * **Target:** the `V-5` result under [Validation And Testing](#validation-and-testing).
  * **Current → required:** Only the planning prototype has checked the workbook → the implemented checker's result is recorded.
  * **Implementation:** Compare each issue with the `V-5` expected result. Check any other issue, or any different count, against the workbook cells. If the checker is wrong, fix it and add a test. If the proposal is wrong, stop and report it; the proposal is changed before the code relaxes a rule. Save the full error report outside Git for the curator.
  * **Validation:** `V-5`.
* [ ] `T5.2` **Change:** Run the final checks and update progress.
  * **Target:** this task plan.
  * **Current → required:** Open → checklists, baselines and the progress tracker show the results.
  * **Implementation:** Run `V-6` to `V-8`.
  * **Validation:** `V-6`, `V-7`, `V-8`.

**Completion evidence:** `V-5` to `V-8` have recorded results.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` | `T1.2`, `T2.1` | `V-1`, `V-2` | Names follow the four rules, and each naming error is reported |
| `PH1-AC-2` | `T1.3`, `T3.1`, `T4.2` | `V-1`, `V-3`, `V-4` | All named columns appear in the result; empty unnamed columns do not |
| `PH1-AC-3` | `T1.3`, `T3.1`, `T3.2`, `T4.1` | `V-1`, `V-3`, `V-5` | Each invalid case is reported; stored values are unchanged |
| `PH1-AC-4` | `T4.1` | `V-3`, `V-5` | Unmatched references block the run; no option disables the check |
| `PH1-AC-5` | `T4.1`, `T4.2`, `T5.1` | `V-3`, `V-4`, `V-5` | One run lists all errors with complete details |

Phase plan milestones: `VM-1` is `V-1` to `V-3`, `VM-2` is `V-4`, and `VM-3` is `V-5`.

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Options and reading | `uv run pytest tests/excel_bootstrap/test_options.py tests/excel_bootstrap/test_reader.py` | AC 1, 2, 3 | Tests pass | Not run: tests do not exist |
| `V-2` | Naming | `uv run pytest tests/excel_bootstrap/test_naming.py` | AC 1 | Tests pass | Not run: tests do not exist |
| `V-3` | Sheet and reference checks | `uv run pytest tests/excel_bootstrap/test_sheet_checks.py tests/excel_bootstrap/test_reference_checks.py` | AC 2 to 5 | Tests pass | Not run: tests do not exist |
| `V-4` | Complete run | `uv run pytest tests/excel_bootstrap/test_check_workbook.py` | AC 2, 5 | Tests pass | Not run: tests do not exist |
| `V-5` | Uncorrected example | Manual method below | AC 3, 4, 5 | Expected result below | Not run: checker does not exist |
| `V-6` | Core regression | `uv run pytest tests` | Existing behavior | No failures | Pass, with the uncommitted changes |
| `V-7` | Style and layers | `uv run ruff check src/excel_bootstrap tests/excel_bootstrap && uv run black --check src/excel_bootstrap tests/excel_bootstrap && uv run isort --check-only src/excel_bootstrap tests/excel_bootstrap && uv run pylint src/excel_bootstrap tests/excel_bootstrap && make check-layer-imports` | Conventions | No findings | Layer check passes; other checks not run: files do not exist |
| `V-8` | Document links | `make check-doc-links` | This task plan | No broken links | Pass before this file was added |

### V-5 Manual Method

Run from the repository root. The workbook `data/living_trees_gothenburg_stockholm_20241219.xlsx` is not in Git. If it is missing or has been corrected, stop and ask for the uncorrected file.

```bash
options_file=$(mktemp --suffix=.yml)
cat > "$options_file" <<'YAML'
sheets:
  tbl_s_g_descriptions: tbl_sample_group_descriptions
  tbl_sample_description: tbl_sample_descriptions
  tbl_genera: tbl_taxa_tree_genera
YAML
uv run python - "$options_file" <<'PY'
import sys
from pathlib import Path

import yaml

from src.excel_bootstrap import check_workbook
from src.target_model.models import TargetModel

model = TargetModel.model_validate(yaml.safe_load(Path("resources/target_models/sead_standard_model.yml").read_text(encoding="utf-8")))
result = check_workbook(Path("data/living_trees_gothenburg_stockholm_20241219.xlsx"), model, Path(sys.argv[1]))
for issue in result.errors:
    rows = issue.metadata.get("rows", [])
    print(issue.code, issue.metadata.get("sheet"), issue.column, issue.metadata.get("value"), len(rows), issue.metadata.get("matches_public_id"))
print("blocked:", result.is_blocked, "issues:", len(result.errors))
PY
```

**Expected result:** the run is blocked, with these results and no others. Row counts for a reference column are the sum over its unmatched values.

| Code | Sheet and column | Rows | Detail |
|---|---|---:|---|
| `REFERENCE_UNMATCHED` | `tbl_site_locations.location_id` | 96 | No value matches a public ID |
| `REFERENCE_UNMATCHED` | `tbl_abundances.taxon_id` | 1009 | Values 974, 2614, 3590, 18083; no public ID match |
| `REFERENCE_UNMATCHED` | `tbl_dataset_submissions.contact_id` | 38 | Value 67; no public ID match |
| `REFERENCE_UNMATCHED` | `tbl_value_classes.value_type_id` | 1 | Value 11; no public ID match |
| `REFERENCE_UNMATCHED` | `tbl_taxa_tree_master.genus_id` | 1 | Value 764; no public ID match |
| `REFERENCE_UNMATCHED` | `tbl_analysis_values.value_class_id` | 3878 | Every value matches a public ID |
| `DATA_AFTER_EMPTY_ROW` | `tbl_value_types` | 11 | Excel rows 16 to 26 |
| `SYSTEM_ID_INVALID` | `tbl_value_types` | 1 | The value 0 above the empty rows |
| `SYSTEM_ID_MISSING` | `tbl_value_classes` | 23 | |
| `SYSTEM_ID_MISSING` | `tbl_value_qualifiers` | 11 | The sheet has no `system_id` column |

No `SYSTEM_ID_DUPLICATE` is expected for `tbl_value_types`. The repeated values are in rows that the checks skip, so a later run can still report errors there after the empty rows are removed.

**Result:** not run yet. `T5.1` records it here.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Result types | `src/excel_bootstrap/models.py` `NEW` | `T1.1` | Used by `check_workbook` |
| Options loader | `src/excel_bootstrap/options.py` `NEW` | `T1.2` | `V-1` |
| Workbook reader | `src/excel_bootstrap/reader.py` `NEW` | `T1.3` | `V-1` |
| Naming rules | `src/excel_bootstrap/naming.py` `NEW` | `T2.1` | `V-2` |
| Blocking checks | `src/excel_bootstrap/checks.py` `NEW` | `T3.1`, `T3.2`, `T4.1` | `V-3` |
| Entry point | `src/excel_bootstrap/checker.py`, `__init__.py` `NEW` | `T4.2` | `V-4` |
| Test workbook helper | `tests/excel_bootstrap/workbook_builder.py` `NEW` | `T1.4` | Used by the Phase 1 tests |
| Tests | `tests/excel_bootstrap/__init__.py` and `test_*.py` files named in Areas 1 to 4 `NEW` | `T1.2` to `T4.2` | `V-1` to `V-4` |
| Example result | This task plan, `V-5` result | `T5.1` | Recorded comparison |
| Curator error report | A file outside Git | `T5.1` | Full report from the `V-5` run |

The curator report holds the full `message` of every issue from the `V-5` run.

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| 1. Result types, options and reading | Not started | None | |
| 2. Naming | Not started | Area 1 | |
| 3. Sheet and identity checks | Not started | Areas 1, 2 | |
| 4. References and result | Not started | Areas 2, 3 | |
| 5. Example validation | Not started | Area 4 | |

## Definition Of Done

- [ ] `PH1-AC-1` to `PH1-AC-5` have implementation and validation results.
- [ ] All tasks and deliverables are complete.
- [ ] `V-1` to `V-8` pass, and the `V-5` comparison is recorded.
- [ ] No existing code, target model or ingester behavior changed.
- [ ] No curated workbook or error report is in Git.
- [ ] Any difference from this plan or the proposal is recorded.
- [ ] The tracker and checklists in this plan are up to date.

## Risks And Open Questions

No open question blocks implementation.

- **Draft proposal.** A review change to a design rule or `P-AC-*` criterion means updating the phase plan and this plan first.
- **Local workbook.** `V-5` depends on a file outside Git. A changed file changes the expected counts.
- **Hidden errors.** The uncorrected example can show more errors after the curator's fixes, because rows after the empty rows in `tbl_value_types` are skipped.
- **Headers in Phase 2.** Phase 1 accepts any header text. Phase 2 has to confirm that headers such as those in the example work as project column names.
