---
description: "Use when validating or editing shapeshifter.yml project files. Covers required structure, entity types, identity system, foreign keys, extra columns, dependency rules, data sources, common errors, and valid patterns."
applyTo: "**/shapeshifter.yml,data/projects/**/*.yml,data/projects/**/*.yaml"
---
# Shape Shifter YAML Validation Rules

## Required Top-Level Structure

```yaml
metadata:
  name: string                    # REQUIRED
  type: shapeshifter-project      # REQUIRED - exact string
entities:                         # REQUIRED - at least 1 entity
  <name>: { ... }
options:                          # OPTIONAL
  data_sources: {}
```

---

## Entity Types and Required Fields

| Type | Required | Notes |
|------|----------|-------|
| `fixed` | `columns`, `values`, `public_id` | Values row width must equal columns length |
| `sql` | `data_source`, `query` OR `table` | Not both; data_source must exist in `options.data_sources` |
| `csv` | `filename` (or `options.filename`) | |
| `xlsx` / `openpyxl` | `filename`, `sheet_name` (or in `options`) | |
| `entity` | `source` | Source entity must exist |
| `merged` | `items` list of sub-entity configs | Each branch gets a discriminator column |

---

## Three-Tier Identity System

| Tier | Field | Rule |
|------|-------|------|
| 1 | `system_id` | Auto-generated. All FK values are `system_id`. Never declare manually except in `fixed` entities. |
| 2 | `keys` | Business keys for deduplication and FK matching. Optional. |
| 3 | `public_id` | Target schema column name. Must end with `_id`. Required for fixed entities and FK parents. |

**Fixed entity `columns` list must include `system_id` and `public_id`.**  
**All other entity types: do not put `system_id` or `public_id` in `columns`.**

---

## Foreign Key Rules

- `entity` must reference an existing entity.
- `local_keys` must exist in: `columns`, source entity columns, or `extra_columns`.
- `remote_keys` must exist in the target entity.
- No self-references.
- `extra_columns` + FK using that column is **valid** — not an error.
- Use `defer_dependency: true` on a FK config to break circular dependency chains.

---

## Extra Columns

```yaml
extra_columns:
  col_name: 42               # constant integer/string
  col_name: other_col        # copies an existing column
  col_name: "{a} {b}"        # interpolated string
  col_name: "=concat(a, b)"  # DSL formula (concat/upper/lower/trim/substr/coalesce)
```

Evaluated before unnest. Deferred automatically if a referenced column is not yet available.

---

## Dependency Rules

- Topological sort: dependencies must exist and be acyclic.
- Dependency sources: `source:`, `foreign_keys[].entity`, `depends_on: []`.
- Circular deps → add `defer_dependency: true` on the FK that creates the cycle.

---

## Directives

```yaml
field: "@include: ${DIR}/file.yml"   # inline YAML inclusion
field: "@value: path.to.key"         # value lookup
field: "${ENV_VAR}"                  # environment variable substitution
```

- Preserve directives in YAML and API layer; never resolve them in services.
- Resolve only at the API → Core boundary (`ProjectMapper.to_core()`).
- Core always receives resolved values — never raw directives.

---

## Common Errors

| Error | Cause |
|-------|-------|
| Column width mismatch | Fixed entity: `columns` length ≠ row width in `values` |
| Missing `public_id` | Fixed entity, or entity that is a FK parent |
| Missing `data_source` | `type: sql` entity |
| Missing `sheet_name` | `type: xlsx` or `openpyxl` entity |
| Missing `source` | `type: entity` derived entity |
| Non-existent FK target | `foreign_keys[].entity` not in entities |
| `system_id` in `columns` | Non-fixed entity declaring `system_id` manually |
| Circular dependency | No `defer_dependency: true` on the FK that breaks the cycle |

---

## Materialized Entities

```yaml
materialized:
  enabled: true
  timestamp: "2024-01-15T10:30:00Z"
  source_hash: "abc123"
```

- Treat as frozen snapshot; do not re-validate data.
- FK references reflect dependencies at time of materialization.
