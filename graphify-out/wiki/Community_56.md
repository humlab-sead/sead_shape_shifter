# Community 56

> 37 nodes · cohesion 0.09

## Key Concepts

- **Specification** (30 connections) — `src/specifications/base.py`
- **ForeignKeyDataSpecification** (17 connections) — `src/specifications/foreign_key.py`
- **ForeignKeySpec** (17 connections) — `src/target_model/data_validators.py`
- **ForeignKeyConfigSpecification** (13 connections) — `src/specifications/foreign_key.py`
- **ForeignKeyConfig** (10 connections) — `src/specifications/foreign_key.py`
- **.is_satisfied_by()** (8 connections) — `src/specifications/foreign_key.py`
- **.get_missing_fields()** (6 connections) — `src/specifications/foreign_key.py`
- **TableStore** (6 connections) — `src/specifications/foreign_key.py`
- **.get_missing_local_fields()** (5 connections) — `src/specifications/foreign_key.py`
- **.get_missing_pending_fields()** (5 connections) — `src/specifications/foreign_key.py`
- **.get_missing_remote_fields()** (5 connections) — `src/specifications/foreign_key.py`
- **.get_report()** (4 connections) — `src/specifications/base.py`
- **.is_satisfied_by()** (4 connections) — `src/specifications/fd.py`
- **.compile_error_message()** (4 connections) — `src/specifications/fd.py`
- **.link_entity()** (4 connections) — `src/transforms/link.py`
- **.has_errors()** (3 connections) — `src/specifications/base.py`
- **.has_warnings()** (3 connections) — `src/specifications/base.py`
- **.__init__()** (3 connections) — `src/specifications/foreign_key.py`
- **.is_already_linked()** (3 connections) — `src/specifications/foreign_key.py`
- **Base specification for project validation.** (2 connections) — `src/specifications/base.py`
- **DataFrame** (2 connections) — `src/specifications/fd.py`
- **Series** (2 connections) — `src/specifications/fd.py`
- **DataFrameGroupBy** (2 connections) — `src/specifications/fd.py`
- **.clear()** (2 connections) — `src/specifications/foreign_key.py`
- **Returns foreign key columns from SEAD columns (performance only).** (1 connections) — `ingesters/sead/metadata.py`
- *... and 12 more nodes in this community*

## Relationships

- [[Community 4]] (6 shared connections)
- [[Community 67]] (6 shared connections)
- [[Community 14]] (6 shared connections)
- [[Community 8]] (6 shared connections)
- [[Community 90]] (5 shared connections)
- [[Community 17]] (5 shared connections)
- [[Community 65]] (3 shared connections)
- [[Community 29]] (3 shared connections)
- [[Community 27]] (2 shared connections)
- [[Community 32]] (2 shared connections)
- [[Community 82]] (2 shared connections)
- [[Community 35]] (1 shared connections)

## Source Files

- `ingesters/sead/metadata.py`
- `src/specifications/base.py`
- `src/specifications/fd.py`
- `src/specifications/foreign_key.py`
- `src/target_model/data_validators.py`
- `src/transforms/link.py`

## Audit Trail

- EXTRACTED: 134 (77%)
- INFERRED: 39 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*