# Community 131

> 25 nodes · cohesion 0.13

## Key Concepts

- **QueryExecutionError** (12 connections) — `backend/app/exceptions.py`
- **QuerySecurityError** (11 connections) — `backend/app/exceptions.py`
- **.validate_query()** (9 connections) — `backend/app/services/query_service.py`
- **DataSourceConfig** (9 connections) — `backend/app/services/query_service.py`
- **QueryValidation** (8 connections) — `backend/app/services/query_service.py`
- **QueryResult** (8 connections) — `backend/app/services/query_service.py`
- **.execute_query()** (7 connections) — `backend/app/services/query_service.py`
- **.introspect_query_columns()** (7 connections) — `backend/app/services/query_service.py`
- **Statement** (7 connections) — `backend/app/utils/sql.py`
- **extract_select_columns()** (6 connections) — `backend/app/utils/sql.py`
- **has_wildcard_select()** (5 connections) — `backend/app/utils/sql.py`
- **get_statement_type()** (5 connections) — `backend/app/utils/sql.py`
- **has_where_clause()** (5 connections) — `backend/app/utils/sql.py`
- **_resolve_select_alias()** (4 connections) — `backend/app/utils/sql.py`
- **Execute a SQL query against a data source.      Args:         data_source_name:** (2 connections) — `backend/app/api/v1/endpoints/query.py`
- **Identifier** (2 connections) — `backend/app/utils/sql.py`
- **Query execution failed.      Common causes:     - Data source connection issues** (1 connections) — `backend/app/exceptions.py`
- **Query contains prohibited operations.      Occurs when query attempts destructiv** (1 connections) — `backend/app/exceptions.py`
- **Validate a SQL query for safety and syntax.          Args:             query: SQ** (1 connections) — `backend/app/services/query_service.py`
- **Introspect column names from a SQL query without fetching data.          Execute** (1 connections) — `backend/app/services/query_service.py`
- **Return effective output name for a SELECT-list identifier: alias > real_name > r** (1 connections) — `backend/app/utils/sql.py`
- **Return True if the outermost SELECT clause projects all columns via * or table.*** (1 connections) — `backend/app/utils/sql.py`
- **Extract projected column names/aliases from the outermost SELECT clause.      Fo** (1 connections) — `backend/app/utils/sql.py`
- **Return the SQL statement type (SELECT, INSERT, etc.) from a parsed statement.** (1 connections) — `backend/app/utils/sql.py`
- **Return True if the statement contains a WHERE clause.** (1 connections) — `backend/app/utils/sql.py`

## Relationships

- [[Community 46]] (20 shared connections)
- [[Community 66]] (6 shared connections)
- [[Community 144]] (6 shared connections)
- [[Community 3]] (3 shared connections)
- [[Community 6]] (3 shared connections)

## Source Files

- `backend/app/api/v1/endpoints/query.py`
- `backend/app/exceptions.py`
- `backend/app/services/query_service.py`
- `backend/app/utils/sql.py`

## Audit Trail

- EXTRACTED: 80 (69%)
- INFERRED: 36 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*