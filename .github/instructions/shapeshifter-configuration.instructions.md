---
description: "Current rules for reviewing and editing Shape Shifter project YAML: entity types, identity, fixed rows, relationships, transforms, directives, and validation."
applyTo: "**/shapeshifter.yml,**/shapeshifter.yaml,data/projects/**/*.yml,data/projects/**/*.yaml"
---

# Shape Shifter project YAML

Use these rules for project configuration. Confirm a consequential rule in the current implementation when the project is unusual or a document disagrees with code. The main sources are `src/model.py`, `src/specifications/entity.py`, `src/loaders/`, `src/configuration/resolve.py`, `backend/app/utils/fixed_schema.py`, and `backend/app/mappers/project_mapper.py`. Use `docs/CONFIGURATION_GUIDE.md` for examples; parts of that guide may lag the implementation.

## Project and entity shape

```yaml
metadata:
  type: shapeshifter-project
  name: Example project
entities:
  entity_name:
    type: entity
    keys: []
    columns: []
options:
  data_sources: {}
  translations: {}
  fixed_entity_types: {}
```

- `options` is optional unless a setting is referenced. A project normally contains at least one entity.
- `metadata.type: shapeshifter-project` is required by structural validation. Include a clear `metadata.name`, but note that the backend derives the API project name from its project folder or filename rather than trusting a stale YAML name.
- `entities` is a mapping keyed by entity name. Non-merged entities should declare `type`, `keys`, and `columns`; structural validation checks those fields. A missing `type` is not automatically treated as `entity` by the Core structural specification.
- `type: entity` reads a root/default source or another entity through `source`. An omitted or null `source` can be valid for a root entity. It must not carry SQL `data_source` or `query` fields.
- `type: fixed` requires `public_id`, `columns`, and usually `values`. When append supplies all rows, `values` may be empty or omitted. Fixed values can also be loaded through `@load:` for processing.
- `type: sql` requires a non-empty `query` and `data_source`. The source must exist under `options.data_sources`, except for `data_source: "@internal"`.
- `type: duckdb` runs a read-only query over already processed entities in the internal workspace. Give it a `query` and explicit `depends_on` entries for referenced entities; it needs no external `data_source`. Check the current API/editor model if the file will be edited through that interface.
- File loaders include `csv`, `tsv`, `xlsx`, `xls`, and `openpyxl`. They need a filename in loader options or a configured data source. Excel `sheet_name` is optional; inspect the relevant loader for other options.
- `type: merged` requires `public_id` and non-empty `branches`. Each branch has a unique `name` and an existing entity `source`. Its fields are defined by branches, so do not apply ordinary entity-level `keys` and `columns` requirements to the merged parent.
- Check that each merged branch source produces the columns its branch configuration uses. Do not replace `branches` with the older `items` form.
- `metadata.target_model` is optional. It may be an inline mapping or a file reference such as `@load:`; run target-model conformance only when a target model is configured or requested.
- When a target model is configured, compare it with the columns that survive processing. Unnest keeps its identifier columns and emits `var_name` and `value_name`; append branches must conform to the parent schema rather than expand it.

### SQL and file sources

- External `type: sql` uses the named `data_source` from `options.data_sources`. The `"@internal"` source is a special processed-data source, so it needs no entry there.
- For `data_source: "@internal"` and `type: duckdb`, list referenced processed entities in `depends_on`. A table name in SQL text alone does not create a reliable processing dependency.
- A DuckDB entity queries the internal workspace; check that the referenced entities have run before it. The Core loader supports this form, while the API entity-type enum may not expose it.
- File loaders read from a configured file or source. Confirm the filename, delimiter, sheet, and selected columns against the actual loader options when they matter. Do not assume an Excel sheet name is always required.
- A source-based `type: entity` can use another processed entity as input. A root entity can omit `source` or set it to null, depending on the project workflow.

## Identity and fixed rows

- `system_id` is the local sequential identity. A child FK column takes its name from the parent `public_id`, while its values are the parent's local `system_id` values. Do not put external target IDs into the generated FK column.
- `keys` name produced columns used for matching or deduplication; they do not create output fields. `keys: []` can be intentional. `public_id` must end in `_id`; it is required for fixed and merged entities and for an entity used as an FK parent.
- The extractor can read keys, FK join inputs, and unnest `id_vars` from a source as temporary fields even when `columns` omits them. Some structural checks still require those names in `columns` or another declared producer. When this disagreement appears, report the structural failure and inspect the intended final output before recommending that the names be added to `columns`.
- A `keys` list may name a managed `system_id` or `public_id` if that field is produced. Prefer business columns when deduplication is meant to identify the same real-world row across imports; do not reject an identity key solely because it is absent from fixed `columns`.
- Current structural validation warns when a non-fixed entity lists `system_id` in `columns`, so data and conformance workflows can still run. The extractor and normalization pipeline retain an explicitly selected source value. Non-fixed IDs are not currently checked for positive, unique integer values; if a file supplies IDs, confirm they are intentional and report that limitation.
- For newly authored fixed entities, `columns` lists produced data fields, without `system_id` or `public_id`. The full positional row order is `system_id`, then `public_id` when configured, then the data fields in `columns`. `values` may use either data-only rows (`len(columns)`) or full rows (`len(full_columns)`); do not equate row width with persisted `columns` alone.
- Older fixed configurations may list identity fields in `columns`. The persistence strategy normalizes those names out of `columns` and preserves the row values. Do not reject the old form solely for that reason. Reject duplicate column names and inconsistent row widths.
- A fixed entity's `keys` must be addressable in its fixed row schema: managed identity fields plus configured data fields. A key made only by `extra_columns`, an FK, or unnest has no fixed row position.
- When fixed `system_id` values are explicitly supplied, check that they are positive, unique, non-null integers. When absent, the fixed loader adds them.
- An explicit ID value such as `"53.0"`, `"abc"`, or a boolean does not satisfy a strict integer declaration. Distinguish the raw YAML value from a value coerced while loading an external `@load:` payload.
- Fixed `column_types` keys must name configured columns. Allowed types are `int`, `string`, `float`, `bool`, and `date`. Type resolution uses explicit `column_types`, then the first matching `options.fixed_entity_types.conventions` rule, then `_id` as `int`; undeclared non-ID fields have no inferred fixed type. Load-time coercion of a string integer does not mean a save accepts the same uncoerced value.
- `surrogate_id` is a compatibility field. Prefer `public_id` in new configuration, and check how the active mapper handles an older project before changing it.
- Fixed `values` loaded through `@load:` may resolve to dictionaries keyed by column name. Inspect the resolved data shape before applying positional-row checks to those rows.

For example, a fixed entity can store a full positional row without listing identities in `columns`:

```yaml
method:
  type: fixed
  public_id: method_id
  keys: [name]
  columns: [name]
  values:
    - [1, 53, Sampling]
```

The row contains `system_id = 1`, `method_id = 53`, and `name = Sampling`. Data-only `values: [[Sampling]]` is also valid; the loader supplies `system_id`. This distinction matters when checking saved `columns` and row widths.

## Foreign keys and dependencies

- A normal FK has `entity`, nonempty `local_keys`, and nonempty `remote_keys`; the two key lists have equal length. The target entity must exist. A `how: cross` FK uses empty join-key lists. Check keys against columns available at the linking stage, not only raw `columns`.
- Child `local_keys` may come from `extra_columns` or an earlier FK in the same ordered list. Parent `remote_keys` must be produced by the parent. If a child already contains external parent IDs, match those as business data and let linking add a separate local-ID FK column.
- For example, retain a child's external `sead_method_id` as a separate lookup field, join it to a parent business key, and let linking add the child `method_id` field holding the parent's local `system_id`. Do not copy the external value into `method_id`.
- FK `how` selects merge behavior; inspect the relationship before treating unmatched rows from a left join as an error. A self-reference is not a normal FK target.
- An FK without `how` uses an inner join. If every local key is null and the remote identity keys are non-null, the join removes every local row; check fixed-row values before accepting that default.
- Supported FK constraint fields are `cardinality`, `allow_unmatched_left`, `allow_unmatched_right`, `require_unique_left`, `require_unique_right`, `allow_null_keys`, and `allow_row_decrease`.
- `cardinality` may be `one_to_one`, `many_to_one`, `one_to_many`, or `many_to_many`. `many_to_one` with `require_unique_right: true` fits a lookup entity with one row per remote key.
- `allow_unmatched_left: false` requires every child row to match. `allow_row_decrease: false` catches a join that unexpectedly removes rows. An omitted `allow_null_keys` has different handling from an explicitly strict setting in some left-join paths; inspect the current validator before changing it.
- Do not tighten permissive constraints merely because a relationship has unmatched or null keys. Determine whether the source permits sparse or optional relationships.
- Processing dependencies come from explicit `depends_on`, `source`, non-deferred FKs, append sources, merged branch sources, and entity references in filters. SQL text is not a reliable source of dependencies; list referenced processed entities explicitly for internal SQL and DuckDB.
- A genuine FK cycle may use `defer_dependency: true` on the specific FK that must link in the final pass. It does not defer `source`, append, filter, or explicit `depends_on` edges. Check the remaining graph for cycles.
- `depends_on: []` is valid. Each named dependency must exist. Add only the explicit dependencies needed for references that the processing graph cannot infer.

## Transforms and rows

- Pipeline order is Extract → Filter → Link → Unnest → Translate → Store. Filters have `stage: extract`, `after_link`, or `after_unnest`; omitted stage means `extract`. An extract-stage filter cannot use columns created by FK linking or unnest. An `exists_in` filter needs a local `column` and an existing `other_entity`; verify the remote column it uses.
- `extra_columns` supports formulas beginning with `=`, copies, strings interpolating `{column}`, and constants. Missing inputs can defer evaluation until a later stage. Formulas use the allowlisted DSL in `src/transforms/dsl.py` (`DEFAULT_FUNCTIONS`), not arbitrary Python or SQL.
- A plain string copies a column only when its name matches an available column; otherwise it becomes a literal string value. If a copy is intended, confirm that the source column is produced by extraction or by an earlier transform. Formulas and interpolation have separate missing-column handling.
- A string beginning `==` is an escaped literal beginning with `=`; it is not a formula. An `extra_columns` formula or interpolation may refer to a column produced later, so check when it is evaluated before reporting a missing column.
- Current DSL functions include `concat`, `upper`, `lower`, `trim`, `substr`, `coalesce`, `replace`, `regex_extract`, `to_decimal`, `to_int`, `to_float`, `to_str`, and `to_date`. Check `DEFAULT_FUNCTIONS` when a formula uses another name.
- Append accepts inline `fixed` rows, an `sql` query, or rows from an existing entity through `source`. A source append is an implicit dependency. Match columns by name by default; use `column_mapping` or `align_by_position` when needed, never both. Positional alignment compares payload columns after identity columns are excluded. `append_mode` is `all` or `distinct`; check inherited parent options before changing an append item.
- A type-based append accepts `fixed` or `sql`. `fixed` needs `values`; `sql` needs `query` and an effective data source. A source-based append accepts `source` alone or `type: entity` plus `source`; the source must exist. The current structural specification does not accept a type-based file-loader append.
- Append items inherit most parent settings unless they override them. This includes `keys`, `columns`, `filters`, `replacements`, `drop_duplicates`, `drop_empty_rows`, and `check_column_names`. The merge omits parent `foreign_keys`, `unnest`, `append`, `append_mode`, and `depends_on`.
- A source-based append does not inherit loader-driving `type`, `values`, `query`, `data_source`, or `sql`. With `column_mapping` or `align_by_position`, omitted item `columns` and `keys` come from the source entity. Check the effective configuration before changing an item.
- Append runs before FK linking and unnesting. Its branches must fit the parent output contract; adding a field to one branch alone does not widen the final entity schema.
- For source append, check the parent payload columns against the source payload columns. Without mapping or positional alignment, names must match. `column_mapping` maps source names to target names; `align_by_position` requires equal counts after the identity fields are removed.
- Unnest needs distinct `var_name` and `value_name`. Its `id_vars` and `value_vars` must exist when unnest runs, after FK linking; the two lists must not overlap. Check any `@value:` references before treating a column as missing.
- `value_vars`, `var_name`, and `value_name` are required by structural validation; `id_vars` is optional. A nonempty `value_vars` list is normally needed to produce meaningful rows. Missing or overlapping `id_vars` and `value_vars` can raise or silently lose melted data.
- Preserve intentional `drop_duplicates`, `drop_empty_rows`, `replacements`, and FK constraints. These options have several forms; confirm the relevant implementation before simplifying an existing rule.

## Data quality and replacements

- `drop_duplicates` accepts a boolean, a list of column names, a directive string such as `@value:`, or a mapping with `columns`. The mapping may also carry `check_functional_dependency` and `strict_functional_dependency` booleans.
- `drop_empty_rows` accepts a boolean, a list of columns, or a mapping from columns to values considered empty. A missing named column currently causes a warning and leaves rows unchanged; check actual column availability.
- `replacements` maps column names to one of three forms: an old-to-new value mapping, legacy values to blank out and forward-fill, or an ordered list of rule mappings. Ordered rules can do more than simple value substitution; inspect `src/transforms/replace.py` before changing them.
- `filters` is a list of mappings. The registered `exists_in` filter needs `column` and `other_entity`; `other_column` defaults to the local column. Check the remote column on the referenced entity. A `query` filter is also registered; inspect its expression before rewriting it.
- Filter `stage` may be `extract`, `after_link`, or `after_unnest`. `extract` is the default. Check the columns available at that stage: FK-produced columns appear after linking, and unnest output names appear after unnesting.

## Directives and materialized entities

- Preserve raw `@include:`, `@load:`, `@value:`, and `${ENV_VAR}` strings when reviewing or editing YAML. API and YAML storage preserve them; `ProjectMapper.to_core()` resolves them for backend processing. Inspect referenced files or environment values only as needed to verify behavior. Do not inline a directive just to satisfy a static review.

Common forms include:

```yaml
data_sources: "@include:config/data_sources.yml"
values: "@load:data/methods.csv"
columns: "@value: entities.method.keys"
filename: "${PROJECT_DATA_DIR}/methods.csv"
```

These are examples of directive syntax, not a complete entity. Keep the raw string in saved YAML even when processing resolves it to a list, mapping, or loaded rows.

- `@include:` loads a YAML mapping relative to the current configuration file and recursively resolves directives in it. `@load:` loads a file or a dotted configuration reference as raw data; directives introduced by that loaded payload are not recursively resolved.
- `@value:` reads another resolved configuration path and can compose list values. It resolves after includes, loads, and environment variables. A list containing `@value:` references can flatten referenced lists; do not treat it as a literal column name.
- `${ENV_VAR}` may replace a whole value or part of a string. File and directory variables can be resolved relative to the runtime root. Report an unresolved or inaccessible reference as a validation limit until its expected environment is known.
- A materialized entity is saved as `type: fixed` with `materialized.enabled: true`. Its `materialized.source_state` retains the original configuration for restoration; `values` may be inline or an `@load:` sidecar. Review the saved rows as a snapshot and preserve `source_state` unless changing materialization is the task. `materialized_at` is expected metadata.

## Avoid false findings

Check context before calling any of these an error:

- `keys: []`, `depends_on: []`, or a root `type: entity` with omitted or null `source`.
- A fixed entity whose `values` is empty or omitted because append supplies its rows.
- A fixed full row containing `system_id` and `public_id` while persisted `columns` lists only data fields.
- An older fixed entity with identity names still in `columns`, or a legacy `surrogate_id` field.
- `data_source: "@internal"` without a matching `options.data_sources` entry, or `type: duckdb` without an external `data_source`.
- `extra_columns` or a prior FK producing a key used by a later FK.
- Source-based append without a `type`, or an append source absent from explicit `depends_on` when the graph already infers that edge.
- A left join with permissive constraints, or omitted `allow_null_keys` for an optional lookup relationship.
- A directive that requires a file, database, or environment value unavailable in the current workspace.

Do treat an omitted non-merged entity `type` as a structural validation issue in the current Core specification. Do not carry forward the older claim that it defaults to `entity` for structural review.

## Validation and findings

- After a focused config edit, run structural validation when the project and referenced files are available: `rtk uv run python scripts/validate_project.py <path> --workflow structural --log-level ERROR`. Retry without `rtk` if its wrapper fails.
- Read the output rows and their `severity` values. The current command may exit with status 0 while printing structural errors, so its process exit code alone does not establish a pass.
- Structural validation does not currently reject every unknown FK option or unsupported cardinality string. Check `constraints` spelling and compare `cardinality` with `one_to_one`, `many_to_one`, `one_to_many`, or `many_to_many` during static review.
- Use `--workflow data`, `--workflow target-model-conformance`, or `--workflow all` when the task needs those results and required data sources are available. State which workflow ran and whether it completed. An unresolved directive or inaccessible source is a validation limit to report, not proof that the YAML rule is wrong.
- Report confirmed findings with the entity or YAML path, actual rule, effect, and smallest safe fix. Distinguish project-specific assumptions from validation failures. Preserve comments, field order, and local naming when editing.
- Do not invent a data-source name, table, sheet, source column, or target column to make a configuration appear valid. Use the project's files and model definitions, or state what remains unknown.
- State whether a finding came from structural validation, data processing, target-model conformance, or a static review. A static review does not prove that an external database or file can be read.
