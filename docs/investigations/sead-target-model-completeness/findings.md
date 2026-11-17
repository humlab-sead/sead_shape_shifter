# Findings: SEAD standard target model completeness status

**Status: CLOSED 2026-11-10.** The authoritative current-state record now lives in
`resources/target_models/README.md` (with the gap triage in
`TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md`). This file records how the
investigation resolved; consult the README for the living status.

## Executive completeness statement

Measured against the declared source of truth — `columns.csv`, a run of
`exported-columns.sql` against `sead_staging` (maintainer decision, 2026-11-10):

| Measure | Raw | Effective (after declared exclusions) |
|---|---|---|
| Source tables | 156 | 150 |
| Mapped by a model entity | 101 | 99 |
| Unmapped (candidate gaps) | 55 | **51** |
| Model `target_table` absent from source | 0 | **0** |

Model: 102 entities, 101 with a `target_table` (`abundance_element_group` has
none), no duplicates, no disabled entities. Verified locally 2026-11-10 with
PyYAML against `sead_standard_model.yml` v2.1.0 and `columns.csv`.

Declared exclusions (never counted as gaps):

- Export-query filters: `tbl_aggregate*`, `tbl_mcr%`, `tbl_tephra%`,
  `tbl_isotope%`, `tbl_updates_log` — pending deprecation or unused.
- Maintainer decision: all `%colours` / `%images` tables (6 in the export).

## Resolution of the 42-vs-55 discrepancy

Fully explained by surface definitions, table by table:

- The 42-gap list (2026-10-26) used the 137-table schema dump
  (`docs/sead/01_tables.sql`). Correct on that surface.
- The 55-unmapped result (2026-11-10) used the raw 156-table `sead_staging`
  export. Correct on that surface.
- The effective recount is 51: 42 of the original triage tables remain unmapped,
  and 9 are new because `sead_staging` includes subsystem tables the dump omits —
  `tbl_ceramics`, `tbl_ceramics_lookup`, `tbl_ceramics_measurements`, `tbl_dendro`,
  `tbl_dendro_dates`, `tbl_dendro_date_notes`, `tbl_dendro_lookup`,
  `tbl_image_types`, `tbl_property_type_groups`. All 9 are listed as Tier-3-style
  scope decisions in the candidates report.
- The 4 tables the candidates report flagged as reverse-direction (model targets
  absent from the dump: five submission tables and `tbl_feature_properties`) are
  all present in `columns.csv`: 0 out-of-source. The dump predates them.

## Ledger of document counts

| Count | Correct on which surface |
|---|---|
| 23, 61 | Historical milestones in archived proposals; superseded |
| 42 unmapped | 137-table schema dump, 2026-10-26 |
| 94 mapped / 42 unmapped / 7 out-of-source | 136-table filtered snapshot (proposal-era; out-of-source claim now stale) |
| 101 mapped / 55 unmapped | raw 156-table export |
| 99 mapped / 51 unmapped / 0 out-of-source | **effective surface — the authoritative number** |
| 102 entities / 101 target tables | model YAML itself |

## Hypothesis outcomes

- **H1 (surface drift): CONFIRMED.** The 42→51 difference is surface width, not
  model regression; the 9 new tables are ceramics/dendro subsystem tables plus two
  classifiers.
- **H2 (stale pending-DDL claims): CONFIRMED.** The five submission tables are
  live (maintainer, 2026-11-10); proposal-era "not deployed" claims are stale.
  Deploying Sqitch CR not recorded — minor evidence gap, not blocking.
- **H3 (structural defects): OPEN, carried forward as known model defects.**
  `site.site_type_id` (no such column in `tbl_sites`; real bridge is
  `tbl_site_site_types`, unmapped) and the seven qualifier-family FKs remain
  unfixed. Recorded in README "Known model defects" and in the candidates-report
  next steps. Fixing them is model-edit work requiring separate approval.
- **H4 (export not clean): SUPERSEDED by decision.** `columns.csv` /
  `sead_staging` is the declared source of truth; filter-excluded tables are of
  no interest.

## Disposition

- Authoritative status: `resources/target_models/README.md`.
- Gap queue: `resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md`
  (recounted 2026-11-10; Tier 1 list unchanged and still the priority queue).
- Follow-up work needing approval: Tier-1 entity additions, `site`/`site_type`
  bridge fix, qualifier FK fix, colour-entity disposition, and the
  coverage-boundary proposal (#532), which should now encode `columns.csv` /
  `sead_staging` as its declared `coverage.source`.
- Evidence: `columns.csv` and `exported-columns.sql` archived in this folder.
