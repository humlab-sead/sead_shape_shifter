# Proposal: Define And Verify The SEAD Target Model Coverage Boundary

## Status

- Proposed change request
- Scope: how the SEAD target model's completeness boundary is defined, measured, and enforced
- Goal: make "complete" a checkable result instead of a prose claim
- Related: [SEAD v2 Target Model Completeness](done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md) (closed metadata-boundary decision), [Target Model Conformance Enhancements](done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md), [SEAD v2 Target Model Follow-Up Issue Drafts](done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md)
- Tracking issue: [#532 feat(target-model): track SEAD superset coverage completion](https://github.com/humlab-sead/sead_shape_shifter/issues/532)

## Summary

The shared SEAD target model at [resources/target_models/sead_superset_model.yml](../../resources/target_models/sead_superset_model.yml) is described as the near-complete shared SEAD model, but nothing defines or checks what "complete" means. Three documents state different coverage counts for the same file: 23 entities in the [implementation plan](done/SEAD_V2_IMPLEMENTATION_PLAN.md), 61 in the [completeness proposal](done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md), and 92 in [docs/TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md) against an actual 102. The model also now contains tables that its own reference snapshot excludes while missing 42 tables that the snapshot includes.

Recommendation: pin the coverage boundary as a versioned list of source surfaces, record every table in those surfaces as either mapped or excluded-with-reason in a coverage manifest, generate the coverage report from that manifest, and fail the test suite when the model and the manifest disagree.

This is the right time because the shared model is now the metadata boundary for `sead_change_request`, and the alternative is more unevidenced coverage claims layered on top of each other.

## Problem

### The completeness boundary is undefined

No document states which schema surface the shared model is supposed to cover, so no one can tell whether a missing table is a gap or a decision.

The consequences are measurable. Counting the in-scope tables in [filtered_import_tables.csv](CHANGE_REQUEST_INGESTER/resources/filtered_import_tables.csv) against the `target_table` values in the model gives 136 in-scope tables and 42 with no entity. That number has never appeared in a repository document.

### The reference snapshot and the model disagree in both directions

The filtered snapshot is documented as the working comparison surface, but it does not cover the model:

- 5 model entities target tables the raw snapshot never contained: `tbl_data_providers`, `tbl_submissions`, `tbl_submission_states`, `tbl_submission_tasks`, `tbl_submission_task_types`. These come from a submission surface that is still a proposed upstream DDL change ([REFACTOR_SEAD_SUBMISSION_METADATA.md](CHANGE_REQUEST_INGESTER/REFACTOR_SEAD_SUBMISSION_METADATA.md), "upstream PostgreSQL validation pending") rather than from the deployed SEAD ingestion schema.
- 2 model entities target tables the earlier review deliberately excluded: `tbl_colours` and `tbl_sample_colours`.

A single snapshot therefore cannot serve as the boundary while the model mixes two schema surfaces.

### Nothing enforces coverage or consistency

`TargetModelSpecValidator` checks internal consistency only. No test, script, or Makefile target loads the filtered snapshot; the only target-model drift guard wired into `make lint` is the generated schema reference.

Recent history shows the cost. Commit `d677113b` disabled two entities and one column in the model and did not update the spec tests, the committed schema reference, or the prose. `tests/target_model` was red on `dev` until `9b3ca12f`, while [docs/TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md) still claimed 92 entities against an actual 102. That class of change is only caught by running the suite locally, because no workflow runs it.

### Unverified claims reached an accepted document

The accepted completeness proposal states that `coordinate_system` is "modeled explicitly" and appears in "Verified Current Coverage". The entity was added in `ccc53c66`, disabled in `d677113b`, and removed in `9b3ca12f`; `tbl_coordinate_systems` exists in none of the three schema sources checked (the [schema dump](../sead/01_tables.sql), the raw `import_tables.csv` snapshot, and `sead_change_control/resources/tables_and_columns.csv`). The claim survived because no check connected prose coverage claims to the model.

## Scope

- The definition of the coverage boundary, its source surfaces, and how each is pinned.
- A machine-readable coverage manifest recording a disposition for every table in the boundary.
- A coverage checker, a generated coverage report, and the tests and Makefile hook that enforce them.
- The remaining coverage gaps, grouped into ordered slices.
- A minimal test workflow so a red suite cannot sit unnoticed on `dev`.

## Non-Goals

- Reopening the metadata-boundary decision (target model versus `SeadSchema`). That decision is accepted and stays closed.
- Changing the target-model format. The `TargetModel` schema, `spec_validator`, and `conformance` modules are not part of this decision.
- Defining completeness for project-level curated subsets. This is about the shared superset only.
- Fixing the 42 coverage gaps. This proposal defines and verifies the boundary; the gaps become the follow-up slices.
- Workflow changes beyond a minimal test workflow.

## Current Behavior

Verified against the current tree on `dev` at `9b3ca12f`:

- The model loads to 102 entities; 101 declare a `target_table`; `abundance_element_group` declares none; no two entities share a `target_table`.
- The spec validator reports no issues, so internal consistency is already enforced.
- The filtered snapshot contains 136 `tbl_*` tables and is committed to the repository, so the comparison is reproducible offline.
- The snapshot carries `is_lookup` and `is_unknown` flags per table. Of the 42 unmapped tables, 30 are flagged as lookups, 1 as unknown, and 11 as neither.
- Unmapped tables group as: taxonomy support 10, generic lookups and operational tables 10, sample-group description family 5, site support 4, analysis-entity extensions 3, text blocks 3, dataset and submission support 3, reference bridges 2, measured values 2.
- `make lint` runs `tidy`, `ruff`, `pylint`, `check-target-model-schema-reference`, and `check-doc-links`. `make test` runs `pytest tests backend/tests ingesters/sead/tests`.
- The only workflow in `.github/workflows/` is `release.yml`, which runs `semantic-release` on pushes to `main`. No workflow runs tests or lint.
- `docs/TARGET_MODEL_SCHEMA_REFERENCE.md` is generated by `scripts/generate_target_model_schema_reference.py`, has a `--check` mode, and is guarded by both a Makefile target and a test. That is the pattern this proposal follows.

Two model entities do not map cleanly to the boundary and need an explicit decision rather than a silent exclusion:

- `site` declares a foreign key to `site_type` with no `via`, but `tbl_sites` has no `site_type_id` column; the schema expresses that relationship through the `tbl_site_site_types` bridge, which has no entity. The `site.site_type_id` column is currently commented out, which is consistent with the schema but leaves the declared foreign key unsupported. `site` also omits `site_preservation_status_id` and `site_location_accuracy`, which exist in the table.
- `tbl_site_references` — the site-to-citation bridge requested in issue #483 — has no entity. The SEAD table is named `tbl_site_references` (plural).

## Proposed Design

### 1. Pin the boundary as named source surfaces

The manifest declares its surfaces explicitly instead of inheriting an implicit one:

- **Surface A — deployed SEAD ingestion schema.** Pinned to `filtered_import_tables.csv` (136 tables), with `filtered_import_columns.csv` as column-level evidence.
- **Surface B — pending SEAD submission DDL.** The five submission tables (`tbl_data_providers`, `tbl_submissions`, `tbl_submission_states`, `tbl_submission_task_types`, `tbl_submission_tasks`). This surface has no committed authoritative DDL reference, so its provenance is recorded as `TBD` with the proposal text named as the only source. Recording the surface as pending, not deployed, keeps "modeled" distinguishable from "live".

Each surface records its reference path and a one-line provenance note. Adding a surface is an explicit edit, not a side effect of adding an entity.

### 2. Record one disposition per boundary table

Add `resources/target_models/sead_coverage_manifest.yml`:

```yaml
surfaces:
  - id: sead-ingestion
    reference: docs/proposals/CHANGE_REQUEST_INGESTER/resources/filtered_import_tables.csv
    columns_reference: docs/proposals/CHANGE_REQUEST_INGESTER/resources/filtered_import_columns.csv
    state: deployed
  - id: sead-submission
    reference: TBD
    state: pending-upstream-ddl
    provenance: >
      No committed authoritative DDL reference. Table list taken from the submission
      entities currently in the model. DDL text appears only in
      CHANGE_REQUEST_INGESTER/REFACTOR_SEAD_SUBMISSION_METADATA.md and in the
      historical docs/archive/SEAD_REFACTOR_WORK_IN_PROGRESS.md. See Open Question Q1.

exclusions:
  - table: tbl_text_biology
    surface: sead-ingestion
    category: operational
    reason: Free-text publication content with no role in change-request mapping.
```

Two dispositions only:

- **mapped** — an entity declares this `target_table`. Derived from the model; never listed by hand.
- **excluded** — listed in the manifest with a surface, a category, and a reason.

Exclusion categories: `superseded` (replaced by the `tbl_analysis_values` path), `derived` (runtime-computed), `operational` (support data with no domain meaning), `out-of-current-tranche` (a real gap deferred to a numbered slice).

### 3. Check coverage in both directions

Add `src/target_model/coverage.py` exposing `check_coverage(model, manifest) -> CoverageReport`, reporting counts for `in_scope`, `mapped`, `excluded`, and `unmapped`, plus violations:

| Code | Condition |
|---|---|
| `COVERAGE_UNMAPPED_TABLE` | Boundary table with no entity and no exclusion |
| `COVERAGE_STALE_EXCLUSION` | Exclusion names a table already mapped by an entity |
| `COVERAGE_UNKNOWN_TABLE` | Exclusion names a table in no declared surface |
| `COVERAGE_OUT_OF_BOUNDARY_MODEL_TABLE` | A `target_table` in no declared surface |
| `COVERAGE_DUPLICATE_TARGET_TABLE` | Two entities declare the same `target_table` |
| `COVERAGE_UNDECLARED_SURFACE` | An exclusion cites a surface that is not declared |

The checker is read-only and does not load a project. Entities without a `target_table` are skipped rather than flagged.

### 4. Generate the coverage report

Add `scripts/generate_target_model_coverage.py` with an optional `--check`, writing `docs/TARGET_MODEL_COVERAGE.md`: current counts per surface, the unmapped list with the slice that owns each table, and the exclusion list.

This mirrors the existing generated-reference pattern, and makes the numbers in prose replaceable by a link. Entity counts and coverage claims are removed from hand-written documents, including the "currently covers N entities" sentence in [docs/TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md).

### 5. Enforce it

- `make check-target-model-coverage` calls the generator with `--check`, added to the `lint` target next to `check-target-model-schema-reference`.
- A test in `tests/target_model/` asserts the committed coverage report matches the generated one and that `check_coverage` reports no violations.
- Add `.github/workflows/test.yml` running `make test` and `make lint` on pushes and pull requests. The existing release workflow is unaffected.

### 6. Then close the gaps in slices

The manifest makes each slice measurable: a slice is done when its tables move from `out-of-current-tranche` to `mapped` and the coverage check reports fewer unmapped tables.

## Alternatives Considered

**Keep completeness as prose.** Rejected. Three documents already disagree, and one accepted document contains a false coverage claim.

**Reuse the existing manifest-free approach and simply list unmapped tables in a doc.** Rejected. A hand-maintained list has the same drift mode as the current prose; only the reason text becomes structured.

**Pin the boundary to the live database via `SeadSchema`.** Rejected. This reverses the accepted metadata-boundary decision and makes the check depend on a running database.

**Treat the raw unfiltered snapshot (137+ tables) as the boundary.** Rejected. It re-admits the deprecated, derived, and image families the earlier review removed for stated reasons, and it cannot express the pending submission surface.

**Require every in-scope table to be modeled.** Rejected. Tables such as text blocks and generic operational lookups have no change-request mapping value, so forcing entities would add noise to the shared model.

## Risks And Tradeoffs

- **Manifest maintenance.** Every new entity or surface needs one manifest touch. The stale-exclusion and out-of-boundary checks keep that cost visible rather than silent.
- **Category judgement.** `operational` and `out-of-current-tranche` are subjective. Recording the reason and requiring a surface keeps the judgement reviewable.
- **Two-directional checking may surface existing inconsistencies immediately.** `tbl_colours`, `tbl_sample_colours`, and the five submission tables already sit outside the ingestion surface, so the first run will report violations until the manifest decision in Open Questions 1 and 2 is taken.
- **A CI test workflow is new infrastructure** and will need secrets-free setup for the core and backend suites. The ingester tests in `make test` may require environment configuration; if so, the workflow should run the core and backend suites only, and that difference must be stated in the workflow rather than hidden.
- **Generated report churn.** Slices will change `docs/TARGET_MODEL_COVERAGE.md` frequently. That is intended: it is the visible measure of progress.

## Testing And Validation

- Unit tests for `check_coverage` covering each violation code, an empty model, a model with no `target_table` values, a fully covered surface, and an entirely unmapped surface.
- A model-versus-manifest test asserting no violations for the committed files.
- A generated-report test asserting the committed `docs/TARGET_MODEL_COVERAGE.md` matches `--check` output.
- A regression test asserting that commenting out an entity which the spec tests assert causes a failure, covering the `d677113b` failure mode.
- Existing suites must stay green: `tests/target_model`, `tests/model/test_target_model_conformance.py`, `tests/validators/test_target_model_data_validators.py`, and the backend target-model tests.
- `make lint` and `make test` must pass, including the new coverage hook.

## Acceptance Criteria

- `P-AC-1` The coverage boundary is defined in one versioned manifest that declares every source surface with its reference path and deployment state.
- `P-AC-2` Every table in every declared surface has exactly one disposition: mapped by an entity, or excluded with a surface, category, and reason.
- `P-AC-3` `check_coverage` returns a structured report with counts and the six violation codes, and loads no project or database.
- `P-AC-4` The repository state reports zero coverage violations once the boundary decisions in the Open Questions are applied.
- `P-AC-5` `docs/TARGET_MODEL_COVERAGE.md` is generated from the model and manifest and is verified in `--check` mode.
- `P-AC-6` Hand-written documents contain no unverified entity counts or coverage claims; prose links to the generated report instead.
- `P-AC-7` `make lint` fails when the model, the manifest, and the generated report disagree.
- `P-AC-8` A workflow runs the test suite and lint on pushes and pull requests, so model edits that invalidate tests fail before merge.
- `P-AC-9` Removing or disabling an entity that existing tests or the coverage check depend on fails the suite.
- `P-AC-10` Each remaining unmapped table is assigned to a named slice, and slice completion is measurable as a reduction in the unmapped count.

## Planning Handoff

Confirmed decisions:

- The boundary is expressed as named, pinned source surfaces; the ingestion snapshot alone is not the boundary.
- A table is either mapped or excluded with a recorded reason. No third state and no silent gaps.
- Mapped status is derived from `target_table` and is never hand-listed.
- The manifest, checker, and report follow the existing generated-schema-reference pattern.
- The target-model format, spec validator, and conformance validator are unchanged.
- The metadata-boundary decision stays closed.

Constraints and behaviour to preserve:

- The filtered snapshot is committed and is the offline reference; the checker must not require a database.
- Entities without a `target_table` remain legal.
- `make test`, `make lint`, and the existing generated-reference check must keep passing.
- Existing `tests/target_model` assertions are the contract for currently modeled entities and must not be weakened to make the checker pass.

Expected validation outcomes:

- All six violation codes are demonstrably detected by tests.
- The committed report and manifest produce zero violations after the open boundary questions are answered.
- The suite fails when a required entity is disabled.

Open questions and the slice that must resolve each:

| Question | Resolve by |
|---|---|
| Q1: Is the pending submission surface in the boundary, and does it block "complete"? | Manifest slice |
| Q2: Do `tbl_colours` and `tbl_sample_colours` belong in the boundary (in-scope) or in the model as accepted additions? | Manifest slice |
| Q3: Which tables are permanently `operational` versus deferred to a later slice, and how are text blocks classified? | Manifest slice |
| Q4: Does the test workflow run the full `make test` including ingester tests, or core and backend only? | Enforcement slice |
| Q5: Does `site → site_type` become a `via` relationship through a `tbl_site_site_types` entity, or stay a direct foreign key? | Site slice |

## Recommended Delivery Order

1. **Boundary and manifest.** Declare surfaces, record exclusions, resolve Q1-Q3, and land `check_coverage` with the full violation set.
2. **Generated report and enforcement.** Add the generator, the `lint` hook, the coverage tests, and resolve Q4.
3. **Site slice.** `site_reference` ([#483](https://github.com/humlab-sead/sead_shape_shifter/issues/483)), a disposition for `tbl_site_site_types` (Q5), `tbl_site_other_records`, and `tbl_site_preservation_status`. Four tables.
4. **Sample-group description slice.** The `tbl_sample_group_descriptions` family and the related sampling-context joins. Five tables.
5. **Analysis-entity and measured-value slice.** `tbl_analysis_entity_ages`, `tbl_analysis_entity_dimensions`, `tbl_analysis_entity_prep_methods`, `tbl_measured_values`, `tbl_measured_value_dimensions`. Five tables.
6. **Taxonomy support slice.** The `tbl_taxa_tree_*` hierarchy, `tbl_species_associations`, `tbl_taxa_seasonality`, `tbl_taxonomy_notes`, `tbl_taxonomic_order_biblio`, and `tbl_taxa_reference_specimens`. Ten tables.
7. **Dataset, submission, and reference slice.** `tbl_dataset_methods`, `tbl_dataset_submission_types`, `tbl_dataset_submissions`, `tbl_geochron_refs`, `tbl_relative_age_refs`. Five tables.

## Open Questions

- Should the shared model carry a pending-DDL surface at all, or should submission entities live in a separate model until the upstream DDL deploys?
- Should the coverage check run in `lint`, in `test`, or in both?
- Is a workflow the right enforcement point, or is a repository-wide pre-push expectation sufficient given the current release-only workflow setup?

## Final Recommendation

Define the boundary as named, pinned surfaces; give every table one recorded disposition; and verify the result with a generated report and a lint hook instead of prose.

Two facts make this urgent rather than tidy-up work. The model already contains tables from two different schema surfaces, so "complete" currently has no defined meaning. And the previous round produced an accepted coverage claim for a table that exists in no schema source, which is the failure mode the checker exists to prevent.

The measurable target is a coverage report showing zero unmapped tables and zero violations, with each of the current 42 gaps either mapped or excluded with a stated reason.
