"""Test data builders for creating minimal test fixtures.

These builder functions create minimal, focused test data instead of loading
large CSV fixtures. Use these for unit tests that don't need the full schema.
"""

import pandas as pd
from ingesters.sead.metadata import Column, MockSchemaService, SeadSchema, SeadSchemaFactory, Table


def build_column(
    table_name: str = "tbl_test",
    column_name: str = "col1",
    data_type: str = "integer",
    is_pk: bool = False,
    is_fk: bool = False,
    fk_table_name: str | None = None,
    fk_column_name: str | None = None,
    is_nullable: bool = False,
    **kwargs,
) -> Column:
    """Factory for creating test Column objects with sensible defaults."""
    defaults = {
        "table_name": table_name,
        "column_name": column_name,
        "data_type": data_type,
        "xml_column_name": column_name,
        "position": 1,
        "is_pk": is_pk,
        "is_fk": is_fk,
        "is_nullable": is_nullable,
        "fk_table_name": fk_table_name,
        "fk_column_name": fk_column_name,
        "class_name": f"Tbl{table_name.replace('tbl_', '').title()}",
        "numeric_precision": 10 if "int" in data_type else None,
        "numeric_scale": 0 if "int" in data_type else None,
        "character_maximum_length": 255 if "varchar" in data_type or "text" in data_type else None,
    }
    return Column(**(defaults | kwargs))


def build_table(
    table_name: str = "tbl_test",
    pk_name: str = "test_id",
    is_lookup: bool = False,
    columns: dict[str, Column] | None = None,
    **kwargs,
) -> Table:
    """Factory for creating test Table objects with sensible defaults."""
    if columns is None:
        # Default: one PK column
        columns = {pk_name: build_column(table_name=table_name, column_name=pk_name, is_pk=True)}

    defaults = {
        "table_name": table_name,
        "pk_name": pk_name,
        "java_class": f"Tbl{table_name.replace('tbl_', '').title()}",
        "excel_sheet": table_name,
        "is_lookup": is_lookup,
        "is_unknown": False,
        "is_new": False,
        "columns": columns,
    }
    return Table(**(defaults | kwargs))


def build_schema(
    tables: list[Table] | None = None,
    extra_columns: list[Column] | None = None,
) -> SeadSchema:
    """Factory for creating minimal SeadSchema with just the tables you need.

    Args:
        tables: List of Table objects. If None, creates one default table.
        extra_columns: Additional columns beyond what's in the tables.

    Returns:
        SeadSchema instance ready for testing

    Example:
        >>> schema = build_schema([
        ...     build_table("tbl_sites", "site_id"),
        ...     build_table("tbl_samples", "sample_id", columns={
        ...         "sample_id": build_column("tbl_samples", "sample_id", is_pk=True),
        ...         "site_id": build_column("tbl_samples", "site_id", is_fk=True, fk_table_name="tbl_sites")
        ...     })
        ... ])
    """
    if tables is None:
        tables = [build_table()]

    # Convert tables to DataFrames for MockSchemaService
    tables_data = pd.DataFrame(
        [
            {
                "table_name": t.table_name,
                "pk_name": t.pk_name,
                "java_class": t.java_class,
                "excel_sheet": t.excel_sheet,
                "is_lookup": t.is_lookup,
                "is_unknown": t.is_unknown,
            }
            for t in tables
        ]
    )

    # Collect all columns from all tables
    all_columns = []
    for table in tables:
        for col in table.columns.values():
            all_columns.append(
                {
                    "table_name": col.table_name,
                    "column_name": col.column_name,
                    "data_type": col.data_type,
                    "xml_column_name": col.xml_column_name,
                    "position": col.position,
                    "is_pk": col.is_pk,
                    "is_fk": col.is_fk,
                    "is_nullable": col.is_nullable,
                    "fk_table_name": col.fk_table_name,
                    "fk_column_name": col.fk_column_name,
                    "class_name": col.class_name,
                    "numeric_precision": col.numeric_precision,
                    "numeric_scale": col.numeric_scale,
                    "character_maximum_length": col.character_maximum_length,
                }
            )

    if extra_columns:
        for col in extra_columns:
            all_columns.append(
                {
                    "table_name": col.table_name,
                    "column_name": col.column_name,
                    "data_type": col.data_type,
                    "xml_column_name": col.xml_column_name,
                    "position": col.position,
                    "is_pk": col.is_pk,
                    "is_fk": col.is_fk,
                    "is_nullable": col.is_nullable,
                    "fk_table_name": col.fk_table_name,
                    "fk_column_name": col.fk_column_name,
                    "class_name": col.class_name,
                    "numeric_precision": col.numeric_precision,
                    "numeric_scale": col.numeric_scale,
                    "character_maximum_length": col.character_maximum_length,
                }
            )

    columns_data = pd.DataFrame(all_columns)

    # Use bare-bones MockSchemaService that doesn't try to resolve config
    service = MockSchemaService.__new__(MockSchemaService)
    service.db_uri = ""
    service.ignore_columns = ["date_updated", "*_uuid", "(*"]
    service._sead_tables = service._load_sead_data(tables_data, ["table_name"], ["table_name"])
    service._sead_columns = service._load_sead_data(columns_data, ["table_name", "column_name"], ["table_name", "position"])

    return SeadSchemaFactory().create(service._sead_tables, service._sead_columns)


def build_two_table_schema() -> SeadSchema:
    """Common pattern: schema with a main table and a lookup table."""
    return build_schema(
        [
            build_table(
                "tbl_main",
                "main_id",
                columns={
                    "main_id": build_column("tbl_main", "main_id", is_pk=True),
                    "lookup_id": build_column("tbl_main", "lookup_id", is_fk=True, fk_table_name="tbl_lookup"),
                    "name": build_column("tbl_main", "name", data_type="varchar"),
                },
            ),
            build_table(
                "tbl_lookup",
                "lookup_id",
                is_lookup=True,
                columns={
                    "lookup_id": build_column("tbl_lookup", "lookup_id", is_pk=True),
                    "value": build_column("tbl_lookup", "value", data_type="varchar"),
                },
            ),
        ]
    )
