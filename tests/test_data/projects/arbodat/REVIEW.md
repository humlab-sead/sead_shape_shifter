# arbodat shapeshifter.yml — Configuration Review

**Date:** 2026-06-30
**File:** `data/projects/arbodat/shapeshifter.yml`
**Validator command:**
```
rtk uv run python scripts/validate_project.py data/projects/arbodat/shapeshifter.yml --workflow all --log-level ERROR
```

---

## Findings

### High

#### H1 — `sample_group` → FK to `method`: wrong `remote_keys`

- **Path:** `entities.sample_group.foreign_keys[method]`
- **Rule:** FK values must reference the parent entity's `system_id`. `remote_keys` must name a column that exists in the target entity after extraction.
- **Evidence:** Validator reports `FK_DATA_INTEGRITY: 1 foreign key value(s) not found in 'method' (11)`.
- **Root cause:** `extra_columns: method_id: 11` produces the constant `11`, which is the `system_id` of the intended method row, not its `method_id` value (which is `53`). The FK join `method.method_id = 11` finds no match.
- **Impact:** `sample_group` → `method` FK link fails for all rows; `method_id` is never resolved in `sample_group`.
- **Fix:**

```yaml
# sample_group
foreign_keys:
- entity: method
  local_keys: [method_id]
  remote_keys: [system_id]    # was: [method_id]
  how: inner
  ...
```

---

### Medium

#### M1 — `dataset` FK to `project`: `contraints` typo silently ignores `allow_unmatched_left: false`

- **Path:** `entities.dataset.foreign_keys[project]`
- **Rule:** All constraint keys must be spelled correctly; unrecognised keys are silently ignored.
- **Evidence:** The FK block has both a misspelled `contraints` block (containing `allow_unmatched_left: false`) and a valid `constraints` block (which does not include `allow_unmatched_left`). The misspelled block is dropped; the effective constraint defaults to permissive.
- **Impact:** Projects with no matching `Projekt` in `project` are silently retained rather than rejected. This may produce orphaned `dataset` rows.
- **Fix:** Remove the `contraints` block and add `allow_unmatched_left: false` to the valid `constraints` block:

```yaml
# dataset → project FK
- entity: project
  local_keys: [Projekt]
  remote_keys: [Projekt]
  how: left
  constraints:
    cardinality: many_to_one
    require_unique_left: false
    allow_null_keys: false
    allow_unmatched_left: false    # moved from misspelled block
```

---

#### M3 — `method_group`: `method_group_id` absent from `columns`

- **Path:** `entities.method_group.columns`
- **Rule:** `columns` for SQL entities declares which columns are kept; FK `remote_keys` columns must be present in the processed entity.
- **Evidence:** The query SELECTs `method_group_id, group_name, description`, but `columns: [group_name, description]` omits `method_group_id`. The FK from `method` uses `remote_keys: [method_group_id]`. The validator did not hard-error here because the FK is a `left` join with `allow_null_keys: true`, which suppresses strict integrity checking.
- **Impact:** If the system enforces `columns` as a filter, `method_group_id` is dropped and the `method → method_group` join fails silently; `sead_method_group_id` will be unresolved for all method rows.
- **Fix:**

```yaml
# method_group
columns: [method_group_id, group_name, description]    # add method_group_id
```

> **Note:** Confirm whether `keys` columns are preserved regardless of `columns` before applying this fix. If the system always retains `keys`, the issue may be cosmetic only.

---

### Low

#### L1 — `site_property.unnest.value_vars` overlaps with `id_vars`

- **Path:** `entities.site_property.unnest`
- **Rule:** `value_vars` should not overlap with `id_vars`.
- **Evidence:** `id_vars: [Fustel, EVNr]`; `value_vars: '@value: entities.site_property.columns'` resolves to `[Fustel, EVNr, okFustel, Limes, TK, AnmFustel]`, which includes the two id_vars.
- **Impact:** Whether the overlap is rejected or silently handled depends on the unnest implementation. If silently handled, no harm. If strict, unnesting fails.
- **Assumption:** The system likely handles the overlap gracefully, but the intent appears to be `value_vars: [okFustel, Limes, TK, AnmFustel]` only. Consider using a more targeted `@value:` reference or an explicit list if the columns are stable.

---

#### L2 — `analysis_entity.columns` does not include its own `keys`

- **Path:** `entities.analysis_entity`
- **Rule:** Keys should normally be present in `columns` or be produced before FK linking.
- **Evidence:** `keys: [Projekt, Befu, ProbNr, analysis_entity_type, analysis_entity_value]` but `columns: [PCODE, Fraktion, cf, RTyp, Zust]`. All key columns arrive exclusively through `append`. This is valid since `values: []` and all rows come from append sources, but it means the entity's declared `columns` is not the full column schema.
- **Impact:** Low. The config is consistent internally (append items provide all key columns). Fragile if append sources change.

---

#### L3 — `contact_type`: unknown field `contact_types`

- **Path:** `entities.contact_type.contact_types`
- **Rule:** Entity-level fields should be recognised Shape Shifter config keys.
- **Evidence:** `contact_types: [ArchAusg, ArchBear, BotBear, Aut, BotBest]` is not a standard entity field. It does not appear to be referenced via `@value:` anywhere in the file.
- **Impact:** Silently ignored by the runtime. Dead metadata or a documentation annotation. No runtime risk.

---

#### L4 — `dataset_contacts` FK to `_project_contact`: `extra_columns` inside FK block

- **Path:** `entities.dataset_contacts.foreign_keys[_project_contact].extra_columns`
- **Rule:** FK blocks do not normally carry `extra_columns`; this is a non-standard placement.
- **Evidence:** No other FK block in this file uses `extra_columns`. The intent appears to be: when joining with `_project_contact`, carry `contact_name` into `dataset_contacts`.
- **Impact:** If the system supports this extension, it works. If not, it is silently ignored and `contact_name` would need to be produced another way.

---

## Conformance Errors (target model compliance — in-progress)

These are not YAML config bugs. They indicate the project does not yet implement all entities required by the SEAD target model. They should be addressed as the project progresses but do not indicate structural or identity errors in the existing config.

| Entity | Issue | Notes |
|---|---|---|
| `taxa_tree_master` | Required by target model (induced by `abundance`, `ecocode`) but not declared | Entity not yet implemented |
| `property_type` | Required by target model (induced by `abundance_property`, `site_property`, `feature_property`) but not declared | Entity not yet implemented |
| `analysis_entity` | Missing target column `dataset_id`; append items missing `physical_sample_id` | FK target `dataset` required by target model |
| `abundance_ident_level` | Missing target column `abundance_id`; FK to `abundance` required | Source is `analysis_entity`, not `abundance` — FK may be needed |
| `coordinate_system` | Missing target column `coordinate_system` | Column name collision with entity name |
| `site_property`, `feature_property` | Missing `property_type_id`, `property_value` | Depend on missing `property_type` entity |

---

## Data Warnings

| Entity | Code | Notes |
|---|---|---|
| `dating`, `dating_chronological_period`, `site_natural_region` | `EMPTY_RESULT` | No data in source for the filtered project set; not a config error |
| `relative_dating` → `relative_ages` | `FK_DATA_INTEGRITY` | 5 `ArchDat` codes (`Meso2, BZ, Meso, La, NZ`) absent from `relative_ages_arbodat_pilot_subset.xlsx`; data coverage gap, not a config error |
| `sample_group` → `method` | `FK_DATA_INTEGRITY` | Confirms **H1** above |

---

## Summary

| Severity    | Count | Items                                                                                        |
|-------------|-------|----------------------------------------------------------------------------------------------|
| High        | 1     | H1 (`sample_group → method` wrong `remote_keys`)                                             |
| Medium      | 2     | M1 (`contraints` typo), M3 (`method_group.columns` missing key) |
| Low         | 4     | L1–L4                                                                                        |
| Conformance | ~10   | Missing target-model entities/columns — in-progress work                                     |
| Data        | 4     | Empty results + FK coverage gaps — not config bugs                                           |

**Recommended immediate fixes:** H1, M1. Confirm system behaviour for `keys` vs `columns` before applying M3.
