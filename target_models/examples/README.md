# Example Projects

This directory holds standalone `shapeshifter.yml` fixtures used for target-model conformance work inside `target_models/`.

## Fixtures

- `sead_arbodat_core.yml` — trimmed SEAD-oriented fixture derived from `tests/test_data/projects/arbodat/shapeshifter.yml`
- `sead_missing_sample_group.yml` — intentionally non-conforming derivative used to exercise obvious target-model mismatches

## Provenance And Simplifications

- Both fixtures are derived from the Arbodat project in `tests/test_data/projects/arbodat/shapeshifter.yml`.
- They keep only the iteration-1 SEAD core entities relevant to `target_models/specs/sead_v2.yml`.
- They are designed for standalone loading and conformance experimentation, not for full pipeline execution.
- Queries, values, and auxiliary fields are reduced to the minimum needed to preserve recognizable Shape Shifter structure.
- The broken fixture is deliberately edited to omit `sample_group` and to use a wrong `sample.public_id` so future conformance checks have stable negative cases.