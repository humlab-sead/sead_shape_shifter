# Community 46

> 34 nodes · cohesion 0.14

## Key Concepts

- **QueryService** (30 connections) — `backend/app/api/v1/endpoints/query.py`
- **query.py** (23 connections) — `backend/app/api/v1/endpoints/query.py`
- **QueryService** (20 connections) — `backend/app/services/query_service.py`
- **QueryResult** (18 connections) — `backend/app/api/v1/endpoints/query.py`
- **QueryValidation** (18 connections) — `backend/app/api/v1/endpoints/query.py`
- **QueryExecution** (16 connections) — `backend/app/api/v1/endpoints/query.py`
- **QueryIntrospection** (15 connections) — `backend/app/api/v1/endpoints/query.py`
- **DataSourceService** (14 connections) — `backend/app/api/v1/endpoints/query.py`
- **ProjectService** (13 connections) — `backend/app/api/v1/endpoints/query.py`
- **DataSourceConfig** (12 connections) — `backend/app/api/v1/endpoints/query.py`
- **_resolve_data_source_config()** (9 connections) — `backend/app/api/v1/endpoints/query.py`
- **execute_query()** (7 connections) — `backend/app/api/v1/endpoints/query.py`
- **introspect_query_columns()** (7 connections) — `backend/app/api/v1/endpoints/query.py`
- **query.py** (6 connections) — `backend/app/models/query.py`
- **QueryResult** (6 connections) — `backend/app/models/query.py`
- **QueryValidation** (6 connections) — `backend/app/models/query.py`
- **validate_query()** (5 connections) — `backend/app/api/v1/endpoints/query.py`
- **QueryExecution** (5 connections) — `backend/app/models/query.py`
- **get_query_service()** (4 connections) — `backend/app/api/v1/endpoints/query.py`
- **QueryIntrospection** (4 connections) — `backend/app/models/query.py`
- **is_internal_data_source()** (4 connections) — `backend/app/services/query_service.py`
- **\nQuery execution API endpoints.\n** (1 connections) — `backend/app/api/v1/endpoints/query.py`
- **Dependency to get query service instance.** (1 connections) — `backend/app/api/v1/endpoints/query.py`
- **Resolve a data source from a project or the global data source directory.      R** (1 connections) — `backend/app/api/v1/endpoints/query.py`
- **Validate a SQL query without executing it.      Args:         data_source_name:** (1 connections) — `backend/app/api/v1/endpoints/query.py`
- *... and 9 more nodes in this community*

## Relationships

- [[Community 131]] (20 shared connections)
- [[Community 1]] (11 shared connections)
- [[Community 3]] (11 shared connections)
- [[Community 6]] (11 shared connections)
- [[Community 5]] (9 shared connections)
- [[Community 11]] (9 shared connections)
- [[Community 14]] (9 shared connections)
- [[Community 2]] (8 shared connections)
- [[Community 85]] (2 shared connections)
- [[Community 24]] (2 shared connections)
- [[Community 52]] (1 shared connections)
- [[Community 0]] (1 shared connections)

## Source Files

- `backend/app/api/v1/endpoints/query.py`
- `backend/app/models/query.py`
- `backend/app/services/query_service.py`

## Audit Trail

- EXTRACTED: 135 (53%)
- INFERRED: 120 (47%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*