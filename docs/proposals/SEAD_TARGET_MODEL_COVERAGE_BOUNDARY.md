# Proposal: Report Target Model Coverage Against SEAD

## Status

- Proposed change request (revised: separate manifest removed, CI/CD dropped)
- Scope: how a SEAD target model declares its coverage source and how coverage is measured
- Goal: make "complete" a computed result instead of a prose claim
- Related: [SEAD v2 Target Model Completeness](done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md) (closed metadata-boundary decision), [Target Model Conformance Enhancements](done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md)
- Gap triage: [TARGET_MODEL_MISSING_ENTITY_CANDIDATES_20261026.md](../../resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES_20261026.md)
- Tracking issue: [#532 feat(target-model): track SEAD standard model coverage completion](https://github.com/humlab-sead/sead_shape_shifter/issues/532)

## Summary

The shared SEAD target model at [resources/target_models/sead_standard_model.yml](../../resources/target_models/sead_standard_model.yml) is described as nearly complete, but nothing computes what "complete" means. Hand-written counts have drifted across documents — 23 entities in the [implementation plan](done/SEAD_V2_IMPLEMENTATION_PLAN.md), 61 in the [completeness proposal](done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md), 102 in [docs/TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md) today — and one accepted document claimed coverage of a table that exists in no schema source.

Recommendation: let each target model declare its own SEAD coverage source inside the model file, and add a CLI that reports model-to-SEAD coverage directly against that source — offline against the pinned ingestion snapshot, or live against a SEAD database. No separate coverage manifest: the model is the only source of truth, unmapped tables are reported as gaps, and gap triage stays in the existing candidates report.

This is the right time because the shared model is now the metadata boundary for `sead_change_request`, and more data kinds will bring more models, each covering a different subset of SEAD tables.

## Problem

### The completeness boundary is undefined, and it is not one boundary

Future imports will use several target models, one per kind of data. A table required by one dataset may be irrelevant to another, so completeness is a property of each model against its own SEAD surface — not of one global list. No document states which surface the shared model covers, so a missing table cannot be told apart from a deliberate omission.

The measurable state: counting the in-scope tables in [filtered_import_tables.csv](CHANGE_REQUEST_INGESTER/resources/filtered_import_tables.csv) against the model's `target_table` values gives 136 in-scope tables, 94 mapped, and 42 unmapped. That number has never appeared in a repository document.

### The model and its reference snapshot disagree in both directions

- 5 model entities target tables the snapshot never contained: `tbl_data_providers`, `tbl_submissions`, `tbl_submission_states`, `tbl_submission_tasks`, `tbl_submission_task_types`. These come from a proposed upstream DDL change ([REFACTOR_SEAD_SUBMISSION_METADATA.md](CHANGE_REQUEST_INGESTER/done/REFACTOR_SEAD_SUBMISSION_METADATA/REFACTOR_SEAD_SUBMISSION_METADATA.md)) that is not yet deployed.
- 2 model entities target tables the earlier review excluded from the snapshot: `tbl_colours` and `tbl_sample_colours`.

The schema dump (`docs/sead/01_tables.sql`, 137 tables) and the filtered snapshot (136 tables) agree on the 42-table gap set; they differ only on `tbl_colours` and `tbl_sample_colours` (in the dump, not the snapshot) and `tbl_feature_properties` (in the snapshot, not the dump).

### Nothing computes coverage

`TargetModelSpecValidator` checks internal consistency only. No test, script, or Makefile target loads the filtered snapshot or queries SEAD to compare against the model. The only target-model drift guard in `make lint` is the generated schema reference.

Recent history shows the cost. Commit `d677113b` disabled two entities and one column without updating the spec tests or the prose, and `tests/target_model` was red on `dev` until `9b3ca12f`. The accepted completeness proposal also states that `coordinate_system` is "modeled explicitly" and "kept in the shared superset"; the entity was added, disabled, and removed, and `tbl_coordinate_systems` exists in none of the three schema sources checked. The claim survived because no tool connected prose coverage claims to the model.

## Scope

- An optional `coverage` block in the target-model format: the SEAD source the model is measured against, plus provenance for that source.
- An optional per-entity `provenance` field for statements such as "targets pending submission DDL, not deployed".
- A CLI that reports model-to-SEAD coverage: mapped, unmapped, out-of-source, and duplicate target tables, offline against the pinned snapshot or live against a SEAD database.
- Replacing hand-written coverage counts in prose with the CLI command.

## Non-Goals

- A separate coverage manifest. It would duplicate what the model already states and add a second artifact to keep in sync.
- CI/CD workflow changes. Running tests on pull requests is worth doing but is separate work with its own decisions.
- A lint gate that fails on unmapped tables. Unmapped tables are known gaps during slice delivery, not errors.
- Fixing the 42 coverage gaps. This proposal measures them; the candidates report triages them.
- Reopening the metadata-boundary decision (target model versus `SeadSchema`). That decision stays closed.
- Changing the target-model format beyond additive optional fields.

## Current Behavior

Verified against the current tree on `dev`:

- The model loads to 102 entities; 101 declare a `target_table`; `abundance_element_group` declares none; no two entities share a `target_table`.
- The filtered snapshot contains 136 `tbl_*` tables, is committed to the repository, and carries `is_lookup` and `is_unknown` flags per table. Of the 42 unmapped tables, 30 are flagged lookups, 1 unknown, 11 neither.
- 7 model target tables sit outside the snapshot: the 5 submission tables plus `tbl_colours` and `tbl_sample_colours`.
- [docs/TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md) states the entity count by hand (currently 102, line 534).
- `make lint` runs `tidy`, `ruff`, `pylint`, `check-target-model-schema-reference`, and `check-doc-links`. No check loads the snapshot.
- `docs/TARGET_MODEL_SCHEMA_REFERENCE.md` is generated by `scripts/generate_target_model_schema_reference.py` with a `--check` mode. That generation pattern informs the CLI output here, but this proposal commits no generated report.
- `site` declares a foreign key to `site_type` with no `via`, but `tbl_sites` has no `site_type_id` column; the schema expresses the relationship through the `tbl_site_site_types` bridge, which has no entity.
- `sead_superset_model.yml` and `sead_standard_model.yml` currently declare identical `target_table` sets.

## Proposed Design

### 1. The model declares its own coverage source

Add an optional `coverage` block to the model metadata in the target-model YAML:

```yaml
model:
  name: SEAD Clearinghouse Extended
  version: 2.1.0
  coverage:
    source_kind: pinned-snapshot   # or: sead-database
    source: docs/proposals/CHANGE_REQUEST_INGESTER/resources/filtered_import_tables.csv
    provenance: >
      Filtered ingestion snapshot from the change-request ingester review;
      deployed SEAD ingestion schema as of the snapshot date.
```

- Each model declares its own source, so a future dating-domain model or specimen model pins its own SEAD surface without touching this one.
- `source_kind: sead-database` means measure against live SEAD introspection instead of a file.
- Models without a `coverage` block are legal and simply not measured.

### 2. Entities carry their own provenance

Add an optional `provenance: str` field to `EntitySpec`. The five submission entities use it to record that they target pending upstream DDL, keeping "modeled" distinguishable from "live" without a second file:

```yaml
  submission:
    target_table: tbl_submissions
    provenance: Pending upstream DDL (REFACTOR_SEAD_SUBMISSION_METADATA); not deployed.
```

### 3. A CLI reports model-to-SEAD coverage

Add `scripts/target_model_coverage.py`:

```
uv run python scripts/target_model_coverage.py resources/target_models/sead_standard_model.yml
```

It loads the model, reads its `coverage` block, and reports:

| Measure | Meaning |
|---|---|
| `in_scope` | Tables in the declared source |
| `mapped` | Source tables with a model entity |
| `unmapped` | Source tables with no entity, with the snapshot flags when present |
| `out_of_source` | Model `target_table` values absent from the source |
| `duplicates` | `target_table` values declared by two entities |

- Default exit code 0; `--strict` fails only on `out_of_source` or `duplicates`, never on `unmapped`.
- `--format md` writes the same report to stdout for linking from documents; nothing is committed.
- The comparison lives in `src/target_model/coverage.py`, is read-only, and loads no project.

### 4. Live SEAD mode

With `source_kind: sead-database` (or a CLI override), the CLI lists SEAD tables through read-only schema access and runs the same comparison. Offline snapshot mode stays the default so the check works without a database.

### 5. Gap triage stays in documents

The CLI reports unmapped tables; [TARGET_MODEL_MISSING_ENTITY_CANDIDATES_20261026.md](../../resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES_20261026.md) keeps the tiering and reasons (Tier 1 FK-referenced, Tier 2 data-capture, Tier 3 probably out of scope). Slice completion is measured by the unmapped count falling as entities are added. If a deliberate-exclusion record is later needed, it can be added to the `coverage` block then — no placeholder now.

### 6. Prose stops carrying counts

Replace the hand-written entity count in [docs/TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md) with the CLI command and a link to the candidates report.

## Alternatives Considered

**Separate coverage manifest with per-table dispositions.** Rejected. The model already states what it maps; a manifest adds a file to maintain and a second coverage question (manifest versus SEAD) on top of the real one (model versus SEAD).

**Keep completeness as prose.** Rejected. Three documents already disagree and one accepted document contains a false coverage claim.

**Pin the boundary to the live database only.** Rejected as the default. It makes every check depend on a running database; live mode is offered as an option instead.

**Treat the raw unfiltered snapshot (137+ tables) as the source.** Rejected. It re-admits the deprecated, derived, and image families the earlier review removed for stated reasons.

**Require every in-scope table to be modeled.** Rejected. Text blocks and operational lookups have no change-request mapping value, and per-dataset models make global completeness the wrong target.

## Risks And Tradeoffs

- **Unmapped tables stay a document judgement.** Without per-table dispositions in a manifest, "gap versus deliberate omission" lives in the candidates report rather than structured data. Accepted: the report already carries the tiering, and the snapshot flags give the CLI its grouping for free.
- **Snapshot drift.** The pinned snapshot ages against live SEAD. The `source_kind` label makes the age explicit, and live mode exists for verification.
- **First run reports violations.** The 5 pending submission tables and 2 colour tables are `out_of_source` today. `--strict` will fail until Open Questions Q1 and Q2 are answered; the default report mode is not blocked.
- **Two model files.** The superset and standard models currently duplicate the same tables. Whether both carry a `coverage` block is an open question, not a design dependency.

## Testing And Validation

- Unit tests for the coverage comparison with fixture model/source pairs: fully mapped, partially unmapped, out-of-source, duplicate target tables, and a model with no `coverage` block.
- A CLI test against the committed model and snapshot asserting the known counts: 136 in scope, 94 mapped, 42 unmapped, 7 out of source, 0 duplicates.
- A `--strict` test: fails on out-of-source, passes on unmapped.
- Live-mode test marked integration; skipped without a database.
- Existing suites stay green: `tests/target_model`, `tests/model/test_target_model_conformance.py`, `tests/validators/test_target_model_data_validators.py`, and the backend target-model tests.

## Acceptance Criteria

- `P-AC-1` The target-model format accepts an optional `coverage` block (`source_kind`, `source`, `provenance`) and an optional per-entity `provenance`; models without them load unchanged.
- `P-AC-2` The CLI reports `in_scope`, `mapped`, `unmapped`, `out_of_source`, and `duplicates` for the committed model against the pinned snapshot, matching 136 / 94 / 42 / 7 / 0.
- `P-AC-3` The CLI runs offline by default and read-only against a live SEAD database on request.
- `P-AC-4` `--strict` fails on out-of-source or duplicate target tables and passes on unmapped tables.
- `P-AC-5` The five pending submission entities carry `provenance` naming the pending DDL.
- `P-AC-6` Hand-written coverage counts in `docs/TARGET_MODEL_GUIDE.md` are replaced by the CLI command and a link to the candidates report.
- `P-AC-7` No new committed generated artifact; `make lint` and `make test` pass unchanged.

## Planning Handoff

Confirmed decisions:

- Coverage is measured model-to-SEAD, per model, using the source the model itself declares.
- No separate manifest, no committed generated report, no CI/CD work.
- Unmapped tables are reported gaps, triaged in the candidates report; they never fail the build.
- The target-model format changes only by additive optional fields.

Constraints to preserve:

- The comparison loads no project and no database in default mode.
- Entities without a `target_table` remain legal.
- Existing `tests/target_model` assertions stay the contract for currently modeled entities.

Open questions and where to resolve them:

| Question | Resolve by |
|---|---|
| Q1: Do the five pending submission entities keep their `target_table` with provenance, or move to a separate model until the upstream DDL deploys? | Format slice |
| Q2: Do `tbl_colours` and `tbl_sample_colours` stay in the model as accepted out-of-source additions, or move out? | Format slice |
| Q3: Does `site → site_type` become a `via` relationship through a `tbl_site_site_types` entity, or stay a direct foreign key? | Gap slices |
| Q4: Does `sead_superset_model.yml` keep its own `coverage` block, or should the two files be merged? | Format slice |
| Q5: Do deliberate exclusions eventually need a recorded disposition in the `coverage` block? | After the first gap slices land |

## Recommended Delivery Order

1. **Format slice.** `coverage` block and entity `provenance` in `src/target_model/models.py` and the spec validator; resolve Q1, Q2, Q4.
2. **Checker and CLI slice.** `src/target_model/coverage.py`, `scripts/target_model_coverage.py`, offline snapshot mode, `--strict`, tests.
3. **Live mode slice.** Read-only SEAD table listing and the same comparison; integration test.
4. **Docs slice.** Replace prose counts; add the CLI to `docs/DEVELOPMENT.md` and the guide.
5. **Gap slices** (from the candidates report tiers): site support, sample-group descriptions, analysis-entity extensions, taxonomy, dataset/reference bridges. Each is done when the CLI unmapped count falls.

## Open Questions

- Should `--strict` be wired into `make lint` once Q1 and Q2 are settled, or stay a manual/release-time check?
- Should the CLI emit JSON for later tooling (dashboards, CI) even though no consumer exists yet?

## Final Recommendation

Let each model name its own SEAD source, put provenance in the model itself, and compute coverage with a CLI that compares the model to SEAD — offline against the pinned snapshot, live on request. This answers the completeness question with one artifact (the model) and one tool, and avoids the maintenance burden of a parallel manifest that would itself need a coverage check.
