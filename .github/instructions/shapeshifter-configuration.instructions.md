---
description: "Compact rules for validating or editing Shape Shifter project YAML. Covers high-risk structure, entity, identity, FK, dependency, append, directive, and false-positive checks."
applyTo: "**/shapeshifter.yml,data/projects/**/*.yml,data/projects/**/*.yaml"
---

# Shape Shifter YAML Validation Rules

Use this as the always-loaded compact rule source. Consult the full configuration guide only for detailed field semantics, examples, or project-version-specific behavior.

## Project Shape

```yaml
metadata:
  type: shapeshifter-project      # required, exact string
  name: string                    # required
entities:                         # required mapping
  entity_name: { ... }
options:                          # optional
  data_sources: {}
  translations: {}
  fixed_entity_types: {}
```

- `metadata.type` is required and must be `shapeshifter-project`.
- `metadata.name` is required.
- `entities` must exist and should be non-empty for normal execution.
- `options` is optional unless referenced.

## Entity Types

- `entity`: default when `type` is omitted; uses root/default source or another entity.
- `fixed`: inline `values`; requires `columns`, `values`, and usually `public_id`.
- `sql`: requires `data_source` and non-empty `query`.
- `duckdb`: requires `query` and explicit `depends_on`; no `data_source`.
- `merged`: requires `branches` and `public_id`; do not use obsolete `items`.
- `csv`, `xlsx`, `openpyxl`: file loaders; commonly used in append/source contexts.

Do not flag omitted `type` as an error if default `entity` semantics are valid.

## Identity

- `system_id`: internal local ID. FK values always reference parent `system_id`.
- `keys`: business keys for matching/deduplication. Should be `list[string]`; `[]` is valid.
- `public_id`: target/export ID and FK column name. Must end with `_id`.

Rules:

- FK values are local parent `system_id` values, not external target IDs.
- FK column names are derived from the parent `public_id`.
- `public_id` is required for fixed, merged, and FK parent entities.
- Non-fixed entities should not declare/import `system_id` in `columns`.
- Fixed entities may intentionally preserve explicit `system_id`.
- Fixed `system_id` values must be positive integers, unique, and non-null.
- `surrogate_id` is legacy; prefer `public_id` in new edits but do not reject legacy configs solely for it.

## Fixed Entities

- `columns` and `values` are required.
- Every `values` row width must match `columns`.
- Primitive single-column `values` require exactly one column.
- Explicit-identity fixed entities include both `system_id` and `public_id` in `columns`.
- `values: []` can be valid for fixed union/schema-parent entities with `append`.
- `column_types` applies only to fixed entities.
- `column_types` keys must exist in `columns`.
- Allowed fixed types: `int`, `string`, `float`, `bool`, `date`; use `int`, not `integer`.
- Fixed type precedence: `column_types`, then `options.fixed_entity_types.conventions`, then `_id -> int`, then no inferred type.
- Invalid non-empty `_id` values such as `"53.0"`, `"abc"`, or booleans are validation problems.

## SQL, Internal SQL, and DuckDB

- External `type: sql` requires `data_source`, `query`, and a matching `options.data_sources` entry.
- `data_source: "@internal"` is an exception: no `options.data_sources` entry is required.
- Internal SQL should list referenced processed entities in `depends_on`.
- `type: duckdb` requires `query` and `depends_on`, and does not require `data_source`.
- Queried FK values in internal SQL/DuckDB are local `system_id` values.

## Merged Entities

- `branches` is required and must be non-empty.
- Each branch requires `name` and `source`.
- Branch names must be unique.
- Branch `source` must reference an existing entity.
- Branch source entities should define `public_id`.
- A config with `branches` should have `type: merged`.

## Foreign Keys

- Non-cross FKs require `entity`, `local_keys`, and `remote_keys`.
- FK `entity` must exist and must not be self-referential.
- `local_keys` and `remote_keys` must have equal length.
- `local_keys` must exist in the child entity at the relevant stage.
- `remote_keys` must exist in the target entity.
- `extra_columns` values used in FK joins are valid.
- `how: cross` should not have `local_keys` or `remote_keys`.
- `defer_dependency: true` is valid only as an explicit advanced cycle-breaking FK setting.

External-ID pattern:

- If a child already contains external parent IDs, keep them in a distinct business-key column, for example `sead_method_group_id`.
- Join that column to the parent business key.
- Let FK linking add the local FK column named from parent `public_id`.

## FK Constraints

Supported keys: `cardinality`, `allow_unmatched_left`, `allow_unmatched_right`, `require_unique_left`, `require_unique_right`, `allow_null_keys`, `allow_row_decrease`.

- `cardinality` must be `one_to_one`, `many_to_one`, `one_to_many`, or `many_to_many`.
- `many_to_one` is the common lookup/reference pattern.
- `require_unique_right: true` is common for lookup/reference entities.
- `allow_unmatched_left: false` enforces required matches.
- `allow_row_decrease: false` catches accidental filtering.
- If `allow_null_keys` is omitted for lookup-style `left` joins, missing local key parts may remain unresolved rather than hard-erroring.
- Do not tighten constraints unless relationship intent is clear.

## Dependencies

Dependency sources:

- `depends_on`
- `source`
- `foreign_keys[].entity`, unless deferred
- `append[].source`
- `merged.branches[].source`
- filters such as `exists_in.other_entity`
- visible internal SQL/DuckDB references

Rules:

- `depends_on` should be `list[string]`; `[]` is valid.
- All dependency references must point to existing entities.
- Dependency graph must be acyclic unless a specific FK uses `defer_dependency: true`.
- Add only minimal dependencies needed to satisfy actual references.

## Extra Columns

Valid forms: copy, constant, interpolation, DSL formula, and escaped literal `==value`.

- `extra_columns` must be a mapping.
- Formula DSL functions include at least `concat`, `upper`, `lower`, `trim`, `substr`, `coalesce`, `replace`, `regex_extract`, `to_decimal`, `to_int`, `to_float`, `to_str`, and `to_date`.
- Formula expressions are not arbitrary code.
- Interpolation is null-safe.
- Some `extra_columns` may be deferred until referenced columns appear later; avoid premature missing-column findings.

## Append

- `append` concatenates sources before FK linking and unnesting.
- Append sources may be fixed, SQL, source/entity-based, or project-version-dependent file loaders.
- Fixed append requires `values`; SQL append requires `data_source` and `query`.
- Source-based append can omit `type`; `source` implies entity/source append.
- Append `source` must reference an existing entity and should be represented in `depends_on`.
- Append schemas must align with parent columns.

Inherited by append sources unless overridden: `columns`, `drop_duplicates`, `drop_empty_rows`, `replacements`, `filters`, `check_column_names`.

Not inherited: `public_id`/`surrogate_id`, `keys`, `foreign_keys`, `unnest`, `depends_on`, `source`, `type`.

If append item has `source`, do not inherit loader-driving fields: `type`, `values`, `query`, `data_source`, or `sql`.

## Unnest

- `var_name` and `value_name` are required when `unnest` is configured.
- `value_vars` should be present and non-empty.
- `id_vars` is optional; empty `id_vars` may deserve a warning.
- `id_vars` and `value_vars` may use `@value:`.
- `var_name` and `value_name` must differ and should not conflict with existing columns.
- `value_vars` should not overlap with `id_vars`.

## Data Quality and Replacements

- `drop_duplicates`: valid as bool, `list[string]`, `@value:` string, or mapping with `columns`.
- `drop_empty_rows`: valid as bool, `list[string]`, or `dict[string, list[any]]`.
- `filters` must be a list of mappings; `exists_in` requires `column`, `other_entity`, and optional `other_column`.
- `replacements` must be a mapping by column and may use mappings, legacy blank-out/fill forms, or ordered rule lists.
- Do not simplify advanced replacement rules unless behavior is equivalent.

## Directives

Preserve during review/editing:

- `@include: path/to/file.yml`
- `@load: path.or.external.spec`
- `@value: entities.entity.property`
- `${ENV_VAR}`

Rules:

- Do not inline or pre-resolve directives unless explicitly asked.
- `@include:` loads YAML and recursively resolves directives/references in included data.
- `@load:` loads external/raw data without resolving directives introduced later.
- `@value:` references another config value by path.
- Treat unresolved directives as residual risk, not automatic errors, unless visibly invalid.

## Configuration Transformations

- When transforming configuration data in code, avoid mutating the input; use deep copies where nested data must change.

## Materialized Entities

If `materialized` is supported by the active project version:

- Treat it as a frozen snapshot.
- Do not re-validate snapshot data as raw extraction input.
- Validate surrounding entity config and references.
- If support is unclear, state the assumption instead of declaring the field valid or invalid.

## High-Risk False Positives

Do not auto-flag these as errors:

- `type` omitted when default `entity` semantics are valid.
- `keys: []` or `depends_on: []`.
- `source: null` or omitted source for root/default source.
- `values: []` on fixed union/schema-parent entities with append.
- `data_source: "@internal"` without `options.data_sources`.
- `type: duckdb` without `data_source`.
- `extra_columns` used as FK join keys.
- Source-based append without `type`.
- Legacy `surrogate_id`.
- Left joins with permissive constraints for sparse or optional relationships.
- Lookup-style `left` joins with omitted `allow_null_keys`.

## Review Practice

- Separate definite errors from warnings, assumptions, and project-version-dependent checks.
- Report entity path, violated rule, impact, and smallest safe fix.
- Preserve comments, ordering, directives, and local style.
- Never invent data-source names, table names, sheet names, source columns, or target columns.
- Only claim validation passed if it actually ran successfully.
