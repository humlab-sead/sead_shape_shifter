---
description: "Current rules for reviewing and editing Shape Shifter project YAML, including entity behavior, provider bindings, identities, transforms, directives, and validation."
applyTo: "**/shapeshifter.yml,**/shapeshifter.yaml,data/projects/**/*.yml,data/projects/**/*.yaml"
---

# Shape Shifter project YAML

Use these rules when reviewing or editing project YAML. Check current code when a rule is consequential or documentation disagrees with the implementation. Main sources are `src/model.py`, `src/specifications/`, `src/loaders/`, `src/configuration/resolve.py`, `backend/app/mappers/project_mapper.py`, and `backend/app/services/validation_service.py`.

Use [the configuration guide](../../docs/CONFIGURATION_GUIDE.md) for examples, [the user guide](../../docs/USER_GUIDE.md) for current editor workflows, and [the upgrade guide](../../docs/PROJECT_CONFIGURATION_UPGRADE_GUIDE.md) for older projects. The implementation determines current behavior.

## Project metadata and entity shape

```yaml
metadata:
  type: shapeshifter-project
  name: Example project
  data_provider_code: provider-code
  provider_schema: schema-code
  target_model: "@load: ${GLOBAL_TARGET_MODEL_DIR}/model.yml"
entities:
  entity_name:
    type: entity
    keys: []
    columns: []
options:
  data_sources: {}
```

- `metadata.type: shapeshifter-project` is required by Core structural validation. In the editor, the project name comes from its folder or filename; a stale YAML `metadata.name` does not rename the project.
- `options` is optional unless the project uses a setting. A project normally has at least one entity.
- Non-merged entities should declare `type`, `keys`, and `columns`. An omitted `type` is a structural issue; do not assume it defaults to `entity`.
- `type: entity` reads a root/default source or another entity through `source`. A root may omit or null `source`; it must not carry SQL `data_source` or `query` fields.
- `type: fixed` requires `public_id`, `columns`, and usually `values`. Values may be empty or omitted when append supplies every row.
- `type: sql` requires a non-empty `query` and `data_source`. The source must be in `options.data_sources`, except for `data_source: "@internal"`. SQL loaders enforce read-only queries.
- `type: duckdb` queries already processed entities in Shape Shifter's internal in-memory workspace. Declare every referenced entity in `depends_on`; SQL text alone is not a reliable dependency. The Core loader supports DuckDB, but the current API entity-type model may not, so check editor round-tripping before changing one through the UI.
- File loaders are registered separately from the API entity-type enum. Check `src/loaders/` and `backend/app/models/entity.py` for the exact loader and editor support. Confirm filenames, source locations, delimiters, sheets, and selected columns against the loader options.
- `type: merged` requires a `public_id` and non-empty `branches`. Each branch needs a unique name and an existing source entity. Branches define the merged output; do not require ordinary entity-level `keys` and `columns` or replace `branches` with legacy `items`.
- A merged branch must produce the fields its source and branch keys use. The merged output adds a branch discriminator and sparse branch foreign keys. Branch columns do not make unrelated branch-only fields part of every branch's data.

### Provider and target-model metadata

- `metadata.data_provider_code` and `metadata.provider_schema` are a stable pair from the deployment's curated provider registry. They identify the provider schema and its SIMS scope. Check the actual registry; do not copy an example pair or invent codes.
- New projects and first-time bindings require a registered pair. Older checked-in projects may still be unbound during migration. Backend YAML Validation reports missing, partial, blank, or unregistered values; the Core CLI structural workflow does not check the provider registry.
- Before the first binding, review the existing entities' `keys`: they are part of the provider-schema identity. After binding, normal saves cannot change or remove the pair and reject changes to established key declarations. Projects sharing a pair must use consistent key meanings. Changing them requires an identity migration or a new provider schema.
- For a bound project, Backend YAML Validation also checks for one fixed `data_provider` row with `public_id: data_provider_id`, `keys: [data_provider_code]`, a positive integer `data_provider_id`, and a `data_provider_code` matching metadata. `data_provider_id` is the SEAD ID, not the local `system_id`. This check does not prove that the ID exists in the target database; workflows that dispatch data perform that check separately.
- `metadata.target_model` is optional for general project processing. It can be an inline mapping or a file reference. The editor's target-model picker saves an `@load:` reference to a project-local or shared file.
- Prefer a deployment-managed shared target model when several projects use the same target schema. The default shared directory is `shared/target-models`; the editor references it with `${GLOBAL_TARGET_MODEL_DIR}`. Shared model changes affect every project that uses the file. Use a project-local model for a deliberate project-specific specification.
- Verify that a configured model file exists and was actually loaded before reporting conformance as passed. The editor's conformance service can return an empty valid result when a referenced file is missing. Some workflows, including SEAD Change Request dispatch, require a target model even though it is optional for general processing.
- Compare a configured target model with the columns that survive processing. Unnest keeps its identifier columns and emits `var_name` and `value_name`; check that required FK keys survive unnest. Append branches must conform to the parent schema rather than expand it.

### SQL and file sources

- External SQL uses the named `data_source` under `options.data_sources`. `@internal` is a special processed-data source and needs no external definition.
- A `type: duckdb` entity also reads the internal workspace. List referenced entities in `depends_on` and use a read-only query.
- File loaders read from a configured file or data source. Check loader-specific options when the filename, delimiter, sheet, range, or selected columns matter; an Excel sheet name is not always required.
- A source-based `type: entity` reads another processed entity. A root entity can omit or set `source: null`, depending on the project workflow.

## Identity and fixed rows

- `system_id` is the local identity used in foreign-key values. A child's FK column is named after the parent's `public_id`, but contains the parent's `system_id`. Never put an external target ID into a generated FK column.
- A parent may be joined through its generated `system_id`. If `remote_keys` uses a parent's `public_id`, check that the parent actually produces populated public IDs; structural validation may warn when it does not.
- `keys` identify business rows for matching and duplicate checks; they do not create columns. Empty keys can be intentional. A produced `system_id` or `public_id` can be a key, but prefer source business fields when identity should remain stable across imports.
- `public_id` must end in `_id`. It is required for fixed and merged entities and for an entity used as a foreign-key parent.
- The extractor can read keys, FK join inputs, and unnest `id_vars` from a source as temporary fields even when `columns` omits them. Some structural checks still require those fields in `columns` or another declared producer. Report the actual structural issue and inspect the intended output before adding a name to `columns`.
- Current structural validation warns when a non-fixed entity lists `system_id` in `columns`. Runtime preserves supplied values but does not check non-fixed IDs for positive, unique integers. Confirm those values are intentional before changing the entity.
- For new fixed entities, `columns` lists data fields without `system_id` or `public_id`. Full positional rows are ordered as `system_id`, `public_id` when configured, then data fields in `columns`. Values can be data-only rows or full rows. Older fixed configurations may still list identity fields in `columns`; persistence removes them from that list and preserves their values. Do not reject the old form only for that reason.
- Reject duplicate fixed column names, inconsistent row widths, and keys that have no position in the fixed row schema. A fixed entity's keys must be managed identities or configured data columns; a key supplied only by `extra_columns`, an FK, or unnest cannot be stored in a fixed row.
- Explicit fixed `system_id` values must be positive, unique, non-null integers. When absent, the fixed loader adds them. A raw string such as `"53"`, a decimal string, or a boolean is not a strict integer value; distinguish raw YAML from values coerced while loading external `@load:` data.
- Fixed `column_types` names must refer to configured data columns. Supported types are `int`, `string`, `float`, `bool`, and `date`. Resolution uses explicit types, then the first matching `options.fixed_entity_types.conventions` rule, then `_id` as `int`; other fields have no inferred type.
- `surrogate_id` is retained for compatibility. Prefer `public_id` in new configuration and check the active mapper before changing an older project.
- Values loaded through `@load:` may be dictionaries keyed by column name. Check the resolved data shape before applying positional-row rules.
- The project mapping sidecar can supply fixed-entity public-ID links during normalization. If assigned IDs or fixed-row edits are under review, inspect it as well as YAML. Core structural validation does not load these links; the CLI `data` workflow normalizes with `ShapeShifter` and applies committed sidecar links.

Example fixed entity with data-only columns and a full positional row:

```yaml
method:
  type: fixed
  public_id: method_id
  keys: [name]
  columns: [name]
  values:
    - [1, 53, Sampling]
```

This row sets `system_id = 1`, `method_id = 53`, and `name = Sampling`. A data-only row such as `values: [[Sampling]]` lets the loader supply `system_id`.

## Foreign keys and dependencies

- A normal FK has `entity`, non-empty `local_keys`, and non-empty `remote_keys` of equal length. The target entity must exist. `how: cross` uses empty key lists.
- Check key availability at the linking stage, not only in raw `columns`. A local key can come from `extra_columns` or an earlier FK; the remote key must be produced by its entity.
- If a child contains an external parent ID, retain it as a separate business/lookup field and join on that field. Let linking add the local FK column with the parent's `system_id`.
- `how` selects merge behavior. An omitted `how` means an inner join and may remove unmatched child rows. A left join preserves child rows; assess unmatched rows against the source's real rules.
- Supported FK constraint fields are `cardinality`, `allow_unmatched_left`, `allow_unmatched_right`, `require_unique_left`, `require_unique_right`, `allow_null_keys`, and `allow_row_decrease`. Cardinality values are `one_to_one`, `many_to_one`, `one_to_many`, and `many_to_many`.
- Check spelling and values directly. Core structural validation may not reject an unknown constraint name or unsupported cardinality value, even when an API model does.
- `many_to_one` with `require_unique_right: true` fits a lookup with one row per remote key. `allow_unmatched_left: false` requires every child row to match. `allow_row_decrease: false` catches an unexpected reduction after linking.
- Do not tighten permissive constraints just because a relationship has null or unmatched keys. Omitted `allow_null_keys` has lookup-style behavior for some left joins; inspect the join and current validator before changing it.
- Dependencies can come from `source`, non-deferred FKs, append sources, merged branches, entity references in filters, and explicit `depends_on`. SQL text alone does not establish a processing dependency.
- A genuine FK cycle may use `defer_dependency: true` on the FK that must link in the final pass. It does not defer `source`, append, filter, merged branch, or explicit dependency edges. Check the remaining graph for cycles.
- FK keys produced by unnest can be linked in the post-unnest pass. Do not set `defer_dependency: true` only because a local key is created by `var_name`.

## Transforms and rows

- Pipeline order is Extract → Filter → Link → Unnest → Translate → Store. Filters can run at `extract`, `after_link`, or `after_unnest`; an extract filter cannot use FK or unnest output. An `exists_in` filter needs a local `column`, an existing `other_entity`, and a produced remote column.
- `extra_columns` supports formulas beginning with `=`, column copies, strings interpolating `{column}`, and constants. A plain string copies a column only if that column is available; otherwise it is a literal. Formulas and interpolations can be evaluated after their inputs are produced. Check `src/transforms/dsl.py` for the current formula allowlist; formulas are not Python or SQL.
- A string beginning with `==` is an escaped literal beginning with `=`. Do not report a missing input until checking whether a formula or interpolation is deferred to a later stage.
- An `extra_columns` definition must not redefine `system_id`, `public_id`, or an unnest output. An extra column can supply an unnest `id_var`, an FK local key, or a later transform input.
- Append supports inline `fixed` rows, an `sql` query, or rows from another entity through `source`. A source append creates an implicit dependency. Append matches columns by name unless `column_mapping` or `align_by_position` is used; never set both. Positional alignment compares payload columns after identity columns are excluded.
- `append_mode` is `all` or `distinct`. Check inherited parent options before changing an append item.
- Type-based append supports `fixed` or `sql`. Fixed append needs `values`; SQL append needs `query` and an effective data source. Core structural validation accepts source-based append as `source` alone or `type: entity` plus `source`; the source must exist. For editor/API compatibility, prefer `source` alone because the API append model allows only `fixed` or `sql` as `type`. The current structural specification does not accept a type-based file-loader append.
- Append items inherit most parent settings, including `keys`, `columns`, filters, replacements, duplicate handling, and empty-row handling. They do not inherit `foreign_keys`, `unnest`, `append`, `append_mode`, or `depends_on`.
- A source append does not inherit loader fields such as `type`, `values`, `query`, or `data_source`. When `column_mapping` or `align_by_position` is used, omitted item `columns` and `keys` come from the source entity. Check the effective configuration before changing it.
- Append runs before FK linking and unnesting. Each branch must fit the parent output contract; a branch does not widen the final schema.
- `unnest` needs distinct `var_name` and `value_name`. Its `id_vars` and `value_vars` must exist when unnest runs and must not overlap after directives resolve. Broad `@value:` lists can include identifiers; name the intended measurements when needed. Missing or overlapping values can raise an error or lose melted data.
- Unnest preserves its `id_vars` and emits `var_name` and `value_name`; original `value_vars` are consumed. A FK using a produced `var_name` is linked after unnest. A filter at `after_unnest` can see those outputs.
- Preserve intentional `drop_duplicates`, `drop_empty_rows`, `replacements`, and FK constraints. These options accept several forms; check the relevant implementation before simplifying them.

## Data quality and replacements

- `drop_duplicates` accepts a boolean, a list of column names, a directive, or a mapping with `columns`. A mapping may also include `check_functional_dependency` and `strict_functional_dependency`.
- `drop_empty_rows` accepts a boolean, a list of columns, or a mapping from columns to values considered empty. A missing named column currently warns and leaves rows unchanged.
- `replacements` maps column names to a value mapping, a legacy blank-and-forward-fill form, or an ordered list of rule mappings. Do not mix forms for one column. Inspect `src/transforms/replace.py` before changing replacement rules.
- Filters are a list of mappings. The registered `exists_in` filter needs `column` and `other_entity`; `other_column` defaults to the local column. A `query` filter is also available; inspect its expression before rewriting it.

## Directives, materialization, and mapping state

- Keep `@include:`, `@load:`, `@value:`, and `${ENV_VAR}` in the raw YAML. API and YAML editing preserve them; `ProjectMapper.to_core()` resolves them for processing.
- `@include:` loads a YAML mapping relative to the current configuration and recursively resolves directives in it. `@load:` loads a file or dotted configuration path as raw data; directives inside that loaded payload are not recursively resolved.
- `@value:` reads a resolved configuration path and can compose list values. It resolves after includes, loads, and environment-variable expansion. A list of `@value:` references can flatten referenced lists.
- In the editor/backend resolver, `${ENV_VAR}` expands only names allowed by `RESOLVER_ALLOWED_ENV_VARS`. Directive file paths must remain under approved project or shared data roots. Check the deployment settings; a shell variable being set does not prove the editor will resolve it. CLI and editor resolution contexts may differ.
- The target-model picker uses `@load: ${GLOBAL_TARGET_MODEL_DIR}/...` for a shared model and a project-local `@load:` for a local model. The deployment default for `GLOBAL_TARGET_MODEL_DIR` is `shared/target-models`.
- A materialized entity is a fixed snapshot with `materialized.enabled: true`; `materialized.source_state` stores the original configuration for restoration. Snapshot values may be inline or in a sidecar file. Review them as saved data and preserve `source_state` unless materialization is the task. `materialized_at` is expected metadata.
- Normalization can apply committed public-ID links from the project mapping sidecar. Raw YAML and Core structural validation do not include those links; CLI data validation does because it runs the normalizer.

## Avoid false findings

Check context before reporting these as errors:

- `keys: []`, `depends_on: []`, or a root `type: entity` with omitted or null `source`.
- A fixed entity with empty or omitted `values` because append supplies its rows.
- A full fixed row containing `system_id` and `public_id` while saved `columns` contains only data fields.
- An older fixed entity with identity names in `columns`, or a legacy `surrogate_id`.
- `data_source: "@internal"` without an `options.data_sources` entry, or DuckDB without an external data source.
- A key produced by `extra_columns`, an earlier FK, or a source field used only during extraction.
- A left join with permissive constraints or omitted `allow_null_keys` for an optional lookup.
- A missing provider pair in a legacy checked-in project that has not yet been migrated. Report the migration state; do not choose a pair without checking the registry.
- A shared or local directive whose referenced file, environment variable, or service is unavailable in the current workspace.

Do treat an omitted non-merged entity `type` as a Core structural issue. Do not assume it defaults to `entity`.

## Validation and reporting

- For a changed project, or when structural validation is requested, start with:
  ```bash
  rtk uv run python scripts/validate_project.py <path-to-shapeshifter.yml> --workflow structural --log-level ERROR
  ```
  If `rtk` fails because of its wrapper, retry the same command without it.
- The CLI accepts `structural`, `data`, `conformance`, and `all`; `target-model-conformance` is an alias for `conformance`. `data` normalizes the project and may read external files or databases. `conformance` needs a resolved target model. `all` runs structural, data, and conformance.
- The CLI can exit 0 while printing error-severity findings. Read the reported issue severities and workflow statuses; exit status alone does not prove validation passed, and a skipped workflow did not validate that layer.
- Core CLI structural validation does not check the deployment provider registry or the bound project's fixed `data_provider` row. Use Backend YAML Validation for those checks. Neither check proves that an external SEAD database contains the selected provider row.
- Backend conformance validation can treat a missing `@load:` model file as a skipped, valid result. Confirm the resolved model before reporting conformance as complete.
- Report findings with the entity or YAML path, the violated rule, its effect, and the smallest safe fix, ordered by impact. State whether each finding came from Core structural validation, data validation, conformance, Backend YAML Validation, or static review.
- For edits, name the changed file and summarize the change and validation result. Separate confirmed errors from assumptions about unavailable files, database schemas, environment variables, or registry state.
- Do not invent data-source names, tables, sheets, source columns, target columns, provider codes, or schemas. Use project files and the active deployment registry, or state what remains unknown.
- Preserve comments, field order, directives, and local naming where practical.
