# Delivery 1 Follow-Up Issue Drafts

This document turns the follow-up CR into GitHub-ready issue drafts and records their current status on this branch.

Issues 1 through 3 are now satisfied by branch work. Keep them only if the repository needs backfilled tracking history. Remaining follow-up work starts at Issue 4.

Current status snapshot:

- Issue 1: resolved on current branch
- Issue 2: prototype complete on current branch
- Issue 3: implemented on current branch
- Issue 4: open
- Issue 5: partial progress on current branch
- Issue 6: open

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

- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md`
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

- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md`
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

Keep the current planning and identity logic unchanged. Use [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_HARDENING.md](./DELIVERY_1_HARDENING.md) as the target contract for this work.

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

- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_HARDENING.md`
- `ingesters/sead_change_request/sql_builder.py`
- `ingesters/sead_change_request/ingester.py`
- `backend/tests/ingesters/test_sead_change_request_sql_builder.py`
- `backend/tests/ingesters/test_sead_change_request_ingester.py`

## Issue 4 [proposal(sead_change_request): decide whether to adopt Jinja2 for deploy rendering](https://github.com/humlab-sead/sead_shape_shifter/issues/440)

Status:

`Open`

Title:

`proposal(sead_change_request): decide whether to adopt Jinja2 for deploy rendering`

Problem:

Once multiple deploy strategies exist, plain Python string assembly may become harder to read and maintain. Jinja2 may help, but only if it stays limited to formatting and does not absorb business logic.

Solution:

Evaluate plain Python rendering against Jinja2 at the strategy boundary and document whether Jinja2 is accepted or deferred.

If adopted, Jinja2 should be limited to rendering deploy templates from structured inputs and should not contain row-selection, identity, or FK logic.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md`
- `ingesters/sead_change_request/sql_builder.py`

## Issue 5 [docs(target_model): complete SEAD v2 target model completeness review](https://github.com/humlab-sead/sead_shape_shifter/issues/441)

Status:

`Partial progress on current branch`

Title:

`docs(target_model): complete SEAD v2 target model completeness review`

Problem:

`docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md` is useful as an inventory, but it does not yet clearly separate documentation gaps, metadata-model gaps, and real schema-coverage gaps.

Solution:

Finish the completeness review so it supports concrete follow-up decisions.

The result should identify the highest-value remaining gaps and classify them by type and priority.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md`
- `resources/target_models/sead_standard_model.yml`

## Issue 6 [docs(metadata): compare SEAD target model with SeadSchema live-schema approach](https://github.com/humlab-sead/sead_shape_shifter/issues/442)

Status:

`Open`

Title:

`docs(metadata): compare SEAD target model with SeadSchema live-schema approach`

Problem:

The current change-request ingester uses target-model metadata, while the older `sead` ingester uses `SeadSchema` from the live SQL schema. The repository needs a clear written comparison before more output-format work hardens the wrong metadata boundary.

Solution:

Document the tradeoffs between the target-model-driven approach and the older `SeadSchema` live-schema approach.

The comparison should cover source of truth, drift risk, testability, offline reproducibility, SEAD-specific output generation, and operational dependence on a live schema.

Files:

- `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `ingesters/sead/metadata.py`
