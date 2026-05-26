# Proposal: Delivery 1 Follow-Up CR

## Status

- Proposed change request
- Scope: Post-Delivery-1 hardening and extensibility for `sead_change_request`
- Goal: Harden the current deploy-strategy baseline and review the SEAD metadata source-of-truth strategy
- Current branch status: deploy rendering is already split behind a strategy boundary
- Current branch status: an initial `copy_csv` plus `\copy` prototype already exists

## Summary

Delivery 1 is now closed on the current inline-`INSERT` artifact shape.

The current branch has already completed two of the original follow-up steps:

- deploy rendering is split behind an explicit strategy boundary
- an initial `copy_csv` plus `\copy` deploy strategy now exists beside the default inline-`INSERT` renderer

The next change request should focus on the remaining follow-up work:

- harden the `copy_csv` prototype into a stable operator-facing artifact contract
- defer Jinja2 for now and keep plain Python rendering at the current strategy boundary
- treat [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md) as the detailed home for the SEAD v2 target-model review and the `SeadSchema` comparison

These are follow-up improvements. They should not reopen Delivery 1 identity, confirmation, materialization, or collision-check behavior.

## Problem

The current Delivery 1 output path is intentionally narrow. It emits deploy SQL as inline `INSERT` statements and packages that output directly.

That is enough to close Delivery 1, but it still leaves three practical follow-up problems.

First, the repository now has a strategy boundary and an initial `copy_csv` prototype, but that second path is still rough. It needs a stable artifact contract, better CSV hardening, clearer operator execution support, and stronger bundle metadata before it should be treated as an operational format.

The target contract for that hardening work is now documented in [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_HARDENING.md](./DELIVERY_1_HARDENING.md).

Second, the repository now has a clear historical example of a different deploy shape in [docs/proposals/CHANGE_REQUEST_INGESTER/example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql](./example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql). The current prototype proves the architecture path, but it does not yet match the older pattern closely enough to settle path rules, payload shape, or operator workflow.

Third, the metadata source of truth still needs review. Delivery 1 uses the SEAD v2 target model, but the completeness review in [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md) is unfinished, and the tradeoffs versus the older live-schema approach based on `SeadSchema` in [ingesters/sead/metadata.py](../../../ingesters/sead/metadata.py) have not been documented clearly enough.

## Scope

This follow-up CR covers:

- hardening the current `copy_csv` plus `\copy` deploy prototype
- recording the decision to defer Jinja2 for deploy rendering for now
- completion of the SEAD v2 target-model completeness review through [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md)
- comparison of target-model-driven generation with the older `SeadSchema` live-schema approach through that same proposal

## Non-Goals

- reopening Delivery 1 identity orchestration
- changing SIMS or reconciliation behavior
- adding rollback or `UPDATE` generation in this CR by default
- replacing the target model outright before the review is complete
- rewriting the old `sead` ingester as part of this first follow-up step

## Current Behavior

The current `sead_change_request` implementation assumes one main deploy-artifact style:

- render inline `INSERT` SQL from the prepared change package
- emit the current Delivery 1 artifact bundle around that SQL

That path works, but it couples two distinct concerns:

- deciding what data must be inserted
- deciding how that insert payload should be rendered for deployment

The older SEAD path demonstrates a different rendering model. It uses temp tables, file-backed payloads, and `\copy`-based loading in a change-request script, as shown in [docs/proposals/CHANGE_REQUEST_INGESTER/example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql](./example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql).

Separately, the old `sead` ingester uses `SeadSchema` from [ingesters/sead/metadata.py](../../../ingesters/sead/metadata.py) to fetch and work from the live SEAD SQL schema. Delivery 1 instead relies on the target model and related metadata.

## Intentional Differences From The Historical SCCS Example

The historical script in [docs/proposals/CHANGE_REQUEST_INGESTER/example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql](./example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql) remains the reference point for SCCS-oriented deploy output.

The hardened Delivery 1 `copy_csv` contract intentionally differs from that example in these ways:

- it uses direct `\copy` into the target table rather than temp-table staging plus `INSERT ... SELECT`, because Delivery 1 keeps rendering limited to payload loading and leaves SCCS-specific DDL, merge logic, and Sqitch orchestration outside Shape Shifter output
- it uses `FORMAT csv` with a tab delimiter rather than `FORMAT text`, because the hardened contract needs explicit and testable rules for nulls, empty strings, quotes, tabs, carriage returns, and multiline text
- it emits a minimal bundle contract of `manifest.json` plus `deploy`, `revert`, and `verify`, rather than the broader session setup shown in the historical script such as `\cd`, sequence reset calls, temp-table lifecycle SQL, and extra execution wrappers
- it keeps the SQL header to the metadata fields currently owned by Shape Shifter: author, date, description, and issue number, instead of reproducing historical SCCS-only fields such as prerequisites, reviewer, approver, idempotency, and operator notes
- it treats `revert` and `verify` as required placeholder files in Delivery 1 hardening, rather than implying fuller rollback or verification behavior from the historical deploy example

These differences are deliberate scope choices, not gaps that should be silently “fixed” by making the renderer imitate the old script line for line.

## Proposed Design

### 1. Treat the current strategy split and `copy_csv` prototype as the baseline

The strategy boundary now exists for `sead_change_request`, and the current baseline should be preserved.

The renderer should continue to receive a stable, already-resolved input such as the change package or deploy-artifact planning model. It should not participate in identity resolution, FK materialization, collision checking, or Binding Set orchestration.

The current strategy set is:

- `InlineInsertDeployStrategy` — preserves the current Delivery 1 inline-`INSERT` output
- `CopyCsvDeployStrategy` — prototype strategy that emits tabular payload files plus deploy SQL that uses `\copy`

The next step is not another architecture split. It is to harden the prototype around deterministic file layout, value-shape handling, operator execution support, and artifact metadata.

That hardening should use the current contract decisions in [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_HARDENING.md](./DELIVERY_1_HARDENING.md), including:

- unpacked directory output as the only Delivery 1 artifact form
- approved `datatype` validation against the current SCCS project subset
- gzip-compressed tab-delimited CSV-mode payload files with no header row
- unquoted empty-field null encoding and quoted-empty-field empty-string encoding
- `\copy` plus `zcat` as the current SCCS execution assumption

### 2. Defer Jinja2 and keep the current rendering boundary

The strategy split already gives the package a clean rendering boundary.

For now, the repository should keep deploy rendering in plain Python. The current inline and `copy_csv` renderers are still small enough to stay readable without templates, and adding Jinja2 now would add another abstraction layer before a concrete maintenance problem exists.

This is a deferral, not a permanent rejection.

Reopen the question only if one or more of these become true:

- strategy-local rendering grows enough that plain Python becomes materially harder to read
- template duplication across deploy strategies becomes hard to control
- operator-facing artifact formats require larger, mostly-static text templates that would clearly benefit from a template engine

If the question is reopened later, Jinja2 should still be limited to formatting structured inputs at the rendering boundary. It should not become the place where row selection, identity rules, or FK logic are encoded.

### 3. Use the target-model completeness proposal as the detailed metadata review surface

The detailed home for the remaining metadata review work is now [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md).

That proposal now carries both parts of the remaining metadata work:

- completion of the SEAD v2 target-model completeness review
- comparison of the current target-model-driven approach with the older `SeadSchema` live-schema approach in [ingesters/sead/metadata.py](../../../ingesters/sead/metadata.py)

This follow-up CR should stay high level.

It only needs to make the dependency clear: further output-format work should not harden the wrong metadata boundary before that proposal is accepted.

## Risks And Tradeoffs

- A strategy split adds one more abstraction layer. That is worthwhile only if the boundary stays narrow and data-driven.
- A `\copy` plus CSV strategy may produce artifacts that are closer to older SEAD operational practice, but it also increases packaging and file-layout complexity.
- Deferring Jinja2 avoids extra complexity now, but it may need to be revisited if rendering logic becomes significantly larger.
- A target-model versus live-schema review may expose mismatches that lead to broader follow-up work than this CR should absorb directly.

## Testing And Validation

Validation for this follow-up CR should include:

- regression tests proving the current inline-`INSERT` strategy still emits the existing Delivery 1 artifact shape
- focused hardening tests for the current `copy_csv` output, including generated payload files, deploy SQL structure, CSV edge cases, and emitted bundle metadata
- focused hardening tests that prove conformance to [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_HARDENING.md](./DELIVERY_1_HARDENING.md)
- comparison of the hardened `copy_csv` output shape with the historical example in [docs/proposals/CHANGE_REQUEST_INGESTER/example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql](./example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql), with any intentional differences documented explicitly
- review of [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md) as the detailed home for both the completeness review and the `SeadSchema` comparison

## Acceptance Criteria

- the current deploy-strategy boundary remains intact
- the current inline-`INSERT` behavior remains available as the default strategy
- the `copy_csv` artifact contract is hardened enough for operator review and stable test coverage
- the `copy_csv` artifact contract conforms to [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_HARDENING.md](./DELIVERY_1_HARDENING.md)
- the Jinja2 decision is documented as deferred with reasons
- [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md) is the accepted detailed home for both the completeness review and the `SeadSchema` comparison

## Recommended Delivery Order

1. Harden the current `copy_csv` prototype against the historical artifact shape and realistic operator needs.
2. Finish the remaining metadata review through [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md).

## Suggested Issue Breakdown

### Issue 1. Extract Deploy Rendering Strategy

Status: done on current branch

Includes:

- define a strategy boundary for deploy-artifact rendering
- preserve the current inline-`INSERT` output as the default strategy
- keep identity, materialization, and collision logic outside the rendering layer

Exit criteria:

- deploy rendering is selected through an explicit strategy interface
- current Delivery 1 output still renders unchanged through the default strategy

### Issue 2. Prototype CSV Plus `\copy` Deploy Strategy

Status: prototype complete on current branch

Includes:

- define the artifact shape for file-backed payloads
- generate gzip-compressed, tab-delimited CSV-mode payload files and matching deploy SQL
- compare the output shape with the historical example in `example/20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT.sql`

Exit criteria:

- the repository can render a second deploy format without changing identity or planning logic
- the generated artifact set is concrete enough for operator review

### Issue 3. Harden `copy_csv` Deploy Artifacts

Status: open

Includes:

- lock down path rules, naming rules, and deterministic table ordering
- harden CSV value handling for realistic payloads
- add an operator execution wrapper or equivalent bundle guidance
- expand strategy metadata and end-to-end artifact tests
- implement the contract documented in `docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_HARDENING.md`

Exit criteria:

- the `copy_csv` bundle shape is stable enough for operator review
- the emitted bundle matches the hardened contract note
- artifact-level tests cover both bundle structure and CSV edge cases

### Issue 4. Decide On Jinja2 For Rendering

Status: resolved by decision on current branch

Includes:

- document that Jinja2 is deferred for now
- keep deploy rendering in plain Python at the current strategy boundary
- record when the question should be revisited

Exit criteria:

- the Jinja2 decision is explicit and recorded with reasons
- plain Python remains the current rendering approach
- any future Jinja2 adoption stays limited to formatting concerns at the rendering boundary

### Issue 5. Complete SEAD v2 Target Model Review

Status: resolved on current branch

Detailed proposal home:

- [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md)

Exit criteria:

- the completeness document supports a concrete decision rather than an open-ended inventory
- remaining gaps are prioritized clearly enough for follow-up implementation

### Issue 6. Compare Target Model With `SeadSchema`

Status: open

Detailed proposal home:

- [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](../SEAD_V2_TARGET_MODEL_COMPLETENESS.md)

Exit criteria:

- the repository has a clear written comparison of the two metadata approaches
- the comparison is strong enough to guide the next implementation step

## Final Recommendation

Close Delivery 1 on the current working implementation and treat this as the next focused CR.

Start from the current strategy boundary and the existing `copy_csv` prototype rather than reopening that groundwork. Treat `copy_csv` hardening as the next implementation slice, keep Jinja2 deferred unless rendering complexity materially grows, and complete the metadata review before further output-format work hardens the current metadata boundary.

## Issue-Ready Drafts

Use [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_ISSUES.md](./DELIVERY_1_FOLLOWUP_ISSUES.md) as the current source of truth for issue-ready drafts and per-issue status.