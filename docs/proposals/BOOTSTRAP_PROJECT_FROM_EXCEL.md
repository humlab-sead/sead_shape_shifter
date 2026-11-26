# Bootstrap A Project From A Curated Excel Workbook

## Status

- Proposed feature, draft for review
- Scope: a command-line tool that creates a project from a workbook with one sheet per table
- Goal: turn a curated, reconciled dataset into a project with fixed entities, without changing its identities

## Summary

Add a command that turns each sheet of a curated workbook into a `fixed` entity with a Parquet sidecar file. Entity names and foreign keys come from the standard target model, where it covers them. The command keeps all identities and creates no project if the workbook breaks a rule.

## Problem

Several curated datasets are waiting to be processed. Each is a workbook laid out like a Shape Shifter export: one sheet per table. They are already reconciled: a filled public ID names an existing SEAD row. Shape Shifter cannot create a project from them. The example, `data/living_trees_gothenburg_stockholm_20241219.xlsx`, would need about 25 entities and thousands of rows set up by hand.

It also cannot be converted as it stands. Other pending workbooks have not been inspected.

- **Altered sheet names.** Most sheets are named after a SEAD table. Three need a mapping, shown under Options File.
- **Rows and identities.** `tbl_value_types` has 11 extra rows after three empty rows, repeats `system_id` values and uses 0. Some rows in `tbl_value_classes`, and all rows in `tbl_value_qualifiers`, have no `system_id`.
- **Foreign keys.** Five columns break the foreign key rule:

| Column                               | Values that match no `system_id` in the referenced sheet                 |
|--------------------------------------|--------------------------------------------------------------------------|
| `tbl_site_locations.location_id`     | 96 of 148 rows                                                           |
| `tbl_abundances.taxon_id`            | 1009 of 1384 rows (taxa 974, 2614, 3590 and 18083)                       |
| `tbl_dataset_submissions.contact_id` | 38 of 114 rows (contact 67)                                              |
| `tbl_value_classes.value_type_id`    | 1 of 24 rows (value type 11)                                             |
| `tbl_analysis_values.value_class_id` | All 3878 rows; they match the public ID of rows that have no `system_id` |

The curator must fix these. Where a value is a SEAD ID, the fix is a row in the referenced sheet with that `system_id` and public ID.

## Scope

Creating a new project from one workbook, including the workbook checks.

## Non-Goals

- Updating an existing project, or adding an API or web interface.
- Reconciliation, SEAD database lookups, or repairing workbooks.
- Adding target model entities. Apart from `submission` and `data_provider`, the command creates no entity for a table missing from the workbook.
- Changing how required values are validated on existing SEAD rows. A row that only maps a `system_id` to a public ID may lack them. This needs a separate change.
- Changing change request ingester behaviour. Skipping unlisted columns is tracked in [#829](https://github.com/humlab-sead/sead_shape_shifter/issues/829).
- Deciding how a project's `data_provider` entity is used in change requests, including the rows it needs and how the ingester receives it. This is deferred to [#830](https://github.com/humlab-sead/sead_shape_shifter/issues/830).

## Proposed Design

### Command

Add a script under `scripts/project/`, with the conversion logic in `src/`. It takes the workbook, a new output directory, the project name and an optional YAML options file. The required options `--data-provider-code` and `--provider-schema` set `metadata.data_provider_code` and `metadata.provider_schema` in the new project. It writes `shapeshifter.yml`, which references the standard target model, and one `materialized/<entity>.parquet` file per entity. It never writes into a non-empty directory. It does not check that the two values are a registered pair. Project validation reports an unregistered pair.

The command runs every possible check before writing. If any fails, it prints all blocking errors, exits with a non-zero status and writes no project files. The error report can be saved and contains only those errors.

### Sheets

Every sheet is loaded. The first matching rule applies:

| Sheet                                   | Entity name                         | Public ID name        |
|-----------------------------------------|-------------------------------------|-----------------------|
| Mapped to a table name in the options   | The entity with that `target_table` | From the target model |
| Named after a target model entity       | The sheet name                      | From the target model |
| Named after a target model table        | The entity with that `target_table` | From the target model |
| Anything else: outside the target model | The sheet name                      | From the options file |

These errors block the run:

- A sheet outside the target model has no public ID name. The command does not guess it. The error suggests mapping the sheet, which helps catch altered names. Checks that depend on the name are skipped, so adding it may reveal more errors.
- A mapped table name is not in the target model.
- A public ID name does not end with `_id`.
- Two sheets have the same entity name or public ID name.

### Options File

```yaml
sheets:                       # sheet name: SEAD table name
  tbl_s_g_descriptions: tbl_sample_group_descriptions
  tbl_sample_description: tbl_sample_descriptions
  tbl_genera: tbl_taxa_tree_genera
public_ids:                   # only for sheets outside the target model
  tbl_local_notes: local_note_id  # hypothetical sheet
```

The options file cannot exclude sheets or disable checks.

### Submission And Data Provider

If the workbook has no sheet for `submission` or `data_provider`, the command creates that entity from the target model. It is a `fixed` entity with the model's `public_id`, `system_id`, its non-generated columns and direct foreign key columns, and no rows. The command invents no values.

The command declares foreign keys for a created entity under the rules in Foreign Keys. For the foreign key check, a created entity is not in the workbook.

### Rows, Columns And Identities

- A sheet holds one header row and one block of data. Data after an empty row blocks the run. The error gives the row numbers, and other checks skip those rows.
- Every column with a header is loaded, including columns the target model does not list. A column without a header is skipped if empty and blocks the run otherwise.
- The command adds a missing public ID column, left empty. In a sheet where every row has a public ID, it also adds missing columns that the target model marks as required, except generated columns. These are left empty. In a sheet with any new row, it adds no required columns, so conformance validation reports missing and misnamed ones.
- Every row needs a unique, positive `system_id`. The command never assigns or changes one.
- Supplied public IDs are kept, never inferred. A row with one exists in SEAD; a row without one is new.
- The command declares `column_types`. Identity and foreign key columns are nullable integers. Mixed-type columns become text. Non-integer identity or foreign key values, and formulas without a saved result, block the run.
- `keys` is empty for every entity. Business keys serve reconciliation, which is already done.

### Foreign Keys

| Referenced entity   | Each non-null value must be                 | Project declaration                                                                         |
|---------------------|---------------------------------------------|---------------------------------------------------------------------------------------------|
| In the workbook     | A `system_id` in the referenced sheet       | `foreign_keys` entry with `local_keys: [<target public ID>]` and `remote_keys: [system_id]` |
| Not in the workbook | A SEAD ID. The command does not look it up. | `foreign_key_value_sources.<target>: public_id`                                             |

**Check.** Matching only a public ID is not enough, and no option overrides the rule. The check covers direct target model foreign keys and any other column named after another entity's public ID, including to and from sheets outside the model. For every unmatched value, without truncation, the error report gives the sheet, column, referenced sheet, Excel row numbers, and whether the value matches a public ID there.

**Declarations.** Only direct target model foreign keys whose column is in the entity, including added columns, are declared. A link is also used when the referenced entity was created by the command and the referring entity was created too. Self-references, `via` relationships and other ID columns keep their values without a declaration. An ID column that neither rule covers, such as `tbl_sample_dimensions.symbol_id`, is not checked.

No `public_id` value source is declared for `submission`, `data_provider` or `submission_state`. The change request ingester creates these tables and sets `submission_id` on new datasets to a local ID. From the code, a `public_id` declaration would make it treat that ID as a SEAD ID.

The command must check linked values itself: Core skips a link when the child already has the parent's public ID column. A test confirmed that the values then stay unchanged.

## Alternatives Considered

- **Add rows, rewrite values or assign IDs to repair references.** Rejected: this changes curated data or hides mistakes.
- **Declare a column with mixed local and SEAD IDs as `public_id`.** Rejected: new rows have no SEAD ID.
- **Leave out sheets or columns the target model does not cover.** Rejected: all curated data must be loaded.
- **Take public ID names from the SEAD schema reference.** Deferred: it adds a second metadata source for few sheets.
- **Use CSV sidecar files.** Rejected: unlike Parquet, they do not store column types.

## Risks And Tradeoffs

- **Wrong references can pass.** A mistyped value may match another `system_id`. SEAD IDs are not looked up.
- **Misnamed optional columns are not reported.** Conformance reports `qualifier_symbol` and `master_set_name` indirectly, because `symbol` and `master_name` are required. It does not report `tbl_sample_dimensions.symbol_id` (1365 values), which may be meant as `qualifier_id`. The command does not report it either.
- **Validation errors are expected.** The example lacks required tables such as `method` and `sample_type`. Created `submission` and `data_provider` entities have no rows, and `dataset` gets no `submission_id` column. Until validation changes, empty required values on existing rows can also fail data validation and change requests. One target model check is also expected to warn about links to new rows, because it compares them with public IDs.
- **A change request is expected to fail after project creation.** These limits come from ingester and backend behaviour, which this proposal does not change. No full change request was run.
  - The ingester builds `submission` and `data_provider` itself and rejects input tables with those names. How projects with these entities reach it is unresolved; see [#830](https://github.com/humlab-sead/sead_shape_shifter/issues/830).
  - Tracked entities need business keys, and the command sets none. The [User Guide](../USER_GUIDE.md) states that a run rejects missing keys. Some new rows also need an approval matched on `keys`.
  - The ingester writes unlisted columns, so deployment is expected to fail if the database lacks one. It also rejects tables outside the target model.
- **Circular links stop normalization.** For example, `site` and `site_preservation_status` can refer to each other. Cycle detection stops such a project until one link is removed or deferred.
- **The project is a snapshot.** Later workbook changes do not update it.

## Testing And Validation

- Unit tests with small workbooks for each rule and blocking error, including errors in several tables at once.
- Round-trip tests that bootstrap, load and normalize, then compare values. Cover empty and mixed-type columns, sheets outside the model, and a workbook exported by the `xlsx` dispatcher.
- Run the example before and after the curator corrects it.

## Acceptance Criteria

- `P-AC-1` Every sheet becomes a `fixed` entity with a Parquet sidecar file. The only other entities created are a missing `submission` or `data_provider`. Every entity has empty `keys`.
- `P-AC-2` Without circular links, the project loads and normalizes with all `system_id`, public ID and foreign key values unchanged.
- `P-AC-3` Entity names, public ID names and their blocking errors follow Sheets, using mappings from the options file.
- `P-AC-4` Every named column is loaded. The only added columns in a sheet are a missing public ID column and, when every row has a public ID, missing non-generated required columns.
- `P-AC-5` Data after an empty row, data without a header, invalid identity or foreign key values, and formulas without a saved result block the run. The command assigns no `system_id`.
- `P-AC-6` An unmatched reference to a sheet in the workbook blocks the run, with no override.
- `P-AC-7` One run lists every detectable error, including all foreign key details under Foreign Keys.
- `P-AC-8` Declarations follow Foreign Keys.
- `P-AC-9` A blocked run reports only blocking errors, exits with a non-zero status and writes no project files. No existing project is overwritten.
- `P-AC-10` A missing `submission` or `data_provider` is created as described under Submission And Data Provider, with no rows.
- `P-AC-11` The command requires `--data-provider-code` and `--provider-schema`, and writes their values to the project metadata. It does not check whether they are a registered pair.

## Final Recommendation

Add the bootstrap command with a strict foreign key rule and one complete error list. Load all curated data without changing identities. Handle validation of existing rows, ingester behaviour and the `data_provider` question separately.
