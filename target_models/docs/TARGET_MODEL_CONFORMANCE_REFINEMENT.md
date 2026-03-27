# Target Model Conformance Refinement

This note records the first standalone conformance-validator findings from the Phase 4 fixture corpus.

It exists to separate low-noise rules that are safe to keep from heuristic checks that need more evidence before backend integration.

## Corpus Used

- `target_models/examples/sead_arbodat_core.yml`
- `target_models/examples/sead_missing_sample_group.yml`

Both were validated against `target_models/specs/sead_v2.yml` using the standalone `TargetModelConformanceValidator`.

## Current Stable Findings

These findings are considered low-noise based on the current corpus and can remain in the standalone validator.

### Stable entity-level checks

- Missing required entity
- Unexpected `public_id`
- Missing required foreign-key target by entity name

### Stable target-facing column checks

These are reliable when the project expresses the target-facing column explicitly enough that the validator can see it without guessing.

- Direct presence in `columns`
- Direct presence in `keys`
- Direct presence in `extra_columns`
- Presence implied by `public_id`
- Presence implied by `unnest.var_name` or `unnest.value_name`
- Presence implied by a required foreign key whose target declares `public_id`

## Observed Findings

### `sead_arbodat_core.yml`

- `sample_type` is missing required target-facing column `type_name`
- `method` is missing required target-facing column `method_group_id`
- `analysis_entity` is missing required foreign-key target `dataset`
- `analysis_entity` is missing required target-facing column `dataset_id`

### `sead_missing_sample_group.yml`

- `site` is missing required foreign-key target `location`
- `sample_group` is missing entirely
- `sample` uses unexpected `public_id` `sample_id` instead of `physical_sample_id`
- `sample` is missing required foreign-key target `sample_group`
- `sample` is missing required target-facing column `sample_group_id`
- `sample_type` is missing required target-facing column `type_name`
- `method` is missing required target-facing column `method_group_id`
- `analysis_entity` is missing required foreign-key target `dataset`
- `analysis_entity` is missing required target-facing column `dataset_id`

## Ambiguous Cases And Deferred Heuristics

The following cases are real mismatches between the current Arbodat-derived fixture and the SEAD target model, but they are not yet good candidates for more aggressive inference rules.

### Alias-like target naming mismatches

- `sample_type` currently exposes `sample_type_name` in `extra_columns`, while the target model expects `type_name`
- `method` currently exposes `sead_method_group_id` in `columns`, while the target model expects `method_group_id`

These may be genuine conformance failures, but the validator should not silently treat them as equivalent yet. Doing so would require explicit alias rules or target-model metadata for acceptable project-side source names.

### Transitive relationship expectations

The current validator only checks required foreign-key targets explicitly declared on the project entity. It does not infer that an entity is effectively linked through some longer path.

This is intentional for now. Inferring transitive conformance would increase false positives and make failure explanations harder to trust.

## Minimal Safe Rule Set For Future Integration

If a subset of the standalone validator is later integrated into backend validation, the safe minimum rule set is:

- Required entities from the target model
- Exact `public_id` expectation when the target model declares one
- Required foreign-key targets by direct entity reference only
- Required target-facing columns only when they are explicit or safely inferable from current standalone rules

## Not Yet Safe For Integration

- Alias matching such as `sample_type_name -> type_name`
- Semantic normalization such as `sead_method_group_id -> method_group_id`
- Transitive FK satisfaction
- Value-level checks requiring execution of the Shape Shifter pipeline
- Any rule that depends on interpreting `@value:` expressions rather than reading direct structure