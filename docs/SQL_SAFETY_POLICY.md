# SQL Safety Policy

## Purpose

Shape Shifter accepts SQL for query validation, query execution, schema introspection, SQL-backed entities, and internal DuckDB queries. All of these paths use the same read-only policy before execution.

The policy is implemented in [src/sql_policy.py](../src/sql_policy.py). `validate_read_only_sql()` returns structured validation results. `ensure_read_only_sql()` raises when a caller attempts to execute rejected SQL.

## Allowed SQL

Only one executable SQL statement is allowed. The statement must be a `SELECT`, including a `WITH` query whose executable operation is read-only `SELECT`.

Whitespace, semicolons, and trailing comments do not count as additional executable statements.

## Rejected SQL

The policy rejects:

- More than one executable statement.
- DDL and DML, including `CREATE`, `ALTER`, `DROP`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `REPLACE`, and `TRUNCATE`.
- File, extension, and attachment operations, including `COPY`, `ATTACH`, `DETACH`, `INSTALL`, `LOAD`, `EXPORT`, and `IMPORT`.
- Transaction, session, procedure, and administrative operations, including `BEGIN`, `COMMIT`, `ROLLBACK`, `SET`, `RESET`, `CALL`, `DO`, `PREPARE`, `DEALLOCATE`, `GRANT`, `REVOKE`, `PRAGMA`, `SHOW`, `VACUUM`, and `ANALYZE`.
- Operations that cannot be classified safely as `SELECT`.
- Forbidden operations nested inside a query expression or CTE.

Validation fails closed. A parser result that is empty, malformed, unclassified, or contains a rejected operation is not sent to a database.

## Covered Execution Paths

The policy is applied at both the backend service boundary and the core execution boundary:

- `QueryService.validate_query()` for API validation responses.
- `QueryService.execute_query()` before a SQL loader is created.
- `QueryService.introspect_query_columns()` before parsing or executing introspection SQL.
- `SqlLoader` and its SQLite, PostgreSQL, and UCanAccess implementations before `read_sql()` and scalar execution.
- `DuckDbLoader.read_sql()` and `DuckDbLoader.execute_scalar_sql()`.
- `DuckDbWorkspace.execute()`, `query_df()`, `query_scalar()`, and `explain()`.
- SQL-backed workflow entities and schema operations that execute through these loader methods.

Trusted DuckDB materialization code creates internal tables from DataFrames and is not a client SQL execution path. It remains separate from the read-only query boundary.

## Enforcement Rules

- Callers must validate before opening a connection or invoking a loader.
- A validation warning must never be returned while the unvalidated query is executed.
- Backend callers may translate policy failures into stable API errors; raw SQL, connection details, and filesystem paths must not be returned to clients.
- This policy does not replace database grants, DuckDB runtime restrictions, path containment, result limits, timeout limits, or authorization. Those controls are separate Phase 3 work areas.

## Verification

Focused policy and execution-boundary tests cover single statements, comments, stacked statements, nested writes, non-SELECT operations, DuckDB file export, and direct loader/workspace bypasses. Production PostgreSQL grants and runtime settings require separate deployment verification.
