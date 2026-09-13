"""Security regression coverage for SQL policy and internal DuckDB execution."""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from backend.app.exceptions import QuerySecurityError
from backend.app.models.data_source import DataSourceConfig
from backend.app.services.query_service import QueryService
from src.loaders.duckdb_loader import DuckDbLoader, DuckDbWorkspace
from src.loaders.sql_loaders import PostgresSqlLoader, SqliteLoader
from src.model import DataSourceConfig as CoreDataSourceConfig
from src.sql_policy import validate_read_only_sql
from src.table_store import TableStore

FORBIDDEN_OPERATIONS = [
    "DROP TABLE users",
    "ALTER TABLE users ADD COLUMN secret TEXT",
    "CREATE TABLE users_copy AS SELECT * FROM users",
    "INSERT INTO users VALUES (1)",
    "UPDATE users SET name = 'changed'",
    "DELETE FROM users",
    "TRUNCATE users",
    "MERGE INTO users USING other ON users.id = other.id WHEN MATCHED THEN UPDATE SET name = other.name",
    "REPLACE INTO users VALUES (1)",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "SET search_path TO public",
    "RESET search_path",
    "CALL dangerous()",
    "DO $$ BEGIN PERFORM 1; END $$",
    "PREPARE query AS SELECT 1",
    "DEALLOCATE query",
    "GRANT SELECT ON users TO public",
    "REVOKE SELECT ON users FROM public",
    "PRAGMA enable_object_cache=true",
    "SHOW tables",
    "VACUUM",
    "ANALYZE users",
    "COPY users TO '/tmp/users.csv'",
    "ATTACH 'other.duckdb' AS other",
    "DETACH other",
    "INSTALL httpfs",
    "LOAD httpfs",
    "EXPORT DATABASE '/tmp/export'",
    "IMPORT DATABASE '/tmp/import'",
]


@pytest.mark.parametrize("query", FORBIDDEN_OPERATIONS)
def test_read_only_policy_rejects_destructive_and_administrative_sql(query: str) -> None:
    result = validate_read_only_sql(query)

    assert result.is_valid is False
    assert result.errors


@pytest.mark.parametrize(
    "query",
    [
        "SELECT 1; SELECT 2",
        "SELECT 1 /* comment ; SELECT 2 */; SELECT 3",
        "SELECT 1 -- comment ; SELECT 2\n; SELECT 3",
        "SELECT 1; /* trailing comment */ SELECT 2",
        "\n\tSELECT 1\n;\n\tSELECT 2",
    ],
)
def test_read_only_policy_rejects_stacked_statements_hidden_by_comments_or_whitespace(query: str) -> None:
    result = validate_read_only_sql(query)

    assert result.is_valid is False
    assert any("multiple statements" in error.lower() for error in result.errors)


def test_read_only_policy_preserves_literals_containing_sql_metacharacters() -> None:
    result = validate_read_only_sql("SELECT * FROM users WHERE name = 'a; DROP TABLE users --'")

    assert result.is_valid is True


@pytest.mark.parametrize("identifier", ['user"data', "schema.table", "name; DROP TABLE users", ""])
def test_sql_identifier_quoting_handles_edge_cases_without_interpolation(identifier: str) -> None:
    loader = SqliteLoader(data_source={})

    if not identifier:
        with pytest.raises(ValueError):
            loader.quote_name(identifier)
    else:
        quoted = loader.quote_name(identifier)
        assert quoted.startswith('"') and quoted.endswith('"')
        assert "DROP TABLE" in quoted or ";" in quoted or '""' in quoted or "." in quoted


@pytest.mark.asyncio
async def test_query_service_caps_user_limit_with_outer_limit() -> None:
    service = QueryService()
    config = DataSourceConfig(name="test", driver="sqlite", options={"filename": ":memory:"})
    loader = Mock()
    loader.inject_limit.side_effect = SqliteLoader(data_source={}).inject_limit
    loader.read_sql = AsyncMock(return_value=pd.DataFrame({"id": range(2)}))

    with patch("backend.app.services.query_service.DataLoaders.get", return_value=Mock(return_value=loader)):
        await service.execute_query(config, "SELECT * FROM users LIMIT 999999", limit=100)

    called_query = loader.read_sql.await_args.args[0]
    assert "LIMIT 100" in called_query.upper()
    assert "999999" not in called_query


@pytest.mark.asyncio
async def test_query_service_rejects_stacked_sql_before_loader() -> None:
    config = DataSourceConfig(name="test", driver="sqlite", options={"filename": ":memory:"})
    service = QueryService()

    with patch("backend.app.services.query_service.DataLoaders.get") as get_loader:
        with pytest.raises(QuerySecurityError, match="prohibited operations"):
            await service.execute_query(config, "SELECT 1; SELECT 2")

        get_loader.assert_not_called()


@pytest.mark.parametrize("query", FORBIDDEN_OPERATIONS)
@pytest.mark.asyncio
async def test_postgres_loader_rejects_policy_cases_before_connection(query: str) -> None:
    config = CoreDataSourceConfig(name="test", cfg={"driver": "postgres", "options": {"database": "test"}})
    loader = PostgresSqlLoader(data_source=config)

    with patch("src.loaders.sql_loaders.create_engine") as create_engine:
        with pytest.raises(ValueError):
            await loader.read_sql(query)

        create_engine.assert_not_called()


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM read_csv('/outside/file.csv')",
        "SELECT * FROM read_csv_auto('/outside/file.csv')",
        "SELECT * FROM read_json('/outside/file.json')",
        "SELECT * FROM read_parquet('/outside/file.parquet')",
        "SELECT * FROM read_text('/outside/file.txt')",
        "SELECT * FROM read_blob('/outside/file.bin')",
        "SELECT * FROM glob('/outside/*')",
        "SELECT * FROM read_csv_auto('https://example.com/data.csv')",
        "SELECT * FROM read_csv_auto('s3://bucket/data.csv')",
    ],
)
def test_duckdb_workspace_rejects_file_functions_network_and_outside_paths(query: str) -> None:
    workspace = DuckDbWorkspace()
    try:
        with pytest.raises(ValueError, match="external file, network, and extension"):
            workspace.query_df(query)
    finally:
        workspace.close()


@pytest.mark.parametrize("query", FORBIDDEN_OPERATIONS)
def test_duckdb_workspace_rejects_policy_cases(query: str) -> None:
    workspace = DuckDbWorkspace()
    try:
        with pytest.raises(ValueError):
            workspace.query_df(query)
    finally:
        workspace.close()


@pytest.mark.asyncio
async def test_internal_duckdb_loader_applies_policy_on_read_and_scalar_paths() -> None:
    workspace = DuckDbWorkspace()
    try:
        store = TableStore()
        loader = DuckDbLoader(data_source=None, workspace=workspace, table_store=store)

        for method in (loader.read_sql, loader.execute_scalar_sql):
            with pytest.raises(ValueError):
                await method("SELECT 1; SELECT 2")
    finally:
        workspace.close()
