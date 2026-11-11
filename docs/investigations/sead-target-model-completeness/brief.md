# Investigation brief: SEAD standard target model completeness status against the live column export

> **Status: CLOSED 2026-11-10.** Resolutions are in [findings.md](findings.md); the
> authoritative current-state record now lives in
> [`resources/target_models/README.md`](../../../resources/target_models/README.md).

> This brief defines an investigation contract. It assesses whether `resources/target_models/sead_standard_model.yml` can be called "nearly complete", against which SEAD surface, and where model claims and schema evidence disagree. It is not an implementation plan.

## Objective

Establish, with computed evidence, the current completeness status of the SEAD standard target model (`sead_standard_model.yml`, version 2.1.0) against `columns.csv` — the declared source of truth, a current run of `exported-columns.sql` against `sead_staging` — and produce a defensible completeness statement that replaces the drifting hand-written counts in the proposal documents.

Specifically, the investigation should establish:

1. The authoritative unmapped-table list against the column export, and how it reconciles with the 42-gap list in `resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md` (which used a 137-table schema dump, not this 156-table export).
2. ~~Whether the "pending DDL" claim for the five submission tables is still true.~~ **Resolved (2026-11-10):** the five submission tables are live in the database (confirmed by the maintainer), so the proposal-era "not yet deployed" claims are stale and the model's five submission entities target real tables. Remaining check: whether the deployed column shapes match the proposed DDL. (The former colour-exclusion dispute is likewise closed by decision: `tbl_colours` / `tbl_sample_colours` are excluded from the completeness surface, along with all `%images` tables; see the exclusion rule below.)
3. Whether the verified structural defects (a `site.site_type_id` column that does not exist in `tbl_sites`; seven foreign keys whose implied column name is absent from the target table — six analysis-value/range qualifier FKs plus `value_qualifier_symbol` → `value_qualifier`) are model errors, format limitations, stale model, or export artifacts.
4. Whether the pending coverage-boundary proposal is implemented at all, and what the smallest verified completeness check would be in the meantime.

**Mode:** Investigation only. Remediation (model edits, new entities, format changes, script implementation) requires separate approval.

## Issue description

**Observed behavior:** Multiple repository documents make different completeness claims about the same model, and a direct comparison of the model against the exported column list produces numbers that appear in none of them.

Verified locally on 2026-11-10 against the current tree:

- The model declares 102 entities; 101 declare a `target_table`; `abundance_element_group` declares none; no duplicates; no disabled entities.
- `columns.csv` contains 156 distinct `tbl_*` tables (756 column rows).
- 101 of 156 export tables are mapped; 55 are unmapped; 0 model `target_table` values are absent from the export. Applying the declared `%colours` / `%images` exclusion (6 tables, 2 of them mapped), the effective surface is 150 tables: 99 mapped, 51 unmapped, 0 out-of-source.
- The five submission tables (`tbl_submissions`, `tbl_submission_states`, `tbl_submission_tasks`, `tbl_submission_task_types`, `tbl_data_providers`) and `tbl_colours` / `tbl_sample_colours` are all present in the export.
- **Confirmed live (2026-11-10, maintainer):** the five submission tables exist in the live database. All five are also mapped by model entities (`data_provider`, `submission_state`, `submission`, `submission_task_type`, `submission_task` in `sead_standard_model.yml`), so the "pending DDL" / out-of-source claims in the proposal documents are stale.
- **Declared source of truth (2026-11-10, maintainer):** `columns.csv` is the current source of truth for the completeness surface, produced by `exported-columns.sql` against `sead_staging`. Tables removed by the query filters (aggregate, mcr, tephra, isotope prefixes and `tbl_updates_log`) are tables of no interest to the standard target model — pending deprecation or unused — and are never counted as gaps.
- **Declared exclusion (2026-11-10):** tables ending in `colours` or `images` are excluded from the completeness surface. Six export tables match — `tbl_colours`, `tbl_sample_colours`, `tbl_sample_group_images`, `tbl_sample_images`, `tbl_site_images`, `tbl_taxa_images` — so the effective surface is 150 tables: 99 mapped (the model's `colour` and `sample_colour` entities fall out of the mapped set), 51 unmapped, 0 out-of-source.
- `sead_superset_model.yml` is a symlink to `sead_standard_model.yml`, so the two "models" are now one file.
- No `scripts/target_model_coverage.py` and no `src/target_model/coverage.py` exist; the coverage-boundary proposal's CLI is not implemented.

**Expected behavior / invariant:** Per [SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md](../../proposals/SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md), "complete" should be a computed result against a declared source, prose documents should not carry hand-written counts, and every model `target_table` should exist in the declared schema source. Per the accepted completeness proposal, the shared model should be a near-complete, provider-independent SEAD surface with deliberate omissions recorded explicitly.

**Impact:**
- Possible (observed pattern, recurring): prose coverage claims continue to diverge from the model; the earlier `coordinate_system` claim (documented as "modeled explicitly" after removal) shows the failure mode is real.
- Observed: two accepted documents and one dated candidates report disagree on gap counts (42 vs 55) and on whether submission/colour tables exist; a downstream consumer cannot tell a deliberate omission from a gap.
- Observed pattern: at least one live project (arbodat-rebecka) declares `site_type_id` and the `site` → `site_type` relationship that the schema does not support; conformance or materialization work built on that relationship or the analysis-value qualifier FKs would target columns that do not exist. Extent across other projects to be enumerated.

**Known evidence and timeline:**

| Observation or artifact | Source / location | Date or version | Status / qualification |
| --- | --- | --- | --- |
| Model: 102 entities, 101 target tables, 0 duplicates | `resources/target_models/sead_standard_model.yml` | model version 2.1.0, checked 2026-11-10 | Verified locally |
| Export: 156 `tbl_*` tables; with the declared `%colours` / `%images` exclusion, 150 effective (99 mapped, 51 unmapped, 0 out-of-source) | `columns.csv` (archived in this brief's folder; originally `tmp/columns.csv`) | declared source of truth: current run of `exported-columns.sql` against `sead_staging` (maintainer, 2026-11-10) | Verified locally; generated by a filtered query over `sead_utility.table_columns` that excludes `date_updated` columns and the `tbl_aggregate*`, `tbl_mcr%`, `tbl_tephra%`, `tbl_isotope%`, and `tbl_updates_log` tables, so the 156-table surface is a curated subset by design: the filter-excluded tables are pending deprecation or unused and out of scope |
| 42 unmapped tables against a 137-table schema dump | `resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md` | 2026-10-26 | Verified as a document claim; based on `docs/sead/01_tables.sql`, a different surface |
| 136 in-scope tables, 94 mapped, 42 unmapped; 7 out-of-source target tables | `docs/proposals/SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md` | proposal, current branch | Document claim; its snapshot surface (`filtered_import_tables.csv`) differs from `columns.csv` |
| Submission + colour tables "not deployed" / "excluded" | same proposal; `SEAD_V2_TARGET_MODEL_COMPLETENESS.md` | proposal-era | Submission tables: **stale** — confirmed live (maintainer, 2026-11-10) and present in `columns.csv`. Colour tables: resolved by decision — excluded from the completeness surface with all `%colours` / `%images` tables |
| `site` declares `site_type_id`; `tbl_sites` has no such column | model YAML vs `columns.csv`; also flagged in the 2026-10-26 candidates report | 2026-11-10 | Verified locally |
| Seven model FKs imply a column absent from the target table: six analysis-value/range entities (real column is text `qualifier` / `low_qualifier` / `high_qualifier` referencing `tbl_value_qualifier_symbols.symbol`) plus `value_qualifier_symbol` → `value_qualifier` (real column `cardinal_qualifier_id`) | model YAML vs `columns.csv`; `tbl_analysis_integer_values_qualifier_fkey` in `docs/sead/05_constraints.sql` ~L1965 | 2026-11-10 | Verified locally |
| arbodat-rebecka project YAML declares `site_type_id` and an FK to `site_type` | `data/projects/arbodat-rebecka/shapeshifter.yml` ~L955/L991 | checked 2026-11-10 | Verified locally; live dependency on the defective `site` → `site_type` relationship |
| Coverage CLI not implemented | absence of `scripts/target_model_coverage.py`, `src/target_model/coverage.py` | 2026-11-10 | Verified locally |
| Hand-written counts 23 / 61 / 102 across documents | `SEAD_V2_IMPLEMENTATION_PLAN.md`, `SEAD_V2_TARGET_MODEL_COMPLETENESS.md`, `docs/TARGET_MODEL_GUIDE.md` | various | Verified as document claims; drift acknowledged in the proposal |

**Conflicting evidence to resolve, not average:** the 42-gap list and the 55-unmapped result are both correct on their own surfaces. The surfaces are: schema dump (137 tables), filtered import snapshot (136 tables), and `columns.csv` (156 tables raw, 150 after the declared `%colours` / `%images` exclusion). That decision is now made (maintainer, 2026-11-10): `columns.csv` — a current run of `exported-columns.sql` against `sead_staging` — is the declared source of truth; the schema dump and filtered snapshot remain only as historical context for explaining earlier counts.

## Working hypotheses

- **H1 (surface drift, not model regression):** the 42 → 55 gap difference is explained by `columns.csv` covering a wider live surface (156 raw, 150 after the declared `%colours` / `%images` exclusion) that includes subsystem and operational tables (e.g. `tbl_ceramics*`, `tbl_dendro*`, `tbl_lithology`, `tbl_imported_taxa_replacements`) outside the filtered clearinghouse scope. Check: set-difference the three surfaces table by table and classify each additional unmapped table (the unmapped-set difference between the export and the 42-gap list, count to be computed) by Sqitch project ownership in `sead_change_control/projects.txt` and the FK references in the candidates report.
- **H2 (stale pending-DDL claims): CONFIRMED (2026-11-10).** The five submission tables are live (maintainer confirmation), so the proposal's "not yet deployed" and out-of-source findings are stale. Remaining check: compare `columns.csv` submission-table columns against the proposed DDL in `REFACTOR_SEAD_SUBMISSION_METADATA` to confirm the deployed shape matches the design. The export's provenance is now declared: `columns.csv` is a current run against `sead_staging` (2026-11-10).
- **H3 (modeling errors or format limitations, not gaps):** `site.site_type_id` and the seven qualifier-family FKs are authoring mistakes — or a target-model format limitation, since the FK format may not express a column name other than the referenced entity's `public_id` — while the schema expresses these relationships via the `tbl_site_site_types` bridge and text qualifier columns respectively. Check: read the FK definitions in `docs/sead/05_constraints.sql` (or live introspection) for `tbl_sites`, `tbl_analysis_integer_values`, and `tbl_analysis_dating_ranges`; check whether the FK format supports a `via`/`column` attribute for non-`public_id` FK columns; confirm `TargetModelSpecValidator` does not currently detect declared-column-vs-schema mismatches (it validates internal consistency only, per the proposal — verify).
- **H4 (alternative: the export is not a clean SEAD-core surface): SUPERSEDED by decision (2026-11-10).** The maintainer declared `columns.csv` the current source of truth, run against `sead_staging`. The query filters are deliberate: the dropped tables (aggregate, mcr, tephra, isotope, updates log) are pending deprecation or unused and are tables of no interest to the standard target model. The 42-vs-55 reconciliation remains as an explanation task, not a challenge to the export's authority.

## System context

Shape Shifter validates project YAML against a shared SEAD target model. The model file declares entities with `target_table`, `public_id`, `columns`, `unique_sets`, and `foreign_keys`. `TargetModelSpecValidator` (`src/target_model/spec_validator.py`) checks internal consistency; `src/target_model/conformance.py` checks project-versus-model conformance. Neither compares the model to a live or pinned SEAD schema — that gap is what the coverage-boundary proposal (#532) proposes to close with a `coverage` block and `scripts/target_model_coverage.py`, currently unimplemented.

Delivery history: the SEAD v2 plan (Milestones 1–3 complete) and the completeness proposal (Issues 1–7, all implemented) built the model to its current 102-entity surface; both are archived under `docs/proposals/done/`. The coverage-boundary proposal is the live pending decision on how completeness is defined and measured.

**Relevant entry points:**

- `resources/target_models/sead_standard_model.yml` (model under review; `sead_superset_model.yml` is a symlink to it)
- `columns.csv` (declared source of truth: current run of `exported-columns.sql` against `sead_staging`)
- `resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md`, `TARGET_MODEL_CONDITIONAL_CANDIDATES.md`, `TARGET_MODEL_REVIEW.md` (prior gap triage)
- `docs/proposals/SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md` and issue #532 (pending coverage design)
- `docs/proposals/CHANGE_REQUEST_INGESTER/resources/filtered_import_tables.csv` (the 136-table snapshot with `is_lookup` / `is_unknown` flags)
- `docs/sead/01_tables.sql`, `docs/sead/05_constraints.sql` (pinned 137-table schema dump)
- `src/target_model/spec_validator.py`, `src/target_model/models.py` (what is and is not validated today)
- `sead_change_control/projects.txt` and per-project deploy SQL (to attribute unmapped tables to owning Sqitch projects)
- Read-only live SEAD access: Postgres MCP server, or `bin/psql.sh` from `sead_change_control` (never write)

**Environment and baseline:** branch `add-copy-project-script` in `sead_shape_shifter`; model version 2.1.0; Python via root `.venv/`. Known-good reference surfaces: the 2026-10-26 candidates report and the 136-table filtered snapshot. `columns.csv` is the **declared source of truth**: a current run of `exported-columns.sql` against `sead_staging` (maintainer, 2026-11-10).

## Investigation priorities

### 1. Establish the authoritative surfaces and their diffs

- Compute the three table surfaces (schema dump 137, filtered snapshot 136, `columns.csv` 156 raw / 150 after the declared `%colours` / `%images` exclusion) and produce the pairwise diffs with table names, reporting each diff both raw and post-exclusion.
- For each of the 51 unmapped tables in the effective export surface, classify: in/out of the filtered snapshot, `is_lookup` / `is_unknown` flag, FK-referenced-by-modeled-entity (Tier 1 in the candidates report), and owning Sqitch project.
- Account for the `exported-columns.sql` exclusions when diffing surfaces: tables excluded by the query filters (`tbl_aggregate*`, `tbl_mcr%`, `tbl_tephra%`, `tbl_isotope%`, `tbl_updates_log`) and by the declared `%colours` / `%images` rule are declared tables of no interest (pending deprecation or unused), not model gaps, and the dropped `date_updated` column means column-level model-to-export comparisons are incomplete by construction.
- Re-run `exported-columns.sql` read-only against `sead_staging` to confirm `columns.csv` still matches current staging, and use that run to confirm or correct the locally computed 99/51/0 numbers (101/55/0 raw).

### 2. Close out the provenance claims

- Deployment of the submission DDL is confirmed (maintainer, 2026-11-10): the five tables are live. Narrowed check: compare the deployed column shapes (live database read-only, or `columns.csv` once its provenance is verified) against the proposed DDL in `docs/proposals/CHANGE_REQUEST_INGESTER/done/REFACTOR_SEAD_SUBMISSION_METADATA/`, and record which Sqitch CR deployed them for dated evidence.
- The colour tables are excluded from the completeness surface by decision (2026-11-10); report their live-database status only as context, not as an open dispute.
- Export provenance is declared (maintainer, 2026-11-10): `columns.csv` is a current run of `exported-columns.sql` against `sead_staging`. findings.md should restate this as the declared source and record the Priority-1 re-run as the freshness confirmation.

### 3. Characterize the structural defects

- Verify against schema constraints that `tbl_sites` has no `site_type_id` and that `tbl_site_site_types` is the intended bridge; check whether any Shape Shifter project YAML currently relies on the `site` → `site_type` FK as declared.
- Verify the actual qualifier column shape in `tbl_analysis_*_values` / `_ranges` tables and determine whether the seven model FKs are misdeclared or format-limited: the six analysis-value/range entities reference `value_qualifier_symbol` but their real FK column is the text `qualifier` / `low_qualifier` / `high_qualifier` (not `qualifier_symbol_id`), and `value_qualifier_symbol` → `value_qualifier` has the real column `cardinal_qualifier_id` (not bare `qualifier_id`). Note `value_qualifier_symbol.public_id: qualifier_symbol_id` is itself correct and its PK exists in the schema dump — do not re-check that claim.
- Check whether `TargetModelSpecValidator` or any test would have caught these; if not, record the missing check as a prevention finding.

### 4. Assess completeness status and remediation options (report only)

- State the mapped/unmapped counts per surface, with the declared-surface question framed as the decision the coverage-boundary proposal must answer, noting that `columns.csv` (the `sead_staging` run) is now the declared source of truth, so the proposal's remaining question is how to encode it as `coverage.source` (pinned snapshot vs live query).
- Propose, without implementing: the smallest interim check that would have caught the `coordinate_system`-class drift (e.g. a model-vs-snapshot script or test), and how it relates to the pending proposal's CLI so the investigation does not pre-empt or duplicate that design.
- List the Tier-1 FK-dangling candidates from the 2026-10-26 report that are still unmapped, as the prioritized gap queue a follow-up model change would use.

## Scope and constraints

**In scope:** the three schema surfaces above; the unmapped export tables after the declared `%colours` / `%images` exclusion (51 tables); the deployed-shape check for the five (confirmed-live) submission tables; the `site.site_type_id` and qualifier FK defects; the implemented/unimplemented status of the coverage-boundary proposal; documentation count drift.

**Declared exclusion:** tables whose names end in `colours` or `images` are excluded from the completeness surface and are never counted as model gaps. Matching export tables: `tbl_colours`, `tbl_sample_colours`, `tbl_sample_group_images`, `tbl_sample_images`, `tbl_site_images`, `tbl_taxa_images`. The model's `colour` and `sample_colour` entities remain in the model file; whether they should be removed or marked explicitly excluded is a follow-up question for the coverage-boundary proposal (see deliverable 7). The tables dropped by the `exported-columns.sql` filters (the aggregate, mcr, tephra, and isotope prefixes, plus `tbl_updates_log`) are likewise declared out of scope (2026-11-10): pending deprecation or unused, and never counted as gaps.

**Secondary scope (only if findings justify):** whether `abundance_element_group` needs a `target_table` or an explicit no-table declaration; whether the symlinked superset model should be retired; whether `docs/TARGET_MODEL_GUIDE.md` counts should be replaced by the future CLI output.

**Out of scope:** adding or fixing entities in the model; implementing the coverage CLI or `coverage` block; CI/CD changes; the metadata-boundary decision (target model vs `SeadSchema`), which stays closed; project YAML changes; anything in `sead_change_control` beyond read-only attribution of unmapped tables to projects.

**Permissions / safety:** read-only by default. Live SEAD access via the Postgres MCP server or `bin/psql.sh` with the read-only role only — never write to the database. No model edits, no commits, no migrations, no deployment. `columns.csv` is the declared source of truth (`sead_staging`, current as of 2026-11-10); re-verify against `sead_staging` read-only only where a finding hinges on a specific column shape.

## Expected deliverables

Produce `docs/investigations/sead-target-model-completeness/findings.md` containing:

1. Executive completeness statement: mapped/unmapped/out-of-source counts per surface, with the declared source of truth (`columns.csv`, `sead_staging`) as the primary measure.
2. Surface-diff tables (137 vs 136 vs 156 raw / 150 effective) and the classified 51-table unmapped list, with the `%colours` / `%images` exclusions applied and listed.
3. Resolution of the five submission-table provenance claims — deployment confirmed live (maintainer), extended with dated evidence (deploying Sqitch CR) and a deployed-shape-vs-proposed-DDL comparison — plus a note on the excluded colour/image tables.
4. Root-cause assessment for the `site.site_type_id` and qualifier FK defects: confirmed model error, schema drift, or export artifact — with exact files/lines and constraint evidence.
5. Verified-vs-hypothesis ledger, including which document counts (23 / 42 / 55 / 61 / 94 / 101 / 102) are correct on which surface.
6. Remediation alternatives with risks: interim minimal check vs waiting for the #532 CLI; prioritized Tier-1 gap queue. Do not implement any of them in this phase.
7. Open questions for the coverage-boundary proposal (how to encode `coverage.source`: pinned snapshot vs live query; treatment of subsystem tables). The declared-source question is answered: `columns.csv` against `sead_staging`.

## Completion criteria

- Every count in the findings report is reproducible from a named artifact or a documented read-only query; no count is copied from prose.
- The 42-vs-55 discrepancy is fully explained by surface definitions, table by table.
- Each of the five submission tables and the two structural defects has a confirmed status (deployed/undeployed, error/valid) or an explicit evidence gap. The five submission tables are confirmed deployed (maintainer, 2026-11-10); the findings must still record the deploying CR and the shape comparison.
- The findings adopt the declared source of truth (`columns.csv` against `sead_staging`) and state how the coverage-boundary proposal should encode it (snapshot vs live), without changing the model or the proposal.

## References

- Model: `resources/target_models/sead_standard_model.yml` (v2.1.0)
- Export: `columns.csv`, produced by the query in `exported-columns.sql` — both archived in this brief's folder; declared source of truth, run against `sead_staging` (maintainer, 2026-11-10)
- Pending proposal: `docs/proposals/SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md`, issue [#532](https://github.com/humlab-sead/sead_shape_shifter/issues/532)
- Completed work: `docs/proposals/done/SEAD_V2_IMPLEMENTATION_PLAN.md`, `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`, `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md` (issues #447–#453)
- Gap triage: `resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md`, `TARGET_MODEL_CONDITIONAL_CANDIDATES.md`
- Schema sources: `docs/sead/01_tables.sql`, `docs/sead/05_constraints.sql`, `docs/proposals/CHANGE_REQUEST_INGESTER/resources/filtered_import_tables.csv`
- Validator: `src/target_model/spec_validator.py`; guide: `docs/TARGET_MODEL_GUIDE.md`
