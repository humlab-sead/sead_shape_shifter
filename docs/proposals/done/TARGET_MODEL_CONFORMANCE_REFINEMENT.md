# Target Model Conformance Refinement

This note records the first standalone conformance-validator findings from the Phase 4 fixture corpus.

It exists to separate low-noise rules that are safe to keep from heuristic checks that need more evidence before backend integration.

**Status:** Findings incorporated. Deferred heuristics and items not yet safe for integration have been consolidated into [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](../../docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).

## Corpus Used

- `target_models/examples/sead_arbodat_core.yml`
- `target_models/examples/sead_missing_sample_group.yml`
- `tests/test_data/projects/arbodat/shapeshifter.yml`

All were validated against `resources/target_models/sead_standard_model.yml` using the standalone `TargetModelConformanceValidator`.

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

### Comparison matrix

| Project shape                   | Required entity | Public ID | Required FK target | Required column |
|---------------------------------|----------------:|----------:|-------------------:|----------------:|
| `sead_arbodat_core.yml`         |               0 |         0 |                  1 |               3 |
| `sead_missing_sample_group.yml` |               1 |         1 |                  3 |               4 |
| Full `arbodat` project          |               0 |         0 |                  4 |               3 |

This matrix is useful because it shows that the current validator is not surfacing new rule families as the project shape gets larger. The differences are in where the same rule families appear, not in the validator inventing new classes of findings.

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

### Full `arbodat` project

- `site` is missing required foreign-key target `location`
- `sample_group` is missing required foreign-key target `site`
- `sample_group` is missing required foreign-key target `method`
- `sample_type` is missing required target-facing column `type_name`
- `method` is missing required target-facing column `method_group_id`
- `analysis_entity` is missing required foreign-key target `dataset`
- `analysis_entity` is missing required target-facing column `dataset_id`

This is useful because it corroborates the same rule families against a fuller real project, rather than only against trimmed standalone fixtures.

## Ambiguous Cases And Deferred Heuristics

The following cases are real mismatches between the current Arbodat-derived fixture and the SEAD target model, but they are not yet good candidates for more aggressive inference rules.

### Alias-like target naming mismatches

- `sample_type` currently exposes `sample_type_name` in `extra_columns`, while the target model expects `type_name`
- `method` currently exposes `sead_method_group_id` in `columns`, while the target model expects `method_group_id`

These may be genuine conformance failures, but the validator should not silently treat them as equivalent yet. Doing so would require explicit alias rules or target-model metadata for acceptable project-side source names.

### Current decision

For the current Phase 6 iteration, keep both the target model and the validator strict.

- Do not change `sead_standard_model.yml` to encode project-specific aliases.
- Do not teach the validator implicit alias equivalence.
- Treat these as real conformance failures unless a later target-model extension introduces explicit alias metadata.

Rationale:

- The target model is meant to express canonical target-facing names, not source-specific naming habits.
- Implicit alias acceptance would hide real modeling gaps and make validator behavior harder to explain.
- The current fixture corpus is too small to justify a general alias mechanism.

### Transitive relationship expectations

The current validator only checks required foreign-key targets explicitly declared on the project entity. It does not infer that an entity is effectively linked through some longer path.

This is intentional for now. Inferring transitive conformance would increase false positives and make failure explanations harder to trust.

The full Arbodat project reinforces this decision. For example, `sample_group` currently depends on `feature`, and `feature` may carry some of the missing parent semantics, but the project entity does not declare the direct target-model relationships to `site` and `method`. Treating those links as satisfied transitively would blur the distinction between Shape Shifter processing structure and explicit target-model conformance.

## Minimal Safe Rule Set For Future Integration

If a subset of the standalone validator is later integrated into backend validation, the safe minimum rule set is:

- Required entities from the target model
- Exact `public_id` expectation when the target model declares one
- Required foreign-key targets by direct entity reference only
- Required target-facing columns only when they are explicit or safely inferable from current standalone rules

## Current Phase 6 Conclusion

At this point, the evidence still supports keeping `sead_standard_model.yml` strict and leaving alias metadata out of the format.

- The full Arbodat project confirms the same mismatch families already visible in the standalone fixtures.
- Those mismatches are explainable as either direct target-model gaps in the project or intentional source-specific naming choices.
- Neither case justifies weakening the target model yet.

So the current Phase 6 direction remains:

- keep the validator conservative
- keep the target model canonical
- defer any alias mechanism until there is evidence from multiple distinct real project shapes

## Not Yet Safe For Integration

Deferred items (alias matching, semantic normalization, transitive FK satisfaction, value-level checks, `@value:` expression interpretation) have been consolidated into [docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](../../docs/proposals/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md).