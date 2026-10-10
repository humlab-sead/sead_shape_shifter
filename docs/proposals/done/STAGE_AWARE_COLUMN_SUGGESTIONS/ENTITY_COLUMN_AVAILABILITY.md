# Entity Editor Column Availability

This note records the investigation of [issue #511](https://github.com/humlab-sead/sead_shape_shifter/issues/511): entity-editor column suggestions omit names that can be produced by configured transformations. It defines which columns each editor control should suggest based on when the corresponding operation runs. This is an investigation note; it does not describe an implemented shared resolver.

## Findings

The reported behavior is real, but the available history does not point to a recent regression. The FK column-introspection service was introduced in #202 with the legacy `value_column` unnest shape. The current runtime uses `id_vars`, `value_vars`, `var_name`, and `value_name`. Its tests still assert legacy `value_id` and `value_name` outputs, and do not assert the outputs for the current configuration shape. The general deduplication and drop-empty suggestions were added later in #303 to comboboxes that previously accepted free text; those suggestions have been incomplete since their introduction.

The controls are comboboxes, so a user can type a missing column name. The defect is incomplete or stale suggestions, not an absolute inability to configure these fields.

`get_target_facing_columns()` is used by target-model conformance. It describes the entity's final target-facing shape, not all intermediate inputs. It has no stage parameter and should not be used as the shared source for every editor dropdown. `get_columns()` and `keys_and_columns` describe configured names, but do not resolve loader output, transformation timing, or the current unsaved editor draft.

## Intended Suggestions

Suggestions should represent columns available at the operation's execution stage. A suggestion is not a guarantee that the runtime data contains the column; source files and queries can still drift. Keep comboboxes free-text capable and validate actual availability during project validation or execution.

| Editor control | Columns to suggest |
| --- | --- |
| Entity `Columns` | Source fields that can be selected for the entity. For files and SQL, use detected loader/query fields. For an entity source, use the source entity's processed output, not only its configured `columns` and `keys`. Fixed entities define their own fields; merged entities use the union of branch outputs. Extra-column output names are configured separately and should be available to controls that consume those outputs. |
| `Business Keys` | Entity data fields that can be present by the duplicate-key check. Include source fields and resolvable generated fields; do not suggest the automatically assigned `system_id` as a business key. |
| `Replacements` | Columns present during extraction after eligible `extra_columns` have been evaluated. Replacements run before linking and unnesting, so do not suggest FK or unnest outputs. An extra column deferred because it depends on a later stage is not available for this operation. |
| `Drop Duplicates` | Columns present at the deduplication call. Normally this is the extraction output after early extras and linking-independent projection, before FK linking and unnesting. If a selected subset includes the configured unnest `var_name` or `value_name`, the implementation delays that deduplication until after unnesting; then suggest only columns present in that post-unnest table. |
| `Drop Empty Rows` | Columns present at the final cleanup call: after linking and, when configured, unnesting and post-unnest extra-column evaluation. Do not suggest unnest `value_vars` unless they also survive as `id_vars`; they are consumed by the melt. This setting currently has no explicit stage selector. |
| FK `Local Keys` | Columns present when the FK is linked. The first linking pass can use extracted columns and early extras; later FKs can also use columns added by earlier FKs. A second pass runs after unnesting, so keys made available only by unnest outputs can be used there. Suggestions should use the current unsaved local entity draft, not only the saved project. |
| FK `Remote Keys` and FK extra columns | Columns in the selected parent entity's processed output, including available keys, declared columns, computed columns, unnest outputs, and linked columns. Include `system_id` as a valid match key. The child FK value is still populated from the parent's `system_id`; `remote_keys` controls row matching. |
| Unnest `ID Variables` and `Value Variables` | Input columns present immediately before unnesting: extracted fields, eligible extra columns, and columns added by the first FK-link pass. The resulting table contains `id_vars`, `var_name`, and `value_name`; `value_vars` are not output columns unless also listed in `id_vars`. |
| Extra-column source references | Columns available when that expression is evaluated. Some expressions can be deferred until FK linking or unnesting, so the editor may show later-stage candidates but should distinguish them from extraction-time inputs. The new extra-column name itself is an output, not a source reference. |
| Filter column fields | Columns available at the filter's selected stage: `extract`, `after_link`, or `after_unnest`. The current filter editor uses text fields rather than column suggestions. |

## Runtime Call Sequence

The public workflow in `src/workflow.py` resolves the project, calls `ShapeShifter.normalize()`, optionally drops FK columns, optionally translates column names, then stores the result. Within normalization, entities are processed in dependency order; deferred FK links are retried after the entity loop.

For each entity, the current call sequence is:

1. Resolve each base, append, or branch source.
2. `SubsetService.get_subset()` selects configured source fields and helper dependencies, evaluates available `extra_columns`, performs early per-subtable deduplication unless delayed for unnest, and applies replacements. The normalizer passes `drop_empty=False` here.
3. Apply append/branch column handling and combine the extracted tables.
4. Evaluate remaining early `extra_columns` and run `extract` filters.
5. Run entity-level deduplication unless it must wait for unnest output. This follows the extraction filters; early per-subtable deduplication may already have run.
6. Store the intermediate table and link available foreign keys.
7. Re-evaluate deferred extra columns, then run `after_link` filters.
8. If unnest is configured, unnest the table, run FK linking again, re-evaluate deferred extra columns, and run `after_unnest` filters.
9. Run delayed deduplication when selected deduplication columns depend on unnest output.
10. Check business keys for duplicates, then apply configured `drop_empty_rows` once, after linking and any unnesting.
11. Add a missing `system_id`, add a missing `public_id` column, apply sidecar links, retry deferred FK links, verify extra columns, and reorder columns.
12. After all entities are processed, retry deferred FK links. The outer workflow then performs optional FK-column removal and translation before storing.

At the extraction subset step, `get_subset2()` evaluates eligible extra columns, then performs deduplication, applies `drop_empty_rows` only if the caller enabled it, and applies replacements. In the normalizer's entity path that caller explicitly disables the subset-level empty-row removal; the configured `drop_empty_rows` runs at step 10 instead.

## Resolver Direction

A shared resolver should return stage-specific candidate sets from the current entity draft and known loader/source metadata. At minimum, distinguish extraction, before unnest, after link, after unnest, and final cleanup. FK remote suggestions should use the selected saved parent entity; FK local suggestions should account for unsaved edits. The resolver should not equate "configured somewhere" with "available at every stage".

Relevant implementation and tests:

- [`src/normalizer.py`](../../../../src/normalizer.py)
- [`src/extract.py`](../../../../src/extract.py)
- [`src/transforms/unnest.py`](../../../../src/transforms/unnest.py)
- [`src/model.py`](../../../../src/model.py)
- [`src/target_model/conformance.py`](../../../../src/target_model/conformance.py)
- [`frontend/src/components/entities/EntityFormDialog.vue`](../../../../frontend/src/components/entities/EntityFormDialog.vue)
- [`frontend/src/components/entities/ForeignKeyEditor.vue`](../../../../frontend/src/components/entities/ForeignKeyEditor.vue)
- [`backend/app/services/column_introspection_service.py`](../../../../backend/app/services/column_introspection_service.py)
- [`backend/tests/services/test_column_introspection_service.py`](../../../../backend/tests/services/test_column_introspection_service.py)