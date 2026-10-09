# Make Business Keys Declarative Over Produced Columns

## Status

- Proposed change based on [issue #324](https://github.com/humlab-sead/sead_shape_shifter/issues/324).
- Scope: Core extraction and validation, fixed/materialized persistence, API compatibility, and the entity editor.
- The additive `fixed_schema` API work from [#325](https://github.com/humlab-sead/sead_shape_shifter/issues/325) is complete. Frontend adoption in [#326](https://github.com/humlab-sead/sead_shape_shifter/issues/326) remains open.
- Goal: make `keys` identify fields that an entity already produces. A key must not select, create, or reorder a result column.

## Summary

This proposal recommends separating business-key metadata from entity output columns. The entity configuration and its declared output producers determine which columns exist and their order. `keys` refer to a subset of those columns and continue to drive business-key checks.

For fixed and materialized entities, the backend will expose one positional schema made from managed identity columns followed by produced data columns. Key metadata will not add positions to that schema. Existing projects that rely on keys to add output columns will fail validation with enough detail for their owners to correct the configuration; the system will not rewrite project or values files automatically.

This change touches Core, backend, frontend, and saved project data. It should be planned as a coordinated change rather than delivered as a single issue-sized implementation.

## Problem

`keys` currently has two roles: it describes business-key behavior and also contributes columns to extracted and fixed data. This lets a project refer to a field in `keys` without declaring where the field comes from.

The two roles create inconsistent schemas. A field can appear in the result because it is in `keys`, even though it is absent from `columns`. Fixed row order can also depend on both lists. This makes it harder to validate missing fields and can shift positional values during editing or saving.

The behavior is spread across Core extraction and SQL ordering, fixed-schema derivation and materialization, and frontend grid ordering. The general keys-subset validator exists, but its use in the entity field specification is currently disabled.

## Scope

- Make configured and detected output fields, plus explicitly configured output producers, determine entity columns.
- Keep `keys` as metadata that refers to fields available where the business-key operation uses them.
- Apply the rule to extraction, fixed/materialized rows, validation, column-availability suggestions, and editor save behavior.
- Reject existing configurations that rely on keys to add output columns and explain how owners can correct them without changing project or values files automatically.
- Keep the existing `fixed_schema` response and make its column order independent of `keys`.

## Non-Goals

- Changing the three-tier identity model or the meaning of `system_id` and `public_id`.
- Changing `foreign_keys[].local_keys` or `foreign_keys[].remote_keys` join behavior.
- Removing business-key checks or changing their configured use.
- Making column suggestions a runtime guarantee. Validation and execution remain responsible for confirming actual source data.

## Current Behavior

- `TableConfig.keys_and_columns`, `get_columns()`, and `values_column_order` combine keys with configured columns. `SubsetService.get_subset_columns()` uses those results for extraction, and SQL loader column ordering also reads keys.
- `build_fixed_entity_full_columns()` places keys into the fixed order. Backend persistence uses that order, and materialization currently adds null-valued columns for keys absent from the materialized data.
- `derive_fixed_schema()` reports the backend order, but currently derives it from both keys and columns. The editor reads `fixed_schema.full_columns` on entity hydration, then also rebuilds grid and save order from local columns and keys.
- The operation-aware column resolver includes configured keys among source candidates. A configured key can therefore be suggested even when no output source provides it.
- Fixed-schema API metadata and row-width checks already exist. Those parts should be extended, not recreated.

## Proposed Design

### Output columns and keys

`columns` lists produced data fields in their output order. When a source supports auto-detection and `columns` is empty, the detected source result supplies the data fields. Other explicitly configured producers, such as `extra_columns`, foreign-key outputs, unnest outputs, or merged branches, may add fields at their defined pipeline stages.

`keys` lists business-key fields only. Each key must refer to a field that the entity produces and that is available at the operation that uses it. A key name does not make that field available. Keep using keys for business-key checks and any existing operation that consumes this metadata.

Check known configurations structurally. When source fields are not known until a loader runs, check the key against the loaded output and return a clear validation error if it is missing. Do not treat a key as valid just because it appears in the `keys` list.

The column-availability resolver should suggest business keys from known source and produced fields, not from configured keys themselves. Suggestions remain free-text and advisory, consistent with the completed [stage-aware column suggestions proposal](../done/STAGE_AWARE_COLUMN_SUGGESTIONS/STAGE_AWARE_COLUMN_SUGGESTIONS.md).

### Fixed and materialized rows

For fixed entities, `entity_data.columns` contains produced data fields and excludes managed identity fields. `fixed_schema.full_columns` defines positional row and values-file order: `system_id`, `public_id` when configured, then the produced data columns in their declared or stored order. A field used as a key appears once in the data columns if the entity produces it; `key_columns` describes its business role without adding another position.

Use this same schema to validate row widths, column types, API values updates, materialized data, and editor grids. Materialization must not invent a missing key column filled with nulls. If a key is absent from the output where it is needed, validation should fail and identify the entity, missing key, and expected output schema. For fixed or materialized rows, the error should also show the expected positional column order so the owner can update configuration and values without guessing.

### API and editor behavior

Keep `fixed_schema` additive on entity responses. Populate `full_columns`, `editable_columns`, `identity_columns`, and `key_columns` from the new rule. New frontend code should use this metadata for fixed row order and key editing. It must not rebuild positional order from `keys` when the metadata is present.

Keep the values request's `columns` field during the compatibility period. Accept the new authoritative order and, if needed for existing clients, recognize the exact legacy order and remap its rows by column name before saving. Reject duplicate names, unknown orders, and row widths that match neither accepted layout. Do not guess when column names cannot be mapped safely.

### Existing project validation

Do not add a separate migration tool or write project files or values as a side effect of validation or GET requests. Apply the same strict key validation to existing and new projects.

When a key is not produced at the stage where it is used, validation should fail with an actionable error. The error should name the entity and missing key, explain that `keys` do not create output columns, and point to the relevant way to produce the field, such as declaring it in `columns` or configuring its actual producer. For keys discovered only after loading source data, report the missing field at runtime with the same detail.

For fixed and materialized data, report the expected `fixed_schema.full_columns` order and row-width mismatch where applicable. Owners correct the project configuration and positional values explicitly. Validation must not guess a mapping or alter either file.

## Alternatives Considered

- **Keep keys as implicit output columns and only deduplicate the final schema.** Rejected because it keeps key metadata responsible for creating output fields and leaves missing-key validation unclear.
- **Normalize projects whenever they are read.** Rejected because a read would write project configuration or data files, making inspection and GET requests have side effects.
- **Keep frontend key-based reconstruction indefinitely.** Rejected because it would preserve a second column-ordering rule after the backend already provides authoritative metadata.

## Risks And Tradeoffs

- Existing configurations may rely on a key being selected even when no configured producer supplies it. Those projects will fail strict validation until their owners correct the configuration.
- Fixed values and materialized files are positional. Actionable validation errors must show the expected column order so owners can correct values safely; validation must not guess a mapping or write files.
- Validation quality is important for rollout: vague missing-key errors would block project owners without showing how to fix the configuration.
- Changing the meaning of `entity_data.columns` and fixed values order can affect API clients. Keeping the request field alone is not sufficient if an older client sends the old order, so the transition must either map recognized legacy requests or coordinate a client upgrade.
- Source metadata can be incomplete. Structural checks must not claim that a dynamic source field is missing before the loader has supplied its columns; the runtime check remains necessary.
- Operation-aware suggestions can omit fields when source metadata is unavailable. Keeping controls free-text avoids turning incomplete suggestions into an editor restriction.

## Testing And Validation

- Core tests should show that keys do not add extracted columns or change configured output order. Cover auto-detected sources, explicit columns, generated columns, and missing source keys.
- Specification tests should show that keys must refer to known produced fields, while fields produced by supported configuration stages remain valid. Failure messages should identify the entity, missing key, and relevant producer or stage.
- Fixed-entity tests should cover identity-plus-data ordering, keys already present in columns, duplicate columns, invalid row widths, and missing key fields. Materialization tests should confirm that absent keys fail instead of receiving generated null columns, with the expected column order included where positional values are affected.
- Backend tests should cover `fixed_schema` derivation, GET and PUT normalization, exact new values order, recognized legacy order remapping, and rejection of ambiguous payloads.
- Frontend tests should cover hydration from all `fixed_schema` fields, grid order, keys that are also produced columns, save round-trips, and responses without `fixed_schema` during the transition.
- Integration tests should cover an existing fixed entity with a missing key, materialized values through open/edit/save, and a source-backed entity whose key is missing from the loader result. Confirm validation reports actionable errors and does not rewrite project or values files.

## Acceptance Criteria

- `P-AC-1` Entity output columns come from configured, detected, or explicitly configured output producers. `keys` do not select or create output fields.
- `P-AC-2` Each business key refers to a field available at the operation that uses it. Missing keys fail structural validation when fields are known and runtime validation when fields are discovered by a loader.
- `P-AC-3` Fixed and materialized rows use one backend schema made from managed identity fields and produced data columns. Keys do not add positions or null placeholders.
- `P-AC-4` Validation rejects existing or new configurations whose keys are not produced and reports enough detail to correct them. It does not modify project or values files; fixed and materialized data errors include the expected positional column order.
- `P-AC-5` The frontend uses backend fixed-schema metadata for row order and does not reconstruct order from keys when metadata is present.
- `P-AC-6` Business-key suggestions come from known produced fields; an incomplete suggestion list remains advisory and free-text entry remains available.
- `P-AC-7` Regression tests cover extraction, validation errors, fixed values, materialization, API updates, and frontend save round-trips, including that validation does not modify project or values files.

## Planning Handoff

- Preserve business-key checks and the existing foreign-key identity rules.
- Use `fixed_schema.full_columns` as the positional order for fixed rows and external values.
- Do not infer that a field exists from its presence in `keys` or a suggestion list.
- Do not write project or values files during validation or reads. Existing projects are subject to the same validation as new projects; owners make any required corrections.
- Validation errors must name the entity and missing key, identify why the key is not produced, and show the expected positional column order when fixed or materialized values are affected.
- Before implementation is sequenced, decide how existing API clients that send the legacy fixed-values order will be supported.

## Recommended Delivery Order

1. Confirm validation error details and the API compatibility period.
2. Remove key-driven output selection and add key validation in Core.
3. Update fixed-schema derivation, persistence, and legacy value conversion.
4. Complete frontend adoption and remove key-based order reconstruction.
5. Run the regression and integration checks before retiring legacy input support.

## Open Questions

- Should API v1 accept recognized legacy fixed-values column order during the transition, or should old clients be required to upgrade together with the backend? The recommendation is to accept and remap only an exact, unambiguous legacy order for a limited transition period.
- What is the rollout period for removing the legacy values-order compatibility path? Set it when the deployment and client-upgrade process is known.

## Final Recommendation

Make `keys` references to produced columns, never sources of columns. Keep the backend fixed schema as the only positional schema for fixed and materialized data. Apply strict validation to existing projects and give owners actionable errors so they can correct configurations and positional values themselves; do not introduce an automatic migration step. Retain a narrow compatibility path for known legacy values requests while clients adopt the new contract.
