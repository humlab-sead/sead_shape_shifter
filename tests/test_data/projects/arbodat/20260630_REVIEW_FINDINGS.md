# Arbodat Shape Shifter Review

Reviewed file: `tests/test_data/projects/arbodat/shapeshifter.yml`

## Validation Status

- Command run: `rtk uv run python scripts/validate_project.py tests/test_data/projects/arbodat/shapeshifter.yml --workflow all --log-level ERROR`
- Result: validation completed with conformance errors and data warnings.

## Findings

### High

1. `entities.analysis_entity` and downstream `entities.dataset`
   - Path: `entities.analysis_entity` and `entities.dataset`
   - Rule violated: `MISSING_REQUIRED_FOREIGN_KEY_TARGET`, `MISSING_REQUIRED_COLUMN`, `APPEND_MISSING_REQUIRED_COLUMN`
   - Evidence: `analysis_entity` is defined at line 230 and `dataset` at line 383. `analysis_entity` has no foreign key to `dataset`, no `dataset_id` target column, and both append branches omit `physical_sample_id` even though `sample` exposes `public_id: physical_sample_id` at line 897.
   - Impact: the analysis entity chain does not satisfy target-model requirements, so downstream dataset and sample linkage cannot be exported correctly.
   - Smallest safe fix: add the required dataset relationship and ensure `analysis_entity` carries the target columns required by the target model, including `dataset_id`; update both append branches so the assembled rows include `physical_sample_id`.

2. `entities.abundance`, `entities.taxa`, and `entities.ecocode`
   - Path: `entities.abundance`, `entities.taxa`, `entities.ecocode`
   - Rule violated: `MISSING_REQUIRED_FOREIGN_KEY_TARGET`, `MISSING_INDUCED_REQUIRED_ENTITY`
   - Evidence: `abundance` starts at line 9, `taxa` at line 1329, and `ecocode` at line 1656. The project defines `taxa`, but there is no `taxa_tree_master` entity anywhere in the file, and neither `abundance` nor `ecocode` reaches that required lookup chain.
   - Impact: taxon-bearing facts cannot satisfy the target model's required taxonomy parent path.
   - Smallest safe fix: add or map a `taxa_tree_master` entity and link `taxa` to it, then let `abundance` and `ecocode` reach the required lookup through `taxa`.

3. Property-style fact entities use project-specific lookup entities instead of the required generic property lookup.
   - Path: `entities.abundance_property`, `entities.feature_property`, `entities.site_property`
   - Rule violated: `MISSING_REQUIRED_FOREIGN_KEY_TARGET`, `MISSING_INDUCED_REQUIRED_ENTITY`, `ORPHAN_FACT_ENTITY`
   - Evidence: `abundance_property` starts at line 153 and links to `abundance_property_type`; `feature_property` starts at line 646 and links to `feature_property_type`; `site_property` starts at line 1207 and links to `site_property_type`. There is no `property_type` entity in the file.
   - Impact: these fact tables do not terminate in the required classifier entity, and `abundance_property` is explicitly flagged as an orphan fact entity by the validator.
   - Smallest safe fix: introduce or map the generic `property_type` entity expected by the target model, then point property facts at that target or add a bridging lookup that reaches it.

### Medium

4. `entities.abundance_ident_level` does not expose the required parent target column.
   - Path: `entities.abundance_ident_level`
   - Rule violated: `MISSING_REQUIRED_FOREIGN_KEY_TARGET`, `MISSING_REQUIRED_COLUMN`
   - Evidence: the entity starts at line 1559 with `columns: [analysis_entity_id, cf]` and only links to `identification_level`. The validator expects the target column `abundance_id`, not `analysis_entity_id`.
   - Impact: identification-level rows cannot be tied back to the abundance fact required by the target model.
   - Smallest safe fix: source this entity from `abundance` or otherwise carry `abundance_id`, and add the required FK path back to the abundance fact.

5. `entities.coordinate_system` uses source-shaped columns instead of the required target column name.
   - Path: `entities.coordinate_system`
   - Rule violated: `MISSING_REQUIRED_COLUMN`
   - Evidence: the entity starts at line 363 with `columns: [Index, Koordsys, Bemerkung]`, while the validator requires target column `coordinate_system`.
   - Impact: the lookup exists, but the exported target-model field name is missing.
   - Smallest safe fix: add or derive the target column `coordinate_system`, likely from `Koordsys`, while preserving the original source field if still needed.

6. `entities.feature_property` and `entities.site_property` do not expose the required target-model value columns.
   - Path: `entities.feature_property`, `entities.site_property`
   - Rule violated: `MISSING_REQUIRED_COLUMN`
   - Evidence: `feature_property` un-nests to `feature_property_value` at line 666, and `site_property` un-nests to `site_property_value` at line 1233. The validator still requires generic target columns `property_type_id` and `property_value` for these entities.
   - Impact: the current entity-specific naming does not satisfy the target model's expected property schema.
   - Smallest safe fix: normalize these entities to the generic property contract by exposing `property_type_id` and `property_value`, either directly or through a bridging transform.

### Low

7. Runtime data warnings remain even after structural fixes.
   - Path: `entities.dating`, `entities.dating_chronological_period`, `entities.relative_dating`, `entities.site_natural_region`
   - Rule violated: `EMPTY_RESULT`, `FK_DATA_INTEGRITY`
   - Evidence: the validator reported empty results for `dating`, `dating_chronological_period`, and `site_natural_region`, plus five unmatched `relative_dating` values against `relative_ages`: `Meso`, `NZ`, `La`, `BZ`, `Meso2`.
   - Impact: these do not necessarily block configuration loading, but they indicate sparse output or lookup drift in the current source data.
   - Smallest safe fix: confirm whether empty outputs are expected for the fixture dataset; if not, widen the source query or repair the lookup coverage in `relative_ages`.

## Overall Assessment

- Structural YAML validity: passed.
- Entity-type contract checks: passed for the reviewed slices used by the validator.
- Identity model: no obvious `system_id` misuse was reported by validation.
- Main failure mode: target-model conformance gaps in dataset, taxonomy, and generic property lookup chains.

## Remaining Risks And Assumptions

- This review assumes the target model referenced by `@load: sead_superset_model.yml` is the intended contract.
- `@load:materialized/*.parquet` snapshots were treated as frozen state and not re-validated as raw source extraction.
- Some required fixes may be better implemented by adding bridging entities rather than renaming existing project-specific entities.