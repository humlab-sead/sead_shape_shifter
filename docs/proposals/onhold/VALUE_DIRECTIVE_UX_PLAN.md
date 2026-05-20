# @value Directive UX — Implementation Plan

## Current State

The codebase already has good foundations:
- **`src/configuration/utility.py`** — Resolution of scalar `@value` directives and string `+` expressions  
- **`useDirectiveValidation.ts`** — Composable that validates directives via backend API (`/projects/{name}/validate-directive`)  
- **`ForeignKeyEditor.vue`** — Partial support: `normalizeKeysArray` normalizes keys, directive validation is called on blur  
- **`EntityFormDialog.vue`** — `columns` and `keys` use `v-combobox` with `availableColumns`, but **no `@value` directive support at all**

---

## The Key Problem

The `@value` directive serves two purposes that a plain column picklist cannot:

1. **Ergonomics** — a compound key of 8 columns is a single reference instead of 8 chips
2. **Abstraction** — `@value: entities.site.keys` means *"whatever constitutes a site's identity"*, surviving future key changes without touching every dependent entity

The current approach of embedding directives in string expressions (`"@value: X + ['a']"`) is hard to read, hard to write, and impossible to represent safely in a multi-select UI. Analysis of a real 60+ entity project shows:

- ~83% of usages are a **single pure directive** (`'@value: entities.X.field'`)
- ~13% are **two chained directives** (`'@value: X + @value: Y'`)
- ~4% mix a **directive with a literal list** (`"@value: X + ['col']"`)

---

## Chosen Approach: `@value` as a First-Class List Element

Rather than a toggle between "list mode" and "directive mode", the cleanest solution is to allow `@value` directives to appear directly as **items in a YAML list**, with the resolver flattening them in-place:

```yaml
# Old awkward string expression (still supported for backward compat)
columns: "@value: entities.specimen.keys + ['extra_col']"

# New clean list form
columns:
  - "@value: entities.specimen.keys"   # expands and flattens in-place
  - extra_col
```

This is natural YAML, readable, and extensible. A single unified combobox can express the full range — plain columns, directive references, or any mix.

### Serialization Rules

| Content | Stored YAML value |
|---|---|
| Only plain strings | `["v1", "v2", "v3"]` (array) |
| Only a single directive, nothing else | `"@value: dot.path"` (scalar string — backward compat shorthand) |
| Mix of directives and/or literals | `["@value: path1", "col_a", "@value: path2"]` (array) |

The scalar shorthand for a single directive is preserved so existing projects require no migration.

---

## Core Change: List Flattening in `utility.py`

A small, backward-compatible change to `_replace_references`:

```python
# Before: list items resolved independently, no flattening
if isinstance(data, list):
    return [_replace_references(i, full_data=full_data) for i in data]

# After: directive items that resolve to lists are flattened
if isinstance(data, list):
    result = []
    for item in data:
        resolved = _replace_references(item, full_data=full_data)
        if isinstance(item, str) and item.startswith(REF_TAG) and isinstance(resolved, list):
            result.extend(resolved)   # flatten directive expansion
        else:
            result.append(resolved)
    return result
```

This replaces the need for the `+` string expression syntax for all practical cases. The existing string expression parser is kept for backward compatibility with current projects.

---

## Supported Expression Forms (updated)

```
1. Scalar directive:    "@value: path.to.value"            # stored as scalar string
2. List with directive: ["@value: path.to.list", "col_a"]  # NEW: list element, flattened
3. Multi directive:     ["@value: path1", "@value: path2"] # NEW: replaces string "+" syntax
4. Legacy prepend:      "['a', 'b'] + @value: path"        # still resolved, backward compat
5. Legacy chaining:     "@value: p1 + @value: p2"          # still resolved, backward compat
```

---

## Implementation Plan

### Phase 1 — Core: list flattening in `utility.py`

- Modify `_replace_references` to flatten directive items in lists (see above)
- Add tests covering all new list forms
- Existing tests must remain green (full backward compatibility)

### Phase 2 — Frontend: unified combobox with `@value` items

Extend the existing `v-combobox` for `columns`, `keys`, `local_keys`, `remote_keys` to include `@value:` paths alongside plain column names in the items list.

**Item types in the dropdown:**

| Item | Visual treatment |
|---|---|
| Plain column name | Normal chip |
| `@value: entities.X.field` | Distinct chip color + small `@` badge |

**Suggested `@value` paths** served from backend, always include:
```
@value: entities.<entity_name>.keys
@value: entities.<entity_name>.columns
```
(filtered to semantically relevant entities for the field being edited)

**Auto-detection on load:** if the stored value is a scalar string starting with `@value:`, pre-populate the combobox with that single directive item. If the stored value is an array containing `@value:` items, populate all chips correctly.

**Guard rail:** if a user types `@value:` freehand without selecting from the dropdown, show an inline warning: *"Looks like a directive — pick from the suggestions list to ensure a valid path."*

**Serialization on save:**
- All chips are plain strings → store as array
- Exactly one chip and it is a directive → store as scalar string (backward compat shorthand)
- Mixed or multiple directives → store as array

### Phase 3 — Fix `normalizeKeysArray` in `ForeignKeyEditor.vue`

Currently converts everything to `string[]`, destroying scalar directive strings. Fix to preserve them:

```typescript
// Before (destroys directives)
function normalizeKeysArray(keys: any): string[] { ... always returns array ... }

// After
function normalizeKeys(keys: any): string[] | string {
  if (typeof keys === 'string' && keys.startsWith('@value:')) return keys  // preserve scalar directive
  return normalizeKeysArray(keys)  // existing logic for arrays
}
```

### Phase 4 — Backend: context-aware `/valid-directives`

The endpoint `GET /projects/{name}/valid-directives` already exists. Extend it to:
- Accept optional `context_entity` and `field_type` query params
- Return structured suggestions scoped to the entity and field type
- Return the resolved value alongside each suggestion for optional preview display

### Phase 5 — Backend validation: dangling `@value` references

Add a `DanglingValueReferenceSpecification` to `src/specifications.py` that:
1. Scans all entity fields (`columns`, `keys`, `foreign_keys[*].local_keys`, `foreign_keys[*].remote_keys`, `unnest.id_vars`, `unnest.value_vars`, `drop_duplicates`) for `@value:` directives (both scalar and list-element forms)
2. Extracts the dot-path from each directive
3. Calls `dotexists(project_cfg, path)` (from `utility.py`) to verify the path exists
4. Reports an error for each dangling reference

Surface errors through the existing `ValidationService` pipeline so they appear in the frontend validation panel.

### Phase 6 — Legacy string expressions: read-only display

For existing configs that use the `+` string expression syntax (e.g. `"@value: X + ['a']"`):
- Detect on load and display as a read-only chip labelled **Expression (legacy)** with an info icon
- Provide a "Edit in YAML" shortcut that jumps to the YAML editor tab with the field highlighted
- These configs continue to resolve correctly via the existing parser; no migration forced

---

## UX Sketch

Unified combobox — no mode toggle needed:

```
[ Business Keys ]
┌──────────────────────────────────────────────────────────────────┐
│ [@  entities.sample.keys] [extra_col  ×]   + type or pick...    │
└──────────────────────────────────────────────────────────────────┘
  Directive chips shown in accent colour with @ badge
```

```
[ Local Keys ]
┌──────────────────────────────────────────────────────────────────┐
│ [@  entities.site.keys] [@  entities.feature.keys]  + ...       │
└──────────────────────────────────────────────────────────────────┘
  Stored as: ["@value: entities.site.keys", "@value: entities.feature.keys"]
```

---

## Recommended Build Order

1. **Core list flattening** in `src/configuration/utility.py` + tests  
2. **Extend `/valid-directives`** backend endpoint with context-aware path suggestions  
3. **Fix `normalizeKeys`** in `ForeignKeyEditor.vue`  
4. **Extend combobox items** in `EntityFormDialog.vue` (`columns`, `keys`) with `@value` paths + chip styling  
5. **Wire into `ForeignKeyEditor`** for `local_keys` and `remote_keys`  
6. **`DanglingValueReferenceSpecification`** in `src/specifications.py` + tests  
7. **Legacy expression read-only display** in combobox (deferred)
