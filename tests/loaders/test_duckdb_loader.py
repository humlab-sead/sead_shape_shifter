"""
Tests for DuckDbWorkspace and DuckDbLoader.
"""

from __future__ import annotations

from typing import Generator

import pandas as pd
import pytest

from src.loaders.base_loader import DataLoaders, LoaderType
from src.loaders.duckdb_loader import DuckDbLoader, DuckDbWorkspace
from src.model import TableConfig
from src.table_store import TableStore

# pylint: disable=redefined-outer-name


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace() -> Generator[DuckDbWorkspace, None, None]:
    ws = DuckDbWorkspace(database=":memory:")
    yield ws
    ws.close()


@pytest.fixture
def site_df() -> pd.DataFrame:
    return pd.DataFrame({"system_id": [1, 2, 3], "site_name": ["Alpha", "Beta", "Gamma"]})


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({"system_id": [10, 11, 12], "site_id": [1, 1, 2], "sample_name": ["S1", "S2", "S3"]})


@pytest.fixture
def table_store(site_df: pd.DataFrame, sample_df: pd.DataFrame) -> TableStore:
    store = TableStore()
    store["site"] = site_df
    store["sample"] = sample_df
    return store


@pytest.fixture
def loader(workspace: DuckDbWorkspace, table_store: TableStore) -> DuckDbLoader:
    return DuckDbLoader(data_source=None, workspace=workspace, table_store=table_store)


# ---------------------------------------------------------------------------
# TestDuckDbWorkspace
# ---------------------------------------------------------------------------


class TestDuckDbWorkspace:
    """Tests for DuckDbWorkspace registration and querying."""

    def test_register_entity_makes_it_queryable(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        result = workspace.query_df("SELECT * FROM site ORDER BY system_id")
        assert list(result["site_name"]) == ["Alpha", "Beta", "Gamma"]

    def test_register_entity_tracks_registration(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        assert "site" in workspace.list_registered()

    def test_register_entity_skips_unchanged_object(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        """Re-registering the same DataFrame object should be a no-op after flush."""
        workspace.register_entity("site", site_df)
        workspace.flush()
        first_id = workspace._registered_object_ids["site"]

        workspace.register_entity("site", site_df)  # same object — flush should skip re-registration
        workspace.flush()
        assert workspace._registered_object_ids["site"] == first_id

    def test_register_entity_replaces_when_object_changes(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)

        new_df = pd.DataFrame({"system_id": [99], "site_name": ["New"]})
        workspace.register_entity("site", new_df)

        result = workspace.query_df("SELECT site_name FROM site")
        assert list(result["site_name"]) == ["New"]

    def test_unregister_entity_removes_view(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        workspace.unregister_entity("site")

        assert "site" not in workspace.list_registered()
        with pytest.raises(Exception):
            workspace.query_df("SELECT * FROM site")

    def test_unregister_entity_is_idempotent(self, workspace: DuckDbWorkspace) -> None:
        """Unregistering a name that was never registered should not raise."""
        workspace.unregister_entity("nonexistent")  # should not raise

    def test_register_many_registers_all(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame, sample_df: pd.DataFrame) -> None:
        tables = {"site": site_df, "sample": sample_df}
        workspace.register_many(tables)
        assert set(workspace.list_registered()) == {"site", "sample"}

    def test_register_many_with_only_subset(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame, sample_df: pd.DataFrame) -> None:
        tables = {"site": site_df, "sample": sample_df}
        workspace.register_many(tables, only=["site"])
        assert workspace.list_registered() == ["site"]

    def test_register_many_raises_for_missing_name(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            workspace.register_many({"site": site_df}, only=["nonexistent"])

    def test_query_df_returns_dataframe(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        result = workspace.query_df("SELECT COUNT(*) AS n FROM site")
        assert isinstance(result, pd.DataFrame)
        assert result["n"].iloc[0] == 3

    def test_query_scalar_returns_single_value(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        result = workspace.query_scalar("SELECT COUNT(*) FROM site")
        assert result == 3

    def test_query_scalar_returns_none_for_empty_result(self, workspace: DuckDbWorkspace) -> None:
        result = workspace.query_scalar("SELECT NULL WHERE FALSE")
        assert result is None

    def test_list_registered_returns_sorted(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame, sample_df: pd.DataFrame) -> None:
        workspace.register_entity("sample", sample_df)
        workspace.register_entity("site", site_df)
        assert workspace.list_registered() == ["sample", "site"]


# ---------------------------------------------------------------------------
# TestDuckDbWorkspaceTableStoreHooks
# ---------------------------------------------------------------------------


class TestDuckDbWorkspaceTableStoreHooks:
    """Verify that TableStore hooks keep the workspace in sync automatically."""

    def test_on_set_hook_registers_entity(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        store = TableStore()
        store.add_on_set_hook(workspace.register_entity, replay=False)

        store["site"] = site_df
        assert "site" in workspace.list_registered()

    def test_on_set_hook_replays_existing_entries(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        store = TableStore()
        store["site"] = site_df  # added before hook

        store.add_on_set_hook(workspace.register_entity, replay=True)
        assert "site" in workspace.list_registered()

    def test_on_delete_hook_unregisters_entity(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        store = TableStore()
        store.add_on_set_hook(workspace.register_entity, replay=False)
        store.add_on_delete_hook(workspace.unregister_entity)

        store["site"] = site_df
        del store["site"]

        assert "site" not in workspace.list_registered()

    def test_workspace_sees_updated_data_after_reassignment(self, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        store = TableStore()
        store.add_on_set_hook(workspace.register_entity, replay=False)
        store["site"] = site_df

        new_df = pd.DataFrame({"system_id": [99], "site_name": ["Updated"]})
        store["site"] = new_df  # triggers hook with new object

        result = workspace.query_df("SELECT site_name FROM site")
        assert result["site_name"].iloc[0] == "Updated"


# ---------------------------------------------------------------------------
# TestDuckDbLoaderCreate
# ---------------------------------------------------------------------------


class TestDuckDbLoaderCreate:
    """Tests for the DuckDbLoader.create() factory classmethod."""

    def test_create_returns_duckdb_loader(self, workspace: DuckDbWorkspace, table_store: TableStore) -> None:
        loader = DuckDbLoader.create(
            data_source=None,
            workspace=workspace,
            table_store=table_store,
        )
        assert isinstance(loader, DuckDbLoader)

    def test_create_wires_workspace_and_table_store(self, workspace: DuckDbWorkspace, table_store: TableStore) -> None:
        loader = DuckDbLoader.create(
            data_source=None,
            workspace=workspace,
            table_store=table_store,
        )
        assert loader.workspace is workspace
        assert loader.table_store is table_store

    def test_create_raises_on_missing_context_key(self, workspace: DuckDbWorkspace) -> None:
        with pytest.raises(KeyError):
            DuckDbLoader.create(data_source=None, workspace=workspace)  # missing table_store

    def test_create_is_registered_and_accessible_via_registry(self) -> None:
        loader_cls = DataLoaders.get(key="duckdb")
        assert loader_cls is DuckDbLoader

    def test_create_via_registry_key_internal(self) -> None:
        assert DataLoaders.get(key="internal") is DuckDbLoader

    def test_loader_type_is_sql(self) -> None:
        assert DuckDbLoader.loader_type() == LoaderType.SQL


# ---------------------------------------------------------------------------
# TestDuckDbLoaderReadSql
# ---------------------------------------------------------------------------


class TestDuckDbLoaderReadSql:
    """Tests for DuckDbLoader.read_sql and execute_scalar_sql."""

    @pytest.mark.asyncio
    async def test_read_sql_returns_dataframe(self, loader: DuckDbLoader, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        result = await loader.read_sql("SELECT * FROM site")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_execute_scalar_sql_returns_count(self, loader: DuckDbLoader, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        result = await loader.execute_scalar_sql("SELECT COUNT(*) FROM site")
        assert result == 3

    def test_create_db_uri(self, loader: DuckDbLoader) -> None:
        assert loader.create_db_uri() == "duckdb://internal"

    def test_get_test_query(self, loader: DuckDbLoader) -> None:
        query = loader.get_test_query("site", 5)
        assert "site" in query
        assert "5" in query


# ---------------------------------------------------------------------------
# TestDuckDbLoaderLoad
# ---------------------------------------------------------------------------


class TestDuckDbLoaderLoad:
    """Tests for DuckDbLoader.load() — the main entity loading path."""

    def _make_table_cfg(self, query: str, columns: list[str] | None = None, **overrides) -> TableConfig:
        entity_cfg: dict = {"type": "sql", "data_source": "@internal", "query": query}
        if columns:
            entity_cfg["columns"] = columns
        entity_cfg.update(overrides)
        return TableConfig(entities_cfg={"derived": entity_cfg}, entity_name="derived")

    @pytest.mark.asyncio
    async def test_load_returns_dataframe_from_sql(self, loader: DuckDbLoader, workspace: DuckDbWorkspace, site_df: pd.DataFrame) -> None:
        workspace.register_entity("site", site_df)
        table_cfg = self._make_table_cfg("SELECT system_id, site_name FROM site")

        result = await loader.load("derived", table_cfg)

        assert isinstance(result, pd.DataFrame)
        assert set(result.columns).issuperset({"system_id", "site_name"})

    @pytest.mark.asyncio
    async def test_load_raises_when_query_is_missing(self, loader: DuckDbLoader) -> None:
        table_cfg = TableConfig(entities_cfg={"derived": {"type": "sql", "data_source": "@internal"}}, entity_name="derived")

        with pytest.raises(ValueError, match="no query"):
            await loader.load("derived", table_cfg)

    @pytest.mark.asyncio
    async def test_load_injects_system_id_when_configured(
        self, loader: DuckDbLoader, workspace: DuckDbWorkspace, site_df: pd.DataFrame
    ) -> None:
        workspace.register_entity("site", site_df)
        table_cfg = TableConfig(
            entities_cfg={
                "derived": {
                    "type": "sql",
                    "data_source": "@internal",
                    "query": "SELECT site_name FROM site",
                    "system_id": "derived_id",
                    "public_id": "derived_id",
                    "keys": ["site_name"],
                }
            },
            entity_name="derived",
        )

        result = await loader.load("derived", table_cfg)
        assert "derived_id" in result.columns

    @pytest.mark.asyncio
    async def test_load_cross_entity_join(
        self,
        loader: DuckDbLoader,
        workspace: DuckDbWorkspace,
        site_df: pd.DataFrame,
        sample_df: pd.DataFrame,
    ) -> None:
        workspace.register_entity("site", site_df)
        workspace.register_entity("sample", sample_df)

        sql = """
            SELECT s.site_name, COUNT(sa.system_id) AS sample_count
            FROM site s
            JOIN sample sa ON sa.site_id = s.system_id
            GROUP BY s.site_name
            ORDER BY s.site_name
        """
        table_cfg = self._make_table_cfg(sql)

        result = await loader.load("derived", table_cfg)

        assert len(result) == 2
        by_name = result.set_index("site_name")["sample_count"].to_dict()
        assert by_name["Alpha"] == 2
        assert by_name["Beta"] == 1


# ---------------------------------------------------------------------------
# TestDuckDbLoaderGetTables
# ---------------------------------------------------------------------------


class TestDuckDbLoaderGetTables:
    """Tests for DuckDbLoader.get_tables() and get_table_schema()."""

    @pytest.mark.asyncio
    async def test_get_tables_lists_all_table_store_entries(self, loader: DuckDbLoader) -> None:
        tables = await loader.get_tables()
        assert set(tables.keys()) == {"site", "sample"}

    @pytest.mark.asyncio
    async def test_get_tables_metadata_contains_row_count(self, loader: DuckDbLoader) -> None:
        tables = await loader.get_tables()
        assert tables["site"].row_count == 3
        assert tables["sample"].row_count == 3

    @pytest.mark.asyncio
    async def test_get_table_schema_returns_column_metadata(self, loader: DuckDbLoader) -> None:
        schema = await loader.get_table_schema("site")
        column_names = [col.name for col in schema.columns]
        assert "system_id" in column_names
        assert "site_name" in column_names

    @pytest.mark.asyncio
    async def test_get_table_schema_raises_for_unknown_entity(self, loader: DuckDbLoader) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            await loader.get_table_schema("nonexistent")
