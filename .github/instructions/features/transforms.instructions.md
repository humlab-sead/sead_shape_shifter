---
applyTo: "src/transforms/**,tests/process/**,tests/test_dispatch*"
---

# Transforms – AI Coding Instructions

## Pipeline Position

Transforms run in this fixed order inside `ShapeShifter.normalize()`: **Filter → Link → Unnest → Translate → Store**. Extra columns are evaluated before unnest. Never reorder.

## Replace Rules (`src/transforms/replace.py`)

`ReplacementRules` is a registry pattern — rules register with `@ReplacementRules.register(key="...")`.

Three spec forms per column (evaluated in order, most specific first):

| Form | When used | Behaviour |
|------|-----------|-----------|
| `list[dict]` | Advanced: ordered rule list | Each dict dispatched to a `ReplacementRule` subclass by `key` |
| `Mapping` | Simple value substitution | `Series.replace(mapping)` |
| `scalar / list / set` | Legacy blank-out | Replaces matched values with `pd.NA`, then forward-fills |

- **Never mix forms** within a single column spec — the evaluator picks one branch and stops.
- Forward-fill (`ffill`) only applies to the legacy scalar/list form. Advanced and mapping forms do not forward-fill.
- `RuleContext` carries `normalize_ops`, `coerce`, `negate`, `report_replaced`, `report_unmatched` — always pass it through when calling a rule's `apply()`.

## Extra Columns (`src/transforms/extra_columns.py`)

`ExtraColumnEvaluator` supports four evaluation modes (checked in order):

1. **DSL formula** — string starting with `=` (e.g. `"=concat(first, ' ', last)"`)
2. **Column copy** — string matching an existing column name exactly
3. **Interpolated string** — string containing `{col_name}` placeholders
4. **Constant** — any other value

- DSL functions: `concat`, `upper`, `lower`, `trim`, `substr`, `coalesce` — no others.
- Deferred evaluation: if a referenced column doesn't exist yet, the entry is returned as deferred and retried after FK linking. Do not raise on missing columns during first pass.
- Escaped braces `{{ }}` produce literal `{ }` — do not treat them as column references.
- `collect_source_dependencies()` returns the set of columns required — use this to detect forward references.

## Unnest (`src/transforms/unnest.py`)

`unnest()` calls `pd.melt()`. Key constraints:

- `id_vars` columns survive the melt and must exist in the DataFrame at unnest time — raises `ValueError` if missing.
- `value_vars` columns are melted away — they must also exist at unnest time. All `extra_columns`, FK-added columns, and `columns` / `keys` are available by then.
- If `value_name` already exists as a column the entity is considered already-melted and unnesting is skipped silently.
- `var_name` and `value_name` are required — missing either raises `ValueError` at config construction, not at runtime.

## Filter (`src/transforms/filter.py`)

- Filters are applied to the raw source DataFrame **before** linking — FK targets are not yet available.
- Do not reference FK-added columns in filter expressions.

## Common Mistakes

- Writing a `ReplacementRule` that forward-fills — only the legacy scalar form does this.
- Referencing a post-link column in a filter.
- Treating interpolated strings and DSL formulas as the same — `=` prefix is the discriminator.
- Forgetting deferred evaluation: raising on a missing column in `extra_columns` instead of deferring.
- Using DSL functions not in the allowlist (`concat`, `upper`, `lower`, `trim`, `substr`, `coalesce`).
- Assuming `value_vars` columns exist before `extra_columns` runs — they may be defined as `extra_columns` themselves.

## Testing Expectations

- Test each replacement form independently (legacy, mapping, advanced rule list).
- Test deferred extra_columns: first pass defers, second pass resolves.
- Test unnest with missing `id_vars` (should raise) and pre-melted input (should skip).
- Construct test DataFrames directly — no project loader or backend needed.
