# Delivery 1 Follow-Up Issue Drafts

This document turns the follow-up CR into GitHub-ready issue drafts and records their current status on this branch.

All issues captured here are now resolved or implemented on the current branch. Keep this file only if the repository needs backfilled tracking history.

Current status snapshot:

- Issue 1: resolved on current branch
- Issue 2: prototype complete on current branch
- Issue 3: implemented on current branch
- Issue 4: resolved by decision on current branch
- Issue 5: resolved on current branch
- Issue 6: resolved on current branch
- Issue 7: implemented on current branch

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

## Issue 1 [refactor(sead_change_request): extract deploy rendering strategy boundary](https://github.com/humlab-sead/sead_shape_shifter/issues/438)

Status:

`Resolved on current branch`

Title:

`refactor(sead_change_request): extract deploy rendering strategy boundary`

Problem:

The current `sead_change_request` deploy path couples two separate concerns:

- deciding what rows belong in the change package
- deciding how those rows are rendered into deploy artifacts

That makes it harder to add a second deploy format without threading output-format logic through the current SQL builder.

Solution:

Extract deploy-artifact rendering behind an explicit strategy interface.

Keep the current inline-`INSERT` output as the default strategy. Keep identity resolution, FK materialization, collision checking, and Binding Set handling outside the rendering layer.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md`
- `ingesters/sead_change_request/sql_builder.py`
- `ingesters/sead_change_request/ingester.py`

## Issue 2 [feat(sead_change_request): prototype CSV and \copy deploy strategy](https://github.com/humlab-sead/sead_shape_shifter/issues/439)

Status:

`Prototype complete on current branch`

Title:

`feat(sead_change_request): prototype CSV and \copy deploy strategy`

Problem:

The repository has a historical SEAD deploy pattern that stages payloads in files and loads them via `\copy`, but the current change-request ingester only emits inline `INSERT` SQL.

Reference example:

- `docs/proposals/CHANGE_REQUEST_INGESTER/example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql`

Solution:

Add a second deploy-rendering strategy that emits gzip-compressed, tab-delimited CSV-mode payload files plus deploy SQL using `\copy`.

The prototype should preserve the current planning and identity logic and only change artifact rendering and payload packaging.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql`
- `ingesters/sead_change_request/sql_builder.py`
- `ingesters/sead_change_request/ingester.py`

## Issue 3 #439

Status:

`Implemented on current branch`

Title:

`refactor(sead_change_request): harden copy_csv deploy artifact contract`

Problem:

The current `copy_csv` deploy path started as a prototype proving that a second rendering strategy could work.

The hardening work on this branch locks down the operator-facing artifact contract around file naming, deterministic table ordering, CSV value encoding, bundle metadata, and execution guidance.

Solution:

Harden the `copy_csv` artifact bundle rather than redesigning the strategy.

Keep the current planning and identity logic unchanged. Use [docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_HARDENING.md](./closed_delivery_1/DELIVERY_1_HARDENING.md) as the target contract for this work.

Concrete steps:

- emit only the unpacked directory form described in the hardening note and treat tar packaging as out of scope for Delivery 1
- validate `CR_NAME` and restrict `datatype` to the approved SCCS list: `mal`, `archaeobotany`, `dendrochronology`, `adna`, `bugs`, `isotope`, `ceramics`, `radiocarbon`
- lock down a deterministic bundle layout for `copy_csv`, including stable table ordering, stable file naming, and explicit payload paths under `deploy/CR_NAME/`
- harden payload rendering around gzip-compressed, headerless, tab-delimited CSV-mode files and document both the null and empty-string rules explicitly
- keep the current `\copy` plus `zcat` execution pattern and treat `psql` plus `zcat` as part of the SCCS runtime assumption for this contract
- add manifest and SQL-header metadata that makes the bundle inspectable without opening every payload file
- add focused artifact-level tests for both in-memory rendering and emitted files on disk so the bundle shape stays stable across refactors
- compare the hardened `copy_csv` artifact shape with the historical SEAD example and record any intentional differences rather than leaving them implicit

Current branch result:

- deterministic bundle rewrites are implemented, including stable gzip payload bytes and manifest checksums over emitted file content
- manifest metadata now records emitted table order and real row counts rather than reconstructing them indirectly
- submission metadata validation now rejects malformed descriptions before bundle emission
- focused tests cover nulls, empty strings, tabs, quotes, backslashes, carriage returns, multiline text, emitted files on disk, and manifest-to-disk checksum verification
- the hardening note now records the intentional differences from the historical SCCS example instead of leaving them implicit

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_HARDENING.md`
- `ingesters/sead_change_request/sql_builder.py`
- `ingesters/sead_change_request/ingester.py`
- `backend/tests/ingesters/test_sead_change_request_sql_builder.py`
- `backend/tests/ingesters/test_sead_change_request_ingester.py`

## Issue 4 [proposal(sead_change_request): decide whether to adopt Jinja2 for deploy rendering](https://github.com/humlab-sead/sead_shape_shifter/issues/440)

Status:

`Resolved by decision on current branch`

Title:

`proposal(sead_change_request): decide whether to adopt Jinja2 for deploy rendering`

Problem:

Once multiple deploy strategies exist, plain Python string assembly may become harder to read and maintain. Jinja2 may help, but only if it stays limited to formatting and does not absorb business logic.

Solution:

Evaluate plain Python rendering against Jinja2 at the strategy boundary and document whether Jinja2 is accepted or deferred.

If adopted, Jinja2 should be limited to rendering deploy templates from structured inputs and should not contain row-selection, identity, or FK logic.

Current branch decision:

- defer Jinja2 for now
- keep deploy rendering in plain Python at the current strategy boundary
- reopen the question only if the renderers become materially harder to read or duplication grows enough to justify templates

Reasoning:

- the current strategy split already gives a clean rendering boundary without adding another abstraction layer
- the current inline and `copy_csv` renderers are still small enough to keep readable in plain Python
- adding Jinja2 now would increase moving parts without solving a demonstrated maintenance problem

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md`
- `ingesters/sead_change_request/sql_builder.py`

## Issue 5 [docs(target_model): complete SEAD v2 target model completeness review](https://github.com/humlab-sead/sead_shape_shifter/issues/441)

Status:

`Resolved on current branch`

Title:

`docs(target_model): complete SEAD v2 target model completeness review`

Detailed proposal home:

- [docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md)

Summary:

Issue 5 is now tracked in detail in the SEAD v2 target-model completeness proposal.

That document now records:

- verified current YAML coverage
- separation of documentation gaps, target-model gaps, and schema-boundary decisions
- prioritized missing areas for follow-up model work

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md`
- `resources/target_models/sead_superset_model.yml`

## Issue 6 [docs(metadata): compare SEAD target model with SeadSchema live-schema approach](https://github.com/humlab-sead/sead_shape_shifter/issues/442)

Status:

`Resolved on current branch`

Title:

`docs(metadata): compare SEAD target model with SeadSchema live-schema approach`

Detailed proposal home:

- [docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md)

Summary:

Issue 6 is now resolved through the same target-model completeness proposal rather than through this change-request issue draft.

That document now includes:

- an explicit target-model versus `SeadSchema` comparison
- a recommendation to keep the target model as the current metadata boundary for `sead_change_request`
- issue-specific acceptance criteria that are now satisfied on the current branch

Issue status note:

- the detailed analysis is now in `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- the comparison and recommendation are complete on the current branch; GitHub issue `#442` can be closed if it is still open

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `ingesters/sead/metadata.py`

## Issue 7 [fix(sead_change_request): render date-only copy_csv values as YYYY-MM-DD](https://github.com/humlab-sead/sead_shape_shifter/issues/446)

Status:

`Implemented on current branch`

Title:

`fix(sead_change_request): render date-only copy_csv values as YYYY-MM-DD`

Problem:

The hardened `copy_csv` contract says date-only values must be rendered as `YYYY-MM-DD`.

The current renderer serializes `datetime`-like values with `isoformat()`. That is acceptable for timestamps, but pandas date columns can arrive as midnight `Timestamp` values and currently render as `YYYY-MM-DDT00:00:00` instead of the contract format.

This is a narrow renderer mismatch, not a reason to reopen the broader `copy_csv` hardening issue.

Solution:

Keep the current hardened `copy_csv` contract and fix only the date-only rendering path.

Detect date-only payload values before generic timestamp serialization, render them as `YYYY-MM-DD`, and add focused regression coverage for both in-memory artifact rendering and emitted bundle output where appropriate.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/closed_delivery_1/DELIVERY_1_HARDENING.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_ISSUES.md`
- `ingesters/sead_change_request/sql_builder.py`
- `backend/tests/ingesters/test_sead_change_request_sql_builder.py`
