"""Tests for metadata edge cases and utilities."""

import pytest

from importer.metadata import Column, Table
from tests.builders import build_column, build_schema, build_table


class TestColumnOperations:
    """Test Column dataclass operations."""

    def test_column_contains(self):
        """Test __contains__ method."""
        col = build_column("tbl_test", "test_col")
        assert "column_name" in col
        assert "nonexistent" not in col

    def test_column_getitem(self):
        """Test __getitem__ method."""
        col = build_column("tbl_test", "test_col", data_type="integer")
        assert col["column_name"] == "test_col"
        assert col["data_type"] == "integer"

    def test_column_keys(self):
        """Test keys() method."""
        col = build_column("tbl_test", "test_col")
        keys = col.keys()
        assert "column_name" in keys
        assert "table_name" in keys
        assert isinstance(keys, list)

    def test_column_values(self):
        """Test values() method."""
        col = build_column("tbl_test", "test_col", data_type="integer")
        values = col.values()
        assert "test_col" in values
        assert "integer" in values
        assert isinstance(values, list)

    def test_column_asdict(self):
        """Test asdict() method."""
        col = build_column("tbl_test", "test_col", data_type="integer")
        col_dict = col.asdict()
        assert isinstance(col_dict, dict)
        assert col_dict["column_name"] == "test_col"
        assert col_dict["data_type"] == "integer"

    def test_column_camel_case_column_name(self):
        """Test camel_case_column_name property."""
        col = build_column("tbl_test", "test_column_name")
        assert col.camel_case_column_name == "testColumnName"


class TestTableOperations:
    """Test Table dataclass operations."""

    def test_table_contains(self):
        """Test __contains__ method for column lookup."""
        table = build_table(
            "tbl_test",
            "test_id",
            columns={
                "test_id": build_column("tbl_test", "test_id", is_pk=True),
                "name": build_column("tbl_test", "name"),
            },
        )
        assert "test_id" in table
        assert "name" in table
        assert "nonexistent" not in table

    def test_table_getitem_single_column(self):
        """Test __getitem__ for single column."""
        table = build_table(
            "tbl_test",
            "test_id",
            columns={
                "test_id": build_column("tbl_test", "test_id", is_pk=True),
            },
        )
        col = table["test_id"]
        assert isinstance(col, Column)
        assert col.column_name == "test_id"

    def test_table_getitem_columns(self):
        """Test __getitem__ for 'columns' key."""
        table = build_table("tbl_test", "test_id")
        columns = table["columns"]
        assert isinstance(columns, dict)

    def test_table_iter(self):
        """Test __iter__ iterates over columns."""
        table = build_table(
            "tbl_test",
            "test_id",
            columns={
                "test_id": build_column("tbl_test", "test_id", is_pk=True),
                "name": build_column("tbl_test", "name"),
            },
        )
        columns = list(table)
        assert len(columns) == 2
        assert all(isinstance(c, Column) for c in columns)

    def test_table_len(self):
        """Test __len__ returns column count."""
        table = build_table(
            "tbl_test",
            "test_id",
            columns={
                "test_id": build_column("tbl_test", "test_id", is_pk=True),
                "name": build_column("tbl_test", "name"),
            },
        )
        assert len(table) == 2

    def test_table_get_column(self):
        """Test get_column() method."""
        table = build_table(
            "tbl_test",
            "test_id",
            columns={
                "test_id": build_column("tbl_test", "test_id", is_pk=True),
            },
        )
        col = table.get_column("test_id")
        assert col is not None
        assert col.column_name == "test_id"

        col = table.get_column("nonexistent")
        assert col is None

    def test_table_column_names(self):
        """Test column_names() method."""
        table = build_table(
            "tbl_test",
            "test_id",
            columns={
                "test_id": build_column("tbl_test", "test_id", is_pk=True),
                "nullable_col": build_column("tbl_test", "nullable_col", is_nullable=True),
            },
        )

        all_names = table.column_names()
        assert "test_id" in all_names
        assert "nullable_col" in all_names

        required_names = table.column_names(skip_nullable=True)
        assert "test_id" in required_names
        assert "nullable_col" not in required_names

    def test_table_nullable_column_names(self):
        """Test nullable_column_names() method."""
        table = build_table(
            "tbl_test",
            "test_id",
            columns={
                "test_id": build_column("tbl_test", "test_id", is_pk=True),
                "nullable_col": build_column("tbl_test", "nullable_col", is_nullable=True),
            },
        )
        nullable = table.nullable_column_names()
        assert "nullable_col" in nullable
        assert "test_id" not in nullable


class TestSeadSchemaOperations:
    """Test SeadSchema operations."""

    def test_schema_getitem(self):
        """Test __getitem__ returns Table."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        table = schema["tbl_test"]
        assert isinstance(table, Table)
        assert table.table_name == "tbl_test"

    def test_schema_iter(self):
        """Test __iter__ iterates over table names."""
        schema = build_schema(
            [
                build_table("tbl_test1", "test1_id"),
                build_table("tbl_test2", "test2_id"),
            ]
        )
        table_names = list(schema)
        assert "tbl_test1" in table_names
        assert "tbl_test2" in table_names

    def test_schema_len(self):
        """Test __len__ returns table count."""
        schema = build_schema(
            [
                build_table("tbl_test1", "test1_id"),
                build_table("tbl_test2", "test2_id"),
            ]
        )
        assert len(schema) == 2

    def test_schema_contains(self):
        """Test __contains__ checks table existence."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        assert "tbl_test" in schema
        assert "tbl_nonexistent" not in schema

    def test_schema_keys(self):
        """Test keys() method."""
        schema = build_schema(
            [
                build_table("tbl_test1", "test1_id"),
                build_table("tbl_test2", "test2_id"),
            ]
        )
        keys = schema.keys()
        assert "tbl_test1" in keys
        assert "tbl_test2" in keys

    def test_schema_values(self):
        """Test values() method."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        values = list(schema.values())
        assert len(values) == 1
        assert isinstance(values[0], Table)

    def test_schema_items(self):
        """Test items() method."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        items = list(schema.items())
        assert len(items) == 1
        assert items[0][0] == "tbl_test"
        assert isinstance(items[0][1], Table)

    def test_schema_get(self):
        """Test get() method with default."""
        schema = build_schema([build_table("tbl_test", "test_id")])

        table = schema.get("tbl_test")
        assert table is not None
        assert table.table_name == "tbl_test"

        table = schema.get("tbl_nonexistent")
        assert table is None

        table = schema.get("tbl_nonexistent", default=build_table("default", "id"))
        assert table is not None
        assert table.table_name == "default"

    def test_schema_get_table_by_java_class(self):
        """Test get_table() with java_class alias."""
        schema = build_schema([build_table("tbl_test", "test_id", java_class="TblTest")])

        # Should work with table_name
        table = schema.get_table("tbl_test")
        assert table.table_name == "tbl_test"

        # Should also work with java_class
        table = schema.get_table("TblTest")
        assert table.table_name == "tbl_test"

    def test_schema_get_table_by_excel_sheet(self):
        """Test get_table() with excel_sheet alias."""
        schema = build_schema([build_table("tbl_test", "test_id", excel_sheet="TestSheet")])

        # Should work with excel_sheet alias
        table = schema.get_table("TestSheet")
        assert table.table_name == "tbl_test"

    def test_schema_get_table_not_found(self):
        """Test get_table() raises KeyError when not found."""
        schema = build_schema([build_table("tbl_test", "test_id")])

        with pytest.raises(KeyError, match="tbl_nonexistent"):
            schema.get_table("tbl_nonexistent")

    def test_schema_get_column(self):
        """Test get_column() method."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True),
                    },
                )
            ]
        )

        col = schema.get_column("tbl_test", "test_id")
        assert col.column_name == "test_id"
        assert col.is_pk is True

    def test_schema_get_column_not_found(self):
        """Test get_column() raises KeyError when column not found."""
        schema = build_schema([build_table("tbl_test", "test_id")])

        with pytest.raises(KeyError, match="nonexistent"):
            schema.get_column("tbl_test", "nonexistent")

    def test_schema_lookup_tables(self):
        """Test lookup_tables cached property."""
        schema = build_schema(
            [
                build_table("tbl_main", "main_id", is_lookup=False),
                build_table("tbl_lookup", "lookup_id", is_lookup=True),
            ]
        )

        lookup_tables = schema.lookup_tables
        assert len(lookup_tables) == 1
        assert lookup_tables[0].table_name == "tbl_lookup"

    def test_schema_aliased_tables(self):
        """Test aliased_tables cached property."""
        schema = build_schema(
            [
                build_table("tbl_test1", "test1_id", excel_sheet="tbl_test1"),  # Not aliased
                build_table("tbl_test2", "test2_id", excel_sheet="TestSheet2"),  # Aliased
            ]
        )

        aliased = schema.aliased_tables
        assert len(aliased) == 1
        assert aliased[0].table_name == "tbl_test2"

    def test_schema_table_name2excel_sheet(self):
        """Test table_name2excel_sheet mapping."""
        schema = build_schema(
            [
                build_table("tbl_test", "test_id", excel_sheet="TestSheet"),
            ]
        )

        mapping = schema.table_name2excel_sheet
        assert mapping["tbl_test"] == "TestSheet"

    def test_schema_foreign_key_aliases(self):
        """Test foreign_key_aliases attribute."""
        schema = build_schema()
        assert "updated_dataset_id" in schema.foreign_key_aliases
        assert schema.foreign_key_aliases["updated_dataset_id"] == "dataset_id"
