# TableConfig

> God node · 325 connections · `src/model.py`

**Community:** [[Community 4]]

## Connections by Relation

### calls
- [[.get_sub_table_configs()]] `EXTRACTED`
- [[.get_target_facing_columns()]] `EXTRACTED`

### contains
- [[model.py]] `EXTRACTED`

### imports
- [[entity.py]] `EXTRACTED`
- [[shapeshift_service.py]] `EXTRACTED`
- [[normalizer.py]] `EXTRACTED`
- [[conformance.py]] `EXTRACTED`
- [[materialization.ts]] `EXTRACTED`
- [[sql_loaders.py]] `EXTRACTED`
- [[constraints.py]] `EXTRACTED`
- [[resolvers.py]] `EXTRACTED`
- [[dispatch.py]] `EXTRACTED`
- [[base.py]] `EXTRACTED`
- [[base_loader.py]] `EXTRACTED`
- [[ForeignKeySpec]] `EXTRACTED`
- [[link.py]] `EXTRACTED`
- [[validate_fk_service.py]] `EXTRACTED`
- [[caches.py]] `EXTRACTED`
- [[filter.py]] `EXTRACTED`
- [[extract.py]] `EXTRACTED`
- [[unnest.py]] `EXTRACTED`
- [[branch.py]] `EXTRACTED`

### method
- [[.__init__()]] `EXTRACTED`
- [[FixedEntityTypeConvention]] `EXTRACTED`
- [[materialize.py]] `EXTRACTED`
- [[drop_duplicate_rows()]] `EXTRACTED`
- [[.keys()]] `EXTRACTED`
- [[AppendConfig]] `EXTRACTED`
- [[.apply_column_renaming()]] `EXTRACTED`
- [[.create_append_config()]] `EXTRACTED`
- [[.values()]] `EXTRACTED`
- [[ColumnType]] `EXTRACTED`
- [[.extra_columns()]] `EXTRACTED`
- [[.get_columns()]] `EXTRACTED`
- [[.get_target_facing_foreign_key_targets()]] `EXTRACTED`
- [[.options()]] `EXTRACTED`
- [[.add_public_id_column()]] `EXTRACTED`
- [[.add_system_id_column()]] `EXTRACTED`
- [[.branches()]] `EXTRACTED`
- [[.columns()]] `EXTRACTED`
- [[.drop_fk_columns()]] `EXTRACTED`
- [[.get_source_public_id()]] `EXTRACTED`

### rationale_for
- [[Configuration for a database table. Read-Only. Wraps table setting from entities]] `EXTRACTED`

### references
- [[.reorder_columns()]] `EXTRACTED`
- [[.tables()]] `EXTRACTED`

### uses
- [[ShapeShiftService]] `INFERRED`
- [[FixedEntityTypeConvention]] `INFERRED`
- [[ShapeShifter]] `INFERRED`
- [[TaskListSidecarManager]] `INFERRED`
- [[SqlLoader]] `INFERRED`
- [[ConnectTestResult]] `INFERRED`
- [[LoaderType]] `INFERRED`
- [[ProjectSpecification]] `INFERRED`
- [[DataLoader]] `INFERRED`
- [[task_service.py]] `INFERRED`
- [[materialization_service.py]] `INFERRED`
- [[UCanAccessSqlLoader]] `INFERRED`
- [[table_store.py]] `INFERRED`
- [[Specification]] `INFERRED`
- [[ShapeShiftCache]] `INFERRED`
- [[CoreSchema]] `INFERRED`
- [[ForeignKeyConstraintViolation]] `INFERRED`
- [[ForeignKeyNullConstraintViolation]] `INFERRED`
- [[ConformanceIssue]] `INFERRED`
- [[ReconciliationSourceResolver]] `INFERRED`

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*