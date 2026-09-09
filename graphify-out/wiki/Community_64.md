# Community 64

> 35 nodes · cohesion 0.09

## Key Concepts

- **._evaluate_deferred_extra_columns()** (15 connections) — `src/normalizer.py`
- **Any** (10 connections) — `src/transforms/extra_columns.py`
- **extract_column_references()** (9 connections) — `src/transforms/dsl.py`
- **.collect_source_dependencies()** (8 connections) — `src/transforms/extra_columns.py`
- **.get_unresolved_extra_columns()** (8 connections) — `src/transforms/extra_columns.py`
- **DataFrame** (7 connections) — `src/transforms/extra_columns.py`
- **.is_dsl_formula()** (6 connections) — `src/transforms/extra_columns.py`
- **.is_interpolated_string()** (6 connections) — `src/transforms/extra_columns.py`
- **.extract_column_dependencies()** (6 connections) — `src/transforms/extra_columns.py`
- **.evaluate_interpolation()** (6 connections) — `src/transforms/extra_columns.py`
- **extra_columns.py** (5 connections) — `src/transforms/extra_columns.py`
- **.is_escaped_equals_literal()** (4 connections) — `src/transforms/extra_columns.py`
- **.verify_extra_columns()** (4 connections) — `src/transforms/extra_columns.py`
- **.split_extra_columns()** (4 connections) — `src/transforms/extra_columns.py`
- **._validate_formula_expression()** (3 connections) — `src/specifications/entity.py`
- **to_str()** (3 connections) — `src/transforms/extra_columns.py`
- **.unescape_equals_literal()** (3 connections) — `src/transforms/extra_columns.py`
- **.coerce_string_constant_literal()** (3 connections) — `src/transforms/extra_columns.py`
- **Series** (2 connections) — `src/transforms/extra_columns.py`
- **Re-evaluate deferred extra_columns for an entity after FK linking or unnesting.** (1 connections) — `src/normalizer.py`
- **Extract all column references from an expression AST.      Args:         expr: E** (1 connections) — `src/transforms/dsl.py`
- **Extra columns evaluation with support for constants, column copies, interpolated** (1 connections) — `src/transforms/extra_columns.py`
- **Convert value to string, handling numbers and nulls.** (1 connections) — `src/transforms/extra_columns.py`
- **Collect all source column dependencies required to evaluate extra_columns.** (1 connections) — `src/transforms/extra_columns.py`
- **Identify extra_columns that could not be evaluated and their missing dependencie** (1 connections) — `src/transforms/extra_columns.py`
- *... and 10 more nodes in this community*

## Relationships

- [[Community 28]] (18 shared connections)
- [[Community 8]] (2 shared connections)
- [[Community 53]] (2 shared connections)
- [[Community 9]] (2 shared connections)

## Source Files

- `src/normalizer.py`
- `src/specifications/entity.py`
- `src/transforms/dsl.py`
- `src/transforms/extra_columns.py`

## Audit Trail

- EXTRACTED: 125 (98%)
- INFERRED: 3 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*