# Delivery 1 Hardening: `copy_csv` Artifact Contract

## Status

- Implemented hardening contract on current branch
- Scope: operator-facing `copy_csv` artifact contract for `sead_change_request`
- Applies to: bundle layout, naming, payload files, deploy SQL, manifest metadata, and validation expectations

## Summary

The current `copy_csv` renderer proves that a second deploy strategy can work.

This document records the first hardened contract for `copy_csv` bundles as implemented on the current branch. It keeps the integration with the SEAD Change Control System (SCCS) simple. Shape Shifter produces a bundle in a known layout. SCCS consumes that bundle and remains responsible for creating and managing the Sqitch change request.

The goal is to make the bundle deterministic, inspectable, and testable without reopening Delivery 1 planning, identity, materialization, or collision logic.

## Problem

The prototype was too loose in five places before this contract was hardened:

- bundle layout is not final
- CR naming and metadata precedence are not explicit
- payload encoding rules are incomplete
- deploy SQL assumptions are only implied by examples
- bundle metadata is not rich enough for operator review

That leaves too much room for drift between Shape Shifter output, SCCS consumption, and test expectations.

## Scope

This hardening note covers:

- canonical bundle naming
- canonical unpacked directory layout
- payload file format and compression rules
- deploy, revert, and verify SQL file rules
- required manifest fields
- validation expectations for artifact-level tests

This note does not cover:

- SCCS internals after bundle handoff
- Sqitch plan generation details inside SCCS
- rollback implementation beyond the current placeholder model
- non-`copy_csv` rendering strategies

## Contract

### 1. Integration Boundary

Delivery 1 keeps the integration simple.

Shape Shifter is responsible for creating a complete change-request bundle in a target folder.

SCCS is responsible for consuming that bundle and using existing SCCS tools to create the Sqitch change request.

Future releases may tighten the integration. This contract assumes file handoff only.

### 2. Canonical Bundle Form

The canonical contract is an unpacked directory tree.

Delivery 1 hardening should emit only the unpacked directory form. Tar packaging is out of scope for this contract.

The canonical root folder name is `CR_NAME`.

### 3. CR Name

The bundle identifier follows the SCCS naming convention:

`CR_NAME := {date}_DML_{datatype}_{identifier}`

Rules:

- `date`: required; defaults to the submission timestamp date when not supplied explicitly
- `datatype`: required; must be one of the approved SCCS project values listed below
- `identifier`: required; uppercase, filesystem-safe, and shorter than 40 characters
- `issue_number`: optional metadata field; defaults to `NNN` when absent
- `description`: required SQL-header field; when absent it resolves to `submission_name`, and the resolved value must be single line and shorter than 80 characters

Approved `datatype` values for Delivery 1 hardening:

- `mal`
- `archaeobotany`
- `dendrochronology`
- `adna`
- `bugs`
- `isotope`
- `ceramics`
- `radiocarbon`

Normalization rules:

- `identifier` must be normalized before bundle generation rather than patched afterward
- invalid bundle names should fail validation before files are written
- the manifest must record the resolved `CR_NAME` exactly as emitted
- invalid `datatype` values should fail validation before bundle generation

### 4. Canonical Directory Layout

The bundle root uses this structure:

```text
CR_NAME/
  manifest.json
  deploy/
    CR_NAME.sql
    CR_NAME/
      table_1.gz
      ...
      table_n.gz
  revert/
    CR_NAME.sql
  verify/
    CR_NAME.sql
```

Rules:

- payload files live only under `deploy/CR_NAME/`
- payload file paths in deploy SQL are relative to `deploy/`
- bundle layout must be deterministic across repeated renders of the same change package
- table emission order must be stable and recorded in the manifest
- `verify` is the correct directory name

### 5. Payload File Format

The hardened `copy_csv` contract uses file-backed tabular payloads with these rules:

- format: CSV mode with tab as delimiter
- encoding: UTF-8
- compression: gzip
- header row: absent
- one file per emitted target table
- file extension: `.gz`

Value rules must be explicit:

- column order must match the column order declared in the corresponding `\copy` statement exactly
- internal helper columns such as transient workflow fields or `_`-prefixed columns must never be emitted to payload files
- null values must be rendered as an unquoted empty field between delimiters, for example `a<TAB><TAB>c`
- empty string values must be rendered as a quoted empty field, `""`, so they remain distinguishable from null in CSV mode
- boolean values must be rendered as lowercase PostgreSQL-compatible text literals: `true` and `false`
- integer values must be rendered in base-10 form with no thousands separators or extra whitespace
- decimal values must use `.` as the decimal separator and must not use scientific notation unless that format is explicitly accepted by the target column type
- timestamps must be rendered in a single stable textual format, preferably ISO-8601 compatible text, and the chosen format must be used consistently across all payload files
- date-only values must be rendered in `YYYY-MM-DD` format
- text values must be UTF-8 encoded and must follow PostgreSQL CSV escaping rules rather than SQL literal quoting rules
- embedded tab, newline, carriage-return, delimiter, backslash, and quote characters must follow PostgreSQL CSV escaping rules for the entire contract and that rule must be covered by artifact tests
- each emitted row must contain exactly the same number of fields as the `\copy` column list for that table
- payload files must not include a header row, comment row, trailing delimiter padding, or strategy-specific marker columns

### 6. Deploy SQL Contract

The deploy SQL file is the operator entry point for applying the payload.

For each payload file, deploy SQL should emit a `\copy` statement aligned with this form:

```sql
\copy "tbl_name" (column_a, column_b) from program 'zcat -qac CR_NAME/table_name.gz' with (FORMAT csv, DELIMITER E'\t', ENCODING 'utf-8');
```

Rules:

- the hardened contract should preserve the historical SEAD pattern unless there is a documented reason to differ
- SCCS is treated as requiring a `psql` execution environment with `zcat`, because Delivery 1 hardening requires compressed payload files and `\copy`
- any intentional deviation from the historical pattern must be recorded in the manifest or companion documentation
- the current renderer targets the resolved table name directly and does not hardcode `public.` schema qualification in the emitted `\copy` statement
- deploy SQL should include only rendering and loading concerns, not identity or planning logic

Alternative noted but not adopted here:

- a future contract could unpack `.gz` files before execution and use plain file paths instead of `from program 'zcat -qac ...'`
- Delivery 1 hardening keeps the current compressed-file plus `zcat` pattern because it is closer to historical SEAD practice and satisfies the current SCCS expectation

### 7. Revert And Verify Files

`revert/CR_NAME.sql` and `verify/CR_NAME.sql` are part of the required bundle layout.

For Delivery 1 hardening, they may remain placeholders, but they must:

- exist for every emitted bundle
- use the same CR metadata header format as deploy SQL
- clearly state whether they are placeholders

### 8. SQL Header Contract

Each SQL file should begin with this header shape:

```sql
-- {file-type} {datatype}: CR_NAME
/***************************************************************************
  Author            {author}
  Date              {dispatch-date}
  Description       {description}
  Issue             https://github.com/humlab-sead/sead_change_control/issues/{issue-number}
***************************************************************************/
```

Rules:

- `file-type` is one of `deploy`, `revert`, or `verify`
- `author`, `dispatch-date`, `description`, and `issue-number` must come from explicit submission metadata or documented defaults
- documented defaults are: `author = unknown`, `dispatch-date = submission timestamp date`, `description = submission_name`, and `issue-number = NNN`
- missing required header fields should fail validation before bundle emission

### 9. Manifest Contract

`manifest.json` is required.

At minimum it should include:

- `contract_version`
- `deploy_strategy`
- `cr_name`
- `datatype`
- `identifier`
- `dispatch_date`
- `description`
- `issue_number`
- `table_order`
- `files`
- `row_counts`
- `checksums`
- `payload_format`
- `payload_encoding`
- `payload_delimiter`
- `payload_compression`
- `header_row`

The manifest is the primary operator-facing summary. An operator should be able to inspect the manifest and understand what the bundle contains without opening every payload file.

For Delivery 1 hardening, the manifest should also record:

- the approved `datatype` value used for validation
- the payload null rule
- the payload empty-string rule
- whether SCCS consumption assumes `psql` plus `zcat`

### 10. Validation Expectations

Hardening is not complete without artifact-level validation.

Focused tests should cover:

- deterministic bundle layout and stable file naming
- stable table order
- gzip payload emission
- tab-separated, headerless payload files
- CSV-mode payload behavior with tab delimiter
- `\copy` path generation
- manifest completeness
- SQL header completeness
- realistic edge cases for nulls, empty strings, timestamps, booleans, tabs, delimiters, quotes, backslashes, and multiline text
- emitted files on disk, not only in-memory artifact payloads

### 11. Differences From The Current Prototype

The current prototype already proves the renderer split, sidecar file support, and `copy_csv` path.

This hardening contract tightens that prototype in four ways:

- it defines the unpacked directory tree as canonical
- it requires gzip-compressed, headerless, tab-separated payload files
- it makes `manifest.json` required rather than optional
- it treats SQL headers and bundle metadata as part of the contract, not incidental output

## Resolved Decisions

The following points are fixed for Delivery 1 hardening:

- emit only the unpacked directory form
- use an unquoted empty field as the payload null representation
- use a quoted empty field, `""`, as the payload empty-string representation
- require compressed payload files and `\copy`-based loading
- treat SCCS consumption as requiring `psql` plus `zcat`
- restrict `datatype` to this approved list: `mal`, `archaeobotany`, `dendrochronology`, `adna`, `bugs`, `isotope`, `ceramics`, `radiocarbon`

## Intentional Differences From The Historical SCCS Example

The historical example in [docs/proposals/CHANGE_REQUEST_INGESTER/example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql](../../example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql) is a useful operational reference.

Delivery 1 hardening does not adopt that script wholesale.

The current contract intentionally keeps these differences:

- `\copy` loads directly into the target table instead of loading into temp tables and then inserting into the public table
- payload loading uses `FORMAT csv` with tab delimiter instead of `FORMAT text`, so null and empty-string behavior stay explicit and testable
- emitted `\copy` statements target the resolved table name directly and do not hardcode `public.` schema qualification
- Shape Shifter emits the artifact bundle only; it does not emit historical SCCS runtime setup such as `\cd`, sequence reset calls, temp-table DDL, or other session-scoped wrapper SQL
- the SQL header is limited to the metadata owned by the current contract instead of reproducing every historical SCCS header field
- `revert` and `verify` files are required placeholders in Delivery 1 hardening, not claims that rollback or verification are already implemented

These are accepted contract choices for Delivery 1 hardening. If a later SCCS integration requires the historical staging pattern, that should be proposed as a new contract revision rather than treated as an unspoken default.

## Recommendation

Use this contract as the target for Issue 3 hardening.

Do not redesign the `copy_csv` strategy again. Tighten the existing renderer and artifact emitter until they satisfy this document. Record any intentional deviations from the historical SEAD example explicitly rather than leaving them as implementation accidents.